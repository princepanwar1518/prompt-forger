"""Ralph loop: one stable prompt fed to a coding agent repeatedly until it signals completion."""

from __future__ import annotations

from ..models import ModelProfile
from ..output import ForgeFile
from ..schema import ForgeInput
from ..sections import (
    Section, constraints_section, context_section, examples_section, output_format_section, output_rules,
    quality_check, render, role_section, success_section,
)
from ..text import bullets, numbered

DEFAULT_ITERATIONS = 20
PROMISE = "<promise>COMPLETE</promise>"


def _prompt(inp: ForgeInput, profile: ModelProfile) -> str:
    loop = numbered([
        "Read `fix_plan.md`. It is the single source of truth for what is done and what is left.",
        "Pick the ONE most important unchecked item. Work on that item only during this iteration.",
        "Before changing anything, search the existing work to confirm the item is not already done. Do not assume.",
        'Complete the item fully. No placeholders, stubs or "TODO later".',
        "Validate the result: run the relevant tests, build or checks, and fix any failures you caused.",
        'Update `fix_plan.md`: tick the item, add any new tasks or bugs you discovered, and record learnings under "Notes".',
        "If this is a git repository, commit with a message that describes the change.",
    ])
    rules = bullets([
        "One item per iteration. Your memory resets between iterations, so `fix_plan.md` must contain everything the next iteration needs.",
        "Do not rewrite or reformat work unrelated to the current item.",
        "If an item is blocked, write down why in `fix_plan.md`, leave it unchecked and move to the next item.",
    ])
    sections = [
        role_section(inp),
        context_section(inp),
        Section("objective", "Objective", inp.task),
        Section("iteration_loop", "Each iteration", loop),
        Section("rules", "Rules", rules),
        constraints_section(inp),
        success_section(inp, "The objective is met only when all of these are true:"),
        examples_section(inp, profile.style),
        output_format_section(inp),
        Section(
            "completion", "Completion",
            "When every item in `fix_plan.md` is ticked, validation passes"
            + (" and every success criterion above is met" if inp.success_criteria else "")
            + ", output exactly:\n"
            f"{PROMISE}\nNever output that line in any other situation.",
        ),
        output_rules(inp, profile, "iteration"),
        quality_check(inp, [
            "the item you worked on is complete and validated",
            "`fix_plan.md` reflects the real state of the work",
        ]),
    ]
    return render(sections, profile.style)


def _fix_plan(inp: ForgeInput) -> str:
    todo = (
        "\n".join(f"- [ ] {s}" for s in inp.steps)
        if inp.steps
        else "- [ ] Break the objective into small, concrete tasks and replace this line with them"
    )
    objective = " ".join(inp.task.split())
    return f"# Fix plan\n\n**Objective:** {objective}\n\n## To do\n{todo}\n\n## Done\n\n## Notes\n"


def _bash(profile: ModelProfile, max_iterations: int) -> str:
    return f"""#!/usr/bin/env bash
# Ralph loop: feeds PROMPT.md to {profile.cli.name} until it reports completion.
# WARNING: the agent runs unattended with permissions skipped.
# Run it inside a disposable container or VM, never on your main machine.
set -euo pipefail

MAX_ITERATIONS="${{MAX_ITERATIONS:-{max_iterations}}}"
PROMISE='{PROMISE}'

for ((i = 1; i <= MAX_ITERATIONS; i++)); do
  echo "=== Ralph iteration $i/$MAX_ITERATIONS ==="
  output="$({profile.cli.bash} 2>&1 | tee /dev/stderr)" || true
  if grep -qF "$PROMISE" <<<"$output"; then
    echo "Complete after $i iteration(s)."
    exit 0
  fi
done

echo "Stopped: reached $MAX_ITERATIONS iterations without completion." >&2
exit 1
"""


def _powershell(profile: ModelProfile, max_iterations: int) -> str:
    return f"""# Ralph loop: feeds PROMPT.md to {profile.cli.name} until it reports completion.
# WARNING: the agent runs unattended with permissions skipped.
# Run it inside a disposable container, VM or Windows Sandbox, never on your main machine.
param([int]$MaxIterations = {max_iterations})

$Marker = '{PROMISE}'

for ($i = 1; $i -le $MaxIterations; $i++) {{
    Write-Host "=== Ralph iteration $i/$MaxIterations ==="
    $lines = {profile.cli.powershell} 2>&1 | ForEach-Object {{ Write-Host $_; "$_" }}
    $output = $lines -join [Environment]::NewLine
    if ($output.Contains($Marker)) {{
        Write-Host "Complete after $i iteration(s)."
        exit 0
    }}
}}

Write-Error "Stopped: reached $MaxIterations iterations without completion."
exit 1
"""


def forge_ralph(inp: ForgeInput, profile: ModelProfile) -> list[ForgeFile]:
    n = inp.max_iterations or DEFAULT_ITERATIONS
    return [
        ForgeFile("PROMPT.md", "markdown",
                  "The prompt fed to the agent on every iteration. Keep it stable; tune it when the agent drifts.",
                  _prompt(inp, profile)),
        ForgeFile("fix_plan.md", "markdown", "Shared task list. The agent reads and updates it each iteration.",
                  _fix_plan(inp)),
        ForgeFile("ralph.ps1", "powershell",
                  f"Windows runner for {profile.cli.name}. Usage: .\\ralph.ps1 -MaxIterations {n}",
                  _powershell(profile, n)),
        ForgeFile("ralph.sh", "bash",
                  f"Linux/macOS/WSL runner for {profile.cli.name}. Usage: MAX_ITERATIONS={n} ./ralph.sh",
                  _bash(profile, n)),
    ]
