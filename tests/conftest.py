import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.settings import get_settings


@pytest.fixture(scope="function")
def client():
    get_settings.cache_clear()
    # Setup: Create a temporary data directory
    temp_dir = tempfile.mkdtemp()
    
    settings = get_settings()
    original_db_url = settings.database_url
    original_faiss_path = settings.faiss_index_path
    original_chroma_path = settings.chroma_path
    
    settings.database_url = f"sqlite:///{temp_dir}/prompts.db"
    settings.faiss_index_path = f"{temp_dir}/faiss.index"
    settings.chroma_path = f"{temp_dir}/chroma"
    
    app = create_app()
    with TestClient(app) as c:
        yield c
    
    # Teardown: Clean up the temporary directory
    shutil.rmtree(temp_dir)
    
    # Restore original settings
    settings.database_url = original_db_url
    settings.faiss_index_path = original_faiss_path
    settings.chroma_path = original_chroma_path
