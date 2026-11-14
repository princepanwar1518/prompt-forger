"""Generated file type returned by every format."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

FileLanguage = Literal["markdown", "json", "bash", "powershell"]


@dataclass(frozen=True, slots=True)
class ForgeFile:
    path: str  # relative, forward slashes; may include folders such as .claude/agents/x.md
    language: FileLanguage
    description: str  # one line explaining what the file is for
    content: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
