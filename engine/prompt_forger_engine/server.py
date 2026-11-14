"""JSON-lines protocol over stdin/stdout.

Request : {"id": 1, "method": "...", "params": {...}}
Response: {"id": 1, "result": {...}}  or  {"id": 1, "error": {"code": "...", "message": "..."}}

Fast methods (forge, meta, ping, keys.*) run inline. Network methods (describe, run, tokens) run on a
small thread pool, so live forging never waits behind a slow AI call; responses may arrive out of
order and are matched by id. Output is ASCII-only JSON, so Windows code pages can't corrupt it.
"""

from __future__ import annotations

import json
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TextIO

from . import __version__
from .ai import keys
from .ai.describe import describe
from .ai.improve import enhance, rate
from .ai.providers import ProviderError
from .ai.run import exact_tokens, run_prompt
from .forge import forge, meta

MAX_LINE_BYTES = 4 * 1024 * 1024


def _keys_set(p: Any) -> dict[str, Any]:
    if not isinstance(p, dict):
        raise keys.KeyStoreError("keys.set needs an object.")
    keys.set_key(str(p.get("provider", "")), str(p.get("key", "")))
    return keys.status()


def _keys_delete(p: Any) -> dict[str, Any]:
    keys.delete_key(str((p or {}).get("provider", "")))
    return keys.status()


FAST: dict[str, Callable[[Any], Any]] = {
    "forge": forge,
    "meta": lambda _p: meta(),
    "ping": lambda _p: {"version": __version__},
    "keys.status": lambda _p: keys.status(),
    "keys.set": _keys_set,
    "keys.delete": _keys_delete,
}
SLOW: dict[str, Callable[[Any], Any]] = {
    "describe": describe,
    "run": run_prompt,
    "tokens": exact_tokens,
    "enhance": enhance,
    "rate": rate,
}


def _call(fn: Callable[[Any], Any], req_id: Any, params: Any) -> dict[str, Any]:
    try:
        return {"id": req_id, "result": fn(params)}
    except ProviderError as exc:
        return {"id": req_id, "error": {"code": exc.code, "message": str(exc)}}
    except keys.KeyStoreError as exc:
        return {"id": req_id, "error": {"code": "keystore", "message": str(exc)}}
    except Exception as exc:  # never let one bad request kill the engine
        traceback.print_exc(file=sys.stderr)
        return {"id": req_id, "error": {"code": "internal", "message": str(exc) or exc.__class__.__name__}}


def handle(request: Any) -> dict[str, Any] | None:
    """Synchronous handling of one request (all methods). Returns None for shutdown."""
    if not isinstance(request, dict):
        return {"id": None, "error": {"code": "bad_request", "message": "Request must be a JSON object."}}
    req_id, method = request.get("id"), request.get("method")
    if method == "shutdown":
        return None
    fn = FAST.get(method) or SLOW.get(method)
    if fn is None:
        return {"id": req_id, "error": {"code": "unknown_method", "message": f"Unknown method: {method!r}"}}
    return _call(fn, req_id, request.get("params"))


class _Writer:
    def __init__(self, out: TextIO) -> None:
        self._out, self._lock = out, threading.Lock()

    def __call__(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
        with self._lock:
            self._out.write(line)
            self._out.flush()


def serve(inp: TextIO, out: TextIO, workers: int = 4) -> None:
    write = _Writer(out)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="engine") as pool:
        for line in inp:
            if not line.strip():
                continue
            if len(line) > MAX_LINE_BYTES:
                write({"id": None, "error": {"code": "too_large", "message": "Request is too large."}})
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                write({"id": None, "error": {"code": "bad_json", "message": str(exc)}})
                continue
            method = request.get("method") if isinstance(request, dict) else None
            if method in SLOW:
                pool.submit(lambda r=request: write(_call(SLOW[r["method"]], r.get("id"), r.get("params"))))
                continue
            response = handle(request)
            if response is None:
                write({"id": request.get("id"), "result": {"shutdown": True}})
                break  # leaving the with-block waits for in-flight slow calls
            write(response)


def run() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", newline="\n" if stream is not sys.stdin else None)
    serve(sys.stdin, sys.stdout)
