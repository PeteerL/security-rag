"""Citirea documentelor (Markdown si PDF) si impartirea lor in bucati (chunks).

Ideea de baza:
- Markdown: taiem dupa titluri (#, ##, ###...). Fiecare bucata pastreaza "calea"
  titlurilor, de ex. "JSON Web Token Cheat Sheet > Token Sidejacking > Prevention",
  ca LLM-ul si utilizatorul sa stie exact de unde vine textul.
- PDF: nu avem titluri marcate, asa ca taiem dupa dimensiune, cu suprapunere,
  si pastram numarul paginii pentru citare.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src import config


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    collection: str
    url: str
    section: str          # calea titlurilor sau sectiunea din PDF
    text: str
    page: int | None = None
    chunk_id: str = ""
    n_words: int = field(init=False)

    def __post_init__(self) -> None:
        self.n_words = len(self.text.split())

    def embedding_text(self) -> str:
        """Textul care se transforma in vector: titlul documentului si sectiunea
        sunt incluse, ca o bucata scurta sa pastreze contextul."""
        return f"{self.doc_title} > {self.section}\n\n{self.text}"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- curatare text

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_KRAMDOWN_ATTR = re.compile(r"\{:[^}]*\}")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HTML_BLOCK = re.compile(r"<table.*?</table>", re.DOTALL | re.IGNORECASE)
_ASVS_ROW = re.compile(r"^\|\s*\*\*(\d+\.\d+\.\d+)\*\*\s*\|\s*(.+?)\s*\|\s*(\d)\s*\|\s*$")
_TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}")


def clean_markdown(text: str) -> str:
    """Scoate imaginile, atributele de stil si URL-urile linkurilor (pastram textul
    linkului). Randurile de tabel ASVS devin propozitii: 'V6.2.1 (Level 1): ...'."""
    text = _HTML_BLOCK.sub("", text)
    text = html.unescape(text)
    text = _IMAGE.sub("", text)
    text = _KRAMDOWN_ATTR.sub("", text)
    text = _LINK.sub(r"\1", text)

    lines = []
    for line in text.splitlines():
        row = _ASVS_ROW.match(line.strip())
        if row:
            req_id, description, level = row.groups()
            lines.append(f"V{req_id} (Level {level}): {description}")
        elif line.strip().startswith("| # |") or _TABLE_SEPARATOR.match(line.strip()):
            continue  # capul tabelului ASVS si linia |---|
        else:
            lines.append(line.rstrip())
    return "\n".join(lines)


# ------------------------------------------------------------ impartire generica

def split_blocks(text: str) -> list[str]:
    """Imparte textul in paragrafe. Blocurile de cod (```) raman intregi."""
    blocks, current, in_code = [], [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if not line.strip() and not in_code:
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return [b for b in blocks if b.strip()]


def split_long_block(block: str, max_words: int) -> list[str]:
    """Un bloc prea lung se taie intai pe randuri (pastreaza listele si cerintele
    ASVS intregi), apoi pe propozitii si, la nevoie, pe cuvinte."""
    if len(block.split()) <= max_words:
        return [block]
    lines = [line for line in block.splitlines() if line.strip()]
    if len(lines) > 1:
        units, joiner = lines, "\n"
    else:
        units, joiner = re.split(r"(?<=[.!?])\s+", block), " "
    pieces, current, size = [], [], 0
    for unit in units:
        n = len(unit.split())
        if n > max_words:  # o singura unitate prea mare: o taiem mai departe
            if current:
                pieces.append(joiner.join(current))
                current, size = [], 0
            if joiner == "\n":
                pieces.extend(split_long_block(unit, max_words))
            else:
                words = unit.split()
                pieces.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))
            continue
        if current and size + n > max_words:
            pieces.append(joiner.join(current))
            current, size = [], 0
        current.append(unit)
        size += n
    if current:
        pieces.append(joiner.join(current))
    return pieces


def pack_blocks(blocks: list[str], max_words: int) -> list[str]:
    """Pune paragrafe consecutive in aceeasi bucata, pana la max_words. Un bloc
    mare umple intai locul ramas in bucata curenta, ca o introducere scurta
    ("Do the following:") sa ramana langa lista pe care o anunta."""
    chunks, current, size = [], [], 0
    for block in blocks:
        n = len(block.split())
        if size + n <= max_words:
            current.append(block)
            size += n
            continue
        room = max_words - size
        if current and room >= config.MIN_WORDS and n > max_words:
            head, *rest = split_long_block(block, room)
            current.append(head)
            block = "\n".join(rest) if "\n" in block else " ".join(rest)
        if current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        for piece in split_long_block(block, max_words):
            if current and size + len(piece.split()) > max_words:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            current.append(piece)
            size += len(piece.split())
    if current:
        chunks.append("\n\n".join(current))
    return chunks


# ---------------------------------------------------------------------- Markdown

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _normalize_title(title: str) -> str:
    return title.strip().rstrip(".").strip()


def parse_markdown(path: Path, source: dict) -> list[Chunk]:
    text = clean_markdown(path.read_text(encoding="utf-8"))

    sections: list[tuple[list[str], list[str]]] = []  # (calea titlurilor, liniile)
    path_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    in_code = False

    def close_section() -> None:
        titles = [t for _, t in path_stack]
        sections.append((titles, current_lines.copy()))

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        heading = None if in_code else _HEADING.match(line)
        if heading:
            close_section()
            current_lines = []
            level, title = len(heading.group(1)), _normalize_title(heading.group(2))
            while path_stack and path_stack[-1][0] >= level:
                path_stack.pop()
            path_stack.append((level, title))
        else:
            current_lines.append(line)
    close_section()

    chunks: list[Chunk] = []
    for titles, lines in sections:
        if any(skip in t.lower() for t in titles for skip in config.SKIP_SECTIONS):
            continue
        body = "\n".join(lines).strip()
        if not body:
            continue
        # Primul titlu e de obicei chiar numele documentului: il scoatem din cale
        section_titles = titles[1:] if len(titles) > 1 else titles
        section = " > ".join(section_titles) or source["title"]
        for piece in pack_blocks(split_blocks(body), config.MAX_WORDS):
            chunks.append(Chunk(source["id"], source["title"], source["collection"],
                                source["url"], section, piece))
    return merge_small_chunks(chunks)


def merge_small_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Bucatile foarte mici (ex. o sectiune cu o singura propozitie) se lipesc de
    urmatoarea din acelasi document, daca impreuna nu depasesc MAX_WORDS."""
    merged: list[Chunk] = []
    for chunk in chunks:
        previous = merged[-1] if merged else None
        if (previous and previous.doc_id == chunk.doc_id and previous.n_words < config.MIN_WORDS
                and previous.n_words + chunk.n_words <= config.MAX_MERGED_WORDS):
            text = f"{previous.text}\n\n[{chunk.section}]\n{chunk.text}"
            merged[-1] = Chunk(previous.doc_id, previous.doc_title, previous.collection,
                               previous.url, previous.section, text, previous.page)
        else:
            merged.append(chunk)
    return merged


# --------------------------------------------------------------------------- PDF

_SECTION_LINE = re.compile(r"^(\d+(?:\.\d+){0,3})\.?\s+([A-Z][^\n]{2,90})$")
_PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$", re.IGNORECASE)


def parse_pdf(path: Path, source: dict) -> list[Chunk]:
    import pymupdf  # importat aici ca restul proiectului sa mearga si fara el

    with pymupdf.open(path) as pdf:
        pages = [page.get_text("blocks") for page in pdf]

    # Antetele si subsolurile se repeta pe multe pagini: le gasim si le scoatem
    def first_line(block) -> str:
        return block[4].strip().splitlines()[0].strip() if block[4].strip() else ""

    line_counts = Counter(first_line(b) for blocks in pages for b in blocks)
    repeated = {line for line, n in line_counts.items() if line and n >= max(3, len(pages) * 0.3)}

    paragraphs: list[tuple[int, str, str]] = []  # (pagina, sectiune, text)
    section = source["title"]
    for page_number, blocks in enumerate(pages, start=1):
        for block in blocks:
            text = " ".join(block[4].split())  # uneste randurile rupte
            if not text or _PAGE_NUMBER.match(text) or first_line(block) in repeated:
                continue
            match = _SECTION_LINE.match(text)
            if match and len(text.split()) <= 12:
                section = f"{match.group(1)} {match.group(2)}"
                continue
            paragraphs.append((page_number, section, text))

    # Impachetam paragrafele pe sectiuni, cu o mica suprapunere intre bucati
    chunks: list[Chunk] = []
    current: list[tuple[int, str]] = []
    current_section = None

    def flush() -> None:
        if current:
            text = "\n\n".join(t for _, t in current)
            chunks.append(Chunk(source["id"], source["title"], source["collection"], source["url"],
                                current_section, text, page=current[0][0]))

    for page_number, sec, text in paragraphs:
        for piece in split_long_block(text, config.MAX_WORDS):
            size = sum(len(t.split()) for _, t in current)
            if current and (sec != current_section or size + len(piece.split()) > config.MAX_WORDS):
                flush()
                same_section = sec == current_section
                tail = current[-1] if (same_section and len(current[-1][1].split()) <= config.PDF_OVERLAP_WORDS) else None
                current = [tail] if tail else []
            current_section = sec
            current.append((page_number, piece))
    flush()
    return merge_small_chunks(chunks)


# ----------------------------------------------------------------------- general

def parse_document(path: Path, source: dict) -> list[Chunk]:
    if source["type"] == "markdown":
        chunks = parse_markdown(path, source)
    elif source["type"] == "pdf":
        chunks = parse_pdf(path, source)
    else:
        raise ValueError(f"Tip necunoscut pentru RAG: {source['type']}")
    for i, chunk in enumerate(chunks):
        chunk.chunk_id = f"{source['id']}::{i:03d}"
    return chunks
