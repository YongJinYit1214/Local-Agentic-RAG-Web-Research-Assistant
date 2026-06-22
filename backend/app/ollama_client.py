import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings


async def stream_chat(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    settings = get_settings()
    payload = {
        "model": settings.ollama_chat_model,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as client:
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


async def embed(text: str) -> list[float]:
    settings = get_settings()
    embeddings_payload = {"model": settings.ollama_embed_model, "prompt": text}
    embed_payload = {"model": settings.ollama_embed_model, "input": text}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embeddings", json=embeddings_payload
        )
        if response.status_code == 404:
            response = await client.post(f"{settings.ollama_base_url}/api/embed", json=embed_payload)
            response.raise_for_status()
            return response.json()["embeddings"][0]
        response.raise_for_status()
        return response.json()["embedding"]
