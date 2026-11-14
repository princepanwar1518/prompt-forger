"""Small pure text helpers shared by every format generator."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable


def slugify(text: str, max_length: int = 40, sep: str = "-") -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", sep, ascii_text.lower()).strip(sep)
    if len(slug) <= max_length:
        return slug or "untitled"
    # Cut on a word boundary so we never end with half a word.
    cut = slug[: max_length + 1]
    idx = cut.rfind(sep)
    trimmed = (cut[:idx] if idx > 0 else slug[:max_length]).rstrip(sep)
    return trimmed or "untitled"


def ensure_period(text: str) -> str:
    t = text.strip()
    return t if t[-1:] in ".!?:" else f"{t}."


def _lower_first_word(text: str) -> str:
    """'Senior engineer' -> 'senior engineer', but keep acronyms like 'AWS architect'."""
    if len(text) > 1 and text[1] == text[1].lower():
        return text[0].lower() + text[1:]
    return text


def role_sentence(role: str) -> str:
    r = role.strip()
    if re.match(r"^you\s+are\b", r, re.IGNORECASE):
        return ensure_period("You" + r[3:])
    if re.match(r"^(a|an|the|my|your|our)\s", r, re.IGNORECASE):
        return ensure_period(f"You are {r[0].lower()}{r[1:]}")
    body = _lower_first_word(r)
    article = "an" if body[:1].lower() in "aeiou" else "a"
    return ensure_period(f"You are {article} {body}")


def numbered(items: Iterable[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))


def bullets(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def first_sentence(text: str, max_length: int = 200) -> str:
    flat = " ".join(text.split())
    match = re.match(r"^(.+?[.!?])(\s|$)", flat)
    sentence = (match.group(1) if match else flat).strip()
    if len(sentence) <= max_length:
        return sentence
    return sentence[: max_length - 1].rstrip() + "…"


def lower_first(text: str) -> str:
    return _lower_first_word(text)


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token for English prose and code."""
    return 0 if not text else math.ceil(len(text) / 4)


def yaml_string(value: str) -> str:
    flat = " ".join(value.split())
    return '"' + flat.replace("\\", "\\\\").replace('"', '\\"') + '"'
