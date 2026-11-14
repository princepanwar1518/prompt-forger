"""Graph loop: steps become nodes, an evaluator routes back until the work passes."""

from __future__ import annotations

import json
from typing import Any

from ..models import ModelProfile
from ..output import ForgeFile
from ..schema import ForgeInput
from ..sections import (
    Section, constraints_section, context_section, examples_section, output_format_section, output_rules,
    quality_check, render, role_section, success_section,
)
from ..text import bullets, slugify

DEFAULT_ITERATIONS = 3
ROUTER_ID = "evaluate"
END_ID = "__end__"
_RESERVED = {ROUTER_ID, END_ID, "start", "end"}
_DEFAULT_STEPS = ("Plan the approach", "Produce the work", "Refine the result")
_ROUTER_INSTRUCTION = (
    "Compare every node output against the task. If all are acceptable, route to __end__. "
    "Otherwise record the blocking issues and route to the earliest node that must be redone."
)


def build_graph(inp: ForgeInput) -> dict[str, Any]:
    steps = inp.steps or _DEFAULT_STEPS
    max_iter = inp.max_iterations or DEFAULT_ITERATIONS
    used: set[str] = set()
    task_nodes: list[dict[str, str]] = []

    for i, step in enumerate(steps, start=1):
        base = slugify(step, 32, "_")
        if base in _RESERVED or base[0].isdigit():
            base = f"step_{i}_{base}"[:40]
        node_id, n = base, 2
        while node_id in used:
            node_id, n = f"{base}_{n}", n + 1
        used.add(node_id)
        task_nodes.append({"id": node_id, "label": step, "type": "task", "instruction": step})

    instruction = _ROUTER_INSTRUCTION
    if inp.success_criteria:
        instruction += " Judge acceptability against these success criteria: " + "; ".join(inp.success_criteria) + "."
    router = {"id": ROUTER_ID, "label": "Evaluate and route", "type": "router", "instruction": instruction}
    chain = [n["id"] for n in task_nodes] + [ROUTER_ID]
    edges: list[dict[str, str]] = [{"from": a, "to": b} for a, b in zip(chain, chain[1:])]
    edges.append({"from": ROUTER_ID, "to": END_ID, "condition": "issues.length == 0 || iteration >= max_iterations"})
    edges += [{"from": ROUTER_ID, "to": n["id"], "condition": f'route_to == "{n["id"]}"'} for n in task_nodes]

    return {
        "name": slugify(inp.task, 40, "_"),
        "entry": task_nodes[0]["id"] if task_nodes else ROUTER_ID,
        "max_iterations": max_iter,
        "state": {"iteration": 0, "max_iterations": max_iter, "outputs": {}, "issues": [], "route_to": None},
        "nodes": [*task_nodes, router],
        "edges": edges,
    }


def _prompt(inp: ForgeInput, profile: ModelProfile, graph: dict[str, Any]) -> str:
    tasks = [n for n in graph["nodes"] if n["type"] == "task"]
    node_list = "\n".join(
        [f"{i}. `{n['id']}`: {n['label']}" for i, n in enumerate(tasks, start=1)]
        + [f"{len(tasks) + 1}. `{ROUTER_ID}` (router): {graph['nodes'][-1]['instruction']}"]
    )
    path = " → ".join([f"`{n['id']}`" for n in tasks] + [f"`{ROUTER_ID}`"])
    edge_list = bullets([
        f"START → {path}",
        f"`{ROUTER_ID}` → END when no blocking issues remain.",
        f"`{ROUTER_ID}` → any task node when that node's output has a blocking issue. Re-run from that node onward.",
        f"Hard stop: after {graph['max_iterations']} pass(es) through `{ROUTER_ID}`, go to END and list unresolved issues.",
    ])
    protocol = bullets([
        "Before each node, print a heading: `### <node_id> (pass N)`.",
        "Do only that node's work, using the outputs of earlier nodes from the state.",
        "After each task node, update `outputs.<node_id>` with a short summary of what you produced.",
        f'At `{ROUTER_ID}`, list blocking issues (or "none"), then print exactly one line: `ROUTE: <node_id>` or `ROUTE: END`.',
        "After END, print `## Final result` followed by the complete, consolidated deliverable.",
    ])
    state = "```json\n" + json.dumps(graph["state"], indent=2) + "\n```"
    sections = [
        role_section(inp),
        context_section(inp),
        Section("task", "Task", inp.task),
        Section("graph", "Execution graph",
                f"Work through the task as a state graph.\n\nNodes:\n{node_list}\n\nEdges:\n{edge_list}"),
        constraints_section(inp),
        success_section(inp, "The router may route to END only when all of these are true:"),
        examples_section(inp, profile.style),
        output_format_section(inp),
        Section("state", "State", f"Carry this state between nodes and update it as you go:\n{state}"),
        Section("protocol", "Protocol", protocol),
        output_rules(inp, profile, "response"),
        quality_check(inp, [
            "every node ran at least once and the router decision is justified",
            "the final result stands on its own without the trace above it",
        ]),
    ]
    return render(sections, profile.style)


def forge_graph(inp: ForgeInput, profile: ModelProfile) -> list[ForgeFile]:
    graph = build_graph(inp)
    return [
        ForgeFile("graph-prompt.md", "markdown",
                  "Self-running prompt: the model walks the graph itself in one conversation.",
                  _prompt(inp, profile, graph)),
        ForgeFile("graph.json", "json",
                  "Machine-readable nodes, edges and state for an orchestrator such as LangGraph.",
                  json.dumps(graph, indent=2, ensure_ascii=False) + "\n"),
    ]
