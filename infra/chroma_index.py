from __future__ import annotations

from typing import List, Sequence, Optional, Tuple, cast
import numpy as np
from numpy.typing import NDArray
import chromadb

from domain.ports import VectorIndex


class ChromaVectorIndex(VectorIndex):
    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="prompts")

    def add(self, id: str, vector: Sequence[float]) -> None:
        # Convertimos a ndarray 2D float32 (Chroma acepta ndarray o lista de ndarrays)
        emb: NDArray[np.float32] = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        # El cast satisface a mypy por las uniones del SDK
        self.collection.add(
            ids=[id],
            embeddings=cast(Sequence[NDArray[np.float32]], emb),
        )

    def search(self, vector: Sequence[float], k: int) -> List[Tuple[str, float]]:
        q: NDArray[np.float32] = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        res = self.collection.query(
            query_embeddings=cast(Sequence[NDArray[np.float32]], q),
            n_results=k,
        )
        ids_opt: Optional[List[List[str]]] = cast(Optional[List[List[str]]], res.get("ids"))
        dists_opt: Optional[List[List[float]]] = cast(Optional[List[List[float]]], res.get("distances"))
        if not ids_opt or not dists_opt:
            return []
        ids: List[str] = ids_opt[0]
        dists: List[float] = dists_opt[0]
        return list(zip(ids, dists))

