"""Testeaza cautarea: scrii o intrebare si vezi cele mai apropiate bucati.

Utilizare:
    python scripts/search.py "How should passwords be stored?"
    python scripts/search.py "How should passwords be stored?" -k 10
    python scripts/search.py            # mod interactiv, iesi cu Enter gol
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embeddings import Embedder  # noqa: E402
from src.vectorstore import get_collection, search  # noqa: E402


def show(question: str, embedder: Embedder, collection, k: int) -> None:
    hits = search(collection, embedder.embed_query(question), k=k)
    print(f"\nIntrebare: {question}\n" + "=" * 80)
    for rank, hit in enumerate(hits, start=1):
        page = f", pagina {hit['page']}" if hit["page"] != -1 else ""
        print(f"\n[{rank}] scor {hit['score']:.3f} | {hit['doc_title']}{page}")
        print(f"    sectiune: {hit['section']}")
        preview = textwrap.shorten(hit["text"], width=300, placeholder=" ...")
        print(textwrap.indent(textwrap.fill(preview, width=76), "    "))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="intrebarea (fara ea porneste modul interactiv)")
    parser.add_argument("-k", type=int, default=5, help="cate bucati sa afiseze")
    args = parser.parse_args()

    collection = get_collection()
    if collection.count() == 0:
        sys.exit("Indexul e gol. Ruleaza intai: python scripts/ingest.py")
    embedder = Embedder()

    if args.question:
        show(args.question, embedder, collection, args.k)
        return
    while True:
        question = input("\nIntrebare (Enter gol ca sa iesi): ").strip()
        if not question:
            break
        show(question, embedder, collection, args.k)


if __name__ == "__main__":
    main()
