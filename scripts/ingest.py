"""Faza 1: documente -> bucati -> embeddings -> Chroma.

Utilizare:
    python scripts/ingest.py --dry-run   # doar citire si chunking + statistici (rapid)
    python scripts/ingest.py             # tot pipeline-ul, reconstruieste indexul de la zero

Bucatile se salveaza si in data/processed/chunks.jsonl, ca sa le poti citi si verifica.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from src import config  # noqa: E402
from src.parsing import parse_document  # noqa: E402

EXTENSIONS = {"markdown": ".md", "pdf": ".pdf"}


def load_rag_sources() -> list[dict]:
    with open(config.SOURCES_FILE, encoding="utf-8") as f:
        return [s for s in yaml.safe_load(f)["sources"] if s["role"] == "rag"]


def load_token_counter():
    """Numara tokenii exact ca modelul de embeddings. Incarca doar tokenizer-ul (cateva MB),
    nu si modelul, ca --dry-run sa ramana rapid."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config.EMBEDDING_MODEL)
    # verbose=False: fara avertismentul "sequence length is longer than..." (stim, de-aia numaram)
    return lambda text: len(tokenizer(text, add_special_tokens=True, verbose=False)["input_ids"])


def build_chunks(count_tokens=None) -> list:
    all_chunks, missing = [], []
    for source in load_rag_sources():
        path = config.RAW_DIR / f"{source['id']}{EXTENSIONS[source['type']]}"
        if not path.exists():
            missing.append(source["id"])
            continue
        all_chunks.extend(parse_document(path, source, count_tokens))
    if missing:
        print(f"ATENTIE: lipsesc {len(missing)} documente (ruleaza download_docs.py): {', '.join(missing)}")
    return all_chunks


def print_stats(chunks: list, count_tokens=None) -> None:
    sizes = [c.n_words for c in chunks]
    print(f"\nBucati: {len(chunks)} din {len({c.doc_id for c in chunks})} documente")
    print(f"Cuvinte pe bucata: min {min(sizes)}, mediana {statistics.median(sizes):.0f}, max {max(sizes)}")
    print(f"Sub {config.MIN_WORDS} cuvinte: {sum(s < config.MIN_WORDS for s in sizes)}   "
          f"peste {config.MAX_WORDS}: {sum(s > config.MAX_WORDS for s in sizes)}")
    if count_tokens is not None:
        tokens = [count_tokens(c.embedding_text()) for c in chunks]
        print(f"Tokeni pe bucata (cu titlu si sectiune): mediana {statistics.median(tokens):.0f}, "
              f"max {max(tokens)}, peste limita de {config.MAX_TOKENS}: "
              f"{sum(t > config.MAX_TOKENS for t in tokens)}")
    print("Pe colectii:", dict(Counter(c.collection for c in chunks)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="doar chunking, fara embeddings")
    args = parser.parse_args()

    count_tokens = load_token_counter()
    chunks = build_chunks(count_tokens)
    if not chunks:
        sys.exit("Nu am gasit niciun document. Ruleaza intai: python scripts/download_docs.py")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.CHUNKS_FILE, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    print_stats(chunks, count_tokens)
    print(f"Bucatile sunt salvate in {config.CHUNKS_FILE}")

    if args.dry_run:
        return

    from src.embeddings import Embedder
    from src.vectorstore import add_chunks, get_collection

    start = time.time()
    print(f"\nIncarc modelul de embeddings {config.EMBEDDING_MODEL} (prima data il descarca)...")
    embedder = Embedder()
    if embedder.model.max_seq_length != config.MAX_TOKENS:
        sys.exit(f"Modelul taie textul la {embedder.model.max_seq_length} tokeni, dar "
                 f"config.MAX_TOKENS = {config.MAX_TOKENS}. Pune aceeasi valoare in config.")
    vectors = embedder.embed_documents([c.embedding_text() for c in chunks])

    collection = get_collection(reset=True)
    add_chunks(collection, chunks, vectors)
    print(f"\nIndex construit: {collection.count()} bucati in {config.CHROMA_DIR} "
          f"({time.time() - start:.0f} secunde)")


if __name__ == "__main__":
    main()
