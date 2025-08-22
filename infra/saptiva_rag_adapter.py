from domain.ports import VectorIndex


class SaptivaRAGAdapter(VectorIndex):
    def add(self, id: str, vector: list[float]):
        # This is a stub for a future implementation.
        # In a real scenario, this would call the Saptiva RAG API.
        raise NotImplementedError("SaptivaRAGAdapter is not implemented yet.")

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        # This is a stub for a future implementation.
        # In a real scenario, this would call the Saptiva RAG API.
        raise NotImplementedError("SaptivaRAGAdapter is not implemented yet.")
