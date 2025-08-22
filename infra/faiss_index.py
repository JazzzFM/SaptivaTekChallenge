from __future__ import annotations

import json
import os
import tempfile
from threading import RLock
from typing import Sequence

import faiss
import numpy as np

from domain.exceptions import VectorIndexError
from domain.ports import VectorIndex


class FaissVectorIndex(VectorIndex):
    def __init__(self, index_path: str, ids_path: str | None = None, dim: int = 384, auto_save_interval: int | None = None):
        self.index_path = index_path
        self.ids_path = ids_path or (index_path + ".ids.json")
        self.dim = dim
        self.auto_save_interval = auto_save_interval  # Store but don't use for now
        self._lock = RLock()
        self._ids: list[str] = []
        self._index = faiss.IndexFlatIP(self.dim)
        self._load_if_exists()

    # ---------- API ----------
    def add(self, id: str, vector: Sequence[float]) -> None:
        if len(vector) != self.dim:
            raise VectorIndexError(f"Vector dimension {len(vector)} doesn't match index dimension {self.dim}")
        
        # Check for NaN or infinite values
        if any(not np.isfinite(x) for x in vector):
            raise VectorIndexError("Vector contains NaN or infinite values")
            
        v = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        with self._lock:
            self._index.add(v)
            self._ids.append(id)
            self._persist_atomic()

    def search(self, vector: Sequence[float], k: int) -> list[tuple[str, float]]:
        if len(vector) != self.dim:
            raise VectorIndexError(f"Vector dimension {len(vector)} doesn't match index dimension {self.dim}")
        
        # Check for NaN or infinite values
        if any(not np.isfinite(x) for x in vector):
            raise VectorIndexError("Vector contains NaN or infinite values")
            
        v = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        with self._lock:
            distances, indices = self._index.search(v, k)
            idxs: list[int] = indices[0].tolist()
            scores: list[float] = distances[0].tolist()
            out: list[tuple[str, float]] = []
            for pos, score in zip(idxs, scores, strict=True):
                if 0 <= pos < len(self._ids):
                    out.append((self._ids[pos], float(score)))
            return out

    def save(self) -> None:
        """Force save the index to disk."""
        with self._lock:
            self._persist_atomic()

    def get_stats(self) -> dict:
        """Get statistics about the index."""
        with self._lock:
            return {
                "total_vectors": len(self._ids),
                "dimension": self.dim,
                "index_path": self.index_path,
                "ids_path": self.ids_path
            }
 
    # ---------- Internals ----------
    def _load_if_exists(self) -> None:
        # Cargar de forma tolerante: si uno de los dos falta, arranca limpio
        if os.path.exists(self.index_path) and os.path.exists(self.ids_path):
            try:
                self._index = faiss.read_index(self.index_path)
                with open(self.ids_path, "r", encoding="utf-8") as f:
                    self._ids = json.load(f)
            except Exception:
                # Indulgente: evita “No data left in file” en arranque si hubo corte previo
                self._index = faiss.IndexFlatIP(self.dim)
                self._ids = []

    def _persist_atomic(self) -> None:
        # Escribir en archivos temporales y reemplazar de forma atómica
        dir_ = os.path.dirname(self.index_path) or "."
        os.makedirs(dir_, exist_ok=True)

        # Índice FAISS
        fd_idx, tmp_idx = tempfile.mkstemp(dir=dir_, prefix="faiss_", suffix=".idx")
        os.close(fd_idx)
        faiss.write_index(self._index, tmp_idx)

        # IDs
        fd_ids, tmp_ids = tempfile.mkstemp(dir=dir_, prefix="faiss_", suffix=".json")
        os.close(fd_ids)
        with open(tmp_ids, "w", encoding="utf-8") as f:
            json.dump(self._ids, f)
        os.replace(tmp_idx, self.index_path)
        os.replace(tmp_ids, self.ids_path)
