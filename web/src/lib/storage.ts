// Browser storage with graceful failure (private mode, quota, disabled storage). Everything stays on this device.
import { toForm } from "./form";
import type { AiSettings, FormState, Provider } from "./types";

const K = {
  draft: "pf.draft.v1",
  presets: "pf.presets.v1",
  ai: "pf.ai.v1",
  key: "pf.key.v1",
  theme: "pf.theme",
} as const;

function read(store: "local" | "session", key: string): string | null {
  try {
    return (store === "local" ? window.localStorage : window.sessionStorage).getItem(key);
  } catch {
    return null;
  }
}

function write(store: "local" | "session", key: string, value: string | null): void {
  try {
    const s = store === "local" ? window.localStorage : window.sessionStorage;
    if (value === null) s.removeItem(key);
    else s.setItem(key, value);
  } catch {
    /* storage unavailable: keep working in memory */
  }
}

function parse(json: string | null): unknown {
  if (!json) return null;
  try {
    return JSON.parse(json) as unknown;
  } catch {
    return null;
  }
}

export const draftStore = {
  load: (): FormState | null => {
    const raw = parse(read("local", K.draft));
    return raw ? toForm(raw) : null;
  },
  save: (form: FormState) => write("local", K.draft, JSON.stringify(form)),
};

export interface Preset {
  name: string;
  form: FormState;
}

export const presetStore = {
  load: (): Preset[] => {
    const raw = parse(read("local", K.presets));
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((p): p is { name: string; form: unknown } => typeof p === "object" && p !== null && typeof (p as { name?: unknown }).name === "string")
      .map((p) => ({ name: p.name.slice(0, 80), form: toForm(p.form) }));
  },
  save: (presets: Preset[]) => write("local", K.presets, JSON.stringify(presets)),
};

const PROVIDERS: Provider[] = ["rules", "anthropic", "openai"];

export const aiStore = {
  load: (): AiSettings => {
    const raw = parse(read("local", K.ai)) as Partial<AiSettings> | null;
    const remember = raw?.rememberKey === true;
    const provider = PROVIDERS.includes(raw?.provider as Provider) ? (raw?.provider as Provider) : "rules";
    return {
      provider,
      model: typeof raw?.model === "string" ? raw.model.slice(0, 100) : "",
      rememberKey: remember,
      apiKey: (remember ? read("local", K.key) : read("session", K.key)) ?? "",
    };
  },
  save: (s: AiSettings) => {
    write("local", K.ai, JSON.stringify({ provider: s.provider, model: s.model, rememberKey: s.rememberKey }));
    // The key lives in this tab's session by default; only "Remember on this device" keeps it in localStorage.
    write("session", K.key, s.rememberKey ? null : s.apiKey || null);
    write("local", K.key, s.rememberKey ? s.apiKey || null : null);
  },
};

export type ThemeChoice = "light" | "dark";

export const themeStore = {
  key: K.theme,
  save: (t: ThemeChoice) => write("local", K.theme, t),
};
