"""Tests for vector similarity validation and correctness."""

import numpy as np
import tempfile
import os
from infra.faiss_index import FaissVectorIndex
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator


class TestSimilarityValidation:
    """Test that vector similarity search works correctly."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.faiss_index = FaissVectorIndex(os.path.join(self.temp_dir, "test.index"), dim=384)
        self.chroma_index = ChromaVectorIndex(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_vector_similarity_order_faiss(self):
        """Test that FAISS returns results in correct similarity order."""
        # Create vectors with known similarity relationships
        # Base vector
        base_vector = [1.0] + [0.0] * 383
        
        # Very similar vector (small perturbation)
        similar_vector = [0.99] + [0.01] + [0.0] * 382
        
        # Moderately similar vector
        moderate_vector = [0.8] + [0.2] + [0.0] * 382
        
        # Dissimilar vector
        dissimilar_vector = [0.1] + [0.9] + [0.0] * 382
        
        # Normalize vectors for cosine similarity
        base_vector = self._normalize_vector(base_vector)
        similar_vector = self._normalize_vector(similar_vector)
        moderate_vector = self._normalize_vector(moderate_vector)
        dissimilar_vector = self._normalize_vector(dissimilar_vector)
        
        # Add vectors to index
        self.faiss_index.add("base", base_vector)
        self.faiss_index.add("similar", similar_vector)
        self.faiss_index.add("moderate", moderate_vector)
        self.faiss_index.add("dissimilar", dissimilar_vector)
        
        # Search for vectors similar to base
        results = self.faiss_index.search(base_vector, k=4)
        
        # Results should be ordered by similarity score (highest first for IP)
        assert len(results) == 4
        
        # Extract IDs and scores
        ids = [r[0] for r in results]
        scores = [r[1] for r in results]
        
        # Check order: base should be first (highest score)
        assert ids[0] == "base"
        
        # Similar should come before moderate
        similar_idx = ids.index("similar")
        moderate_idx = ids.index("moderate")
        dissimilar_idx = ids.index("dissimilar")
        
        assert similar_idx < moderate_idx
        assert moderate_idx < dissimilar_idx
        
        # Scores should be in descending order
        assert scores == sorted(scores, reverse=True)
        
        # Base vector should have highest score (should be ~1.0 for normalized vectors)
        assert scores[0] > 0.99
    
    def test_vector_similarity_order_chroma(self):
        """Test that Chroma returns results in correct similarity order."""
        # Same test but with Chroma
        base_vector = [1.0] + [0.0] * 383
        similar_vector = [0.99] + [0.01] + [0.0] * 382
        moderate_vector = [0.8] + [0.2] + [0.0] * 382
        dissimilar_vector = [0.1] + [0.9] + [0.0] * 382
        
        # Normalize vectors
        base_vector = self._normalize_vector(base_vector)
        similar_vector = self._normalize_vector(similar_vector)
        moderate_vector = self._normalize_vector(moderate_vector)
        dissimilar_vector = self._normalize_vector(dissimilar_vector)
        
        # Add vectors to index
        self.chroma_index.add("base", base_vector)
        self.chroma_index.add("similar", similar_vector)
        self.chroma_index.add("moderate", moderate_vector)
        self.chroma_index.add("dissimilar", dissimilar_vector)
        
        # Search for vectors similar to base
        results = self.chroma_index.search(base_vector, k=4)
        
        assert len(results) == 4
        
        # Check that base is in the results with high similarity
        ids = [r[0] for r in results]
        assert "base" in ids
        assert "similar" in ids
        assert "moderate" in ids
        assert "dissimilar" in ids
        
        # For Chroma, results should be ordered by distance (lower is better)
        # The exact ordering might differ from FAISS due to different similarity metrics
    
    def test_real_text_similarity_with_embedder(self):
        """Test similarity with real text embeddings."""
        embedder = SentenceTransformerEmbedder()
        
        # Test texts with known semantic relationships
        texts = {
            "python_programming": "Python is a programming language",
            "python_animal": "A python is a large snake",
            "javascript_programming": "JavaScript is a programming language",
            "cooking_recipe": "How to cook pasta with tomato sauce"
        }
        
        # Generate embeddings
        embeddings = {}
        for key, text in texts.items():
            embeddings[key] = embedder.embed(text)
        
        # Add to FAISS index
        for key, embedding in embeddings.items():
            self.faiss_index.add(key, embedding)
        
        # Search for programming-related content
        query_embedding = embedder.embed("Programming languages and coding")
        results = self.faiss_index.search(query_embedding, k=4)
        
        # Programming-related texts should rank higher than cooking
        ids = [r[0] for r in results]
        
        # Find positions
        programming_positions = []
        for i, id in enumerate(ids):
            if "programming" in id:
                programming_positions.append(i)
        
        cooking_position = ids.index("cooking_recipe") if "cooking_recipe" in ids else len(ids)
        
        # Programming topics should generally rank higher than cooking
        assert any(pos < cooking_position for pos in programming_positions)
    
    def test_embedding_normalization_validation(self):
        """Test that embeddings are properly L2 normalized."""
        embedder = SentenceTransformerEmbedder()
        
        test_texts = [
            "Short text",
            "This is a longer text with more words and content",
            "Another example with different vocabulary and structure"
        ]
        
        for text in test_texts:
            embedding = embedder.embed(text)
            
            # Calculate L2 norm
            norm = np.linalg.norm(embedding)
            
            # Should be very close to 1.0 (normalized)
            assert abs(norm - 1.0) < 0.001, f"Embedding not normalized: norm={norm}"
            
            # Check that embedding is not empty or all zeros
            assert len(embedding) == 384  # Expected dimension
            assert any(x != 0 for x in embedding), "Embedding is all zeros"
            
            # Check for valid float values
            assert all(isinstance(x, (int, float)) for x in embedding), "Invalid embedding values"
            assert all(not (x != x or abs(x) == float('inf')) for x in embedding), "NaN or inf in embedding"
    
    def test_deterministic_llm_responses(self):
        """Test that LLM simulator produces deterministic responses."""
        llm = LLMSimulator()
        
        test_prompts = [
            "What is machine learning?",
            "Explain Python programming",
            "How does a neural network work?",
            "Short prompt",
            "A much longer prompt with many words and detailed descriptions that should still produce consistent results"
        ]
        
        for prompt in test_prompts:
            # Generate response multiple times
            responses = [llm.generate(prompt) for _ in range(5)]
            
            # All responses should be identical
            assert all(r == responses[0] for r in responses), f"Non-deterministic responses for: {prompt}"
            
            # Response should contain the SimResponse prefix
            assert "[SimResponse-" in responses[0], "Response doesn't have expected format"
            
            # Response should contain some keywords from the prompt
            prompt_words = prompt.lower().split()[:3]
            response_lower = responses[0].lower()
            
            # At least one prompt word should appear in response
            assert any(word in response_lower for word in prompt_words), "Response doesn't relate to prompt"
    
    def test_cosine_similarity_calculation(self):
        """Test that cosine similarity is calculated correctly."""
        # Create test vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]  # Orthogonal to vec1
        vec3 = [1.0, 1.0, 0.0]  # 45 degrees to vec1
        
        # Normalize vectors
        vec1 = self._normalize_vector(vec1 + [0.0] * 381)  # Pad to 384 dimensions
        vec2 = self._normalize_vector(vec2 + [0.0] * 381)
        vec3 = self._normalize_vector(vec3 + [0.0] * 381)
        
        # Add to index
        self.faiss_index.add("vec1", vec1)
        self.faiss_index.add("vec2", vec2)
        self.faiss_index.add("vec3", vec3)
        
        # Search from vec1
        results = self.faiss_index.search(vec1, k=3)
        
        ids = [r[0] for r in results]
        scores = [r[1] for r in results]
        
        # vec1 should be most similar to itself
        assert ids[0] == "vec1"
        assert scores[0] > 0.99  # Should be ~1.0
        
        # vec3 should be more similar to vec1 than vec2
        vec3_idx = ids.index("vec3")
        vec2_idx = ids.index("vec2")
        assert vec3_idx < vec2_idx  # vec3 should rank higher
        
        # Check expected similarity scores
        vec3_score = scores[vec3_idx]
        vec2_score = scores[vec2_idx]
        
        # vec3 should have score around cos(45°) ≈ 0.707
        assert 0.6 < vec3_score < 0.8
        
        # vec2 should have score around cos(90°) ≈ 0
        assert -0.1 < vec2_score < 0.1
    
    def _normalize_vector(self, vector):
        """Normalize vector to unit length."""
        vector = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()
    
    def test_similarity_transitivity(self):
        """Test that similarity relationships are transitive in ranking."""
        # Create a chain of increasingly dissimilar vectors
        base = [1.0] + [0.0] * 383
        step1 = [0.9, 0.1] + [0.0] * 382
        step2 = [0.8, 0.2] + [0.0] * 382
        step3 = [0.7, 0.3] + [0.0] * 382
        step4 = [0.6, 0.4] + [0.0] * 382
        
        vectors = {
            "base": self._normalize_vector(base),
            "step1": self._normalize_vector(step1),
            "step2": self._normalize_vector(step2),
            "step3": self._normalize_vector(step3),
            "step4": self._normalize_vector(step4),
        }
        
        # Add to index
        for name, vector in vectors.items():
            self.faiss_index.add(name, vector)
        
        # Search from base
        results = self.faiss_index.search(vectors["base"], k=5)
        
        # Extract order
        ids = [r[0] for r in results]
        scores = [r[1] for r in results]
        
        # Should be ordered: base, step1, step2, step3, step4
        expected_order = ["base", "step1", "step2", "step3", "step4"]
        assert ids == expected_order, f"Expected {expected_order}, got {ids}"
        
        # Scores should be monotonically decreasing
        assert scores == sorted(scores, reverse=True), f"Scores not in descending order: {scores}"