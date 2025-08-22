"""Tests for the embedder implementation."""

import pytest

from domain.exceptions import EmbeddingError
from infra.embedder import SentenceTransformerEmbedder


class TestSentenceTransformerEmbedder:
    
    def test_singleton_behavior(self):
        """Test that the embedder follows singleton pattern."""
        embedder1 = SentenceTransformerEmbedder()
        embedder2 = SentenceTransformerEmbedder()
        
        assert embedder1 is embedder2
    
    def test_embed_success(self):
        """Test successful embedding generation."""
        embedder = SentenceTransformerEmbedder()
        result = embedder.embed("test text")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)
        assert all(abs(x) <= 1.0 for x in result)  # Normalized embeddings should be <= 1
    
    def test_embed_empty_text(self):
        """Test embedding of empty text raises error."""
        embedder = SentenceTransformerEmbedder()
        
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            embedder.embed("")
            
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            embedder.embed("   ")
    
    def test_get_dimension(self):
        """Test getting embedding dimension."""
        embedder = SentenceTransformerEmbedder()
        dim = embedder.get_dimension()
        
        assert isinstance(dim, int)
        assert dim > 0
        
        # Test with actual embedding
        result = embedder.embed("test")
        assert len(result) == dim
    
    def test_get_model_info(self):
        """Test getting model information."""
        embedder = SentenceTransformerEmbedder()
        info = embedder.get_model_info()
        
        assert "model_name" in info
        assert "dimension" in info
        assert "device" in info
        assert "initialized" in info
        assert info["initialized"] is True
        assert info["model_name"] == "all-MiniLM-L6-v2"
    
    def test_concurrent_embedding(self):
        """Test that embeddings work correctly with concurrent access."""
        import threading
        
        embedder = SentenceTransformerEmbedder()
        results = []
        errors = []
        
        def embed_text(text):
            try:
                result = embedder.embed(f"concurrent test {text}")
                results.append(len(result))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=embed_text, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 5
        assert all(r > 0 for r in results)
        
        # All results should have the same dimension
        assert len(set(results)) == 1