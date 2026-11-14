"""Section building blocks and the XML / Markdown renderer."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from .models import ModelProfile, PromptStyle
from .schema import ForgeInput
from .text import bullets, numbered, role_sentence

Scope = Literal["response", "iteration", "turn"]


@dataclass(frozen=True, slots=True)
class Section:
    tag: str  # snake_case, used as the XML tag
    title: str  # heading used in Markdown style
    body: str

    def renamed(self, tag: str, title: str) -> "Section":
        return replace(self, tag=tag, title=title)


def render(sections: Iterable[Section], style: PromptStyle) -> str:
    parts = []
    for s in sections:
        body = s.body.strip()
        if not body:
            continue
        parts.append(f"<{s.tag}>\n{body}\n</{s.tag}>" if style == "xml" else f"## {s.title}\n\n{body}")
    return "\n\n".join(parts) + "\n"


_VERBOSITY_RULES = {
    "concise": "Be brief. Lead with the answer, skip preamble and recaps, and use bullets only for genuine lists.",
    "balanced": "Be clear and complete without padding. Briefly explain key decisions.",
    "detailed": "Be thorough. Explain your reasoning, cover edge cases and trade-offs, and include examples where they help.",
}


def verbosity_rule(verbosity: str) -> str:
    return _VERBOSITY_RULES[verbosity]


def budget_rule(budget: int | None, scope: Scope) -> str | None:
    if budget is None:
        return None
    words = round(budget * 0.75 / 10) * 10
    lead = {
        "response": "Keep the response",
        "iteration": "Keep the written output of each iteration",
        "turn": "Keep each reply",
    }[scope]
    return (
        f"{lead} within about {budget:,} tokens (~{words:,} words). "
        "If it will not fit, prioritise the most important parts and say what you left out."
    )


def role_section(inp: ForgeInput) -> Section:
    extra = (
        "\nHold your work to the standard an experienced practitioner in this role would expect."
        if inp.verbosity == "detailed"
        else ""
    )
    return Section("role", "Role", role_sentence(inp.role) + extra)


def context_section(inp: ForgeInput) -> Section:
    return Section("context", "Context", inp.context)


def steps_section(steps: Sequence[str], intro: str = "Work through these steps in order:") -> Section:
    return Section("steps", "Steps", f"{intro}\n{numbered(steps)}" if steps else "")


def output_rules(inp: ForgeInput, profile: ModelProfile, scope: Scope, extra: Sequence[str] = ()) -> Section:
    rules = [
        verbosity_rule(inp.verbosity),
        budget_rule(inp.token_budget, scope),
        None if inp.verbosity == "concise" else "If something is ambiguous, state the assumption you made and continue.",
        profile.style_note,
        *extra,
    ]
    return Section("output_requirements", "Output requirements", bullets(r for r in rules if r))


def quality_check(inp: ForgeInput, checks: Sequence[str]) -> Section:
    if inp.verbosity != "detailed":
        return Section("quality_check", "Quality check", "")
    return Section("quality_check", "Before you respond", "Check that:\n" + bullets(checks))


# ---------------------------------------------------------------- new fields

def constraints_section(inp: ForgeInput) -> Section:
    return Section("constraints", "Constraints", bullets(inp.constraints) if inp.constraints else "")


def success_section(inp: ForgeInput, intro: str = "The work is done when:") -> Section:
    body = f"{intro}\n{bullets(inp.success_criteria)}" if inp.success_criteria else ""
    return Section("success_criteria", "Success criteria", body)


def examples_section(inp: ForgeInput, style: PromptStyle) -> Section:
    if not inp.examples:
        return Section("examples", "Examples", "")
    intro = "Match the style and quality of these examples. Do not copy their content."
    if style == "xml":
        inner = "\n".join(f"<example>\n{e}\n</example>" for e in inp.examples)
    else:
        inner = "\n\n".join(f"### Example {i}\n\n{e}" for i, e in enumerate(inp.examples, start=1))
    return Section("examples", "Examples", f"{intro}\n{inner}" if style == "xml" else f"{intro}\n\n{inner}")


def output_format_section(inp: ForgeInput) -> Section:
    if not inp.output_schema:
        return Section("output_format", "Output format", "")
    fence = "json" if inp.output_schema.lstrip()[:1] in "{[" else ""
    return Section(
        "output_format", "Output format",
        f"Respond in exactly this format, with no text before or after it:\n```{fence}\n{inp.output_schema}\n```",
    )
