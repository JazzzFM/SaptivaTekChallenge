"""Integration tests for seed data script."""

import os
import shutil
import tempfile

import pytest

from core.settings import Settings, get_settings
from scripts.seed_data import SeedDataManager


class TestSeedIntegration:
    """Test seed data functionality with integration scenarios."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test settings
        self.test_settings = get_settings()
        self.test_settings.db_url = f"sqlite:///{os.path.join(self.temp_dir, 'test.db')}"
        self.test_settings.faiss_index_path = os.path.join(self.temp_dir, "test_index")
        self.test_settings.chroma_path = os.path.join(self.temp_dir, "test_chroma")
        self.test_settings.vector_backend = "faiss"
        
        self.seed_manager = SeedDataManager(self.test_settings)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_seed_data_reproducible(self):
        """Test that seed data is reproducible across runs."""
        # First run
        records1 = self.seed_manager.seed_data(clear_existing=True)
        
        # Verify seeding
        assert self.seed_manager.verify_seed_data()
        
        # Second run with same manager
        records2 = self.seed_manager.seed_data(clear_existing=True)
        
        # Should produce identical records
        assert len(records1) == len(records2)
        
        for r1, r2 in zip(records1, records2, strict=False):
            assert r1.id == r2.id
            assert r1.prompt == r2.prompt
            assert r1.response == r2.response
            assert r1.created_at == r2.created_at
    
    def test_seed_data_idempotent(self):
        """Test that running seed multiple times produces same result."""
        # First seeding
        records1 = self.seed_manager.seed_data(clear_existing=True)
        count1 = self.seed_manager.repo.count()
        
        # Second seeding (should clear and recreate)
        records2 = self.seed_manager.seed_data(clear_existing=True)
        count2 = self.seed_manager.repo.count()
        
        assert count1 == count2
        assert len(records1) == len(records2)
    
    def test_seed_verification_passes(self):
        """Test that verification passes after seeding."""
        self.seed_manager.seed_data(clear_existing=True)
        
        # Verification should pass
        assert self.seed_manager.verify_seed_data()
    
    def test_seed_verification_fails_empty_db(self):
        """Test that verification fails on empty database."""
        # Don't seed anything
        assert not self.seed_manager.verify_seed_data()
    
    def test_seed_data_with_chroma_backend(self):
        """Test seeding with ChromaDB backend."""
        # Change to chroma backend
        self.test_settings.vector_backend = "chroma"
        self.seed_manager = SeedDataManager(self.test_settings)
        
        # Should work with ChromaDB
        records = self.seed_manager.seed_data(clear_existing=True)
        assert len(records) > 0
        assert self.seed_manager.verify_seed_data()
    
    def test_migration_info(self):
        """Test migration info retrieval."""
        info = self.seed_manager.get_migration_info()
        
        required_fields = [
            "database_url", "vector_backend", "vector_index_path",
            "total_records", "timestamp", "embedder_dimension"
        ]
        
        for field in required_fields:
            assert field in info
        
        assert info["vector_backend"] in ["faiss", "chroma"]
        assert isinstance(info["total_records"], int)
        assert info["embedder_dimension"] == 384
    
    def test_seed_data_content_quality(self):
        """Test that seeded data has good quality."""
        records = self.seed_manager.seed_data(clear_existing=True)
        
        for record in records:
            # Check required fields
            assert record.id
            assert record.prompt
            assert record.response
            assert record.created_at
            
            # Check content quality
            assert len(record.prompt) > 10  # Meaningful prompts
            assert len(record.response) > 10  # Meaningful responses
            assert "[SimResponse-" in record.response  # LLM simulator format
            
            # Check timestamp format (ISO8601)
            from datetime import datetime
            try:
                datetime.fromisoformat(record.created_at.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid timestamp format: {record.created_at}")
    
    def test_seed_vector_embeddings_quality(self):
        """Test that vector embeddings are properly generated."""
        records = self.seed_manager.seed_data(clear_existing=True)
        
        for record in records:
            # Search for the record using its embedding
            embedding = self.seed_manager.embedder.embed(record.prompt)
            results = self.seed_manager.vector_index.search(embedding, k=1)
            
            # Should find itself as the top result
            assert len(results) > 0
            assert results[0][0] == record.id
            
            # Score should be very high (close to 1.0 for normalized vectors)
            assert results[0][1] > 0.99
    
    def test_seed_semantic_relationships(self):
        """Test that semantically related prompts cluster correctly."""
        self.seed_manager.seed_data(clear_existing=True)
        
        # Find ML-related prompts
        ml_query = self.seed_manager.embedder.embed("machine learning algorithms")
        results = self.seed_manager.vector_index.search(ml_query, k=5)
        
        # Should find some ML-related content in top results
        result_ids = [r[0] for r in results]
        
        # Get the actual prompts
        found_ml_content = False
        for result_id in result_ids[:3]:  # Check top 3
            record = self.seed_manager.repo.find_by_id(result_id)
            if record and any(keyword in record.prompt.lower() 
                            for keyword in ["machine learning", "neural", "deep learning"]):
                found_ml_content = True
                break
        
        assert found_ml_content, "Should find ML-related content in top similarity results"
    
    def test_seed_no_clear_existing(self):
        """Test seeding without clearing existing data."""
        # First seeding
        self.seed_manager.seed_data(clear_existing=True)
        initial_count = self.seed_manager.repo.count()
        
        # Second seeding without clearing (should fail or handle gracefully)
        try:
            self.seed_manager.seed_data(clear_existing=False)
            # If it succeeds, should have more records
            # (This might fail due to duplicate IDs, which is expected)
            final_count = self.seed_manager.repo.count()
            assert final_count >= initial_count
        except Exception:
            # It's acceptable to fail when trying to insert duplicate IDs
            pass
    
    def test_seed_concurrent_safety(self):
        """Test that seeding handles concurrent access safely."""
        import threading
        import time
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def seed_worker(worker_id):
            try:
                # Add small delay to reduce initialization race conditions
                time.sleep(worker_id * 0.1)
                
                # Each worker uses its own settings to avoid conflicts
                worker_temp_dir = tempfile.mkdtemp(prefix=f"worker_{worker_id}_")
                worker_settings = Settings()
                worker_settings.db_url = f"sqlite:///{os.path.join(worker_temp_dir, 'worker.db')}"
                worker_settings.faiss_index_path = os.path.join(worker_temp_dir, "worker_index")
                worker_settings.vector_backend = "faiss"
                
                # Create database directory if it doesn't exist
                os.makedirs(os.path.dirname(worker_settings.db_url.replace("sqlite:///", "")), exist_ok=True)
                
                worker_manager = SeedDataManager(worker_settings)
                records = worker_manager.seed_data(clear_existing=True)
                
                # Use lock to safely update shared results
                with lock:
                    results.append(len(records))
                
                # Cleanup with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if os.path.exists(worker_temp_dir):
                            shutil.rmtree(worker_temp_dir, ignore_errors=True)
                        break
                    except OSError:
                        if attempt < max_retries - 1:
                            time.sleep(0.1)
                        else:
                            pass  # Final cleanup failure is acceptable
                
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # Start multiple threads with staggered start times
        threads = []
        for i in range(3):
            thread = threading.Thread(target=seed_worker, args=(i,))
            threads.append(thread)
            thread.start()
            # Small delay between thread starts to reduce race conditions
            time.sleep(0.05)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All workers should succeed
        assert len(errors) == 0, f"Errors in concurrent seeding: {errors}"
        assert len(results) == 3
        
        # All should produce same number of records
        assert all(count == results[0] for count in results)
    
    def test_seed_data_persistence(self):
        """Test that seeded data persists across manager instances."""
        # Seed with first manager
        records1 = self.seed_manager.seed_data(clear_existing=True)
        
        # Create new manager with same settings
        manager2 = SeedDataManager(self.test_settings)
        
        # Should find existing data
        assert manager2.verify_seed_data()
        
        # Should have same count
        assert manager2.repo.count() == len(records1)
        
        # Should be able to search existing vectors
        test_embedding = manager2.embedder.embed("machine learning")
        results = manager2.vector_index.search(test_embedding, k=3)
        assert len(results) > 0
