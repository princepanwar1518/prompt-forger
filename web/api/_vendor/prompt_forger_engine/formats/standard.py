from __future__ import annotations

from ..models import ModelProfile
from ..output import ForgeFile
from ..schema import ForgeInput
from ..sections import (
    Section, constraints_section, context_section, examples_section, output_format_section, output_rules,
    quality_check, render, role_section, steps_section, success_section,
)


def forge_standard(inp: ForgeInput, profile: ModelProfile) -> list[ForgeFile]:
    checks = [
        "every part of the task is addressed",
        "facts are accurate and any assumptions are stated",
        "the response follows the output requirements above",
    ]
    if inp.constraints:
        checks.append("no constraint is broken")
    if inp.success_criteria:
        checks.append("every success criterion is met")
    sections = [
        role_section(inp),
        context_section(inp),
        Section("task", "Task", inp.task),
        steps_section(inp.steps),
        constraints_section(inp),
        success_section(inp),
        examples_section(inp, profile.style),
        output_format_section(inp),
        output_rules(inp, profile, "response"),
        quality_check(inp, checks),
    ]
    return [ForgeFile("prompt.md", "markdown", "Paste this as the system prompt or the first message.",
                      render(sections, profile.style))]
