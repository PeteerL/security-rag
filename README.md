# Security RAG Assistant

A retrieval-augmented assistant that answers web application and API security questions
from official OWASP and NIST documents, with cited sources and an honest
"not found in the documents" when the answer isn't there.

> Status: **Phase 0 – setup and document collection** (work in progress)

## Document corpus (v1)

| Collection | Documents | Used for |
|---|---|---|
| OWASP Cheat Sheet Series | 20 selected cheat sheets | RAG |
| OWASP Top 10:2025 | 10 categories (A01–A10) | RAG + ID lookup |
| OWASP ASVS 5.0 | Chapters V1–V16 | RAG |
| OWASP ASVS 5.0 (CSV) | All requirements with IDs and levels | ID lookup |
| NIST SP 800-63B-4 | Authentication and authenticator management | RAG |

The full list with URLs is in [`config/sources.yaml`](config/sources.yaml).
Documents are **not** committed to the repository; they are downloaded from the official
sources, and `data/raw/manifest.json` records the SHA-256 hash of every file used.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_docs.py
```

## Roadmap

- [x] Phase 0 – project setup, document selection and download
- [ ] Phase 1 – ingestion: parsing, chunking, embeddings, Chroma
- [ ] Phase 2 – basic RAG with cited answers and refusals
- [ ] Phase 3 – evaluation set (50 questions) and metrics
- [ ] Phase 4 – hybrid search and reranking, measured
- [ ] Phase 5 – LangGraph agent (document search, ID lookup, NVD API)
- [ ] Phase 6 – FastAPI, Streamlit, Docker, CI

## License of the documents

OWASP content is licensed under CC BY-SA 4.0. NIST publications are public domain.
