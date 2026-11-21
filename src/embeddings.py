"""Transformarea textului in vectori (embeddings), cu un model local."""

from __future__ import annotations

from src import config


class Embedder:
    """Invelis peste sentence-transformers. Prima rulare descarca modelul (~130 MB)
    in cache-ul Hugging Face din folderul utilizatorului, nu in proiect."""

    def __init__(self, model_name: str = config.EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        vectors = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                    show_progress_bar=True)
        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        # Doar intrebarile primesc instructiunea BGE; documentele nu.
        vector = self.model.encode(config.QUERY_INSTRUCTION + question, normalize_embeddings=True)
        return vector.tolist()
