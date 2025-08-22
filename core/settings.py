from __future__ import annotations

import os
import pathlib
import tempfile
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    TEST_TMP: pathlib.Path = Field(
        default=pathlib.Path(os.getenv("TEST_TMP_DIR", tempfile.gettempdir()))
    )

    # Bases de datos y rutas
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(pathlib.Path(os.getenv('TEST_TMP_DIR', tempfile.gettempdir())) / 'saptiva_test.db')}"
    )
    faiss_index_path: str = Field(default_factory=lambda: str(pathlib.Path(os.getenv('TEST_TMP_DIR', tempfile.gettempdir())) / "faiss.index"))
    chroma_path: str = Field(default_factory=lambda: str(pathlib.Path(os.getenv('TEST_TMP_DIR', tempfile.gettempdir())) / "chroma"))

    # Vector index / embedder
    embedding_dim: int = 384
    vector_backend: str = "faiss"           # "faiss" o "chroma"
    faiss_auto_save_interval: int = 0       # en segundos; 0 = desactivado

    # API / seguridad
    max_prompt_length: int = 2000
    max_results: int = 100
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    log_sensitive_data: bool = False
    sanitize_logs: bool = True

def ensure_sqlite_dir(db_url: str) -> None:
    if db_url.startswith("sqlite:///"):
        p = pathlib.Path(db_url.replace("sqlite:///", ""))
        p.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.TEST_TMP.mkdir(parents=True, exist_ok=True)
    ensure_sqlite_dir(s.database_url)
    return s
