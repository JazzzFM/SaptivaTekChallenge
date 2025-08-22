from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    db_url: str = "sqlite:///data/prompts.db"
    faiss_index_path: str = "data/faiss.index"
    chroma_path: str = "data/chroma"
    vector_backend: str = Field(default="faiss", description="Vector backend: faiss or chroma")
    max_prompt_length: int = Field(default=2000, gt=0, le=10000)
    max_results: int = Field(default=100, gt=0, le=1000)
    embedding_dim: int = Field(default=384, gt=0)
    
    # Security settings
    enable_rate_limiting: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=60, gt=0)
    log_sensitive_data: bool = Field(default=False)
    sanitize_logs: bool = Field(default=True)
    
    # Performance settings
    faiss_auto_save_interval: int = Field(default=60, gt=0)
    max_concurrent_requests: int = Field(default=10, gt=0)
    
    @field_validator('vector_backend')
    @classmethod
    def validate_backend(cls, v):
        if v not in ['faiss', 'chroma']:
            raise ValueError('vector_backend must be either "faiss" or "chroma"')
        return v
    
    @field_validator('db_url')
    @classmethod
    def validate_db_url(cls, v):
        if not v.startswith('sqlite:///'):
            raise ValueError('Only SQLite databases are supported')
        # Ensure data directory exists
        db_path = v.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        return v
    
    @field_validator('faiss_index_path', 'chroma_path')
    @classmethod
    def validate_paths(cls, v):
        # Ensure directory exists
        directory = os.path.dirname(v) if os.path.dirname(v) else '.'
        os.makedirs(directory, exist_ok=True)
        return v

settings = Settings()
