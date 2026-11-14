"""Web dispatcher for the Prompt Forger engine (used by the Vercel function and the local dev server).

One endpoint, one JSON body: {"method": "...", "params": {...}}.
- The engine is the same package the desktop app ships (vendored into api/_vendor by scripts/sync-engine.mjs).
- AI keys arrive per request in the X-PF-Key header, are used for that request only and are never stored or logged.
- Ollama is refused: it runs on the user's own computer, which a hosted server can't reach.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

_VENDOR = Path(__file__).resolve().parent / "_vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from prompt_forger_engine import __version__  # noqa: E402
from prompt_forger_engine.ai import keys  # noqa: E402
from prompt_forger_engine.ai.describe import describe  # noqa: E402
from prompt_forger_engine.ai.improve import enhance, rate  # noqa: E402
from prompt_forger_engine.ai.providers import ProviderError  # noqa: E402
from prompt_forger_engine.ai.run import run_prompt  # noqa: E402
from prompt_forger_engine.forge import forge, meta  # noqa: E402

MAX_BODY_BYTES = 256 * 1024
AI_PROVIDERS = ("anthropic", "openai")

# Methods that may call an AI provider (and so may need a key).
_AI_METHODS: dict[str, Callable[[Any], Any]] = {
    "describe": describe,
    "enhance": enhance,
    "rate": rate,
    "run": run_prompt,
}
_LOCAL_METHODS: dict[str, Callable[[Any], Any]] = {
    "forge": forge,
    "meta": lambda _p: {**meta(), "version": __version__, "web": True},
}


class _RateLimiter:
    """Sliding-window limiter per client, per warm instance. A guard against floods, not a quota system."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit, self.window = limit, window_s
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(client, deque())
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            if len(self._hits) > 5000:  # keep memory bounded on long-lived instances
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] <= self.window}
            return True


_local_limit = _RateLimiter(240, 60.0)  # live forging fires often while typing
_ai_limit = _RateLimiter(30, 60.0)


def _error(status: int, code: str, message: str) -> tuple[int, dict[str, Any]]:
    return status, {"error": {"code": code, "message": message}}


def dispatch(raw_body: bytes, *, api_key: str | None, client: str) -> tuple[int, dict[str, Any]]:
    """Handle one request. Returns (HTTP status, JSON-able body). Never raises."""
    if len(raw_body) > MAX_BODY_BYTES:
        return _error(413, "too_large", "That request is too large.")
    try:
        req = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "bad_request", "The request body must be JSON.")
    if not isinstance(req, dict):
        return _error(400, "bad_request", "The request body must be a JSON object.")

    method = req.get("method")
    params = req.get("params") if isinstance(req.get("params"), dict) else {}

    if method in _LOCAL_METHODS:
        if not _local_limit.allow(client):
            return _error(429, "rate_limit", "Too many requests. Slow down for a moment.")
        return _run(_LOCAL_METHODS[method], params)

    if method not in _AI_METHODS:
        return _error(404, "unknown_method", f"Unknown method: {method!r}")
    if not _ai_limit.allow(client):
        return _error(429, "rate_limit", "Too many AI requests. Wait a minute and try again.")

    provider = str(params.get("provider") or "rules")
    if provider == "ollama":
        return _error(400, "unsupported", "Ollama runs on your own computer, so it only works in the desktop app.")
    if provider in AI_PROVIDERS:
        if not api_key:
            name = "Claude (Anthropic)" if provider == "anthropic" else "OpenAI"
            return _error(400, "no_key", f"Add your {name} API key in AI settings first.")
        try:
            with keys.request_key(provider, api_key):
                return _run(_AI_METHODS[method], params)
        except keys.KeyStoreError as exc:
            return _error(400, "bad_key", str(exc))
    if method == "run":
        return _error(400, "no_provider", "Choose Claude or OpenAI in AI settings to test a prompt.")
    return _run(_AI_METHODS[method], params)


def _run(fn: Callable[[Any], Any], params: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        return 200, {"result": fn(params)}
    except ProviderError as exc:
        status = 502 if exc.code in ("server", "offline", "timeout", "bad_reply") else 400
        return _error(status, exc.code, str(exc))
    except Exception as exc:  # never leak a traceback (or anything request-specific) to the client
        print(f"[prompt-forger] internal error: {exc.__class__.__name__}", file=sys.stderr)
        return _error(500, "internal", "Something went wrong in the engine. Try again.")
