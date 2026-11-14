"""Pure entry point: raw form in, generated files (or field errors) out."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .formats.agent import forge_agent
from .formats.graph import forge_graph
from .formats.ralph import forge_ralph
from .formats.standard import forge_standard
from .explain import explain
from .lint import check, dimensions, grade, score
from .models import MODEL_PROFILES, ModelProfile
from .output import ForgeFile
from .schema import ForgeInput, ValidationError, validate

Generator = Callable[[ForgeInput, ModelProfile], list[ForgeFile]]

_GENERATORS: dict[str, Generator] = {
    "standard": forge_standard,
    "ralph": forge_ralph,
    "graph": forge_graph,
    "agent": forge_agent,
}


def _warnings(inp: ForgeInput) -> list[str]:
    """Format-specific notes; quality issues live in the checker (lint)."""
    w: list[str] = []
    if inp.format == "graph" and len(inp.steps) > 12:
        w.append("Graphs with more than 12 nodes get hard for a model to follow. Consider grouping steps.")
    if inp.format == "ralph" and not inp.steps:
        w.append("No steps given: the first Ralph iteration will spend its turn writing the plan.")
    if inp.tools and inp.format != "agent":
        w.append("Tools only apply to agent profiles; they are ignored here.")
    if inp.model == "claude-haiku" and inp.verbosity == "detailed" and inp.format != "standard":
        w.append("Haiku is fastest on tight, focused prompts. Consider Balanced verbosity for loops.")
    if inp.max_iterations is not None and inp.format in ("standard", "agent"):
        w.append("Max iterations only applies to Ralph and graph loops; it is ignored here.")
    return w


def forge(form: Any) -> dict[str, Any]:
    """Returns {"ok": True, "files": [...], "warnings": [...]} or {"ok": False, "errors": {field: message}}."""
    try:
        inp = validate(form)
    except ValidationError as exc:
        return {"ok": False, "errors": exc.errors}
    files = _GENERATORS[inp.format](inp, MODEL_PROFILES[inp.model])
    findings = check(inp)
    points = score(findings)
    return {
        "ok": True,
        "files": [f.to_dict() for f in files],
        "warnings": _warnings(inp),
        "quality": {"score": points, "grade": grade(points), "findings": [x.to_dict() for x in findings],
                    "dimensions": dimensions(inp, findings)},
        "explanation": explain(inp),
        "variables": list(inp.variables) + [v for v in inp.unresolved_variables if v not in inp.variables],
    }


def meta() -> dict[str, Any]:
    """Option lists for the UI, so labels and hints live in one place."""
    return {
        "formats": [
            {"id": "standard", "label": "Standard prompt", "hint": "One prompt for any chat or API call"},
            {"id": "ralph", "label": "Ralph loop", "hint": "PROMPT.md + plan + runner scripts for an agent loop"},
            {"id": "graph", "label": "Graph loop", "hint": "Node/edge state graph with an evaluator that routes back"},
            {"id": "agent", "label": "Agent profile", "hint": "Reusable subagent file with front matter"},
        ],
        "models": [{"id": p.id, "label": p.label, "hint": p.hint} for p in MODEL_PROFILES.values()],
        "providers": [
            {"id": "rules", "label": "Offline rules", "hint": "Free, instant, works offline"},
            {"id": "anthropic", "label": "Claude", "hint": "Best results; needs an Anthropic API key"},
            {"id": "openai", "label": "OpenAI", "hint": "Needs an OpenAI API key"},
            {"id": "ollama", "label": "Ollama (local)", "hint": "Free and private; runs on this computer"},
        ],
        "verbosity": [
            {"id": "concise", "label": "Concise"},
            {"id": "balanced", "label": "Balanced"},
            {"id": "detailed", "label": "Detailed"},
        ],
    }
