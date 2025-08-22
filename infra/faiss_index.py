import faiss
import numpy as np
from domain.ports import VectorIndex

class FaissVectorIndex(VectorIndex):
    def __init__(self, index_path: str, dim: int = 384):
        self.index_path = index_path
        self.dim = dim
        try:
            self.index = faiss.read_index(self.index_path)
            # Helper to map faiss index to our id
            self.id_map = np.load(f"{self.index_path}.map.npy").tolist()
        except RuntimeError:
            self.index = faiss.IndexFlatIP(self.dim)
            self.id_map = []

    def add(self, id: str, vector: list[float]):
        self.index.add(np.array([vector], dtype="float32"))
        self.id_map.append(id)
        faiss.write_index(self.index, self.index_path)
        np.save(f"{self.index_path}.map.npy", np.array(self.id_map))

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        distances, indices = self.index.search(np.array([vector], dtype="float32"), k)
        return [(self.id_map[i], d) for d, i in zip(distances[0], indices[0])]
