"""Citirea documentelor (Markdown si PDF) si impartirea lor in bucati (chunks).

Ideea de baza:
- Markdown: taiem dupa titluri (#, ##, ###...). Fiecare bucata pastreaza "calea"
  titlurilor, de ex. "JSON Web Token Cheat Sheet > Token Sidejacking > Prevention",
  ca LLM-ul si utilizatorul sa stie exact de unde vine textul.
- PDF: titlurile le recunoastem dupa font (bold, la inceputul blocului, cu numerotare
  ca "3.1.1.2." sau "B.1."), apoi taiem dupa dimensiune, cu suprapunere, si pastram
  numarul paginii pentru citare. Scoatem antetele, subsolurile, cuprinsul si notele.
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

_PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$", re.IGNORECASE)
_DOT_LEADER = re.compile(r"(?:\.\s?){5,}")  # randuri de cuprins: "2.4. General Requirements . . . . 9"
_PDF_NUMBERED_HEADING = re.compile(
    r"^(?:Appendix\s+(?P<appendix>[A-Z])|(?P<number>\d+(?:\.\d+)*|[A-Z](?:\.\d+)+))\.\s+(?P<title>\S.*)$")
_BOLD = 16  # bitul pentru bold din span["flags"] (PyMuPDF)

Part = tuple[str, bool, float]  # (text, e bold?, marimea fontului)


def _block_parts(block: dict) -> list[Part]:
    """Bucatile de text ale unui bloc PDF, cu fontul lor. Intre randuri punem un spatiu;
    intre doua bucati de pe acelasi rand doar daca exista un gol vizibil intre ele."""
    parts: list[Part] = []
    for line in block.get("lines", []):
        previous = None
        for span in line["spans"]:
            text = span["text"]
            if (previous is None and parts) or (previous and span["bbox"][0] - previous["bbox"][2] > 1):
                text = " " + text
            parts.append((text, bool(span["flags"] & _BOLD), span["size"]))
            previous = span
    return parts


def _join(parts: list[Part]) -> str:
    return " ".join("".join(text for text, _, _ in parts).split())


def _body_font_size(pages: list[list[dict]]) -> float:
    """Marimea fontului textului obisnuit = cea mai folosita marime din document."""
    sizes: Counter = Counter()
    for blocks in pages:
        for block in blocks:
            for text, _, size in _block_parts(block):
                sizes[round(size, 1)] += len(text.strip())
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _is_footnote(parts: list[Part], body_size: float) -> bool:
    """Nota de subsol: incepe cu un numar mic (exponent), urmat de text mai mic decat
    textul obisnuit. Ex. in NIST: '2' (7.4pt) + 'Federal enterprise systems...' (10pt)."""
    visible = [p for p in parts if p[0].strip()]
    return (len(visible) > 1 and visible[0][0].strip().isdigit()
            and visible[0][2] < body_size * 0.75
            and max(size for _, _, size in visible[1:]) < body_size - 0.5)


def _split_heading(parts: list[Part], body_size: float,
                   outline: set[str] | None = None) -> tuple[str, str, str] | None:
    """Daca blocul incepe cu un titlu, returneaza (cheie, titlu, restul textului).

    Titlul = textul bold de la INCEPUTUL blocului, cel putin cat textul obisnuit, care:
    - incepe cu o numerotare: "2.3.3. Reauthentication", "B.1. Introduction",
      "Appendix B. Syncable Authenticators" (cheile: "2.3.3", "B.1", "B"), sau
    - ocupa tot blocul, e scurt si n-are numerotare: "References" (cheia ""). Daca PDF-ul
      are cuprins intern (outline), titlul trebuie sa apara si acolo; altfel celulele
      bold din tabele ("Description Mitigations") ar fi luate drept titluri.
    Textul bold din mijlocul unui paragraf sau urmat de text normal fara numerotare
    (ex. "Authentication Assurance Level 1 ...") nu e titlu. Nici listele "1. ..."
    (nu sunt bold) si nici capetele de tabel (font mai mic)."""
    first_regular = next((i for i, p in enumerate(parts) if p[0].strip() and not p[1]), len(parts))
    lead, rest = parts[:first_regular], parts[first_regular:]
    lead_sizes = [size for text, _, size in lead if text.strip()]
    if not lead_sizes or min(lead_sizes) < body_size - 0.5:
        return None
    lead_text, rest_text = _join(lead), _join(rest)
    match = _PDF_NUMBERED_HEADING.match(lead_text)
    if match and match["appendix"]:
        return match["appendix"], f"Appendix {match['appendix']} {match['title']}", rest_text
    if match:
        return match["number"], f"{match['number']} {match['title']}", rest_text
    if (not rest_text and len(lead_text.split()) <= config.PDF_MAX_UNNUMBERED_HEADING_WORDS
            and (outline is None or lead_text.lower() in outline)):
        return "", lead_text, ""
    return None


def parse_pdf(path: Path, source: dict) -> list[Chunk]:
    import pymupdf  # importat aici ca restul proiectului sa mearga si fara el

    with pymupdf.open(path) as pdf:
        # "dict" da si fontul fiecarei bucati de text (de aici stim ce e bold)
        pages = [[b for b in page.get_text("dict")["blocks"] if b.get("type", 0) == 0] for page in pdf]
        toc = pdf.get_toc()  # cuprinsul intern: [nivel, titlu, pagina]; gol daca lipseste
    body_size = _body_font_size(pages)
    # Cu cuprins intern: titlurile fara numar trebuie sa fie in el, iar paginile dinaintea
    # primei intrari (coperta, Authority, Abstract, cuprinsul tiparit) sunt preambul.
    outline = {" ".join(title.lower().split()) for _, title, _ in toc} if toc else None
    first_content_page = min(page for _, _, page in toc) if toc else 1

    # Antetele si subsolurile se repeta pe multe pagini: le gasim si le scoatem
    def first_line(block: dict) -> str:
        lines = block.get("lines", [])
        return _join(_block_parts({"lines": lines[:1]})) if lines else ""

    line_counts = Counter(first_line(b) for blocks in pages for b in blocks)
    repeated = {line for line, n in line_counts.items() if line and n >= max(3, len(pages) * 0.3)}

    paragraphs: list[tuple[int, str, str]] = []  # (pagina, sectiune, text)
    numbered_titles: dict[str, str] = {}         # "3.1" -> "3.1 Requirements by Authenticator Type"
    section_path = [source["title"]]
    for page_number, blocks in enumerate(pages, start=1):
        if page_number < first_content_page:
            continue
        for block in blocks:
            parts = _block_parts(block)
            text = _join(parts)
            if (not text or _PAGE_NUMBER.match(text) or first_line(block) in repeated
                    or _DOT_LEADER.search(text) or _is_footnote(parts, body_size)):
                continue
            heading = _split_heading(parts, body_size, outline)
            if heading:
                key, title, text = heading
                if key:  # calea se reface din numerotare: "3.1.1.2" -> 3 > 3.1 > 3.1.1 > 3.1.1.2
                    numbered_titles[key] = title
                    pieces = key.split(".")
                    parents = [".".join(pieces[:i]) for i in range(1, len(pieces) + 1)]
                    section_path = [numbered_titles[k] for k in parents if k in numbered_titles]
                else:
                    section_path = [title]
            for phrase in config.PDF_SKIP_LINES:
                text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)
            text = " ".join(text.split())
            if not text or any(skip in t.lower() for t in section_path for skip in config.SKIP_SECTIONS):
                continue
            paragraphs.append((page_number, " > ".join(section_path), text))

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


# ------------------------------------------------------------------ limita tokeni

def _halve(text: str) -> list[str] | None:
    """Imparte textul in doua parti cat mai egale (in cuvinte), taind de preferinta intre
    paragrafe, apoi intre randuri, intre propozitii si abia la urma intre cuvinte.
    Un punct de taiere e acceptat doar daca fiecare parte are macar un sfert din cuvinte."""
    total = len(text.split())
    if total < 2:
        return None
    for separator in ("\n\n", "\n", ". ", " "):
        units = text.split(separator)
        if len(units) < 2:
            continue
        sizes = [len(u.split()) for u in units]
        cuts = [(abs(sum(sizes[:i]) - total / 2), i) for i in range(1, len(units))]
        _, i = min(cuts)
        left_words = sum(sizes[:i])
        if separator != " " and min(left_words, total - left_words) < total / 4:
            continue  # taietura prea dezechilibrata: incercam un separator mai fin
        left = separator.join(units[:i]) + (separator.rstrip() if separator == ". " else "")
        right = separator.join(units[i:])
        if left.strip() and right.strip():
            return [left.strip(), right.strip()]
    return None


def enforce_token_limit(chunks: list[Chunk], count_tokens,
                        max_tokens: int = config.MAX_TOKENS) -> list[Chunk]:
    """Modelul de embeddings vede doar primii max_tokens tokeni din embedding_text();
    restul e taiat fara avertisment. O bucata prea lunga (de obicei una cu cod) se imparte
    in doua, apoi din nou, pana incape. Bucatile care incap raman neschimbate.

    count_tokens: functie text -> numar de tokeni (in ingest: tokenizer-ul modelului)."""
    result: list[Chunk] = []
    pending = list(reversed(chunks))
    while pending:
        chunk = pending.pop()
        halves = _halve(chunk.text) if count_tokens(chunk.embedding_text()) > max_tokens else None
        if not halves:
            result.append(chunk)  # incape (sau e un singur cuvant, nu mai avem ce taia)
            continue
        for text in reversed(halves):  # verificam din nou fiecare jumatate, in ordine
            pending.append(Chunk(chunk.doc_id, chunk.doc_title, chunk.collection, chunk.url,
                                 chunk.section, text, chunk.page))
    return result


# ----------------------------------------------------------------------- general

def parse_document(path: Path, source: dict, count_tokens=None) -> list[Chunk]:
    """count_tokens (optional): daca e dat, bucatile peste config.MAX_TOKENS se impart."""
    if source["type"] == "markdown":
        chunks = parse_markdown(path, source)
    elif source["type"] == "pdf":
        chunks = parse_pdf(path, source)
    else:
        raise ValueError(f"Tip necunoscut pentru RAG: {source['type']}")
    if count_tokens is not None:
        chunks = enforce_token_limit(chunks, count_tokens)
    for i, chunk in enumerate(chunks):
        chunk.chunk_id = f"{source['id']}::{i:03d}"
    return chunks
