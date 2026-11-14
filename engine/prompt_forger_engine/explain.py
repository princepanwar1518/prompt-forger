"""Plain-language summary of what a forged prompt will make the model do. No AI needed."""

from __future__ import annotations

from .models import MODEL_PROFILES
from .schema import ForgeInput
from .text import role_sentence

_FORMAT_PLAIN = {
    "standard": "a single prompt you paste into a chat or an API call",
    "ralph": "a Ralph loop: an AI agent repeats the same instructions, one task at a time, until it reports it is finished",
    "graph": "a graph loop: the AI works through a fixed set of stages and a checker sends work back to a stage if it isn't good enough",
    "agent": "a reusable agent profile that a tool like Claude Code can call on whenever this kind of job comes up",
}
_VERBOSITY_PLAIN = {
    "concise": "short and to the point",
    "balanced": "clear and complete, without padding",
    "detailed": "thorough, with reasoning, edge cases and examples",
}


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _lower_first(s: str) -> str:
    return s[:1].lower() + s[1:] if s[1:2].islower() else s


def explain(inp: ForgeInput) -> str:
    profile = MODEL_PROFILES[inp.model]
    who = role_sentence(inp.role).removeprefix("You are ").rstrip(".")
    lines: list[str] = [
        f"This is {_FORMAT_PLAIN[inp.format]}, written for {profile.label}.",
        f"It asks the AI to act as {who} and to: {_lower_first(inp.task.rstrip('.'))}.",
    ]
    if inp.steps:
        n = len(inp.steps)
        lines.append(f"It works in {n} step{'s' if n != 1 else ''}, starting with \"{_lower_first(inp.steps[0])}\""
                     + (f" and ending with \"{_lower_first(inp.steps[-1])}\"." if n > 1 else "."))
    if inp.context:
        lines.append("It includes background information so the AI doesn't have to guess your situation.")
    if inp.constraints:
        n = len(inp.constraints)
        lines.append(f"It sets {n} rule{'s' if n != 1 else ''} the AI must follow, such as \"{_lower_first(inp.constraints[0])}\".")
    if inp.success_criteria:
        lines.append(f"It defines when the work counts as done: {_join([_lower_first(c.rstrip('.')) for c in inp.success_criteria[:3]])}.")
    if inp.examples:
        n = len(inp.examples)
        lines.append(f"It shows {n} example{'s' if n != 1 else ''} of the kind of answer you want.")
    if inp.output_schema:
        lines.append("It tells the AI exactly what shape the answer must have.")
    lines.append(f"Answers should be {_VERBOSITY_PLAIN[inp.verbosity]}"
                 + (f", and no longer than about {inp.token_budget:,} tokens (~{round(inp.token_budget * 0.75):,} words)."
                    if inp.token_budget else "."))
    if inp.format == "ralph":
        n = inp.max_iterations or 20
        lines.append(f"The loop stops after {n} rounds at most, even if the work isn't finished.")
    if inp.format == "graph":
        n = inp.max_iterations or 3
        lines.append(f"The checker can send work back at most {n} time{'s' if n != 1 else ''}.")
    if inp.format == "agent" and inp.tools:
        lines.append(f"The agent may only use these tools: {_join(list(inp.tools))}.")
    return " ".join(lines)
