"""'Describe it': plain language -> form fields, via offline rules or an AI provider.

The AI only proposes form fields. They are cleaned, length-limited and merged onto the current form,
and the normal forge/validation path builds the prompt, so the user always reviews structured fields.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..schema import DEFAULT_FORM, FORMAT_FIELDS_FROM_AI, OUTPUT_FORMATS, VERBOSITY_LEVELS
from .providers import ProviderConfig, ProviderError, chat
from .rules import describe_with_rules

MAX_DESCRIPTION = 4_000

_SYSTEM = """You turn a person's plain-language request into the fields of a structured AI prompt.
The request may be in English, Hindi or Hinglish; always write the fields in clear English unless the request asks for another output language.
Reply with ONE JSON object and nothing else, using exactly these keys:
{
  "role": "who the AI should act as, specific (e.g. 'senior tax accountant'), max 12 words",
  "task": "what needs to be done, 1-3 sentences, specific and measurable",
  "steps": ["ordered steps, 0-8 items, each a short imperative"],
  "context": "background the AI needs (audience, situation, inputs), may be empty",
  "constraints": ["rules the AI must follow, 0-6 items"],
  "successCriteria": ["checkable conditions for 'done', 1-5 items"],
  "outputSchema": "exact shape of the answer (template, sections or JSON), may be empty",
  "examples": [],
  "format": "standard | ralph | graph | agent",
  "verbosity": "concise | balanced | detailed",
  "questions": ["0-3 short questions, ONLY if the request is too vague to fill the fields well"]
}
Use "ralph" only for long autonomous coding work that loops until done, "graph" for multi-stage work with review, "agent" for a reusable assistant definition, otherwise "standard".
Never invent facts about the person; put unknowns in "questions"."""

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
_LIMITS = {"role": 300, "task": 8000, "context": 50000, "outputSchema": 10000}


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = _FENCE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Some models wrap JSON in prose: take the outermost object.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise json.JSONDecodeError("not an object", cleaned, 0)
    return data


def _as_lines(value: Any, limit: int = 50) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(v).strip() for v in value[:limit] if str(v).strip())
    return ""


def _from_ai(data: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    form: dict[str, str] = {}
    for key in ("role", "task", "context", "outputSchema"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            form[key] = v.strip()[:_LIMITS[key]]
    for key in ("steps", "constraints", "successCriteria"):
        v = _as_lines(data.get(key))
        if v:
            form[key] = v
    ex = data.get("examples")
    if isinstance(ex, list) and ex:
        form["examples"] = "\n---\n".join(str(e).strip() for e in ex[:10] if str(e).strip())
    if data.get("format") in OUTPUT_FORMATS:
        form["format"] = data["format"]
    if data.get("verbosity") in VERBOSITY_LEVELS:
        form["verbosity"] = data["verbosity"]
    qs = data.get("questions")
    questions = [str(q).strip() for q in qs[:3] if str(q).strip()] if isinstance(qs, list) else []
    return form, questions


_RESULT_Q = re.compile(r"what exactly should the result be", re.IGNORECASE)
_WHO_Q = re.compile(r"\bwho\b.*\bfor\b|\baudience\b|who will read", re.IGNORECASE)
_GOOD_Q = re.compile(r"how will you know|what does success look like|good\?$", re.IGNORECASE)


def _answers(raw: Any) -> list[tuple[str, str]]:
    """Accepts [{"question": q, "answer": a}] (or plain strings) and keeps the non-empty answers."""
    out: list[tuple[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:5]:
        if isinstance(item, dict):
            q, a = str(item.get("question") or "").strip(), str(item.get("answer") or "").strip()
        else:
            q, a = "", str(item).strip()
        if a:
            out.append((q[:300], a[:500]))
    return out


def _rules_text(original: str, qa: list[tuple[str, str]]) -> str:
    """The deliverable answer joins the request so the rules recognise the intent ("an email")."""
    extra = [a for q, a in qa if _RESULT_Q.search(q)]
    return f"{original.rstrip('.')}. I need {extra[0]}." if extra else original


def _sentence(s: str) -> str:
    s = s.strip().rstrip(".")
    return (s[:1].upper() + s[1:] + ".") if s else s


def _apply_answers(fields: dict[str, str], original: str, qa: list[tuple[str, str]]) -> None:
    """Puts each answer where it belongs instead of gluing everything into the task."""
    if not qa:
        return
    task = _sentence(original)
    other: list[str] = []
    for q, a in qa:
        if _RESULT_Q.search(q):
            task = f"{task} Deliverable: {a.rstrip('.')}."
        elif _WHO_Q.search(q):
            fields["context"] = (fields.get("context", "") + f"\nAudience: {a.rstrip('.')}.").strip()
        elif _GOOD_Q.search(q):
            existing = fields.get("successCriteria", "")
            fields["successCriteria"] = (_sentence(a) + ("\n" + existing if existing else "")).strip()
        else:
            other.append(f"{q} {a}".strip())
    fields["task"] = task
    if other:
        fields["context"] = (fields.get("context", "") + "\n" + "\n".join(other)).strip()
    # Drop a context line the rules guessed if the user told us the audience explicitly.
    lines = fields.get("context", "").splitlines()
    if sum(1 for line in lines if line.startswith("Audience:")) > 1:
        fields["context"] = "\n".join([l for l in lines if not l.startswith("Audience:")] +
                                       [next(l for l in reversed(lines) if l.startswith("Audience:"))]).strip()


def describe(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ProviderError("Describe needs an object.", "bad_request")
    text = str(params.get("text") or "").strip()
    if not text:
        raise ProviderError("Describe what you need in a sentence or two first.", "bad_request")
    if len(text) > MAX_DESCRIPTION:
        raise ProviderError(f"Keep the description under {MAX_DESCRIPTION:,} characters.", "bad_request")
    qa = _answers(params.get("answers"))
    original = text

    current = params.get("form") if isinstance(params.get("form"), dict) else {}
    base = {k: str(current.get(k, DEFAULT_FORM[k])) for k in DEFAULT_FORM}
    provider = str(params.get("provider") or "rules")

    notes: list[str] = []
    if provider == "rules":
        r = describe_with_rules(_rules_text(original, qa))
        fields, questions, source, confidence = r.form, r.questions, "rules", r.confidence
        notes.extend(r.notes)
        _apply_answers(fields, original, qa)
        if qa:
            questions = []  # the user already answered; don't ask again
    else:
        cfg = ProviderConfig.from_params(params)
        prompt = original
        if qa:
            prompt += "\n\nAnswers to your clarifying questions:\n" + "\n".join(f"- {q} {a}" for q, a in qa)
        reply = chat(cfg, _SYSTEM, prompt, json_mode=True)
        try:
            fields, questions = _from_ai(_parse_json(reply))
            source, confidence = cfg.provider, 0.9
        except (json.JSONDecodeError, ValueError):
            r = describe_with_rules(text)
            fields, questions, source, confidence = r.form, r.questions, "rules", r.confidence
            notes.append("The AI's reply wasn't usable, so the offline rules filled the form instead.")
        if "task" not in fields or "role" not in fields:
            fallback = describe_with_rules(text)
            for k in ("role", "task"):
                fields.setdefault(k, fallback.form.get(k, ""))
            notes.append("The AI left some required fields empty; the offline rules filled them.")

    # Fields the describer produced replace the current ones; target model and limits are kept.
    merged = {**base, **{k: v for k, v in fields.items() if k in FORMAT_FIELDS_FROM_AI}}
    return {
        "form": merged,
        "filled": sorted(k for k in fields if k in FORMAT_FIELDS_FROM_AI),
        "questions": questions,
        "confidence": confidence,
        "source": source,
        "notes": notes,
    }
