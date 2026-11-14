"""Tests for the web dispatcher. Run from web/: python -m pytest tests"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

import _dispatch  # noqa: E402
from _dispatch import dispatch  # noqa: E402

KEY = "sk-test-0123456789abcdef"


def call(method, params=None, key=None, client="t"):
    body = json.dumps({"method": method, "params": params or {}}).encode()
    return dispatch(body, api_key=key, client=client)


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(_dispatch, "_local_limit", _dispatch._RateLimiter(240, 60))
    monkeypatch.setattr(_dispatch, "_ai_limit", _dispatch._RateLimiter(30, 60))


def test_meta_has_formats_and_version():
    status, body = call("meta")
    assert status == 200
    assert {f["id"] for f in body["result"]["formats"]} == {"standard", "ralph", "graph", "agent"}
    assert body["result"]["web"] is True


def test_forge_returns_files_and_dimensions():
    status, body = call("forge", {"role": "editor", "task": "Summarise this article for busy managers", "format": "standard"})
    assert status == 200
    assert body["result"]["files"][0]["content"]
    assert len(body["result"]["quality"]["dimensions"]) == 5


def test_offline_methods_need_no_key():
    assert call("describe", {"text": "write a mail to chase clients who have not paid"})[0] == 200
    assert call("enhance", {"form": {"role": "assistant", "task": "Write a reminder email", "format": "standard"}})[0] == 200
    status, body = call("rate", {"form": {"task": "x", "successCriteria": "Under 50 words"}, "reply": "Short reply."})
    assert status == 200 and body["result"]["accuracy"] == 100


def test_ai_provider_without_key_is_refused():
    status, body = call("describe", {"text": "hi there friend", "provider": "anthropic"})
    assert status == 400 and body["error"]["code"] == "no_key"


def test_bad_key_is_refused_without_echoing_it():
    status, body = call("run", {"prompt": "p", "provider": "openai"}, key="bad key!")
    assert status == 400 and body["error"]["code"] == "bad_key"
    assert "bad key!" not in json.dumps(body)


def test_ollama_and_keychain_methods_are_unavailable():
    assert call("describe", {"text": "x", "provider": "ollama"})[1]["error"]["code"] == "unsupported"
    assert call("keys.status")[0] == 404
    assert call("keys.set", {"provider": "openai", "key": KEY})[0] == 404


def test_run_needs_a_provider():
    status, body = call("run", {"prompt": "hello"})
    assert status == 400 and body["error"]["code"] == "no_provider"


def test_request_key_is_scoped(monkeypatch):
    from prompt_forger_engine.ai import keys

    monkeypatch.delenv("PROMPT_FORGER_OPENAI_KEY", raising=False)
    monkeypatch.setenv("PROMPT_FORGER_KEYSTORE", "file:/nonexistent/pf-keys.json")
    seen = {}

    def fake_run(params):
        seen["key"] = keys.get_key("openai")
        return {"reply": "ok"}

    monkeypatch.setitem(_dispatch._AI_METHODS, "run", fake_run)
    assert call("run", {"prompt": "p", "provider": "openai"}, key=KEY)[0] == 200
    assert seen["key"] == KEY
    assert keys.get_key("openai") is None  # nothing leaks past the request


def test_malformed_and_oversized_bodies():
    assert dispatch(b"not json", api_key=None, client="t")[0] == 400
    assert dispatch(b"[1,2]", api_key=None, client="t")[0] == 400
    assert dispatch(b"x" * (_dispatch.MAX_BODY_BYTES + 1), api_key=None, client="t")[0] == 413


def test_unknown_method():
    assert call("shutdown")[0] == 404


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(_dispatch, "_ai_limit", _dispatch._RateLimiter(2, 60))
    assert call("rate", {"form": {}, "reply": "a"}, client="c1")[0] == 200
    assert call("rate", {"form": {}, "reply": "a"}, client="c1")[0] == 200
    assert call("rate", {"form": {}, "reply": "a"}, client="c1")[0] == 429
    assert call("rate", {"form": {}, "reply": "a"}, client="c2")[0] == 200


def test_internal_errors_are_generic(monkeypatch):
    def boom(_p):
        raise RuntimeError("secret detail")

    monkeypatch.setitem(_dispatch._LOCAL_METHODS, "forge", boom)
    status, body = call("forge", {})
    assert status == 500 and "secret" not in json.dumps(body)
