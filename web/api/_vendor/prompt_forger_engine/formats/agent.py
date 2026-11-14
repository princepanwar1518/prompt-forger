"""Agent profile: YAML front matter + system prompt (Claude Code subagent format for Claude models)."""

from __future__ import annotations

import re

from ..models import ModelProfile
from ..output import ForgeFile
from ..schema import ForgeInput
from ..sections import (
    Section, constraints_section, context_section, examples_section, output_format_section, output_rules, render,
    role_section, steps_section, success_section,
)
from ..text import bullets, first_sentence, lower_first, slugify, yaml_string


def forge_agent(inp: ForgeInput, profile: ModelProfile) -> list[ForgeFile]:
    name = slugify(inp.role, 40, "-")
    summary = re.sub(r"[.!?]$", "", first_sentence(inp.task, 220))
    description = f"Use this agent to {lower_first(summary)}."
    model_line = (
        f"model: {profile.claude_agent_model}" if profile.claude_agent_model else f"target_model: {profile.id}"
    )
    lines = ["---", f"name: {name}", f"description: {yaml_string(description)}"]
    if inp.tools:
        # Claude Code reads a comma-separated allowlist; portable profiles use a YAML list.
        lines.append("tools: " + ", ".join(inp.tools) if profile.claude_agent_model
                     else "tools: [" + ", ".join(yaml_string(t) for t in inp.tools) + "]")
    lines += [model_line, "---"]
    front_matter = "\n".join(lines)

    sections = [
        role_section(inp),
        Section("purpose", "Purpose", inp.task),
        context_section(inp),
        steps_section(inp.steps, "For every request:").renamed("workflow", "Workflow"),
        Section("boundaries", "Boundaries", bullets([
            "Stay within this purpose. If a request falls outside it, say so and hand control back.",
            "Ask one focused question when a missing detail would change the result; otherwise proceed and state your assumption.",
            "Never invent facts, file contents or tool results.",
            *inp.constraints,
        ])),
        success_section(inp, "A request is done when:"),
        examples_section(inp, "markdown"),
        output_format_section(inp),
        output_rules(inp, profile, "turn"),
    ]
    # Agent profile bodies are read as a system prompt; Markdown headings are the convention for these files.
    body = render(sections, "markdown")

    if profile.claude_agent_model:
        path = f".claude/agents/{name}.md"
        desc = "Claude Code subagent. Save into your project root; Claude Code loads it from .claude/agents/."
    else:
        path = f"agents/{name}.md"
        desc = "Portable agent profile: YAML front matter plus a system prompt."
    return [ForgeFile(path, "markdown", desc, f"{front_matter}\n\n{body}")]
