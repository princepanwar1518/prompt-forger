"""Tests for v1.1 features: new fields, variables, tools, checker, explain, Describe it, providers, keys, server."""

import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prompt_forger_engine import DEFAULT_FORM, forge
from prompt_forger_engine.ai import keys
from prompt_forger_engine.ai.describe import describe
from prompt_forger_engine.ai.providers import ProviderError
from prompt_forger_engine.ai.rules import describe_with_rules
from prompt_forger_engine.ai.run import exact_tokens, run_prompt
from prompt_forger_engine.server import serve

BASE = {**DEFAULT_FORM, "role": "senior backend engineer",
        "task": "Build a REST API for a todo app with JWT auth. It must use PostgreSQL and pass all tests."}


def ok(**kw):
    r = forge({**BASE, **kw})
    assert r["ok"], r
    return r


# ---------------------------------------------------------------- new fields

def test_new_sections_render_in_xml_and_markdown():
    kw = dict(constraints="No ORMs\n- Never log secrets", successCriteria="All 20 tests pass",
              examples="Input: a\nOutput: b\n---\nInput: c\nOutput: d", outputSchema='{"status": "ok"}')
    xml = ok(model="claude-opus", **kw)["files"][0]["content"]
    assert "<constraints>\n- No ORMs\n- Never log secrets\n</constraints>" in xml
    assert "<success_criteria>" in xml and "- All 20 tests pass" in xml
    assert xml.count("<example>") == 2
    assert '```json\n{"status": "ok"}\n```' in xml
    md = ok(model="gpt", **kw)["files"][0]["content"]
    assert "## Constraints" in md and "### Example 2" in md and "## Output format" in md


def test_ralph_completion_requires_success_criteria():
    c = ok(format="ralph", successCriteria="All tests pass")["files"][0]["content"]
    assert "and every success criterion above is met" in c


def test_graph_router_uses_success_criteria():
    r = ok(format="graph", successCriteria="Docs cover every endpoint")
    graph = json.loads(r["files"][1]["content"])
    assert "Docs cover every endpoint" in graph["nodes"][-1]["instruction"]


def test_variables_substitute_and_unresolved_are_flagged():
    r = ok(task="Write a launch email for {{product}} aimed at {{audience}} with a clear call to action.",
           variables="product = Prompt Forger\n# comment\n")
    assert "launch email for Prompt Forger" in r["files"][0]["content"]
    assert "{{audience}}" in r["files"][0]["content"]
    assert r["variables"] == ["product", "audience"]
    assert any(f["field"] == "variables" for f in r["quality"]["findings"])


@pytest.mark.parametrize("bad", ["product: x", "2bad = x", "a b = x"])
def test_bad_variable_lines_are_rejected(bad):
    assert "variables" in forge({**BASE, "variables": bad})["errors"]


def test_agent_tools_in_front_matter():
    claude = ok(format="agent", model="claude-sonnet", tools="Read, Grep\nBash(git:*)")["files"][0]["content"]
    assert "\ntools: Read, Grep, Bash(git:*)\nmodel: sonnet\n" in claude
    portable = ok(format="agent", model="gemini", tools="Read")["files"][0]["content"]
    assert 'tools: ["Read"]' in portable
    assert "tools" in forge({**BASE, "tools": "rm -rf /"})["errors"]


# ---------------------------------------------------------------- checker + explain

def test_quality_score_rewards_complete_prompts():
    weak = ok(role="assistant", task="write something good")["quality"]
    strong = ok(constraints="No ORMs", successCriteria="All 20 tests pass", outputSchema="## Summary\n## Code")["quality"]
    assert weak["score"] < 60 and weak["grade"] in ("Weak", "Needs work")
    assert strong["score"] >= 90 and strong["grade"] == "Excellent"


def test_checker_finds_invalid_json_schema_and_budget_conflict():
    r = ok(outputSchema='{"a": 1,}', verbosity="detailed", tokenBudget="300")
    fields = {f["field"] for f in r["quality"]["findings"]}
    assert {"outputSchema", "tokenBudget"} <= fields


def test_explain_is_plain_language():
    e = ok(format="ralph", maxIterations="12", successCriteria="All tests pass")["explanation"]
    assert e.startswith("This is a Ralph loop")
    assert "stops after 12 rounds" in e and "all tests pass" in e


# ---------------------------------------------------------------- Describe it (rules)

def test_rules_email_request():
    r = describe_with_rules("I need help writing emails to clients who haven't paid, polite but firm, under 120 words")
    assert r.form["role"] == "professional business writer"
    assert "Keep it under 120 words." in r.form["constraints"]
    assert "polite and firm" in r.form["constraints"]
    assert r.form["context"] == "Audience: clients."
    assert r.confidence >= 0.9 and not r.questions


