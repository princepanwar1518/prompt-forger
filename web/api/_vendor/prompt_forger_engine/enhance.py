"""Enhance, offline: fixes what the checker found, without AI. Pure and repeatable.

Every fix is recorded as a Change (field, what changed, why) so the user can review before applying.
Things that need real knowledge of the user's situation (vague wording, a missing audience) are left
alone and reported as "needs you", never invented.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from .ai.rules import INTENTS, Intent, normalise
from .lint import _GENERIC_ROLES, _MEASURABLE, _NEGATIVE_HINT, check
from .schema import DEFAULT_FORM, ValidationError, parse_lines, validate

_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")
_GENERIC_SCHEMA = "## Answer\n<the direct answer>\n\n## Details\n<supporting points>\n\n## Next steps\n<what to do now>"
_GENERIC_SUCCESS = ("Every part of the task is addressed.", "The answer follows the output format exactly.")
_GENERIC_LOOP_STEPS = ("Plan the work and list the tasks", "Do the next task", "Check the result against the success criteria")
_READ_ONLY_TOOLS = "Read, Grep, Glob"


@dataclass(frozen=True, slots=True)
class Change:
    field: str
    action: str  # "added" | "changed" | "moved" | "removed"
    summary: str
    before: str = ""
    after: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _intent_for(form: dict[str, str]) -> Intent | None:
    norm = normalise(f"{form.get('role', '')} {form.get('task', '')}")
    best, hits_best = None, 0
    for intent in INTENTS:
        hits = sum(1 for k in intent.keywords if re.search(rf"(?<![a-z]){re.escape(k)}(?:s|es)?(?![a-z])", norm))
        hits += sum(3 for k in intent.strong if k in norm)
        if hits > hits_best:
            best, hits_best = intent, hits
    return best


def _lines(text: str) -> list[str]:
    return list(parse_lines(text))


def enhance_offline(form: dict[str, str]) -> tuple[dict[str, str], list[Change], list[str]]:
    """Returns (improved form, changes made, things only the user can fix)."""
    f = {k: str(form.get(k, DEFAULT_FORM[k])) for k in DEFAULT_FORM}
    changes: list[Change] = []
    needs_you: list[str] = []
    intent = _intent_for(f)

    # 1. Generic role -> the role for the recognised kind of task.
    if f["role"].strip().lower().strip(" .") in _GENERIC_ROLES and intent:
        changes.append(Change("role", "changed", "Made the role specific to the task.", f["role"], intent.role))
        f["role"] = intent.role

    # 2. Rules hidden in the context -> Constraints.
    if f["context"] and _NEGATIVE_HINT.search(f["context"]):
        moved, kept = [], []
        for sentence in (s.strip() for s in _SENTENCE.findall(f["context"])):
            if not sentence:
                continue
            (moved if _NEGATIVE_HINT.search(sentence) else kept).append(sentence)
        if moved:
            existing = _lines(f["constraints"])
            new = existing + [m if m.endswith((".", "!", "?")) else m + "." for m in moved if m not in existing]
            changes.append(Change("constraints", "moved", f"Moved {len(moved)} rule(s) from Context into Constraints.",
                                  f["constraints"], "\n".join(new)))
            f["constraints"] = "\n".join(new)
            f["context"] = " ".join(kept)

    # 3. Duplicate steps.
    steps = _lines(f["steps"])
    deduped = list(dict.fromkeys(s for s in steps))
    if len(deduped) < len(steps):
        changes.append(Change("steps", "removed", f"Removed {len(steps) - len(deduped)} duplicate step(s).",
                              f["steps"], "\n".join(deduped)))
        f["steps"] = "\n".join(deduped)
        steps = deduped

    # 4. Loops with no steps.
    if f["format"] in ("ralph", "graph") and not steps:
        new_steps = list(intent.steps) if intent and intent.steps else list(_GENERIC_LOOP_STEPS)
        changes.append(Change("steps", "added", "Added starting steps so the loop has a plan.", "", "\n".join(new_steps)))
        f["steps"] = "\n".join(new_steps)

    # 5. Success criteria: add when missing; make vague ones checkable.
    success = _lines(f["successCriteria"])
    if not success:
        new = list(intent.success) if intent and intent.success else list(_GENERIC_SUCCESS)
        changes.append(Change("successCriteria", "added", "Added success criteria so \"done\" is checkable.", "", "\n".join(new)))
        f["successCriteria"] = "\n".join(new)
    else:
        rewritten = [c if _MEASURABLE.search(c) else f"Yes/no: {c.rstrip('.')}?" for c in success]
        if rewritten != success:
            changes.append(Change("successCriteria", "changed", "Turned vague criteria into yes/no checks.",
                                  f["successCriteria"], "\n".join(rewritten)))
            f["successCriteria"] = "\n".join(rewritten)

    # 6. Output shape: repair broken JSON, or add a shape when there is none.
    schema = f["outputSchema"].strip()
    if schema[:1] in ("{", "["):
        try:
            json.loads(schema)
        except json.JSONDecodeError:
            repaired = _TRAILING_COMMA.sub(r"\1", schema.replace("'", '"'))
            try:
                json.loads(repaired)
                changes.append(Change("outputSchema", "changed", "Repaired invalid JSON in the output schema.", schema, repaired))
                f["outputSchema"] = repaired
            except json.JSONDecodeError:
                needs_you.append("The output schema is not valid JSON and couldn't be repaired automatically.")
    elif not schema and f["format"] in ("standard", "agent"):
        new = intent.output_schema if intent and intent.output_schema else _GENERIC_SCHEMA
        changes.append(Change("outputSchema", "added", "Added an output format so answers come back in a predictable shape.", "", new))
        f["outputSchema"] = new

    # 7. Budget too small for detailed answers.
    budget = f["tokenBudget"].strip()
    if budget.isdigit():
        n = int(budget)
        floor = 600 if f["verbosity"] == "detailed" else 200
        if n < floor:
            changes.append(Change("tokenBudget", "changed", f"Raised the token budget to {floor} so the answer isn't cut short.",
                                  budget, str(floor)))
            f["tokenBudget"] = str(floor)

    # 8. Claude subagent with every tool -> read-only by default.
    if f["format"] == "agent" and f["model"].startswith("claude") and not f["tools"].strip():
        changes.append(Change("tools", "added", "Limited the agent to read-only tools; add more if it must write.", "", _READ_ONLY_TOOLS))
        f["tools"] = _READ_ONLY_TOOLS

    # Things only the user can fix: report, never invent.
    try:
        inp = validate(f)
        for finding in check(inp):
            if finding.field in ("task", "variables") or (finding.field == "examples"):
                if finding.message not in needs_you:
                    needs_you.append(finding.message)
    except ValidationError as exc:
        needs_you.extend(exc.errors.values())
    return f, changes, needs_you


def diff_changes(before: dict[str, str], after: dict[str, str], why: str) -> list[Change]:
    """Changes between two forms, one per field, for showing an AI rewrite."""
    out = []
    for key in DEFAULT_FORM:
        a, b = before.get(key, ""), after.get(key, "")
        if a.strip() != b.strip():
            action = "added" if not a.strip() else "removed" if not b.strip() else "changed"
            out.append(Change(key, action, why, a, b))
    return out


def score_of(form: dict[str, Any]) -> int | None:
    from .forge import forge  # local import: forge imports this module's siblings

    r = forge(form)
    return r["quality"]["score"] if r["ok"] else None
