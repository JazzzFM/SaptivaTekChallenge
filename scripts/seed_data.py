#!/usr/bin/env python3
"""
Script de migración y seed reproducible con timestamps ISO8601.
Criterio de aceptación: Seeds reproducibles y verificados en tests de integración.
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logging import get_logger
from core.settings import get_settings
from domain.entities import PromptRecord
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.faiss_index import FaissVectorIndex
from infra.llm_simulator import LLMSimulator
from infra.sqlite_repo import SQLitePromptRepository

logger = get_logger(__name__)


class SeedDataManager:
    """Manages database seeding with reproducible data."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.repo = SQLitePromptRepository(self.settings.database_url)
        self.embedder = SentenceTransformerEmbedder()
        self.llm = LLMSimulator()
        
        # Initialize vector index based on backend
        if self.settings.vector_backend == "chroma":
            self.vector_index = ChromaVectorIndex(self.settings.chroma_path)
        else:
            self.vector_index = FaissVectorIndex(self.settings.faiss_index_path, dim=384)
    
    def get_seed_data(self) -> List[Dict[str, Any]]:
        """Get reproducible seed data with deterministic UUIDs."""
        # Use deterministic UUIDs based on prompt content for reproducibility
        seed_prompts = [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt1")),
                "prompt": "What is machine learning and how does it work?",
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt2")),
                "prompt": "Explain the difference between supervised and unsupervised learning",
                "created_at": "2024-01-01T01:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt3")),
                "prompt": "How do neural networks process information?",
                "created_at": "2024-01-01T02:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt4")),
                "prompt": "What are the main applications of deep learning?",
                "created_at": "2024-01-01T03:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt5")),
                "prompt": "How does natural language processing work with transformers?",
                "created_at": "2024-01-01T04:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt6")),
                "prompt": "What is the difference between Python and JavaScript?",
                "created_at": "2024-01-01T05:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt7")),
                "prompt": "How to implement a REST API with FastAPI?",
                "created_at": "2024-01-01T06:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt8")),
                "prompt": "What are the best practices for database design?",
                "created_at": "2024-01-01T07:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt9")),
                "prompt": "How to deploy applications using Docker?",
                "created_at": "2024-01-01T08:00:00Z"
            },
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt10")),
                "prompt": "What is the importance of unit testing in software development?",
                "created_at": "2024-01-01T09:00:00Z"
            }
        ]
        
        return seed_prompts
    
    def clear_existing_data(self):
        """Clear existing data from all stores."""
        logger.info("Clearing existing data...")
        
        # Clear database
        # Note: SQLitePromptRepository doesn't have a clear method, so we recreate the engine
        try:
            import os
            db_path = self.settings.database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Removed existing database: {db_path}")
            
            # Also remove from the set of created dbs
            if self.settings.database_url in SQLitePromptRepository._created_dbs:
                SQLitePromptRepository._created_dbs.remove(self.settings.database_url)

            # Recreate repository
            self.repo = SQLitePromptRepository(self.settings.database_url)
        except Exception as e:
            logger.warning(f"Could not clear database: {e}")
        
        # Clear vector index
        try:
            if hasattr(self.vector_index, 'clear'):
                self.vector_index.clear()
            else:
                # For FAISS, recreate the index
                if isinstance(self.vector_index, FaissVectorIndex):
                    self.vector_index = FaissVectorIndex(self.settings.faiss_index_path, dim=384)
                logger.info("Cleared vector index")
        except Exception as e:
            logger.warning(f"Could not clear vector index: {e}")
    
    def seed_data(self, clear_existing: bool = True) -> List[PromptRecord]:
        """Seed the database with reproducible data."""
        if clear_existing:
            self.clear_existing_data()
        
        logger.info("Starting data seeding...")
        seed_data = self.get_seed_data()
        created_records = []
        
        for item in seed_data:
            try:
                # Generate response using LLM simulator
                response = self.llm.generate(item["prompt"])
                
                # Create record
                record = PromptRecord(
                    id=item["id"],
                    prompt=item["prompt"],
                    response=response,
                    created_at=item["created_at"]
                )
                
                # Save to repository
                self.repo.save(record)
                
                # Generate embedding and add to vector index
                embedding = self.embedder.embed(item["prompt"])
                self.vector_index.add(item["id"], embedding)
                
                created_records.append(record)
                logger.info(f"Seeded record: {item['id']}")
                
            except Exception as e:
                logger.error(f"Failed to seed record {item['id']}: {e}")
                raise
        
        # Save vector index if it supports it
        try:
            if hasattr(self.vector_index, 'save'):
                self.vector_index.save()
                logger.info("Saved vector index to disk")
        except Exception as e:
            logger.warning(f"Could not save vector index: {e}")
        
        logger.info(f"Successfully seeded {len(created_records)} records")
        return created_records
    
    def verify_seed_data(self) -> bool:
        """Verify that seed data was created correctly."""
        logger.info("Verifying seed data...")
        
        try:
            # Check repository count
            total_records = self.repo.count()
            expected_count = len(self.get_seed_data())
            
            if total_records != expected_count:
                logger.error(f"Expected {expected_count} records, found {total_records}")
                return False
            
            # Check that we can retrieve records
            test_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "prompt1"))
            record = self.repo.find_by_id(test_id)
            
            if not record:
                logger.error(f"Could not retrieve test record: {test_id}")
                return False
            
            # Check vector index
            test_embedding = self.embedder.embed(record.prompt)
            results = self.vector_index.search(test_embedding, k=1)
            
            if not results or results[0][0] != test_id:
                logger.error("Vector index verification failed")
                return False
            
            # Check timestamp format (ISO8601)
            from datetime import datetime
            try:
                datetime.fromisoformat(record.created_at.replace('Z', '+00:00'))
            except ValueError:
                logger.error(f"Invalid timestamp format: {record.created_at}")
                return False
            
            logger.info("Seed data verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def get_migration_info(self) -> Dict[str, Any]:
        """Get information about the current migration state."""
        vector_path = self.settings.chroma_path if self.settings.vector_backend == "chroma" else self.settings.faiss_index_path
        return {
            "database_url": self.settings.database_url,
            "vector_backend": self.settings.vector_backend,
            "vector_index_path": vector_path,
            "total_records": self.repo.count(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "embedder_model": self.embedder.model_name if hasattr(self.embedder, 'model_name') else "unknown",
            "embedder_dimension": self.embedder.get_dimension()
        }


def main():
    """Main entry point for seed script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with reproducible data")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing data")
    parser.add_argument("--info", action="store_true", help="Show migration info")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        seed_manager = SeedDataManager()
        
        if args.info:
            info = seed_manager.get_migration_info()
            print("\n=== Migration Info ===")
            for key, value in info.items():
                print(f"{key}: {value}")
            return
        
        if args.verify_only:
            success = seed_manager.verify_seed_data()
            exit(0 if success else 1)
        
        # Seed data
        records = seed_manager.seed_data(clear_existing=not args.no_clear)
        
        # Verify
        if seed_manager.verify_seed_data():
            logger.info("✅ Seeding completed successfully")
            print(f"\n✅ Successfully seeded {len(records)} records")
            
            # Show sample
            print("\n📋 Sample records:")
            for i, record in enumerate(records[:3]):
                print(f"  {i+1}. {record.prompt[:50]}...")
        else:
            logger.error("❌ Seeding verification failed")
            exit(1)
            
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
