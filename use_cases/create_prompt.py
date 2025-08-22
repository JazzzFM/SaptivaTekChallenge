import uuid
from datetime import datetime
from domain.entities import PromptRecord
from domain.ports import LLMProvider, PromptRepository, VectorIndex, Embedder

class CreatePrompt:
    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_repo: PromptRepository,
        vector_index: VectorIndex,
        embedder: Embedder,
    ):
        self.llm_provider = llm_provider
        self.prompt_repo = prompt_repo
        self.vector_index = vector_index
        self.embedder = embedder

    def execute(self, prompt: str) -> PromptRecord:
        response = self.llm_provider.generate(prompt)
        record = PromptRecord(
            id=str(uuid.uuid4()),
            prompt=prompt,
            response=response,
            created_at=datetime.utcnow().isoformat(),
        )
        self.prompt_repo.save(record)
        embedding = self.embedder.embed(prompt)
        self.vector_index.add(record.id, embedding)
        return record
