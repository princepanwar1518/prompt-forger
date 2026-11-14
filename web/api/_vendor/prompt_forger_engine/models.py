"""Per-model prompt style and the CLI used to run loops headlessly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .schema import TargetModel

PromptStyle = Literal["xml", "markdown"]


@dataclass(frozen=True, slots=True)
class AgentCli:
    name: str
    bash: str  # one headless iteration, prompt read from PROMPT.md
    powershell: str


@dataclass(frozen=True, slots=True)
class ModelProfile:
    id: TargetModel
    label: str
    hint: str
    style: PromptStyle
    claude_agent_model: Literal["opus", "sonnet", "haiku"] | None
    style_note: str | None
    cli: AgentCli


_CLAUDE = AgentCli(
    name="Claude Code",
    bash="claude -p --dangerously-skip-permissions < PROMPT.md",
    powershell="Get-Content -Raw PROMPT.md | claude -p --dangerously-skip-permissions",
)
_AIDER = AgentCli(
    name="Aider",
    bash="aider --message-file PROMPT.md --yes-always",
    powershell="aider --message-file PROMPT.md --yes-always",
)

MODEL_PROFILES: dict[str, ModelProfile] = {
    p.id: p
    for p in (
        ModelProfile("claude-opus", "Claude Opus", "XML-tagged sections, strongest reasoning", "xml", "opus", None, _CLAUDE),
        ModelProfile("claude-sonnet", "Claude Sonnet", "XML-tagged sections, balanced speed and depth", "xml", "sonnet", None, _CLAUDE),
        ModelProfile(
            "claude-haiku", "Claude Haiku", "XML-tagged sections, fast; keep tasks focused", "xml", "haiku",
            "Handle one clearly scoped job; do not expand the scope on your own.", _CLAUDE,
        ),
        ModelProfile(
            "gpt", "OpenAI GPT", "Markdown sections; loops run with Codex CLI", "markdown", None, None,
            AgentCli("Codex CLI", "codex exec --full-auto - < PROMPT.md",
                     "Get-Content -Raw PROMPT.md | codex exec --full-auto -"),
        ),
        ModelProfile(
            "gemini", "Google Gemini", "Markdown sections; loops run with Gemini CLI", "markdown", None, None,
            AgentCli("Gemini CLI", "gemini --yolo < PROMPT.md", "Get-Content -Raw PROMPT.md | gemini --yolo"),
        ),
        ModelProfile(
            "open-source", "Open-source (Llama, Qwen, Mistral)", "Plain Markdown, explicit rules; loops run with Aider",
            "markdown", None, "Follow the format exactly. Do not add sections that were not requested.", _AIDER,
        ),
        ModelProfile("generic", "Generic / any model", "Portable Markdown that works anywhere", "markdown", None, None, _AIDER),
    )
}