def test_rules_hinglish_social_post():
    r = describe_with_rules("mujhe ek linkedin post likhna hai mere naye course ke liye, chota aur friendly")
    assert r.form["role"] == "social media copywriter"
    assert r.form["verbosity"] == "concise"
    assert "friendly" in r.form["constraints"]


def test_rules_steps_loop_and_success():
    r = describe_with_rules("build a REST API in Node, first design the schema, then write endpoints, "
                            "then add tests, keep going until all tests pass. dont use any ORM")
    assert r.form["steps"].splitlines() == ["Design the schema", "Write endpoints", "Add tests"]
    assert r.form["format"] == "ralph"
    assert r.form["successCriteria"].splitlines()[0] == "All tests pass."
    assert "Don't use any ORM." in r.form["constraints"]


def test_rules_vague_request_asks_questions():
    r = describe_with_rules("help me with stuff")
    assert len(r.questions) >= 2 and r.confidence < 0.6


def test_describe_merges_onto_current_form_and_keeps_user_settings():
    current = {**DEFAULT_FORM, "model": "gpt", "tokenBudget": "900", "role": "old role"}
    r = describe({"text": "summarize this quarterly report for my investors", "provider": "rules", "form": current})
    assert r["form"]["model"] == "gpt" and r["form"]["tokenBudget"] == "900"
    assert r["form"]["role"] != "old role" and "role" in r["filled"]
    assert forge(r["form"])["ok"]


@pytest.mark.parametrize("params,code", [({"text": ""}, "bad_request"), ({"text": "x" * 5000}, "bad_request"),
                                         ({"text": "hi", "provider": "nope"}, "bad_request")])
def test_describe_rejects_bad_input(params, code):
    with pytest.raises(ProviderError) as e:
        describe(params)
    assert e.value.code == code


# ---------------------------------------------------------------- providers against a mock server

