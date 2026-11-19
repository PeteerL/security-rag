"""Descarca documentele din config/sources.yaml in data/raw/.

Utilizare:
    python scripts/download_docs.py            # descarca doar ce lipseste
    python scripts/download_docs.py --force    # descarca tot din nou

La final scrie data/raw/manifest.json cu: id, fisier, dimensiune, hash SHA-256
si data descarcarii. Manifestul arata exact ce versiune a documentelor a fost
folosita, ca rezultatele sa poata fi reproduse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
EXTENSIONS = {"markdown": ".md", "pdf": ".pdf", "csv": ".csv"}
USER_AGENT = "security-rag/0.1 (educational project)"


def load_sources() -> list[dict]:
    with open(SOURCES_FILE, encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]
    ids = [s["id"] for s in sources]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        sys.exit(f"ID-uri duplicate in sources.yaml: {sorted(duplicates)}")
    return sources


def download(url: str, retries: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as error:  # retea instabila, rate limit etc.
            if attempt == retries:
                raise
            wait = 2 ** attempt
            print(f"    eroare ({error}), reincerc in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="descarca din nou si fisierele existente")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    manifest, failed = [], []

    for i, source in enumerate(sources, start=1):
        path = RAW_DIR / f"{source['id']}{EXTENSIONS[source['type']]}"
        label = f"[{i:2}/{len(sources)}] {source['id']}"

        if path.exists() and not args.force:
            print(f"{label}: exista deja, sar peste")
        else:
            try:
                data = download(source["url"])
            except Exception as error:
                print(f"{label}: ESUAT ({error})")
                failed.append(source["id"])
                continue
            path.write_bytes(data)
            print(f"{label}: {len(data) / 1024:.0f} KB")

        content = path.read_bytes()
        manifest.append({
            "id": source["id"],
            "title": source["title"],
            "url": source["url"],
            "collection": source["collection"],
            "role": source["role"],
            "file": path.name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "downloaded_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        })

    with open(RAW_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nGata: {len(manifest)} documente in {RAW_DIR}")
    if failed:
        print(f"Esuate ({len(failed)}): {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
