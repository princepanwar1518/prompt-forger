import io
import json

import pytest

from prompt_forger_engine import DEFAULT_FORM, forge
from prompt_forger_engine.formats.graph import build_graph
from prompt_forger_engine.schema import validate
from prompt_forger_engine.server import serve
from prompt_forger_engine.text import role_sentence, slugify, yaml_string

BASE = {
    **DEFAULT_FORM,
    "role": "senior backend engineer",
    "task": "Build a REST API for a todo app. It must use PostgreSQL.",
    "steps": "1. Design the schema\n- Write the endpoints\n\nAdd tests",
}


def ok(**overrides):
    result = forge({**BASE, **overrides})
    assert result["ok"], result
    return result


def content(i=0, **overrides):
    return ok(**overrides)["files"][i]["content"]


# --- validation -------------------------------------------------------------

def test_requires_role_and_task():
    r = forge(DEFAULT_FORM)
    assert r == {"ok": False, "errors": {"role": "Role is required.", "task": "Task is required."}}


@pytest.mark.parametrize("budget,valid", [("12abc", False), ("10", False), ("", True), ("2000", True)])
def test_token_budget_validation(budget, valid):
    assert forge({**BASE, "tokenBudget": budget})["ok"] is valid


def test_rejects_non_object_and_wrong_types():
    assert forge(None)["errors"] == {"form": "Form must be an object."}
    assert "role" in forge({**BASE, "role": 5})["errors"]
    assert "format" in forge({**BASE, "format": "nope"})["errors"]


def test_ignores_unknown_keys():
    assert forge({**BASE, "__proto__": "x", "extra": 1})["ok"]


def test_strips_list_markers():
    assert validate(BASE).steps == ("Design the schema", "Write the endpoints", "Add tests")


# --- text helpers -----------------------------------------------------------

@pytest.mark.parametrize("role,expected", [
    ("senior backend engineer", "You are a senior backend engineer."),
    ("Expert copywriter", "You are an expert copywriter."),
    ("AWS architect", "You are an AWS architect."),
    ("You are a tutor", "You are a tutor."),
    ("the release manager", "You are the release manager."),
])
def test_role_sentence(role, expected):
    assert role_sentence(role) == expected


def test_slugify():
    assert slugify("  Senior Backend Engineer!! ") == "senior-backend-engineer"
    assert slugify("***") == "untitled"
    assert slugify("Build a REST API for a todo app with auth", 40, "_") == "build_a_rest_api_for_a_todo_app_with"


def test_yaml_string_escapes():
    assert yaml_string('say "hi" \\ there') == '"say \\"hi\\" \\\\ there"'


# --- standard ---------------------------------------------------------------

def test_xml_for_claude_markdown_for_others():
    assert "<task>" in content(model="claude-opus")
    gpt = content(model="gpt")
    assert "## Task" in gpt and "<task>" not in gpt


def test_omits_empty_optional_sections():
    c = content(steps="", context="")
    assert "<steps>" not in c and "<context>" not in c


def test_verbosity_and_budget():
    concise = content(verbosity="concise", tokenBudget="800")
    assert "Be brief" in concise and "800 tokens" in concise and "<quality_check>" not in concise
    assert "<quality_check>" in content(verbosity="detailed")


# --- ralph ------------------------------------------------------------------

def test_ralph_files_and_promise():
    r = ok(format="ralph", maxIterations="7")
    assert [f["path"] for f in r["files"]] == ["PROMPT.md", "fix_plan.md", "ralph.ps1", "ralph.sh"]
    files = [f["content"] for f in r["files"]]
    assert "<promise>COMPLETE</promise>" in files[0]
    assert "- [ ] Design the schema" in files[1]
    assert "$MaxIterations = 7" in files[2]
    assert "MAX_ITERATIONS:-7" in files[3]


@pytest.mark.parametrize("model,cli", [("gpt", "codex exec"), ("gemini", "gemini --yolo"), ("claude-sonnet", "claude -p"),
                                       ("open-source", "aider")])
def test_ralph_cli_follows_model(model, cli):
    assert cli in content(3, format="ralph", model=model)


# --- graph ------------------------------------------------------------------

def test_graph_ids_unique_and_edges_valid():
    g = build_graph(validate({**BASE, "format": "graph", "steps": "Plan\nPlan\nevaluate"}))
    ids = [n["id"] for n in g["nodes"]]
    assert ids == ["plan", "plan_2", "step_3_evaluate", "evaluate"]
    assert g["entry"] == "plan"
    assert len([e for e in g["edges"] if e["from"] == "evaluate"]) == 4
    assert all(e["to"] in {*ids, "__end__"} for e in g["edges"])


def test_graph_json_is_valid():
    r = ok(format="graph")
    json.loads(r["files"][1]["content"])
    assert "ROUTE: END" in r["files"][0]["content"]


# --- agent ------------------------------------------------------------------

def test_claude_subagent():
    f = ok(format="agent", model="claude-haiku")["files"][0]
    assert f["path"] == ".claude/agents/senior-backend-engineer.md"
    assert f["content"].startswith(
        '---\nname: senior-backend-engineer\ndescription: "Use this agent to build a REST API for a todo app."\nmodel: haiku\n---'
    )


def test_portable_agent():
    f = ok(format="agent", model="gemini")["files"][0]
    assert f["path"] == "agents/senior-backend-engineer.md"
    assert "target_model: gemini" in f["content"]


# --- server protocol --------------------------------------------------------

def run_server(*lines: str) -> list[dict]:
    out = io.StringIO()
    serve(io.StringIO("".join(line + "\n" for line in lines)), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_server_round_trip_and_errors():
    responses = run_server(
        json.dumps({"id": 1, "method": "ping"}),
        "not json",
        json.dumps({"id": 2, "method": "forge", "params": {**BASE, "task": "Écrire un résumé — vite"}}),
        json.dumps({"id": 3, "method": "nope"}),
        json.dumps({"id": 4, "method": "meta"}),
        json.dumps({"id": 5, "method": "shutdown"}),
        json.dumps({"id": 6, "method": "ping"}),  # never reached
    )
    assert [r.get("id") for r in responses] == [1, None, 2, 3, 4, 5]
    assert responses[1]["error"]["code"] == "bad_json"
    assert "Écrire" in responses[2]["result"]["files"][0]["content"]
    assert responses[3]["error"]["code"] == "unknown_method"
    assert len(responses[4]["result"]["formats"]) == 4


def test_server_output_is_ascii():
    out = io.StringIO()
    serve(io.StringIO(json.dumps({"id": 1, "method": "forge", "params": {**BASE, "role": "ingénieur"}}) + "\n"), out)
    assert out.getvalue().isascii()
