from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "sqlite:///data/prompts.db"
    faiss_index_path: str = "data/faiss.index"
    chroma_path: str = "data/chroma"
    vector_backend: str = "faiss"

    class Config:
        env_file = ".env"

settings = Settings()
