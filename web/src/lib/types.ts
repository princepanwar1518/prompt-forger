// Shapes returned by the Prompt Forger engine (engine/prompt_forger_engine). Keep in sync with the desktop app.

export const FORM_KEYS = [
  "role",
  "task",
  "steps",
  "context",
  "constraints",
  "successCriteria",
  "examples",
  "outputSchema",
  "variables",
  "tools",
  "format",
  "model",
  "verbosity",
  "tokenBudget",
  "maxIterations",
] as const;

export type FormKey = (typeof FORM_KEYS)[number];
export type FormState = Record<FormKey, string>;

export type FormatId = "standard" | "ralph" | "graph" | "agent";
export type Provider = "rules" | "anthropic" | "openai";

export interface Option {
  id: string;
  label: string;
  hint?: string;
}

export interface Meta {
  formats: Option[];
  models: Option[];
  providers: Option[];
  verbosity: Option[];
  version: string;
}

export interface Finding {
  level: "warning" | "tip";
  field: string;
  message: string;
}

export interface Dimension {
  name: string;
  score: number;
  hint: string;
}

export interface Quality {
  score: number;
  grade: string;
  findings: Finding[];
  dimensions: Dimension[];
}

export interface ForgeFile {
  path: string;
  language: string;
  description: string;
  content: string;
}

export interface ForgeOk {
  ok: true;
  files: ForgeFile[];
  warnings: string[];
  quality: Quality;
  explanation: string;
  variables: string[];
}

export interface ForgeFail {
  ok: false;
  errors: Record<string, string>;
}

export type ForgeResult = ForgeOk | ForgeFail;

export interface DescribeResult {
  form: FormState;
  filled: string[];
  questions: string[];
  confidence: number;
  source: string;
  notes: string[];
}

export interface Change {
  field: string;
  action: string;
  summary: string;
  before: string;
  after: string;
}

export interface EnhanceResult {
  form: FormState;
  changes: Change[];
  needsYou: string[];
  before: number;
  after: number;
  source: string;
  notes: string[];
}

export interface RateCheck {
  kind: string;
  item: string;
  passed: boolean | null;
  reason: string;
  how: string;
}

export interface RateResult {
  accuracy: number | null;
  passed: number;
  checked: number;
  total: number;
  coverage: number;
  verdict: string;
  summary: string;
  judge: string;
  checks: RateCheck[];
}

export interface RunResult {
  reply: string;
  provider: string;
  model: string;
}

export interface AiSettings {
  provider: Provider;
  model: string;
  /** Kept in this browser only; sent per request over HTTPS and never stored on the server. */
  apiKey: string;
  rememberKey: boolean;
}
