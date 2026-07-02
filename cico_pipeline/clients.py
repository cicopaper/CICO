from __future__ import annotations

from typing import Any

import httpx
from openai import OpenAI


def openai_client(model_cfg: dict[str, Any]) -> OpenAI:
    return OpenAI(
        base_url=model_cfg["base_url"],
        api_key=model_cfg.get("api_key", "token-abc"),
        http_client=httpx.Client(trust_env=bool(model_cfg.get("trust_env", False))),
    )


def chat_completion(
    model_cfg: dict[str, Any],
    system: str,
    user: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    client = openai_client(model_cfg)
    kwargs: dict[str, Any] = {
        "model": model_cfg["model_name_or_path"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": model_cfg.get("temperature", 0.1) if temperature is None else temperature,
    }
    token_limit = model_cfg.get("max_tokens") if max_tokens is None else max_tokens
    if token_limit is not None:
        kwargs["max_tokens"] = token_limit
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def embeddings(model_cfg: dict[str, Any], texts: list[str]) -> list[list[float]]:
    client = openai_client(model_cfg)
    response = client.embeddings.create(
        model=model_cfg["model_name_or_path"],
        input=texts,
    )
    return [item.embedding for item in response.data]
