"""Minimal HTTP clients for Claude, OpenAI and Ollama (stdlib only, no SDKs)."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from . import keys

DEFAULT_MODELS = {"anthropic": "claude-haiku-5-5", "openai": "gpt-4o-mini", "ollama": "llama3.2"}
DEFAULT_OLLAMA_URL = "http://localhost:11434"
TIMEOUT_S = 90


class ProviderError(Exception):
    """User-facing message; never contains the API key."""

    def __init__(self, message: str, code: str = "provider_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProviderConfig:
    provider: str  # anthropic | openai | ollama
    model: str
    ollama_url: str = DEFAULT_OLLAMA_URL

    @staticmethod
    def from_params(p: dict[str, Any]) -> "ProviderConfig":
        provider = str(p.get("provider") or "")
        if provider not in DEFAULT_MODELS:
            raise ProviderError(f"Unknown AI provider: {provider!r}", "bad_request")
        model = str(p.get("model") or "").strip() or DEFAULT_MODELS[provider]
        url = str(p.get("ollamaUrl") or "").strip() or DEFAULT_OLLAMA_URL
        if provider == "ollama" and not url.startswith(("http://", "https://")):
            raise ProviderError("The Ollama address must start with http:// or https://", "bad_request")
        return ProviderConfig(provider, model, url.rstrip("/"))


def _base(provider: str, default: str) -> str:
    # Test hook: point a provider at a local mock server.
    return os.environ.get(f"PROMPT_FORGER_{provider.upper()}_BASE_URL", default).rstrip("/")


def _post(url: str, headers: dict[str, str], body: dict[str, Any], provider: str, model: str) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"content-type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            payload = json.loads(e.read().decode("utf-8", "replace"))
            err = payload.get("error")
            detail = err.get("message", "") if isinstance(err, dict) else str(err or "")
        except Exception:
            pass
        if e.code in (401, 403):
            raise ProviderError("The API key was rejected. Check it in Settings.", "auth") from None
        if e.code == 404:
            raise ProviderError(f"Model \"{model}\" was not found. Check the model name in Settings.", "model") from None
        if e.code == 429:
            raise ProviderError("Rate limit or quota reached. Wait a minute or check your plan.", "rate_limit") from None
        if e.code >= 500:
            raise ProviderError(f"The {provider} service had an error ({e.code}). Try again shortly.", "server") from None
        raise ProviderError(f"Request failed ({e.code}). {detail}".strip(), "http") from None
    except (urllib.error.URLError, ConnectionError) as e:
        reason = getattr(e, "reason", e)
        if provider == "ollama":
            raise ProviderError("Ollama isn't running. Install it from ollama.com, then run `ollama serve`.", "offline") from None
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise ProviderError("The AI took too long to answer. Try again.", "timeout") from None
        raise ProviderError("Couldn't reach the AI service. Check your internet connection.", "offline") from None
    except (socket.timeout, TimeoutError):
        raise ProviderError("The AI took too long to answer. Try again.", "timeout") from None
    except json.JSONDecodeError:
        raise ProviderError("The AI service sent an unreadable reply.", "bad_reply") from None


def _need_key(provider: str) -> str:
    try:
        key = keys.get_key(provider)
    except keys.KeyStoreError as e:
        raise ProviderError(str(e), "keystore") from None
    if not key:
        name = "Claude (Anthropic)" if provider == "anthropic" else "OpenAI"
        raise ProviderError(f"Add your {name} API key in Settings first.", "no_key")
    return key


def chat(cfg: ProviderConfig, system: str, user: str, *, json_mode: bool, max_tokens: int = 1500) -> str:
    """One completion. Returns the model's text."""
    if cfg.provider == "anthropic":
        key = _need_key("anthropic")
        data = _post(f"{_base('anthropic', 'https://api.anthropic.com')}/v1/messages",
                     {"x-api-key": key, "anthropic-version": "2023-06-01"},
                     {"model": cfg.model, "max_tokens": max_tokens, "system": system,
                      "messages": [{"role": "user", "content": user}]},
                     "Claude", cfg.model)
        parts = [b.get("text", "") for b in data.get("content", []) if isinstance(b, dict) and b.get("type") == "text"]
        return "".join(parts)
    if cfg.provider == "openai":
        key = _need_key("openai")
        body: dict[str, Any] = {"model": cfg.model, "max_tokens": max_tokens,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = _post(f"{_base('openai', 'https://api.openai.com')}/v1/chat/completions",
                     {"authorization": f"Bearer {key}"}, body, "OpenAI", cfg.model)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError("OpenAI sent an unexpected reply.", "bad_reply") from None
    body = {"model": cfg.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        body["format"] = "json"
    data = _post(f"{cfg.ollama_url}/api/chat", {}, body, "ollama", cfg.model)
    return (data.get("message") or {}).get("content", "")


def count_tokens(cfg: ProviderConfig, text: str) -> int | None:
    """Exact input tokens for Claude; None for providers without a counting endpoint."""
    if cfg.provider != "anthropic":
        return None
    key = _need_key("anthropic")
    data = _post(f"{_base('anthropic', 'https://api.anthropic.com')}/v1/messages/count_tokens",
                 {"x-api-key": key, "anthropic-version": "2023-06-01"},
                 {"model": cfg.model, "messages": [{"role": "user", "content": text}]}, "Claude", cfg.model)
    n = data.get("input_tokens")
    return int(n) if isinstance(n, int) else None
