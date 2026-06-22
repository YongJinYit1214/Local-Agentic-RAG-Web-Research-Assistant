import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings


class OllamaUnavailableError(RuntimeError):
    pass


async def check_ollama() -> dict:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            return {
                "status": "ok",
                "base_url": settings.ollama_base_url,
                "chat_model": settings.ollama_chat_model,
                "embed_model": settings.ollama_embed_model,
                "installed_models": model_names,
                "chat_model_available": settings.ollama_chat_model in model_names,
                "embed_model_available": settings.ollama_embed_model in model_names,
            }
    except httpx.HTTPError as exc:
        return {
            "status": "offline",
            "base_url": settings.ollama_base_url,
            "message": str(exc),
        }


async def stream_chat(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    settings = get_settings()
    payload = {
        "model": settings.ollama_chat_model,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream(
                "POST", f"{settings.ollama_base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                "Ollama is not reachable. Start Ollama and pull a chat model, for example: "
                "`ollama pull llama3.1:8b`."
            ) from exc


async def embed(text: str) -> list[float]:
    settings = get_settings()
    embeddings_payload = {"model": settings.ollama_embed_model, "prompt": text}
    embed_payload = {"model": settings.ollama_embed_model, "input": text}
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(
                f"{settings.ollama_base_url}/api/embeddings", json=embeddings_payload
            )
            if response.status_code == 404:
                response = await client.post(f"{settings.ollama_base_url}/api/embed", json=embed_payload)
                response.raise_for_status()
                return response.json()["embeddings"][0]
            response.raise_for_status()
            return response.json()["embedding"]
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                "Ollama embeddings are not reachable. Start Ollama and pull the embedding model: "
                "`ollama pull nomic-embed-text`."
            ) from exc
