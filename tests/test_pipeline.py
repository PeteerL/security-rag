"""Teste rapide pentru chunking si pentru salvarea in Chroma.

Ruleaza cu:  python -m pytest -q
Nu au nevoie de internet si nici de modelul de embeddings (folosesc vectori falsi).
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.parsing import clean_markdown, pack_blocks, parse_markdown  # noqa: E402

SOURCE = {"id": "test-doc", "title": "Test Cheat Sheet", "collection": "test", "url": "u", "type": "markdown"}

MARKDOWN = """# Test Cheat Sheet

## Introduction

Intro text with a [link](https://example.com) and an image ![img](a.png).

## Password Storage

### Hashing

Use a slow hashing function for passwords.

```python
# a heading-like comment inside code must not become a section
hash = argon2(password)
```

## References

- https://example.com
"""


def write(tmp_path, text):
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_sections_and_cleaning(tmp_path):
    chunks = parse_markdown(write(tmp_path, MARKDOWN), SOURCE)
    sections = [c.section for c in chunks]
    all_text = " ".join(c.text for c in chunks)
    # sectiunile mici sunt lipite intr-o bucata, dar titlul lor ramane in text
    assert "Password Storage > Hashing" in " ".join(sections) + all_text
    assert "https://example.com" not in all_text          # linkuri curatate, References sarit
    assert "![img]" not in all_text                        # imagini scoase
    assert "hash = argon2(password)" in all_text           # codul ramane
    assert not any("a heading-like comment" in s for s in sections)


def test_asvs_rows_become_sentences():
    row = "| **6.2.1** | Verify that passwords are at least 8 characters. | 1 |"
    assert clean_markdown(row).strip() == "V6.2.1 (Level 1): Verify that passwords are at least 8 characters."


def test_chunks_respect_size_limit():
    blocks = [" ".join(["word"] * 120) for _ in range(10)]
    chunks = pack_blocks(blocks, config.MAX_WORDS)
    assert all(len(c.split()) <= config.MAX_WORDS for c in chunks)
    assert sum(len(c.split()) for c in chunks) == 1200     # nu se pierde text


def test_short_intro_stays_with_list():
    intro = "Do the following, at a minimum:"
    big_list = "\n".join(f"* item number {i} " + "word " * 20 for i in range(30))
    first = pack_blocks([intro, big_list], config.MAX_WORDS)[0]
    assert first.startswith(intro) and "* item number 0" in first


def fake_vector(text, dim=16):
    digest = hashlib.sha256(text.encode()).digest()
    return [b / 255 for b in digest[:dim]]


def test_chroma_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "chroma")
    from src.vectorstore import add_chunks, get_collection, search

    chunks = parse_markdown(write(tmp_path, MARKDOWN), SOURCE)
    for i, c in enumerate(chunks):
        c.chunk_id = f"test::{i}"
    collection = get_collection(reset=True)
    add_chunks(collection, chunks, [fake_vector(c.embedding_text()) for c in chunks])
    assert collection.count() == len(chunks)

    hit = search(collection, fake_vector(chunks[0].embedding_text()), k=1)[0]
    assert hit["chunk_id"] == chunks[0].chunk_id and hit["score"] > 0.99
