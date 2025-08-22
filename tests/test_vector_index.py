"""Tests for vector index implementations."""

import pytest
import tempfile
import os
from infra.faiss_index import FaissVectorIndex
from infra.chroma_index import ChromaVectorIndex
from domain.exceptions import VectorIndexError


class TestFaissVectorIndex:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "test.index")
        self.index = FaissVectorIndex(self.index_path, dim=3, auto_save_interval=1000)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_search_vectors(self):
        # Add vectors
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ids = ["v1", "v2", "v3"]
        
        for vec_id, vector in zip(ids, vectors):
            self.index.add(vec_id, vector)
        
        # Search for similar to first vector
        results = self.index.search([1.0, 0.0, 0.0], k=2)
        
        assert len(results) <= 2
        assert results[0][0] == "v1"  # First result should be exact match
        assert results[0][1] > 0.9   # High similarity score

    def test_add_invalid_dimension(self):
        with pytest.raises(VectorIndexError, match="dimension"):
            self.index.add("test", [1.0, 2.0])  # Wrong dimension

    def test_search_invalid_dimension(self):
        self.index.add("test", [1.0, 0.0, 0.0])
        
        with pytest.raises(VectorIndexError, match="dimension"):
            self.index.search([1.0, 2.0], k=1)  # Wrong dimension

    def test_add_invalid_vector_values(self):
        with pytest.raises(VectorIndexError, match="NaN or infinite"):
            self.index.add("test", [float('nan'), 0.0, 0.0])
        
        with pytest.raises(VectorIndexError, match="NaN or infinite"):
            self.index.add("test", [float('inf'), 0.0, 0.0])

    def test_search_invalid_vector_values(self):
        self.index.add("test", [1.0, 0.0, 0.0])
        
        with pytest.raises(VectorIndexError, match="NaN or infinite"):
            self.index.search([float('nan'), 0.0, 0.0], k=1)

    def test_search_empty_index(self):
        results = self.index.search([1.0, 0.0, 0.0], k=5)
        assert results == []

    def test_search_k_larger_than_available(self):
        self.index.add("v1", [1.0, 0.0, 0.0])
        
        results = self.index.search([1.0, 0.0, 0.0], k=10)
        assert len(results) == 1

    def test_persistence(self):
        # Add vector to first index
        self.index.add("test", [1.0, 0.0, 0.0])
        self.index.save()  # Force save
        
        # Create new index instance with same path
        new_index = FaissVectorIndex(self.index_path, dim=3)
        
        # Should be able to search for the vector
        results = new_index.search([1.0, 0.0, 0.0], k=1)
        assert len(results) == 1
        assert results[0][0] == "test"

    def test_get_stats(self):
        stats = self.index.get_stats()
        assert "total_vectors" in stats
        assert "dimension" in stats
        assert stats["dimension"] == 3
        assert stats["total_vectors"] == 0
        
        self.index.add("test", [1.0, 0.0, 0.0])
        
        stats = self.index.get_stats()
        assert stats["total_vectors"] == 1

    def test_batch_operations_thread_safety(self):
        import threading
        import time
        
        def add_vectors(start_idx, count):
            for i in range(count):
                vector_id = f"thread_{start_idx}_{i}"
                vector = [float(start_idx), float(i), 0.0]
                self.index.add(vector_id, vector)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Start multiple threads adding vectors
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_vectors, args=(i, 5))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all vectors were added
        stats = self.index.get_stats()
        assert stats["total_vectors"] == 15  # 3 threads * 5 vectors each


class TestChromaVectorIndex:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index = ChromaVectorIndex(self.temp_dir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_search_vectors(self):
        # Add vectors
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ids = ["v1", "v2", "v3"]
        
        for vec_id, vector in zip(ids, vectors):
            self.index.add(vec_id, vector)
        
        # Search for similar to first vector
        results = self.index.search([1.0, 0.0, 0.0], k=2)
        
        assert len(results) <= 2
        # Chroma might return different ordering than FAISS, so just check we get results
        result_ids = [result[0] for result in results]
        assert "v1" in result_ids

    def test_search_empty_index(self):
        results = self.index.search([1.0, 0.0, 0.0], k=5)
        assert results == []

    def test_persistence(self):
        # Add vector
        self.index.add("test", [1.0, 0.0, 0.0])
        
        # Create new index instance with same path
        new_index = ChromaVectorIndex(self.temp_dir)
        
        # Should be able to search for the vector
        results = new_index.search([1.0, 0.0, 0.0], k=1)
        assert len(results) >= 1
        result_ids = [result[0] for result in results]
        assert "test" in result_ids


def test_vector_index_compatibility():
    """Test that FAISS and Chroma produce similar results for the same data."""
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()
    
    try:
        faiss_index = FaissVectorIndex(os.path.join(temp_dir1, "faiss.index"), dim=3)
        chroma_index = ChromaVectorIndex(temp_dir2)
        
        # Add same vectors to both indices
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ids = ["v1", "v2", "v3"]
        
        for vec_id, vector in zip(ids, vectors):
            faiss_index.add(vec_id, vector)
            chroma_index.add(vec_id, vector)
        
        # Search both indices
        query = [1.0, 0.0, 0.0]
        faiss_results = faiss_index.search(query, k=3)
        chroma_results = chroma_index.search(query, k=3)
        
        # Both should return all 3 vectors
        assert len(faiss_results) == 3
        assert len(chroma_results) == 3
        
        # Get the IDs from results
        faiss_ids = {result[0] for result in faiss_results}
        chroma_ids = {result[0] for result in chroma_results}
        
        # Both should return the same set of IDs
        assert faiss_ids == chroma_ids == {"v1", "v2", "v3"}
        
    finally:
        import shutil
        shutil.rmtree(temp_dir1, ignore_errors=True)
        shutil.rmtree(temp_dir2, ignore_errors=True)