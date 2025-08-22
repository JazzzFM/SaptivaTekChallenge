import pytest
from fastapi.testclient import TestClient
import os
import shutil

from api.main import app
from core.config import settings

@pytest.fixture(scope="function")
def client():
    # Setup: Create a temporary data directory
    temp_dir = "./test_data"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Override settings
    original_db_url = settings.db_url
    original_faiss_path = settings.faiss_index_path
    original_chroma_path = settings.chroma_path
    
    settings.db_url = f"sqlite:///{temp_dir}/prompts.db"
    settings.faiss_index_path = f"{temp_dir}/faiss.index"
    settings.chroma_path = f"{temp_dir}/chroma"
    
    with TestClient(app) as c:
        yield c
    
    # Teardown: Clean up the temporary directory
    shutil.rmtree(temp_dir)
    
    # Restore original settings
    settings.db_url = original_db_url
    settings.faiss_index_path = original_faiss_path
    settings.chroma_path = original_chroma_path
