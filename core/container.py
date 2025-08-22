"""Dependency injection container for the application."""

from typing import Optional
import threading

from core.config import settings
from domain.ports import LLMProvider, PromptRepository, VectorIndex, Embedder
from infra.sqlite_repo import SQLitePromptRepository
from infra.faiss_index import FaissVectorIndex
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator
from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar


class Container:
    """Dependency injection container with singleton management."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._instances = {}
    
    def _get_singleton(self, key: str, factory):
        """Get or create a singleton instance."""
        if key not in self._instances:
            with self._lock:
                if key not in self._instances:
                    self._instances[key] = factory()
        return self._instances[key]
    
    @property
    def prompt_repository(self) -> PromptRepository:
        """Get the prompt repository singleton."""
        return self._get_singleton(
            "prompt_repo",
            lambda: SQLitePromptRepository(db_url=settings.db_url)
        )
    
    @property
    def vector_index(self) -> VectorIndex:
        """Get the vector index singleton."""
        def create_index():
            backend = settings.vector_backend.lower()
            if backend == "chroma":
                return ChromaVectorIndex(path=settings.chroma_path)
            return FaissVectorIndex(
                index_path=settings.faiss_index_path,
                dim=settings.embedding_dim,
                auto_save_interval=settings.faiss_auto_save_interval
            )
        
        return self._get_singleton("vector_index", create_index)
    
    @property
    def embedder(self) -> Embedder:
        """Get the embedder singleton."""
        return self._get_singleton(
            "embedder",
            lambda: SentenceTransformerEmbedder()
        )
    
    @property
    def llm_provider(self) -> LLMProvider:
        """Get the LLM provider singleton."""
        return self._get_singleton(
            "llm_provider",
            lambda: LLMSimulator()
        )
    
    @property
    def create_prompt_use_case(self) -> CreatePrompt:
        """Get the create prompt use case."""
        return CreatePrompt(
            self.llm_provider,
            self.prompt_repository,
            self.vector_index,
            self.embedder
        )
    
    @property
    def search_similar_use_case(self) -> SearchSimilar:
        """Get the search similar use case."""
        return SearchSimilar(
            self.vector_index,
            self.embedder,
            self.prompt_repository
        )
    
    def get_repository(self):
        """Get the repository instance."""
        return self.prompt_repository
    
    def get_vector_index(self):
        """Get the vector index instance."""
        return self.vector_index
    
    def get_embedder(self):
        """Get the embedder instance."""
        return self.embedder
    
    def get_llm(self):
        """Get the LLM provider instance."""
        return self.llm_provider
    
    def cleanup(self):
        """Cleanup resources."""
        with self._lock:
            # Save vector index if it has pending changes
            if "vector_index" in self._instances:
                vector_index = self._instances["vector_index"]
                if hasattr(vector_index, 'save'):
                    vector_index.save()
            
            self._instances.clear()
    
    def get_health_info(self) -> dict:
        """Get health information about all components."""
        health = {}
        
        try:
            # Check vector index
            index_stats = self.vector_index.get_stats() if hasattr(self.vector_index, 'get_stats') else {}
            health["vector_index"] = {
                "status": "healthy",
                "backend": settings.vector_backend,
                **index_stats
            }
        except Exception as e:
            health["vector_index"] = {"status": "unhealthy", "error": str(e)}
        
        try:
            # Check embedder
            embedder_info = self.embedder.get_model_info() if hasattr(self.embedder, 'get_model_info') else {}
            health["embedder"] = {
                "status": "healthy",
                **embedder_info
            }
        except Exception as e:
            health["embedder"] = {"status": "unhealthy", "error": str(e)}
        
        try:
            # Check database connection
            # Try to access the repository (this validates the connection)
            _ = self.prompt_repository
            health["database"] = {"status": "healthy", "type": "sqlite"}
        except Exception as e:
            health["database"] = {"status": "unhealthy", "error": str(e)}
        
        return health


# Global container instance
_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = Container()
    return _container


def cleanup_container():
    """Cleanup the global container."""
    global _container
    if _container is not None:
        with _container_lock:
            if _container is not None:
                _container.cleanup()
                _container = None