"""Comprehensive tests for ChromaDB integration."""

import pytest
import tempfile
import os
import time
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar
from infra.sqlite_repo import SQLitePromptRepository
from infra.llm_simulator import LLMSimulator


class TestChromaIntegration:
    """Test ChromaDB as alternative vector backend."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_index = ChromaVectorIndex(self.temp_dir)
        self.embedder = SentenceTransformerEmbedder()
        
        # Setup repository for integration tests
        db_path = os.path.join(self.temp_dir, "test.db")
        self.repo = SQLitePromptRepository(f"sqlite:///{db_path}")
        self.llm = LLMSimulator()
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_chroma_basic_operations(self):
        """Test basic CRUD operations with ChromaDB."""
        # Test add
        vector1 = [0.1] * 384
        vector2 = [0.2] * 384
        vector3 = [0.3] * 384
        
        self.chroma_index.add("id1", vector1)
        self.chroma_index.add("id2", vector2)
        self.chroma_index.add("id3", vector3)
        
        # Test search
        results = self.chroma_index.search(vector1, k=3)
        
        assert len(results) == 3
        
        # Check that we get back the IDs
        result_ids = {r[0] for r in results}
        assert result_ids == {"id1", "id2", "id3"}
        
        # The exact same vector should be the closest
        assert results[0][0] == "id1"
    
    def test_chroma_persistence(self):
        """Test that ChromaDB persists data across instances."""
        # Add data to first instance
        vector1 = [1.0] + [0.0] * 383
        vector2 = [0.0, 1.0] + [0.0] * 382
        
        self.chroma_index.add("persistent1", vector1)
        self.chroma_index.add("persistent2", vector2)
        
        # Create new instance with same path
        chroma2 = ChromaVectorIndex(self.temp_dir)
        
        # Should be able to search existing data
        results = chroma2.search(vector1, k=2)
        
        assert len(results) >= 1
        result_ids = {r[0] for r in results}
        assert "persistent1" in result_ids
    
    def test_chroma_large_dataset(self):
        """Test ChromaDB with larger dataset."""
        # Create 100 vectors
        vectors = {}
        for i in range(100):
            # Create slightly different vectors
            vector = [0.0] * 384
            vector[i % 384] = 1.0
            vector[(i + 1) % 384] = 0.5
            
            # Normalize
            import numpy as np
            vector = np.array(vector, dtype=np.float32)
            vector = vector / np.linalg.norm(vector)
            
            vectors[f"vec_{i}"] = vector.tolist()
            self.chroma_index.add(f"vec_{i}", vector.tolist())
        
        # Test search with different k values
        for k in [1, 5, 10, 20]:
            results = self.chroma_index.search(vectors["vec_0"], k=k)
            assert len(results) == min(k, 100)
            
            # Should include vec_0 itself
            result_ids = {r[0] for r in results}
            assert "vec_0" in result_ids
    
    def test_chroma_with_real_embeddings(self):
        """Test ChromaDB with real sentence transformer embeddings."""
        texts = [
            "Machine learning is a subset of artificial intelligence",
            "Deep learning uses neural networks with multiple layers",
            "Python is a popular programming language for data science",
            "JavaScript is used for web development",
            "Cooking pasta requires boiling water and salt"
        ]
        
        # Generate embeddings and add to index
        embeddings = {}
        for i, text in enumerate(texts):
            embedding = self.embedder.embed(text)
            embeddings[f"text_{i}"] = embedding
            self.chroma_index.add(f"text_{i}", embedding)
        
        # Search for AI-related content
        ai_query = self.embedder.embed("artificial intelligence and machine learning")
        results = self.chroma_index.search(ai_query, k=3)
        
        assert len(results) == 3
        
        # Should find the AI/ML related texts
        result_ids = {r[0] for r in results}
        assert "text_0" in result_ids  # Machine learning text
        assert "text_1" in result_ids  # Deep learning text
    
    def test_chroma_empty_index_search(self):
        """Test searching on empty ChromaDB index."""
        query_vector = [0.5] * 384
        results = self.chroma_index.search(query_vector, k=5)
        
        assert results == []
    
    def test_chroma_integration_with_use_cases(self):
        """Test full integration with create and search use cases."""
        # Setup use cases with ChromaDB
        create_use_case = CreatePrompt(
            self.llm,
            self.repo,
            self.chroma_index,
            self.embedder
        )
        
        search_use_case = SearchSimilar(
            self.chroma_index,
            self.embedder,
            self.repo
        )
        
        # Create several prompts
        prompts = [
            "What is machine learning?",
            "How does deep learning work?",
            "Python programming tutorial",
            "JavaScript web development",
            "Recipe for chocolate cake"
        ]
        
        created_records = []
        for prompt in prompts:
            record = create_use_case.execute(prompt)
            created_records.append(record)
        
        # Search for ML-related content
        results = search_use_case.execute("artificial intelligence", k=3)
        
        # Should get some results
        assert len(results) > 0
        assert len(results) <= 3
        
        # Results should be PromptRecord objects
        for result in results:
            assert hasattr(result, 'id')
            assert hasattr(result, 'prompt')
            assert hasattr(result, 'response')
            assert hasattr(result, 'created_at')
    
    def test_chroma_concurrent_access(self):
        """Test that ChromaDB handles concurrent access."""
        import threading
        
        def add_vectors(start_idx, count):
            for i in range(count):
                vector = [0.0] * 384
                vector[start_idx % 384] = 1.0
                vector[i % 384] = 0.5
                
                # Normalize
                import numpy as np
                vector = np.array(vector, dtype=np.float32)
                if np.linalg.norm(vector) > 0:
                    vector = vector / np.linalg.norm(vector)
                
                self.chroma_index.add(f"thread_{start_idx}_{i}", vector.tolist())
                time.sleep(0.001)  # Small delay
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_vectors, args=(i * 100, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all vectors were added
        test_vector = [1.0] + [0.0] * 383
        results = self.chroma_index.search(test_vector, k=50)
        
        # Should have 30 vectors (3 threads * 10 vectors each)
        assert len(results) == 30
    
    def test_chroma_metadata_support(self):
        """Test ChromaDB metadata capabilities (if implemented)."""
        # ChromaDB supports metadata, but our interface doesn't expose it yet
        # This test validates the basic functionality works without metadata
        
        vectors_with_context = [
            ([1.0] + [0.0] * 383, "doc_1", "This is a technical document"),
            ([0.0, 1.0] + [0.0] * 382, "doc_2", "This is a creative writing piece"),
            ([0.0, 0.0, 1.0] + [0.0] * 381, "doc_3", "This is a scientific paper")
        ]
        
        for vector, doc_id, description in vectors_with_context:
            # Normalize vector
            import numpy as np
            vector = np.array(vector, dtype=np.float32)
            vector = vector / np.linalg.norm(vector)
            
            self.chroma_index.add(doc_id, vector.tolist())
        
        # Search should work normally
        query = [1.0, 0.1] + [0.0] * 382
        query = np.array(query, dtype=np.float32)
        query = query / np.linalg.norm(query)
        
        results = self.chroma_index.search(query.tolist(), k=3)
        
        assert len(results) == 3
        result_ids = {r[0] for r in results}
        assert result_ids == {"doc_1", "doc_2", "doc_3"}
    
    def test_chroma_error_handling(self):
        """Test error handling in ChromaDB operations."""
        # Test with invalid vector dimensions
        with pytest.raises(Exception):
            # This should fail as we expect 384-dimensional vectors
            # But ChromaDB might handle dimension mismatches differently than FAISS
            self.chroma_index.add("invalid", [1.0, 2.0])  # Wrong dimension
    
    def test_chroma_vector_validation(self):
        """Test vector validation in ChromaDB."""
        
        # Test with NaN values
        nan_vector = [float('nan')] + [0.0] * 383
        
        # ChromaDB might handle NaN differently than FAISS
        # This test documents the current behavior
        try:
            self.chroma_index.add("nan_test", nan_vector)
            # If it doesn't raise an exception, search should still work
            _ = self.chroma_index.search([1.0] + [0.0] * 383, k=1)
            # Results might be empty or contain the NaN vector
        except Exception:
            # It's acceptable for ChromaDB to reject NaN vectors
            pass
        
        # Test with infinite values
        inf_vector = [float('inf')] + [0.0] * 383
        try:
            self.chroma_index.add("inf_test", inf_vector)
        except Exception:
            # Also acceptable to reject infinite vectors
            pass
    
    def test_chroma_performance_characteristics(self):
        """Test basic performance characteristics of ChromaDB."""
        # Add a reasonable number of vectors and time operations
        
        start_time = time.time()
        
        # Add 50 vectors
        for i in range(50):
            vector = [0.0] * 384
            vector[i % 384] = 1.0
            
            # Normalize
            import numpy as np
            vector = np.array(vector, dtype=np.float32)
            vector = vector / np.linalg.norm(vector)
            
            self.chroma_index.add(f"perf_test_{i}", vector.tolist())
        
        add_time = time.time() - start_time
        
        # Time search operations
        start_time = time.time()
        
        query = [1.0] + [0.0] * 383
        for _ in range(10):
            _ = self.chroma_index.search(query, k=5)
        
        search_time = time.time() - start_time
        
        # Basic performance assertions
        assert add_time < 30.0  # Should not take more than 30 seconds to add 50 vectors
        assert search_time < 5.0  # 10 searches should complete in under 5 seconds
        
        # Verify we got results
        final_results = self.chroma_index.search(query, k=10)
        assert len(final_results) >= 10