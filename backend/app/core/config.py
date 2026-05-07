import os
import json
from typing import List
from pydantic_settings import BaseSettings


def _parse_cors(env_val: str) -> List[str]:
    if not env_val:
        return ["http://localhost:5173", "http://localhost:8000"]
    try:
        return json.loads(env_val)
    except json.JSONDecodeError:
        return [o.strip() for o in env_val.split(",")]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Electricity Bills Recognition"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8000"]

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "electricity_bills")

    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

    # OCR
    OCR_LANG: str = "ch"
    OCR_MAX_CONCURRENCY: int = 1

    # Embedding
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "models/embedding/default")
    RERANK_MODEL_PATH: str = os.getenv("RERANK_MODEL_PATH", "")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "password")

    # Base Dir
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            self.BACKEND_CORS_ORIGINS = _parse_cors(cors_env)

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
