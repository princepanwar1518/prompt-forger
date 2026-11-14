import { FORM_KEYS, type FormKey, type FormState } from "./types";

export const DEFAULT_FORM: FormState = {
  role: "",
  task: "",
  steps: "",
  context: "",
  constraints: "",
  successCriteria: "",
  examples: "",
  outputSchema: "",
  variables: "",
  tools: "",
  format: "standard",
  model: "claude-sonnet",
  verbosity: "balanced",
  tokenBudget: "",
  maxIterations: "",
};

export const EXAMPLE_FORM: FormState = {
  ...DEFAULT_FORM,
  role: "senior backend engineer",
  task: "Build a REST API for a todo app with user accounts.",
  steps: "Design the database schema\nImplement auth with hashed passwords\nWrite CRUD endpoints for todos\nAdd tests for every endpoint",
  context: "Node.js 22, TypeScript, PostgreSQL with Prisma. Deployed on AWS.",
  constraints: "Never store plain-text passwords\nValidate every request body",
  successCriteria: "All tests pass\nEvery endpoint returns typed errors",
};

export interface FieldDef {
  key: FormKey;
  label: string;
  optional: boolean;
  placeholder: string;
  hint?: string;
  rows?: number;
  advanced?: boolean;
}

export const TEXT_FIELDS: FieldDef[] = [
  { key: "role", label: "Role", optional: false, placeholder: "e.g. senior backend engineer", hint: "Who the model should act as." },
  { key: "task", label: "Task", optional: false, rows: 3, placeholder: "What needs to be done? Be specific about the goal and constraints." },
  { key: "steps", label: "Steps", optional: true, rows: 3, placeholder: "One step per line, e.g. Design the schema", hint: "One per line. List markers like 1. or - are removed." },
  { key: "context", label: "Context", optional: true, rows: 3, placeholder: "Background, audience, existing code, inputs..." },
  { key: "constraints", label: "Constraints", optional: true, rows: 3, advanced: true, placeholder: "One rule per line, e.g. Never store plain-text passwords", hint: "Rules the model must not break." },
  { key: "successCriteria", label: "Success criteria", optional: true, rows: 3, advanced: true, placeholder: "One per line, e.g. All tests pass", hint: "How the model knows it's done. Loops need these." },
  { key: "examples", label: "Examples", optional: true, rows: 3, advanced: true, placeholder: "Input: ...  Output: ...   (separate examples with a line of ---)", hint: "1-3 sample answers. Separate them with a line of ---." },
  { key: "outputSchema", label: "Output schema", optional: true, rows: 3, advanced: true, placeholder: "The exact shape of the answer: sections, a template or JSON", hint: "Sections, a template or JSON. JSON is checked." },
  { key: "variables", label: "Variables", optional: true, rows: 2, advanced: true, placeholder: "name = value   (use {{name}} anywhere in the form)", hint: "Fill {{placeholders}} used anywhere above." },
  { key: "tools", label: "Tools", optional: true, advanced: true, placeholder: "Read, Grep, Bash(git:*)", hint: "Agent profiles only: the tools the agent may use." },
];

export const FIELD_LABELS: Record<string, string> = Object.fromEntries([
  ...TEXT_FIELDS.map((f) => [f.key, f.label] as const),
  ["format", "Output format"],
  ["model", "Target model"],
  ["verbosity", "Verbosity"],
  ["tokenBudget", "Token budget"],
  ["maxIterations", "Max iterations"],
]);

export const isLoop = (format: string) => format === "ralph" || format === "graph";

/** Lenient parse of stored or imported data into a complete form. */
export function toForm(raw: unknown): FormState {
  const src = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  const out = { ...DEFAULT_FORM };
  for (const key of FORM_KEYS) {
    const v = src[key];
    if (typeof v === "string") out[key] = v.slice(0, 20_000);
    else if (typeof v === "number" && Number.isFinite(v)) out[key] = String(v);
  }
  return out;
}

export const isBlank = (form: FormState) => !form.role.trim() && !form.task.trim();
