from domain.ports import VectorIndex, Embedder, PromptRepository
from domain.entities import PromptRecord

class SearchSimilar:
    def __init__(
        self,
        vector_index: VectorIndex,
        embedder: Embedder,
        prompt_repo: PromptRepository,
    ):
        self.vector_index = vector_index
        self.embedder = embedder
        self.prompt_repo = prompt_repo

    def execute(self, query: str, k: int) -> list[PromptRecord]:
        embedding = self.embedder.embed(query)
        similar_ids = self.vector_index.search(embedding, k)
        results = []
        for id, score in similar_ids:
            record = self.prompt_repo.find_by_id(id)
            if record:
                results.append(record)
        return results
