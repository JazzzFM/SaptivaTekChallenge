from __future__ import annotations

from typing import Sequence, Optional, Any, cast

import chromadb

from domain.ports import VectorIndex


class ChromaVectorIndex(VectorIndex):
    """
    Adapter de VectorIndex usando ChromaDB.
    Enviamos embeddings como `list[Sequence[float]]`, que es lo que el SDK acepta
    (también admite ndarray, pero evitamos NumPy para simplificar el tipado).
    """

    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="prompts")

    def add(self, id: str, vector: Sequence[float]) -> None:
        # Chroma acepta: Sequence[float] o list[Sequence[float]|Sequence[int]] o ndarray.
        embeddings: list[Sequence[float]] = [vector]
        self.collection.add(ids=[id], embeddings=embeddings)

    def search(self, vector: Sequence[float], k: int) -> list[tuple[str, float]]:
        query_embeddings: list[Sequence[float]] = [vector]
        res: dict[str, Any] = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=k,
        )
        ids_opt = cast(Optional[list[list[str]]], res.get("ids"))
        dists_opt = cast(Optional[list[list[float]]], res.get("distances"))
        if not ids_opt or not dists_opt:
            return []
        ids: list[str] = ids_opt[0]
        dists: list[float] = dists_opt[0]
        return list(zip(ids, dists))

