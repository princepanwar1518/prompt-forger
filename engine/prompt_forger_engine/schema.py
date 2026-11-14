"""Input contract: raw form (all strings) -> validated ForgeInput, or field errors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Final, Literal, get_args

OutputFormat = Literal["standard", "ralph", "graph", "agent"]
TargetModel = Literal[
    "claude-opus", "claude-sonnet", "claude-haiku", "gpt", "gemini", "open-source", "generic"
]
Verbosity = Literal["concise", "balanced", "detailed"]

OUTPUT_FORMATS: Final = get_args(OutputFormat)
TARGET_MODELS: Final = get_args(TargetModel)
VERBOSITY_LEVELS: Final = get_args(Verbosity)

MAX_ROLE: Final = 300
MAX_TASK: Final = 8_000
MAX_CONTEXT: Final = 50_000
MAX_LIST_ITEMS: Final = 50
MAX_LIST_ITEM_LENGTH: Final = 500
MAX_EXAMPLES: Final = 10
MAX_EXAMPLES_TOTAL: Final = 20_000
MAX_SCHEMA: Final = 10_000
MAX_VARIABLES: Final = 30
MAX_TOOLS: Final = 30
TOKEN_BUDGET_RANGE: Final = (50, 1_000_000)
ITERATIONS_RANGE: Final = (1, 500)

FORM_FIELDS: Final = (
    "role", "task", "steps", "context", "constraints", "successCriteria", "examples", "outputSchema",
    "variables", "tools", "format", "model", "verbosity", "tokenBudget", "maxIterations",
)

DEFAULT_FORM: Final[dict[str, str]] = {
    "role": "",
    "task": "",
    "steps": "",
    "context": "",
    "constraints": "",
    "successCriteria": "",
    "examples": "",
    "outputSchema": "",
    "variables": "",
    "tools": "",
    "format": "standard",
    "model": "claude-sonnet",
    "verbosity": "balanced",
    "tokenBudget": "",
    "maxIterations": "",
}

_LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_EXAMPLE_SPLIT = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)
_VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
_VAR_REF = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]{0,40})\s*\}\}")
_TOOL = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*(\([^()\n]{1,80}\))?$")


@dataclass(frozen=True, slots=True)
class ForgeInput:
    role: str
    task: str
    steps: tuple[str, ...]
    context: str
    format: OutputFormat
    model: TargetModel
    verbosity: Verbosity
    token_budget: int | None
    max_iterations: int | None
    constraints: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    output_schema: str = ""
    tools: tuple[str, ...] = ()
    variables: dict[str, str] = field(default_factory=dict)
    unresolved_variables: tuple[str, ...] = ()


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def _optional_int(raw: str, label: str, bounds: tuple[int, int], errors: dict[str, str], key: str) -> int | None:
    value = raw.strip()
    if not value:
        return None
    if not value.isdigit():
        errors[key] = f"{label} must be a whole number."
        return None
    number = int(value)
    lo, hi = bounds
    if not lo <= number <= hi:
        errors[key] = f"{label} must be between {lo:,} and {hi:,}."
        return None
    return number


def parse_lines(raw: str) -> tuple[str, ...]:
    """One item per line; list markers like '1.', '-', '*' are stripped and blank lines dropped."""
    return tuple(s for s in (_LIST_MARKER.sub("", line).strip() for line in raw.splitlines()) if s)


# Backwards-compatible name used by older callers and tests.
parse_steps = parse_lines


def parse_examples(raw: str) -> tuple[str, ...]:
    """Examples are separated by a line of three or more dashes (---)."""
    return tuple(part.strip() for part in _EXAMPLE_SPLIT.split(raw) if part.strip())


def parse_variables(raw: str, errors: dict[str, str]) -> dict[str, str]:
    """`name = value` per line. Later lines win."""
    out: dict[str, str] = {}
    for n, line in enumerate(raw.splitlines(), start=1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if "=" not in line:
            errors["variables"] = f"Line {n}: write variables as name = value."
            return {}
        name, value = (part.strip() for part in line.split("=", 1))
        if not _VAR_NAME.match(name):
            errors["variables"] = f"Line {n}: '{name}' is not a valid name (letters, digits, underscore)."
            return {}
        out[name] = value
    if len(out) > MAX_VARIABLES:
        errors["variables"] = f"Use {MAX_VARIABLES} variables or fewer."
    return out


def parse_tools(raw: str, errors: dict[str, str]) -> tuple[str, ...]:
    tools = tuple(t.strip() for t in re.split(r"[,\n]", raw) if t.strip())
    bad = [t for t in tools if not _TOOL.match(t)]
    if bad:
        errors["tools"] = f"Not a valid tool name: {bad[0]!r}. Use names like Read, Grep or Bash(git:*)."
    elif len(tools) > MAX_TOOLS:
        errors["tools"] = f"Use {MAX_TOOLS} tools or fewer."
    return tools


def find_variables(*texts: str) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for t in texts:
        for m in _VAR_REF.finditer(t):
            seen.setdefault(m.group(1), None)
    return tuple(seen)


def substitute(text: str, variables: dict[str, str]) -> str:
    return _VAR_REF.sub(lambda m: variables.get(m.group(1), m.group(0)), text)


def _check_list(items: tuple[str, ...], key: str, label: str, errors: dict[str, str]) -> None:
    if len(items) > MAX_LIST_ITEMS:
        errors[key] = f"Use {MAX_LIST_ITEMS} {label} or fewer."
    elif any(len(s) > MAX_LIST_ITEM_LENGTH for s in items):
        errors[key] = f"Each of the {label} must be {MAX_LIST_ITEM_LENGTH} characters or fewer."


def validate(form: Any) -> ForgeInput:
    """Validate an untrusted form mapping. Raises ValidationError with per-field messages."""
    if not isinstance(form, dict):
        raise ValidationError({"form": "Form must be an object."})

    merged = {**DEFAULT_FORM, **{k: v for k, v in form.items() if k in FORM_FIELDS}}
    errors: dict[str, str] = {}
    for key, value in merged.items():
        if not isinstance(value, str):
            errors[key] = f"{key} must be text."
    if errors:
        raise ValidationError(errors)

    variables = parse_variables(merged["variables"], errors)

    def sub(text: str) -> str:
        return substitute(text, variables)

    role = sub(merged["role"].strip())
    task = sub(merged["task"].strip())
    context = sub(merged["context"].strip())
    steps = tuple(sub(s) for s in parse_lines(merged["steps"]))
    constraints = tuple(sub(s) for s in parse_lines(merged["constraints"]))
    success = tuple(sub(s) for s in parse_lines(merged["successCriteria"]))
    examples = tuple(sub(e) for e in parse_examples(merged["examples"]))
    output_schema = sub(merged["outputSchema"].strip())
    tools = parse_tools(merged["tools"], errors)

    if not role:
        errors["role"] = "Role is required."
    elif len(role) > MAX_ROLE:
        errors["role"] = f"Role must be {MAX_ROLE} characters or fewer."
    if not task:
        errors["task"] = "Task is required."
    elif len(task) > MAX_TASK:
        errors["task"] = f"Task must be {MAX_TASK:,} characters or fewer."
    if len(context) > MAX_CONTEXT:
        errors["context"] = f"Context must be {MAX_CONTEXT:,} characters or fewer."
    _check_list(steps, "steps", "steps", errors)
    _check_list(constraints, "constraints", "constraints", errors)
    _check_list(success, "successCriteria", "success criteria", errors)
    if len(examples) > MAX_EXAMPLES:
        errors["examples"] = f"Use {MAX_EXAMPLES} examples or fewer."
    elif sum(map(len, examples)) > MAX_EXAMPLES_TOTAL:
        errors["examples"] = f"Examples must total {MAX_EXAMPLES_TOTAL:,} characters or fewer."
    if len(output_schema) > MAX_SCHEMA:
        errors["outputSchema"] = f"Output schema must be {MAX_SCHEMA:,} characters or fewer."

    if merged["format"] not in OUTPUT_FORMATS:
        errors["format"] = "Unknown output format."
    if merged["model"] not in TARGET_MODELS:
        errors["model"] = "Unknown target model."
    if merged["verbosity"] not in VERBOSITY_LEVELS:
        errors["verbosity"] = "Unknown verbosity level."

    budget = _optional_int(merged["tokenBudget"], "Token budget", TOKEN_BUDGET_RANGE, errors, "tokenBudget")
    iterations = _optional_int(
        merged["maxIterations"], "Max iterations", ITERATIONS_RANGE, errors, "maxIterations"
    )

    if errors:
        raise ValidationError(errors)

    unresolved = find_variables(role, task, context, output_schema, *steps, *constraints, *success, *examples)

    return ForgeInput(
        role=role,
        task=task,
        steps=steps,
        context=context,
        format=merged["format"],  # type: ignore[arg-type]
        model=merged["model"],  # type: ignore[arg-type]
        verbosity=merged["verbosity"],  # type: ignore[arg-type]
        token_budget=budget,
        max_iterations=iterations,
        constraints=constraints,
        success_criteria=success,
        examples=examples,
        output_schema=output_schema,
        tools=tools,
        variables=variables,
        unresolved_variables=unresolved,
    )

# Fields "Describe it" may fill. Target model, budget, iterations, variables and tools stay the user's.
FORMAT_FIELDS_FROM_AI: Final = (
    "role", "task", "steps", "context", "constraints", "successCriteria", "examples", "outputSchema",
    "format", "verbosity",
)
