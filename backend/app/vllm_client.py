import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings


class VllmUnavailableError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {"Content-Type": "application/json"}
    if settings.vllm_api_key:
        headers["Authorization"] = f"Bearer {settings.vllm_api_key}"
    return headers


async def _models(base_url: str) -> list[str]:
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(f"{base_url.rstrip('/')}/models", headers=_headers())
        response.raise_for_status()
    return [model.get("id", "") for model in response.json().get("data", [])]


async def check_vllm() -> dict:
    settings = get_settings()
    result = {
        "status": "ok",
        "chat_base_url": settings.vllm_chat_base_url,
        "embed_base_url": settings.vllm_embed_base_url,
        "chat_model": settings.vllm_chat_model,
        "embed_model": settings.vllm_embed_model,
        "chat_model_available": False,
        "embed_model_available": False,
        "chat_models": [],
        "embed_models": [],
    }
    try:
        chat_models = await _models(settings.vllm_chat_base_url)
        embed_models = await _models(settings.vllm_embed_base_url)
        result.update(
            {
                "chat_models": chat_models,
                "embed_models": embed_models,
                "chat_model_available": settings.vllm_chat_model in chat_models,
                "embed_model_available": settings.vllm_embed_model in embed_models,
            }
        )
        return result
    except httpx.HTTPError as exc:
        return {
            **result,
            "status": "offline",
            "message": str(exc),
        }


async def check_embedding_server() -> dict:
    settings = get_settings()
    result = {
        "status": "ok",
        "base_url": settings.vllm_embed_base_url,
        "model": settings.vllm_embed_model,
        "model_available": False,
        "models": [],
    }
    try:
        models = await _models(settings.vllm_embed_base_url)
        return {
            **result,
            "models": models,
            "model_available": settings.vllm_embed_model in models,
        }
    except httpx.HTTPError as exc:
        return {
            **result,
            "status": "offline",
            "message": str(exc),
        }


async def stream_chat(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    settings = get_settings()
    payload = {
        "model": settings.vllm_chat_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.vllm_chat_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=_headers(),
            ) as response:
                if response.status_code >= 400:
                    error_body = (await response.aread()).decode("utf-8", errors="replace")[:500]
                    raise VllmUnavailableError(
                        "vLLM chat request failed. Check that the chat server is running and that the prompt fits "
                        f"the model context window at {settings.vllm_chat_base_url} with model {settings.vllm_chat_model}. "
                        f"Status {response.status_code}: {error_body}"
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_text = line.removeprefix("data:").strip()
                    if data_text == "[DONE]":
                        break
                    data = json.loads(data_text)
                    if data.get("error"):
                        raise VllmUnavailableError(f"vLLM chat request failed: {data['error']}")
                    token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if token:
                        yield token
        except VllmUnavailableError:
            raise
        except httpx.HTTPError as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f" Status {exc.response.status_code}: {exc.response.text[:500]}"
            raise VllmUnavailableError(
                "vLLM chat request failed. Check that the chat server is running and that the prompt fits "
                f"the model context window at {settings.vllm_chat_base_url} with model {settings.vllm_chat_model}."
                f"{detail}"
            ) from exc


async def chat_json(messages: list[dict[str, str]], schema: dict) -> str:
    settings = get_settings()
    payload = {
        "model": settings.vllm_chat_model,
        "messages": messages,
        "stream": False,
        "temperature": 0,
        "max_tokens": 256,
        "guided_json": schema,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            response = await client.post(
                f"{settings.vllm_chat_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f" Status {exc.response.status_code}: {exc.response.text[:500]}"
            raise VllmUnavailableError(
                "vLLM structured chat request failed. Check the chat server, prompt length, and structured-output support."
                f"{detail}"
            ) from exc


async def embed(text: str) -> list[float]:
    settings = get_settings()
    payload = {"model": settings.vllm_embed_model, "input": text}
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(
                f"{settings.vllm_embed_base_url.rstrip('/')}/embeddings",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except httpx.HTTPError as exc:
            raise VllmUnavailableError(
                "vLLM embedding server is not reachable. Start a vLLM embedding server "
                f"at {settings.vllm_embed_base_url} with model {settings.vllm_embed_model}."
            ) from exc
