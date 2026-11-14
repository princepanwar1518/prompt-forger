"""Enhance (with AI) and reply rating.

enhance(): offline fixes always; with a provider, an AI rewrite too. The better-scoring version wins and
every change is listed for the user to accept or discard.

rate(): scores an AI reply against the prompt's own success criteria, constraints, output format and
budget. Format and length are checked deterministically; criteria that need judgement go to an AI judge
when a provider is chosen, otherwise they are reported as "not checked" instead of guessed.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..enhance import Change, diff_changes, enhance_offline, score_of
from ..schema import DEFAULT_FORM, parse_lines
from ..text import estimate_tokens
from .describe import _from_ai, _parse_json
from .providers import ProviderConfig, ProviderError, chat

MAX_REPLY = 200_000

_ENHANCE_SYSTEM = """You improve structured AI prompts. You receive the current prompt fields as JSON and a list of issues.
Return ONE JSON object with exactly these keys, improved:
{"role": str, "task": str, "steps": [str], "context": str, "constraints": [str], "successCriteria": [str], "outputSchema": str, "examples": [str]}
Rules: keep the person's intent, audience and facts; never invent facts, names or numbers; make the task specific and measurable;
success criteria must be checkable yes/no; at most 8 steps; keep existing good content; reply with JSON only."""

_JUDGE_SYSTEM = """You are a strict, fair evaluator of an AI's reply. For each numbered check, decide if the reply satisfies it.
Reply with ONE JSON object: {"results": [{"id": "c1", "pass": true, "reason": "max 20 words"}], "summary": "one sentence"}
Judge only what is in the reply. If a check can't be judged from the reply, set "pass": false and say why."""

_LENGTH = re.compile(r"\b(?:under|max(?:imum)?|less than|at most|within|no more than)\s+(\d{1,5})\s+(words|characters|chars|lines)\b",
                     re.IGNORECASE)
_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_LABEL = re.compile(r"^\s*([A-Z][A-Za-z ]{1,30}):\s*<", re.MULTILINE)
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


def _form(params: dict[str, Any]) -> dict[str, str]:
    raw = params.get("form") if isinstance(params.get("form"), dict) else {}
    return {k: str(raw.get(k, DEFAULT_FORM[k])) for k in DEFAULT_FORM}


# ---------------------------------------------------------------- enhance

