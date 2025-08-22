import chromadb
from domain.ports import VectorIndex

class ChromaVectorIndex(VectorIndex):
    def __init__(self, path: str, collection_name: str = "prompts"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(self, id: str, vector: list[float]):
        self.collection.add(ids=[id], embeddings=[vector])

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        results = self.collection.query(query_embeddings=[vector], n_results=k)
        if not results['ids'][0]:
            return []
        # Chroma returns distances, not scores. We will return them as is.
        return list(zip(results['ids'][0], results['distances'][0]))
