from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Union, cast

import chromadb

from domain.ports import VectorIndex

Scalar = Union[str, int, float, bool, None]
Meta = Mapping[str, Scalar]

class ChromaVectorIndex(VectorIndex):
    """
    Adapter de VectorIndex usando ChromaDB.
    Enviamos embeddings como `list[Sequence[float]]`, que es lo que el SDK acepta
    (también admite ndarray, pero evitamos NumPy para simplificar el tipado).
    """

    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="prompts")

    def add(self, id: str, vector: List[float], metadata: Optional[Meta] = None) -> Any:

        if not vector or not isinstance(vector, (list, tuple)):
            raise ValueError("Vector must be a non-empty sequence of floats")

        try:
            ids = [id]
            embeddings: List[Sequence[float]] = [vector]
            final_metadata = metadata or {}
            if not final_metadata:
                final_metadata = {"created_at": datetime.now(timezone.utc).isoformat()}
            metadatas: List[Meta] = [final_metadata]
            return self.collection.add(ids=ids, 
                        embeddings=embeddings, 
                        metadatas=metadatas)
        except Exception as e:
            raise e 

    def search(self, vector: Sequence[float], k: int) -> list[tuple[str, float]]:
        query_embeddings: list[Sequence[float]] = [vector]
        res = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=k,
        )
        ids_opt = cast(Optional[list[list[str]]], res.get("ids"))
        dists_opt = cast(Optional[list[list[float]]], res.get("distances"))
        if not ids_opt or not dists_opt:
            return []
        ids: list[str] = ids_opt[0]
        dists: list[float] = dists_opt[0]
        return list(zip(ids, dists, strict=False))

