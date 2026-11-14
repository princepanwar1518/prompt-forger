"""Vercel Python function: POST /api/engine -> Prompt Forger engine. Logic lives in _dispatch.py."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dispatch import MAX_BODY_BYTES, dispatch  # noqa: E402


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel looks for this name
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY_BYTES:
            self._send(413, {"error": {"code": "too_large", "message": "That request is too large."}})
            return
        body = self.rfile.read(length) if length > 0 else b""
        forwarded = self.headers.get("x-forwarded-for") or ""
        client = forwarded.split(",")[0].strip() or (self.client_address[0] if self.client_address else "unknown")
        status, payload = dispatch(body, api_key=(self.headers.get("x-pf-key") or "").strip() or None, client=client)
        self._send(status, payload)

    def do_GET(self) -> None:  # noqa: N802
        self._send(405, {"error": {"code": "method_not_allowed", "message": "Use POST."}})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - silence default access log (no keys, no bodies)
        return

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
