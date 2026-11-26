"""Teste rapide pentru chunking si pentru salvarea in Chroma.

Ruleaza cu:  python -m pytest -q
Nu au nevoie de internet si nici de modelul de embeddings (folosesc vectori falsi).
"""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.parsing import (  # noqa: E402
    Chunk, clean_markdown, enforce_token_limit, pack_blocks, parse_document, parse_markdown, parse_pdf)

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


# ---------------------------------------------------------------- PDF (stil NIST)

PDF_SOURCE = {"id": "test-pdf", "title": "Test PDF", "collection": "test", "url": "u", "type": "pdf"}
BODY = "Verifiers SHALL compare every new password against a blocklist of common values."


def make_pdf(path, toc=None):
    """PDF mic care imita structura NIST: titluri bold numerotate lipite de paragraf,
    liste, bold la inceput de paragraf, cuprins, tabel rupt, nota de subsol, anexe."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()

    def put(page, y, text, bold=False, size=12, x=72):
        page.insert_text((x, y), text, fontname="hebo" if bold else "helv", fontsize=size)
        return x + pymupdf.get_text_length(text, fontname="hebo" if bold else "helv", fontsize=size)

    front = doc.new_page()                       # preambul
    put(front, 72, "Authority", bold=True)
    put(front, 110, "This publication has been developed by NIST under its statutory duties.")

    page = doc.new_page()
    put(page, 60, "2.4. General Requirements . . . . . . . . . . . . . . 9")   # rand de cuprins
    put(page, 110, "2.3.3. Reauthentication", bold=True)                      # titlu + paragraf
    put(page, 125, "Periodic reauthentication of subscriber sessions SHALL be performed.")
    put(page, 140, BODY)
    put(page, 190, "1. Verifiers SHALL require passwords of at least 15 characters.")  # lista
    x = put(page, 240, "Authentication Assurance Level 1", bold=True)      # bold la inceput
    put(page, 240, " provides some assurance that the claimant controls", x=x + 3)
    put(page, 255, "an authenticator bound to the subscriber account.")
    put(page, 300, "Continued on next page")                                # tabel rupt
    put(page, 340, "Description Mitigations", bold=True)                    # cap de tabel
    put(page, 380, "Leverage hardware security modules to protect the encrypted keys.")
    put(page, 430, "Appendix B. Syncable Authenticators", bold=True)        # anexa
    put(page, 445, BODY)
    put(page, 490, "B.1. Introduction", bold=True)
    put(page, 505, "Syncable authenticators can copy keys between devices of the same user.")
    x = put(page, 700, "2", size=7)                                         # nota de subsol
    put(page, 700, "Federal enterprise systems include government contractors.", size=10, x=x + 1)

    thanks = doc.new_page()
    put(thanks, 72, "Acknowledgments", bold=True)
    put(thanks, 110, "The authors thank the many reviewers for their contributions.")

    if toc:
        doc.set_toc(toc)
    doc.save(path)
    return path


def pdf_sections_and_text(chunks):
    sections = " | ".join(c.section for c in chunks)
    return sections, sections + " " + " ".join(c.text for c in chunks)


def test_pdf_headings_detected_from_bold_font(tmp_path):
    chunks = parse_pdf(make_pdf(tmp_path / "doc.pdf"), PDF_SOURCE)
    sections, everything = pdf_sections_and_text(chunks)
    text = " ".join(c.text for c in chunks)

    assert "2.3.3 Reauthentication" in everything                     # titlu numerotat
    assert "Periodic reauthentication of subscriber sessions" in text  # paragraful ramane
    assert "2.3.3." not in text                                         # titlul nu e lipit in text
    assert "Appendix B Syncable Authenticators > B.1 Introduction" in everything  # anexe + cale
    # listele si textul bold de la inceputul unui paragraf NU sunt titluri
    assert "1 Verifiers" not in sections and "Assurance Level 1" not in sections
    assert "Authentication Assurance Level 1 provides some assurance" in text


def test_pdf_noise_is_removed(tmp_path):
    chunks = parse_pdf(make_pdf(tmp_path / "doc.pdf"), PDF_SOURCE)
    text = " ".join(c.text for c in chunks)

    assert ". . . . ." not in text and "General Requirements" not in text  # cuprinsul
    assert "Continued on next page" not in text                             # tabel rupt
    assert "Federal enterprise systems" not in text                         # nota de subsol
    assert "thank the many reviewers" not in text                           # Acknowledgments sarit


def test_pdf_outline_filters_table_cells_and_front_matter(tmp_path):
    # Cu cuprins intern: "Description Mitigations" (cap de tabel) nu mai e titlu, iar
    # pagina dinaintea primei intrari din cuprins (preambulul) e sarita.
    toc = [[1, "General Requirements", 2], [1, "Acknowledgments", 3]]
    chunks = parse_pdf(make_pdf(tmp_path / "doc.pdf", toc=toc), PDF_SOURCE)
    sections, everything = pdf_sections_and_text(chunks)

    assert "Description Mitigations" not in sections
    assert "[Description Mitigations]" not in everything
    assert "statutory duties" not in everything                             # preambul sarit
    assert "thank the many reviewers" not in everything                     # tot sarit


# ------------------------------------------------------------ limita de tokeni

def fake_token_count(text):
    """Tokenizer fals: 1 cuvant = 3 tokeni (ca la cod), ca sa fortam impartirea fara model."""
    return 3 * len(text.split())


def make_chunk(text, page=None):
    return Chunk("doc", "Doc", "test", "u", "Sec > Sub", text, page)


def test_token_limit_splits_only_long_chunks():
    short = make_chunk("Short text that fits easily. " * 5)
    # paragrafe de lungimi diferite: jumatatea in cuvinte NU cade intamplator intre paragrafe
    long_text = "\n\n".join(f"Paragraph {i}: " + "token " * (20 + 7 * i) for i in range(8))
    long = make_chunk(long_text, page=7)

    out = enforce_token_limit([short, long], fake_token_count, max_tokens=300)

    assert out[0] is short                                                  # neatinsa
    assert len(out) > 2                                                     # cea lunga s-a impartit
    assert all(fake_token_count(c.embedding_text()) <= 300 for c in out)    # toate incap
    assert " ".join(c.text for c in out[1:]).split() == long_text.split()   # nu se pierde nimic
    assert all(c.section == "Sec > Sub" and c.page == 7 for c in out[1:])   # metadate pastrate
    assert all(p.startswith("Paragraph") for c in out[1:] for p in c.text.split("\n\n"))  # taiat intre paragrafe


def test_token_limit_handles_text_without_paragraphs():
    # cod lung pe un singur rand: singura taietura posibila e intre cuvinte
    code = " ".join(f"call_{i}()" for i in range(400))
    out = enforce_token_limit([make_chunk(code)], fake_token_count, max_tokens=200)
    assert all(fake_token_count(c.embedding_text()) <= 200 for c in out)
    assert " ".join(c.text for c in out).split() == code.split()


def test_parse_document_ids_stay_unique_after_split(tmp_path):
    text = "# Doc\n\n## Long section\n\n" + "\n\n".join("sentence " * 50 for _ in range(6))
    chunks = parse_document(write(tmp_path, text), SOURCE, count_tokens=fake_token_count)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)) and ids[0] == "test-doc::000"
    assert all(fake_token_count(c.embedding_text()) <= config.MAX_TOKENS for c in chunks)


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
