"""Setari comune pentru tot proiectul. Un singur loc in care schimbi o valoare."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fisiere si foldere
SOURCES_FILE = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "chunks.jsonl"
CHROMA_DIR = ROOT / "chroma"
COLLECTION_NAME = "security_docs"

# Chunking (masurat in cuvinte). Masurat pe corpus cu tokenizer-ul BGE: ~1.56 tokeni pe
# cuvant la mediana, dar pana la ~5 la cod (ex. HttpServletResponse.SC_INTERNAL_SERVER_ERROR)
MAX_WORDS = 300   # ~470 tokeni la mediana
MIN_WORDS = 40    # bucatile mai mici se lipesc de urmatoarea din acelasi document
MAX_MERGED_WORDS = 360  # limita cand lipim o bucata mica de urmatoarea
# Limita modelului de embeddings (max_seq_length). Textul de peste ea e taiat FARA
# avertisment, asa ca dupa chunking impartim bucatile mai lungi (vezi enforce_token_limit).
# Se numara tot textul care devine vector: titlu > sectiune + text + tokenii [CLS]/[SEP].
MAX_TOKENS = 512
PDF_OVERLAP_WORDS = 40  # suprapunere intre bucatile din PDF (textul nu are titluri clare)

# Sectiuni care nu ajuta la raspunsuri: liste de linkuri, statistici, mapari CWE
SKIP_SECTIONS = (  # se potriveste orice titlu care CONTINE unul dintre aceste texte
    "references",
    "mapped cwes",
    "score table",
    "related cheat sheet",
    "further reading",
    "related articles",
    "contributors",
    "authors and primary editors",
    # sectiuni din preambulul documentelor NIST (fara continut util pentru raspunsuri)
    "acknowledg",          # Acknowledgments / Acknowledgements
    "note to reviewers",
    "disclaimer",
    "abstract",
    "keywords",
)

# PDF: randuri adaugate de tabelele rupte intre pagini (se scot din text)
PDF_SKIP_LINES = ("continued on next page", "continued from previous page")
# PDF: un bloc scurt, tot bold, fara numerotare (ex. "Acknowledgments") e titlu doar
# daca are cel mult atatea cuvinte
PDF_MAX_UNNUMBERED_HEADING_WORDS = 10

# Embeddings: model local, gratuit, ruleaza pe procesor
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# Modelele BGE cer acest prefix pentru intrebari (nu si pentru documente)
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
