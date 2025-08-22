from abc import ABC, abstractmethod
from typing import List
from domain.entities import PromptRecord

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

class VectorIndex(ABC):
    @abstractmethod
    def add(self, id: str, vector: List[float]):
        raise NotImplementedError

    @abstractmethod
    def search(self, vector: List[float], k: int) -> List[tuple[str, float]]:
        raise NotImplementedError

class PromptRepository(ABC):
    @abstractmethod
    def save(self, record: PromptRecord):
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, id: str) -> PromptRecord | None:
        raise NotImplementedError
