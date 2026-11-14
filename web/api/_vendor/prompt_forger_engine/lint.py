"""Prompt checker: rule-based findings plus a 0-100 quality score. Pure, fast, offline."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Literal

from .schema import ForgeInput

Level = Literal["warning", "tip"]

# Words that usually mean the request is under-specified.
_VAGUE = {
    "something", "stuff", "things", "etc", "etc.", "somehow", "good", "nice", "better", "best", "proper",
    "properly", "some", "various", "anything", "whatever", "cool", "awesome", "amazing", "kind of", "sort of",
    # Hinglish filler
    "kuch", "accha", "achha", "acha", "badhiya", "mast", "sahi",
}
_GENERIC_ROLES = {"assistant", "ai", "ai assistant", "helper", "bot", "chatbot", "expert", "model", "llm", "gpt", "claude"}
_NEGATIVE_HINT = re.compile(r"\b(don't|do not|never|avoid|must not|shouldn't|should not)\b", re.IGNORECASE)
_MEASURABLE = re.compile(r"\d|\b(all|every|each|pass|passes|returns?|under|at least|at most|within|exactly|without|zero|"
                         r"no|none|first|match|matches|same|unchanged|can be sent|yes)\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z']+")

# Penalty per finding; the score starts at 100.
_PENALTY = {"warning": 18, "tip": 5}


@dataclass(frozen=True, slots=True)
class Finding:
    level: Level
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _vague_terms(text: str) -> list[str]:
    lowered = f" {text.lower()} "
    found = [v for v in _VAGUE if f" {v} " in lowered or f" {v}," in lowered or f" {v}." in lowered]
    return sorted(set(found))


def check(inp: ForgeInput) -> list[Finding]:
    f: list[Finding] = []
    loop = inp.format in ("ralph", "graph")

    # --- task
    task_words = _words(inp.task)
    if len(task_words) < 4:
        f.append(Finding("warning", "task", "The task doesn't say what to do yet. Describe the result you want in a full sentence."))
    elif len(task_words) < 8:
        f.append(Finding("warning", "task", "The task is very short. Say what you want, for whom, and what a good result looks like."))
    vague = _vague_terms(inp.task)
    if vague:
        f.append(Finding("warning", "task", f"Vague words in the task: {', '.join(vague)}. Replace them with specifics."))

    # --- role
    if inp.role.lower().strip(" .") in _GENERIC_ROLES:
        f.append(Finding("tip", "role", "The role is generic. A specific role (\"senior tax accountant\") gives sharper answers."))

    # --- success criteria
    if not inp.success_criteria:
        if loop:
            f.append(Finding("warning", "successCriteria",
                             "Loops need success criteria, otherwise the agent decides on its own when it is done."))
        else:
            f.append(Finding("tip", "successCriteria", "Add success criteria so the model knows what \"done\" means."))
    else:
        unmeasurable = [c for c in inp.success_criteria if not _MEASURABLE.search(c)]
        if unmeasurable:
            f.append(Finding("tip", "successCriteria",
                             f"Make this criterion checkable (a number, a test, a yes/no): \"{unmeasurable[0]}\"."))

    # --- output shape
    if not inp.output_schema and inp.format in ("standard", "agent"):
        f.append(Finding("tip", "outputSchema", "No output format given. Describe the exact shape you want back (sections, JSON, table)."))
    schema = inp.output_schema.lstrip()
    if schema[:1] in ("{", "["):
        try:
            json.loads(inp.output_schema)
        except json.JSONDecodeError as exc:
            f.append(Finding("warning", "outputSchema", f"The output schema looks like JSON but is not valid JSON ({exc.msg}, line {exc.lineno})."))

    # --- examples
    if len(inp.examples) == 1:
        f.append(Finding("tip", "examples", "One example tends to get copied. Two or three varied examples work better."))

    # --- steps
    lowered_steps = [s.lower() for s in inp.steps]
    dupes = sorted({s for s in lowered_steps if lowered_steps.count(s) > 1})
    if dupes:
        f.append(Finding("warning", "steps", f"Duplicate step: \"{dupes[0]}\"."))
    if len(inp.steps) > 15:
        f.append(Finding("tip", "steps", "More than 15 steps. Group related steps so the model keeps track."))
    short = [s for s in inp.steps if len(_words(s)) < 2]
    if short:
        f.append(Finding("tip", "steps", f"Step \"{short[0]}\" is very short. Say what the step produces."))

    # --- constraints hidden in context
    if inp.context and _NEGATIVE_HINT.search(inp.context) and not inp.constraints:
        f.append(Finding("tip", "constraints", "Your context contains rules (\"don't\", \"never\"). Move them to Constraints so they stand out."))

    # --- budget vs verbosity
    if inp.token_budget is not None:
        if inp.verbosity == "detailed" and inp.token_budget < 400:
            f.append(Finding("warning", "tokenBudget", "Detailed verbosity with a budget under 400 tokens will force the model to cut corners."))
        if inp.token_budget < 200:
            f.append(Finding("warning", "tokenBudget", "A token budget under 200 is very tight."))

    # --- variables
    if inp.unresolved_variables:
        names = ", ".join("{{" + v + "}}" for v in inp.unresolved_variables)
        f.append(Finding("warning", "variables", f"Unfilled variables: {names}. Give them values under Variables."))

    # --- agent tools
    if inp.format == "agent" and inp.model.startswith("claude") and not inp.tools:
        f.append(Finding("tip", "tools", "No tool list: the subagent can use every tool. Restrict it (e.g. Read, Grep) for safety."))

    # --- loops without steps
    if loop and not inp.steps:
        f.append(Finding("tip", "steps", "Loops work best with a few concrete steps to start from."))

    return f


# Each finding counts against one quality dimension, decided by the field it points at.
DIMENSIONS = ("Clarity", "Specificity", "Structure", "Checkability", "Fit")
_DIMENSION_OF_FIELD = {
    "task": "Clarity", "role": "Clarity",
    "context": "Specificity", "constraints": "Specificity", "variables": "Specificity", "examples": "Specificity",
    "steps": "Structure", "outputSchema": "Structure",
    "successCriteria": "Checkability",
    "tokenBudget": "Fit", "tools": "Fit", "maxIterations": "Fit", "format": "Fit",
}
_DIMENSION_PENALTY = {"warning": 35, "tip": 15}
_DIMENSION_HINT = {
    "Clarity": "Is it obvious who the AI is and what it must produce?",
    "Specificity": "Does it give the background, rules and examples the AI can't guess?",
    "Structure": "Are the steps and the answer's shape spelled out?",
    "Checkability": "Can you tell, yes or no, whether the result is done?",
    "Fit": "Do the budget, format and tools suit the job?",
}


def dimension_of(finding: Finding) -> str:
    return _DIMENSION_OF_FIELD.get(finding.field, "Clarity")


def dimensions(inp: ForgeInput, findings: list[Finding]) -> list[dict[str, object]]:
    """0-100 per dimension, so people see *where* a prompt is weak, not only how weak."""
    points = {d: 100 for d in DIMENSIONS}
    for x in findings:
        points[dimension_of(x)] -= _DIMENSION_PENALTY[x.level]
    if not inp.context and not inp.constraints and not inp.examples:
        points["Specificity"] -= 25  # nothing beyond the task itself
    return [{"name": d, "score": max(0, min(100, points[d])), "hint": _DIMENSION_HINT[d]} for d in DIMENSIONS]


def score(findings: list[Finding]) -> int:
    return max(0, 100 - sum(_PENALTY[x.level] for x in findings))


def grade(points: int) -> str:
    if points >= 90:
        return "Excellent"
    if points >= 75:
        return "Good"
    if points >= 55:
        return "Needs work"
    return "Weak"