class _Mock(BaseHTTPRequestHandler):
    mode = "ok"
    seen: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        _Mock.seen.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        status, payload = 200, None
        fields = {"role": "debt collection specialist", "task": "Write a polite but firm payment reminder email.",
                  "steps": ["Greet", "State the amount", "Ask for payment by Friday"],
                  "constraints": ["Under 120 words"], "successCriteria": ["Client pays within 7 days"],
                  "outputSchema": "Subject: ...", "format": "standard", "verbosity": "concise", "questions": []}
        text = {"ok": json.dumps(fields), "fenced": "```json\n" + json.dumps(fields) + "\n```",
                "prose": "Sure! " + json.dumps(fields) + " Hope this helps.", "garbage": "I can't do JSON today"
                }.get(_Mock.mode, json.dumps(fields))
        if _Mock.mode in ("401", "404", "429", "500"):
            status, payload = int(_Mock.mode), {"error": {"message": "nope"}}
        elif self.path.endswith("/v1/messages/count_tokens"):
            payload = {"input_tokens": 1234}
        elif self.path.endswith("/v1/messages"):
            payload = {"content": [{"type": "text", "text": text}]}
        elif self.path.endswith("/chat/completions"):
            payload = {"choices": [{"message": {"content": text}}]}
        elif self.path.endswith("/api/chat"):
            payload = {"message": {"content": text}}
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture()
def mock_ai(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _Mock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("PROMPT_FORGER_ANTHROPIC_BASE_URL", url)
    monkeypatch.setenv("PROMPT_FORGER_OPENAI_BASE_URL", url)
    monkeypatch.setenv("PROMPT_FORGER_KEYSTORE", f"file:{tmp_path / 'keys.json'}")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    _Mock.mode, _Mock.seen = "ok", []
    yield url
    server.shutdown()


def test_describe_needs_a_key(mock_ai):
    with pytest.raises(ProviderError) as e:
        describe({"text": "chase unpaid invoices", "provider": "anthropic"})
    assert e.value.code == "no_key"


@pytest.mark.parametrize("provider", ["anthropic", "openai", "ollama"])
def test_describe_with_each_provider(mock_ai, provider):
    if provider != "ollama":
        keys.set_key(provider, "sk-test-0123456789abcdef")
    r = describe({"text": "chase unpaid invoices", "provider": provider, "ollamaUrl": mock_ai})
    assert r["source"] == provider and r["form"]["role"] == "debt collection specialist"
    assert r["form"]["steps"].splitlines() == ["Greet", "State the amount", "Ask for payment by Friday"]
    path, headers, body = _Mock.seen[-1]
    if provider == "anthropic":
        assert headers["x-api-key"] == "sk-test-0123456789abcdef" and body["model"] == "claude-haiku-5-5"
    if provider == "openai":
        assert headers["authorization"] == "Bearer sk-test-0123456789abcdef"
        assert body["response_format"] == {"type": "json_object"}
    if provider == "ollama":
        assert body["format"] == "json" and body["stream"] is False


@pytest.mark.parametrize("mode", ["fenced", "prose"])
def test_describe_tolerates_wrapped_json(mock_ai, mode):
    keys.set_key("anthropic", "sk-test-0123456789abcdef")
    _Mock.mode = mode
    assert describe({"text": "x invoices", "provider": "anthropic"})["source"] == "anthropic"


def test_describe_falls_back_to_rules_on_garbage(mock_ai):
    keys.set_key("anthropic", "sk-test-0123456789abcdef")
    _Mock.mode = "garbage"
    r = describe({"text": "write emails to clients who haven't paid", "provider": "anthropic"})
    assert r["source"] == "rules" and r["notes"]


@pytest.mark.parametrize("mode,code", [("401", "auth"), ("404", "model"), ("429", "rate_limit"), ("500", "server")])
def test_provider_errors_are_friendly(mock_ai, mode, code):
    keys.set_key("openai", "sk-test-0123456789abcdef")
    _Mock.mode = mode
    with pytest.raises(ProviderError) as e:
        describe({"text": "anything at all", "provider": "openai"})
    assert e.value.code == code and "sk-test" not in str(e.value)


def test_ollama_offline_message():
    with pytest.raises(ProviderError) as e:
        describe({"text": "anything", "provider": "ollama", "ollamaUrl": "http://127.0.0.1:9"})
    assert e.value.code == "offline" and "ollama serve" in str(e.value)


def test_run_and_exact_tokens(mock_ai):
    keys.set_key("anthropic", "sk-test-0123456789abcdef")
    out = run_prompt({"prompt": "You are helpful.", "provider": "anthropic"})
    assert out["reply"]
    assert exact_tokens({"text": "hello", "provider": "anthropic"})["tokens"] == 1234
    assert exact_tokens({"text": "hello", "provider": "ollama"})["tokens"] is None


# ---------------------------------------------------------------- key store

def test_file_keystore_round_trip_and_permissions(monkeypatch, tmp_path):
    path = tmp_path / "keys.json"
    monkeypatch.setenv("PROMPT_FORGER_KEYSTORE", f"file:{path}")
    assert keys.status()["anthropic"] is False
    keys.set_key("anthropic", "  sk-ant-abcdefghijklmnop  ")
    assert keys.get_key("anthropic") == "sk-ant-abcdefghijklmnop"
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    keys.delete_key("anthropic")
    assert keys.get_key("anthropic") is None


@pytest.mark.parametrize("bad", ["short", "has space in it 1234567890", "inject; rm -rf ~ 1234567890", ""])
def test_keystore_rejects_bad_keys(bad, monkeypatch, tmp_path):
    monkeypatch.setenv("PROMPT_FORGER_KEYSTORE", f"file:{tmp_path / 'k.json'}")
    with pytest.raises(keys.KeyStoreError):
        keys.set_key("anthropic", bad)


# ---------------------------------------------------------------- server concurrency

class _SlowReader(io.StringIO):
    """Feeds lines with a pause so slow calls are in flight while fast ones arrive."""


def test_slow_calls_do_not_block_fast_ones(monkeypatch):
    import prompt_forger_engine.server as srv

    def slow(_p):
        time.sleep(0.5)
        return {"slow": True}

    monkeypatch.setitem(srv.SLOW, "describe", slow)
    lines = [json.dumps({"id": 1, "method": "describe", "params": {}}),
             json.dumps({"id": 2, "method": "ping"}),
             json.dumps({"id": 3, "method": "forge", "params": BASE}),
             json.dumps({"id": 4, "method": "shutdown"})]
    out = io.StringIO()
    serve(io.StringIO("\n".join(lines) + "\n"), out)
    ids = [json.loads(l)["id"] for l in out.getvalue().splitlines()]
    assert ids.index(2) < ids.index(1) and ids.index(3) < ids.index(1)  # fast answers came first
    assert set(ids) == {1, 2, 3, 4}


def test_clarifying_answers_go_to_the_right_fields():
    r = describe({"text": "help me with stuff", "provider": "rules", "answers": [
        {"question": "What exactly should the result be (an email, code, a plan, a post...)?", "answer": "an email"},
        {"question": "Who is it for?", "answer": "my clients who haven't paid"},
        {"question": "How will you know the result is good?", "answer": "they pay within 7 days"},
        {"question": "Anything else?", "answer": ""},
    ]})
    f = r["form"]
    assert f["role"] == "professional business writer"
    assert f["task"] == "Help me with stuff. Deliverable: an email."
    assert f["context"] == "Audience: my clients who haven't paid."
    assert f["successCriteria"].splitlines()[0] == "They pay within 7 days."
    assert r["questions"] == []
    assert forge(f)["quality"]["score"] > 54  # better than the unanswered version
