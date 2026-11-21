"""Salvarea si cautarea bucatilor in Chroma (baza de date vectoriala, locala)."""

from __future__ import annotations

from src import config
from src.parsing import Chunk


def get_collection(reset: bool = False):
    import chromadb

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except Exception:
            pass  # colectia nu exista inca
    # "cosine": vectorii sunt normalizati, deci distanta cosinus e potrivita
    return client.get_or_create_collection(config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def add_chunks(collection, chunks: list[Chunk], vectors: list[list[float]], batch_size: int = 500) -> None:
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.add(
            ids=[c.chunk_id for c in batch],
            embeddings=vectors[start:start + batch_size],
            documents=[c.text for c in batch],
            metadatas=[{
                "doc_id": c.doc_id,
                "doc_title": c.doc_title,
                "collection": c.collection,
                "url": c.url,
                "section": c.section,
                "page": c.page if c.page is not None else -1,  # Chroma nu accepta None
            } for c in batch],
        )


def search(collection, query_vector: list[float], k: int = 5) -> list[dict]:
    result = collection.query(query_embeddings=[query_vector], n_results=k)
    hits = []
    for chunk_id, text, meta, distance in zip(result["ids"][0], result["documents"][0],
                                              result["metadatas"][0], result["distances"][0]):
        hits.append({"chunk_id": chunk_id, "text": text, "score": 1 - distance, **meta})
    return hits