def enhance(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ProviderError("Enhance needs an object.", "bad_request")
    original = _form(params)
    before = score_of(original)
    if before is None:
        raise ProviderError("Fill in Role and Task before enhancing.", "bad_request")

    offline_form, offline_changes, needs_you = enhance_offline(original)
    offline_score = score_of(offline_form) or before
    result: dict[str, Any] = {
        "form": offline_form, "changes": [c.to_dict() for c in offline_changes], "needsYou": needs_you,
        "before": before, "after": offline_score, "source": "offline", "notes": [],
    }

    provider = str(params.get("provider") or "rules")
    if provider == "rules":
        return result

    cfg = ProviderConfig.from_params(params)
    from ..forge import forge
    issues = forge(original)["quality"]["findings"]
    payload = {k: original[k] for k in ("role", "task", "steps", "context", "constraints", "successCriteria",
                                        "outputSchema", "examples")}
    user = json.dumps({"fields": payload, "issues": [i["message"] for i in issues]}, ensure_ascii=False)
    try:
        fields, _ = _from_ai(_parse_json(chat(cfg, _ENHANCE_SYSTEM, user, json_mode=True, max_tokens=2500)))
    except (json.JSONDecodeError, ValueError):
        result["notes"].append("The AI's rewrite wasn't usable, so only the offline fixes are shown.")
        return result

    ai_form = {**original, **{k: v for k, v in fields.items() if k not in ("format", "verbosity")}}
    for key in ("role", "task"):  # never let the AI blank a required field
        if not ai_form[key].strip():
            ai_form[key] = original[key]
    ai_form, extra, needs_you_ai = enhance_offline(ai_form)
    ai_score = score_of(ai_form)
    if ai_score is not None and ai_score >= offline_score:
        changes = diff_changes(original, ai_form, f"Rewritten by {cfg.provider} and checked offline.")
        result.update(form=ai_form, changes=[c.to_dict() for c in changes], needsYou=needs_you_ai,
                      after=ai_score, source=cfg.provider)
    else:
        result["notes"].append("The AI's rewrite scored lower than the offline fixes, so the offline version is shown.")
    return result


# ---------------------------------------------------------------- rate

def _check(kind: str, item: str, passed: bool | None, reason: str, how: str) -> dict[str, Any]:
    return {"kind": kind, "item": item, "passed": passed, "reason": reason, "how": how}


def _count(n_unit: str, reply: str) -> int:
    unit = n_unit.lower()
    if unit.startswith("word"):
        return len(re.findall(r"\b[\w'’-]+\b", reply))
    if unit.startswith("line"):
        return len([l for l in reply.splitlines() if l.strip()])
    return len(reply)


def _format_checks(schema: str, reply: str) -> list[dict[str, Any]]:
    schema = schema.strip()
    if not schema:
        return []
    if schema[:1] in ("{", "["):
        try:
            data = json.loads(_FENCE.sub("", reply.strip()))
        except json.JSONDecodeError:
            return [_check("format", "Reply is valid JSON", False, "The reply is not valid JSON.", "automatic")]
        out = [_check("format", "Reply is valid JSON", True, "Parsed successfully.", "automatic")]
        try:
            keys = list(json.loads(schema).keys()) if schema.startswith("{") else []
        except (json.JSONDecodeError, AttributeError):
            keys = []
        if keys and isinstance(data, dict):
            missing = [k for k in keys if k not in data]
            out.append(_check("format", "JSON has every field of the schema", not missing,
                              "All fields present." if not missing else f"Missing: {', '.join(missing)}.", "automatic"))
        return out
    out = []
    low = reply.lower()
    for h in _HEADING.findall(schema):
        name = re.sub(r"\(.*?\)|<.*?>", "", h).strip(" :")
        if name:
            ok = name.lower() in low
            out.append(_check("format", f"Has section \"{name}\"", ok, "Found." if ok else "Section not found.", "automatic"))
    for label in _LABEL.findall(schema):
        ok = re.search(rf"^\s*{re.escape(label)}\s*:", reply, re.IGNORECASE | re.MULTILINE) is not None
        out.append(_check("format", f"Has \"{label}:\" line", ok, "Found." if ok else "Line not found.", "automatic"))
    return out


def rate(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ProviderError("Rating needs an object.", "bad_request")
    reply = str(params.get("reply") or "")
    if not reply.strip():
        raise ProviderError("There is no reply to rate yet. Run Test it first.", "bad_request")
    if len(reply) > MAX_REPLY:
        raise ProviderError("The reply is too long to rate.", "bad_request")
    form = _form(params)
    checks: list[dict[str, Any]] = []

    # Deterministic: output format, length limits, token budget.
    checks += _format_checks(form["outputSchema"], reply)
    judge_items: list[tuple[str, str]] = []  # (kind, text) needing judgement
    for c in parse_lines(form["constraints"]):
        m = _LENGTH.search(c)
        if m:
            n, used = int(m.group(1)), _count(m.group(2), reply)
            checks.append(_check("constraint", c, used <= n, f"{used} {m.group(2).lower()} (limit {n}).", "automatic"))
        else:
            judge_items.append(("constraint", c))
    for c in parse_lines(form["successCriteria"]):
        m = _LENGTH.search(c)
        if m:
            n, used = int(m.group(1)), _count(m.group(2), reply)
            checks.append(_check("success", c, used <= n, f"{used} {m.group(2).lower()} (limit {n}).", "automatic"))
        else:
            judge_items.append(("success", c))
    if form["tokenBudget"].strip().isdigit():
        budget, used = int(form["tokenBudget"]), estimate_tokens(reply)
        checks.append(_check("budget", f"Within about {budget:,} tokens", used <= budget * 1.1,
                             f"About {used:,} tokens.", "automatic"))

    provider = str(params.get("provider") or "rules")
    judge = "offline"
    summary = ""
    if judge_items and provider != "rules":
        cfg = ProviderConfig.from_params(params)
        numbered = [{"id": f"c{i}", "check": text} for i, (_, text) in enumerate(judge_items, start=1)]
        user = json.dumps({"task": form["task"], "checks": numbered, "reply": reply[:60_000]}, ensure_ascii=False)
        try:
            data = _parse_json(chat(cfg, _JUDGE_SYSTEM, user, json_mode=True, max_tokens=1500))
            by_id = {str(r.get("id")): r for r in data.get("results", []) if isinstance(r, dict)}
            for i, (kind, text) in enumerate(judge_items, start=1):
                r = by_id.get(f"c{i}")
                if r is None:
                    checks.append(_check(kind, text, None, "The judge skipped this check.", cfg.provider))
                else:
                    checks.append(_check(kind, text, bool(r.get("pass")), str(r.get("reason", ""))[:200], cfg.provider))
            summary = str(data.get("summary", ""))[:300]
            judge = cfg.provider
        except (json.JSONDecodeError, ValueError, AttributeError):
            judge_items_left = judge_items
            for kind, text in judge_items_left:
                checks.append(_check(kind, text, None, "The AI judge's answer was unreadable.", "offline"))
    else:
        for kind, text in judge_items:
            checks.append(_check(kind, text, None, "Needs an AI judge: pick Claude, OpenAI or Ollama to check this.", "offline"))

    decided = [c for c in checks if c["passed"] is not None]
    passed = sum(1 for c in decided if c["passed"])
    accuracy = round(100 * passed / len(decided)) if decided else None
    coverage = round(100 * len(decided) / len(checks)) if checks else 0
    if accuracy is None:
        verdict = "Nothing to check yet: add success criteria, constraints or an output schema."
    elif accuracy >= 90:
        verdict = "Meets the brief."
    elif accuracy >= 60:
        verdict = "Partly meets the brief."
    else:
        verdict = "Misses the brief."
    return {"accuracy": accuracy, "passed": passed, "checked": len(decided), "total": len(checks),
            "coverage": coverage, "verdict": verdict, "summary": summary, "judge": judge, "checks": checks}


__all__ = ["enhance", "rate", "Change"]
