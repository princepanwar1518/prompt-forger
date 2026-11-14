"""'Test it': send a forged prompt to a provider and return the reply."""

from __future__ import annotations

from typing import Any

from .providers import ProviderConfig, ProviderError, chat, count_tokens

MAX_PROMPT = 200_000


def run_prompt(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ProviderError("Test needs an object.", "bad_request")
    prompt = str(params.get("prompt") or "")
    if not prompt.strip():
        raise ProviderError("There is no prompt to test yet.", "bad_request")
    if len(prompt) > MAX_PROMPT:
        raise ProviderError("The prompt is too long to test.", "bad_request")
    user = str(params.get("input") or "").strip() or "Please begin."
    cfg = ProviderConfig.from_params(params)
    reply = chat(cfg, prompt, user, json_mode=False, max_tokens=2000)
    return {"reply": reply, "provider": cfg.provider, "model": cfg.model}


def exact_tokens(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ProviderError("Token count needs an object.", "bad_request")
    cfg = ProviderConfig.from_params(params)
    text = str(params.get("text") or "")
    return {"tokens": count_tokens(cfg, text), "provider": cfg.provider, "model": cfg.model}
