from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    database_path: str = "./data/localmind.sqlite3"
    chroma_path: str = "./chroma"
    rag_top_k: int = 5
    web_top_k: int = 5
    search_provider: str = "auto"
    tavily_api_key: str = ""
    brave_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
