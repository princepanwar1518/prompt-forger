import type {
  AiSettings,
  DescribeResult,
  EnhanceResult,
  ForgeResult,
  FormState,
  Meta,
  RateResult,
  RunResult,
} from "./types";

export class EngineError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "EngineError";
  }
}

interface CallOptions {
  signal?: AbortSignal;
  ai?: AiSettings;
}

const ENDPOINT = "/api/engine";

async function call<T>(method: string, params: Record<string, unknown>, opts: CallOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  const ai = opts.ai;
  const usesAi = ai !== undefined && ai.provider !== "rules";
  if (usesAi && ai.apiKey.trim()) headers["x-pf-key"] = ai.apiKey.trim();
  const body = usesAi ? { ...params, provider: ai.provider, model: ai.model.trim() || undefined } : params;

  let res: Response;
  try {
    res = await fetch(ENDPOINT, {
      method: "POST",
      headers,
      body: JSON.stringify({ method, params: body }),
      signal: opts.signal,
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new EngineError("Couldn't reach Prompt Forger. Check your connection and try again.", "offline", 0);
  }

  let payload: unknown;
  try {
    payload = await res.json();
  } catch {
    throw new EngineError(`The server sent an unreadable reply (${res.status}).`, "bad_reply", res.status);
  }
  if (!res.ok || (typeof payload === "object" && payload !== null && "error" in payload)) {
    const err = (payload as { error?: { code?: string; message?: string } }).error;
    throw new EngineError(err?.message ?? `Request failed (${res.status}).`, err?.code ?? "http", res.status);
  }
  return (payload as { result: T }).result;
}

export const engine = {
  meta: (signal?: AbortSignal) => call<Meta>("meta", {}, { signal }),
  forge: (form: FormState, signal?: AbortSignal) => call<ForgeResult>("forge", { ...form }, { signal }),
  describe: (
    text: string,
    form: FormState,
    answers: { question: string; answer: string }[],
    ai: AiSettings,
  ) => call<DescribeResult>("describe", { text, form, answers }, { ai }),
  enhance: (form: FormState, ai: AiSettings) => call<EnhanceResult>("enhance", { form }, { ai }),
  rate: (form: FormState, reply: string, ai: AiSettings) => call<RateResult>("rate", { form, reply }, { ai }),
  run: (prompt: string, input: string, ai: AiSettings) => call<RunResult>("run", { prompt, input }, { ai }),
};
