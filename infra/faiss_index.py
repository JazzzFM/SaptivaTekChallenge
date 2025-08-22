import faiss
import numpy as np
import threading
import time
from domain.ports import VectorIndex
from domain.exceptions import VectorIndexError
from core.logging import get_logger

logger = get_logger(__name__)

class FaissVectorIndex(VectorIndex):
    def __init__(self, index_path: str, dim: int = 384, auto_save_interval: int = 60):
        self.index_path = index_path
        self.dim = dim
        self.auto_save_interval = auto_save_interval
        self._lock = threading.Lock()
        self._pending_saves = 0
        self._last_save_time = time.time()
        
        try:
            self.index = faiss.read_index(self.index_path)
            # Helper to map faiss index to our id
            self.id_map = np.load(f"{self.index_path}.map.npy").tolist()
            logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
        except (RuntimeError, FileNotFoundError, OSError) as e:
            logger.info(f"Creating new FAISS index: {e}")
            self.index = faiss.IndexFlatIP(self.dim)
            self.id_map = []
            self._save_index()

    def add(self, id: str, vector: list[float]):
        if len(vector) != self.dim:
            raise VectorIndexError(f"Vector dimension {len(vector)} does not match expected {self.dim}")
        
        with self._lock:
            try:
                vector_array = np.array([vector], dtype="float32")
                # Validate vector (no NaN or inf)
                if not np.isfinite(vector_array).all():
                    raise VectorIndexError("Vector contains NaN or infinite values")
                
                self.index.add(vector_array)
                self.id_map.append(id)
                self._pending_saves += 1
                
                # Auto-save logic: save periodically or when we have many pending saves
                current_time = time.time()
                if (self._pending_saves >= 10 or 
                    current_time - self._last_save_time > self.auto_save_interval):
                    self._save_index()
                    
            except Exception as e:
                logger.error(f"Failed to add vector to FAISS index: {e}")
                raise VectorIndexError(f"Failed to add vector: {str(e)}") from e

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        if len(vector) != self.dim:
            raise VectorIndexError(f"Query vector dimension {len(vector)} does not match expected {self.dim}")
            
        with self._lock:
            if self.index.ntotal == 0:
                return []
            
            try:
                # Validate and prepare query vector
                vector_array = np.array([vector], dtype="float32")
                if not np.isfinite(vector_array).all():
                    raise VectorIndexError("Query vector contains NaN or infinite values")
                
                # Limit k to available vectors
                actual_k = min(k, self.index.ntotal)
                distances, indices = self.index.search(vector_array, actual_k)
                
                # Filter out invalid indices and return with scores
                results = []
                for i, (distance, index) in enumerate(zip(distances[0], indices[0])):
                    if index != -1 and index < len(self.id_map):
                        results.append((self.id_map[index], float(distance)))
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to search FAISS index: {e}")
                raise VectorIndexError(f"Failed to search: {str(e)}") from e

    def _save_index(self):
        """Internal method to save index and id_map. Must be called with lock held."""
        try:
            faiss.write_index(self.index, self.index_path)
            np.save(f"{self.index_path}.map.npy", np.array(self.id_map))
            self._pending_saves = 0
            self._last_save_time = time.time()
            logger.debug(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            # Don't raise here to avoid cascading failures
    
    def save(self):
        """Explicitly save the index."""
        with self._lock:
            self._save_index()
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        with self._lock:
            return {
                "total_vectors": self.index.ntotal,
                "dimension": self.dim,
                "pending_saves": self._pending_saves,
                "last_save_time": self._last_save_time
            }
