"""Tests for use cases."""

from unittest.mock import Mock

import pytest

from domain.entities import PromptRecord
from domain.exceptions import (
    EmbeddingError,
    LLMError,
    RepositoryError,
    ValidationError,
    VectorIndexError,
)
from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar


class TestCreatePrompt:
    def setup_method(self):
        self.llm_provider = Mock()
        self.prompt_repo = Mock()
        self.vector_index = Mock()
        self.embedder = Mock()
        self.use_case = CreatePrompt(
            self.llm_provider,
            self.prompt_repo,
            self.vector_index,
            self.embedder
        )

    def test_create_prompt_success(self):
        # Arrange
        prompt = "Test prompt"
        self.llm_provider.generate.return_value = "Test response"
        self.embedder.embed.return_value = [0.1, 0.2, 0.3]
        
        # Act
        result = self.use_case.execute(prompt)
        
        # Assert
        assert isinstance(result, PromptRecord)
        assert result.prompt == prompt
        assert result.response == "Test response"
        self.prompt_repo.save.assert_called_once()
        self.vector_index.add.assert_called_once()

    def test_create_prompt_empty_input(self):
        # Act & Assert
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.use_case.execute("")

    def test_create_prompt_whitespace_only(self):
        # Act & Assert
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.use_case.execute("   ")

    def test_create_prompt_llm_failure(self):
        # Arrange
        self.llm_provider.generate.side_effect = Exception("LLM failed")
        
        # Act & Assert
        with pytest.raises(LLMError, match="Failed to generate response"):
            self.use_case.execute("test prompt")

    def test_create_prompt_embedding_failure(self):
        # Arrange
        self.llm_provider.generate.return_value = "Test response"
        self.embedder.embed.side_effect = EmbeddingError("Embedding failed")
        
        # Act & Assert
        with pytest.raises(EmbeddingError, match="Embedding failed"):
            self.use_case.execute("test prompt")

    def test_create_prompt_empty_embedding(self):
        # Arrange
        self.llm_provider.generate.return_value = "Test response"
        self.embedder.embed.return_value = []
        
        # Act & Assert
        with pytest.raises(EmbeddingError, match="Empty embedding generated"):
            self.use_case.execute("test prompt")

    def test_create_prompt_repository_failure(self):
        # Arrange
        self.llm_provider.generate.return_value = "Test response"
        self.prompt_repo.save.side_effect = Exception("DB failed")
        
        # Act & Assert
        with pytest.raises(RepositoryError, match="Failed to save prompt"):
            self.use_case.execute("test prompt")


class TestSearchSimilar:
    def setup_method(self):
        self.vector_index = Mock()
        self.embedder = Mock()
        self.prompt_repo = Mock()
        self.use_case = SearchSimilar(
            self.vector_index,
            self.embedder,
            self.prompt_repo
        )

    def test_search_similar_success(self):
        # Arrange
        query = "test query"
        self.embedder.embed.return_value = [0.1, 0.2, 0.3]
        self.vector_index.search.return_value = [("id1", 0.9), ("id2", 0.8)]
        
        record1 = PromptRecord("id1", "prompt1", "response1", "2023-01-01T00:00:00")
        record2 = PromptRecord("id2", "prompt2", "response2", "2023-01-01T00:00:00")
        self.prompt_repo.find_by_id.side_effect = [record1, record2]
        
        # Act
        results = self.use_case.execute(query, 2)
        
        # Assert
        assert len(results) == 2
        assert results[0] == record1
        assert results[1] == record2

    def test_search_similar_empty_query(self):
        # Act & Assert
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.use_case.execute("", 3)

    def test_search_similar_invalid_k(self):
        # Act & Assert
        with pytest.raises(ValidationError, match="must be positive"):
            self.use_case.execute("test", 0)
        
        with pytest.raises(ValidationError, match="cannot exceed"):
            self.use_case.execute("test", 101)

    def test_search_similar_embedding_failure(self):
        # Arrange
        self.embedder.embed.side_effect = Exception("Embedding failed")
        
        # Act & Assert
        with pytest.raises(EmbeddingError, match="Failed to generate embedding"):
            self.use_case.execute("test query", 3)

    def test_search_similar_vector_search_failure(self):
        # Arrange
        self.embedder.embed.return_value = [0.1, 0.2, 0.3]
        self.vector_index.search.side_effect = Exception("Vector search failed")
        
        # Act & Assert
        with pytest.raises(VectorIndexError, match="Failed to search vector index"):
            self.use_case.execute("test query", 3)

    def test_search_similar_partial_record_retrieval(self):
        # Arrange
        query = "test query"
        self.embedder.embed.return_value = [0.1, 0.2, 0.3]
        self.vector_index.search.return_value = [("id1", 0.9), ("id2", 0.8)]
        
        record1 = PromptRecord("id1", "prompt1", "response1", "2023-01-01T00:00:00")
        self.prompt_repo.find_by_id.side_effect = [record1, None]  # Second record not found
        
        # Act
        results = self.use_case.execute(query, 2)
        
        # Assert
        assert len(results) == 1
        assert results[0] == record1

    def test_search_similar_empty_embedding(self):
        # Arrange
        self.embedder.embed.return_value = []
        
        # Act & Assert
        with pytest.raises(EmbeddingError, match="Empty embedding generated"):
            self.use_case.execute("test query", 3)