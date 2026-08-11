from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vllm_chat_base_url: str = "http://localhost:8001/v1"
    vllm_embed_base_url: str = "http://localhost:8002/v1"
    vllm_api_key: str = "token-local"
    vllm_chat_model: str = "Qwen/Qwen3-4B-Instruct-2507-FP8"
    vllm_embed_model: str = "BAAI/bge-small-en-v1.5"
    database_path: str = "./data/evidencedocs.sqlite3"
    chroma_path: str = "./chroma"
    rag_top_k: int = 5
    web_top_k: int = 5
    search_provider: str = "auto"
    tavily_api_key: str = ""
    brave_api_key: str = ""
    enable_query_rewrite: bool = True
    rerank_min_score: float = 3.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
