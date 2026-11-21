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


def build_chunks() -> list:
    all_chunks, missing = [], []
    for source in load_rag_sources():
        path = config.RAW_DIR / f"{source['id']}{EXTENSIONS[source['type']]}"
        if not path.exists():
            missing.append(source["id"])
            continue
        all_chunks.extend(parse_document(path, source))
    if missing:
        print(f"ATENTIE: lipsesc {len(missing)} documente (ruleaza download_docs.py): {', '.join(missing)}")
    return all_chunks


def print_stats(chunks: list) -> None:
    sizes = [c.n_words for c in chunks]
    print(f"\nBucati: {len(chunks)} din {len({c.doc_id for c in chunks})} documente")
    print(f"Cuvinte pe bucata: min {min(sizes)}, mediana {statistics.median(sizes):.0f}, max {max(sizes)}")
    print(f"Sub {config.MIN_WORDS} cuvinte: {sum(s < config.MIN_WORDS for s in sizes)}   "
          f"peste {config.MAX_WORDS}: {sum(s > config.MAX_WORDS for s in sizes)}")
    print("Pe colectii:", dict(Counter(c.collection for c in chunks)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="doar chunking, fara embeddings")
    args = parser.parse_args()

    chunks = build_chunks()
    if not chunks:
        sys.exit("Nu am gasit niciun document. Ruleaza intai: python scripts/download_docs.py")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.CHUNKS_FILE, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    print_stats(chunks)
    print(f"Bucatile sunt salvate in {config.CHUNKS_FILE}")

    if args.dry_run:
        return

    from src.embeddings import Embedder
    from src.vectorstore import add_chunks, get_collection

    start = time.time()
    print(f"\nIncarc modelul de embeddings {config.EMBEDDING_MODEL} (prima data il descarca)...")
    embedder = Embedder()
    vectors = embedder.embed_documents([c.embedding_text() for c in chunks])

    collection = get_collection(reset=True)
    add_chunks(collection, chunks, vectors)
    print(f"\nIndex construit: {collection.count()} bucati in {config.CHROMA_DIR} "
          f"({time.time() - start:.0f} secunde)")


if __name__ == "__main__":
    main()
