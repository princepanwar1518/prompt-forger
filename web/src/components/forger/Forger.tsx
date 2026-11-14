"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { EngineError, engine } from "@/lib/engine";
import { DEFAULT_FORM, EXAMPLE_FORM, isBlank, toForm } from "@/lib/form";
import { aiStore, draftStore, presetStore, type Preset } from "@/lib/storage";
import type { AiSettings, DescribeResult, EnhanceResult, ForgeOk, FormKey, FormState, Meta } from "@/lib/types";

import { Logo } from "../ui/Logo";
import { ThemeToggle } from "../ui/ThemeToggle";
import { ToastProvider, useToast } from "../ui/Toast";
import { DescribeCard } from "./DescribeCard";
import { EnhanceDialog } from "./EnhanceDialog";
import { FormPanel, type FormPanelHandle } from "./FormPanel";
import { OutputPanel } from "./OutputPanel";
import { SettingsDialog } from "./SettingsDialog";
import { TestDialog } from "./TestDialog";

const FORGE_DEBOUNCE_MS = 300;

export function Forger() {
  return (
    <ToastProvider>
      <ForgerInner />
    </ToastProvider>
  );
}

function ForgerInner() {
  const toast = useToast();
  const formRef = useRef<FormPanelHandle>(null);

  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState("");
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [loaded, setLoaded] = useState(false);
  const [result, setResult] = useState<ForgeOk | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [forging, setForging] = useState(false);

  const [ai, setAi] = useState<AiSettings>({ provider: "rules", model: "", apiKey: "", rememberKey: false });
  const [presets, setPresets] = useState<Preset[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
  const [enhanced, setEnhanced] = useState<EnhanceResult | null>(null);

  // Load saved state after mount (browser storage isn't available during server rendering).
  useEffect(() => {
    setForm(draftStore.load() ?? DEFAULT_FORM);
    setAi(aiStore.load());
    setPresets(presetStore.load());
    setLoaded(true);
    const ctrl = new AbortController();
    engine
      .meta(ctrl.signal)
      .then(setMeta)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setMetaError(err instanceof EngineError ? err.message : "Couldn't load Prompt Forger.");
      });
    return () => ctrl.abort();
  }, []);

  // Live forge: debounced, and any in-flight request is cancelled when the form changes again.
  useEffect(() => {
    if (!loaded) return;
    draftStore.save(form);
    if (isBlank(form)) {
      setResult(null);
      setErrors({});
      return;
    }
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      setForging(true);
      engine
        .forge(form, ctrl.signal)
        .then((res) => {
          if (res.ok) {
            setResult(res);
            setErrors({});
          } else {
            setResult(null);
            setErrors(res.errors);
          }
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          toast(err instanceof EngineError ? err.message : "Couldn't build the prompt.", "error");
        })
        .finally(() => {
          if (!ctrl.signal.aborted) setForging(false);
        });
    }, FORGE_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
  }, [form, loaded, toast]);

  const update = useCallback((key: FormKey, value: string) => setForm((f) => ({ ...f, [key]: value })), []);

  const onFill = (res: DescribeResult) => setForm(toForm(res.form));

  const enhance = async () => {
    setEnhancing(true);
    try {
      setEnhanced(await engine.enhance(form, ai));
    } catch (err) {
      toast(err instanceof EngineError ? err.message : "Couldn't enhance this prompt.", "error");
    } finally {
      setEnhancing(false);
    }
  };

  const applyEnhance = () => {
    if (!enhanced) return;
    setForm(toForm(enhanced.form));
    toast(`Enhanced: score ${enhanced.before} → ${enhanced.after}`, "success");
    setEnhanced(null);
  };

  const saveAi = (s: AiSettings) => {
    setAi(s);
    aiStore.save(s);
    setSettingsOpen(false);
    toast("AI settings saved.", "success");
  };

  const savePreset = () => {
    const name = window.prompt("Name this preset:", form.role.trim().slice(0, 40) || "My preset")?.trim();
    if (!name) return;
    const next = [...presets.filter((p) => p.name !== name), { name: name.slice(0, 80), form }].slice(-50);
    setPresets(next);
    presetStore.save(next);
    toast(`Saved preset “${name}”.`, "success");
  };

  const loadPreset = (name: string) => {
    if (name === "__example") setForm(EXAMPLE_FORM);
    else if (name === "__clear") setForm(DEFAULT_FORM);
    else {
      const p = presets.find((x) => x.name === name);
      if (p) setForm(p.form);
    }
  };

  const deletePreset = (name: string) => {
    const next = presets.filter((p) => p.name !== name);
    setPresets(next);
    presetStore.save(next);
    toast(`Deleted “${name}”.`);
  };

  const promptText = result?.files[0]?.content ?? "";
  const missing = (["role", "task"] as const).filter((k) => !form[k].trim());

  return (
    <>
      <header className="sticky top-0 z-30 border-b-2 border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Logo version={meta?.version} />
          <nav className="flex flex-wrap items-center gap-2" aria-label="App">
            <PresetMenu presets={presets} onLoad={loadPreset} onDelete={deletePreset} />
            <button type="button" onClick={savePreset} className="pill pill-plain hidden sm:inline-flex">
              Save preset
            </button>
            <button type="button" onClick={() => setSettingsOpen(true)} className="pill pill-plain">
              AI settings
            </button>
            <ThemeToggle />
            <Link href="/#download" className="pill pill-ink hidden md:inline-flex">
              Get the app
            </Link>
          </nav>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-10">
        {metaError ? (
          <p role="alert" className="mb-6 rounded-2xl border-2 border-tangerine bg-tangerine/10 p-4 font-semibold">
            {metaError}
          </p>
        ) : null}
        <h1 className="sr-only">Prompt Forger web app</h1>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-12">
          <div className="space-y-10">
            <DescribeCard form={form} ai={ai} onFill={onFill} onOpenSettings={() => setSettingsOpen(true)} />
            <FormPanel ref={formRef} form={form} meta={meta} errors={errors} onChange={update} />
          </div>
          <div className="lg:sticky lg:top-24 lg:max-h-[calc(100dvh-7rem)] lg:self-start lg:overflow-y-auto lg:pr-2 lg:pb-4">
            <OutputPanel
              result={result}
              busy={forging}
              missing={missing}
              onEnhance={() => void enhance()}
              enhancing={enhancing}
              onTest={() => setTestOpen(true)}
              onFocusField={(k) => formRef.current?.focusField(k)}
            />
          </div>
        </div>
      </main>

      <SettingsDialog open={settingsOpen} settings={ai} onSave={saveAi} onClose={() => setSettingsOpen(false)} />
      <EnhanceDialog result={enhanced} onApply={applyEnhance} onDiscard={() => setEnhanced(null)} />
      <TestDialog
        open={testOpen}
        onClose={() => setTestOpen(false)}
        prompt={promptText}
        form={form}
        ai={ai}
        onOpenSettings={() => {
          setTestOpen(false);
          setSettingsOpen(true);
        }}
      />
    </>
  );
}

function PresetMenu({
  presets,
  onLoad,
  onDelete,
}: {
  presets: Preset[];
  onLoad: (name: string) => void;
  onDelete: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const pick = (name: string) => {
    onLoad(name);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="true" className="pill pill-plain">
        Presets <span aria-hidden>▾</span>
      </button>
      {open ? (
        <div className="absolute right-0 z-40 mt-2 w-72 animate-pop rounded-[18px] border-2 border-line bg-surface p-2 shadow-hard">
          <button type="button" onClick={() => pick("__example")} className="w-full rounded-xl px-3 py-2 text-left text-sm font-semibold hover:bg-paper">
            Load example
          </button>
          <button type="button" onClick={() => pick("__clear")} className="w-full rounded-xl px-3 py-2 text-left text-sm font-semibold hover:bg-paper">
            Clear the form
          </button>
          <hr className="my-2 border-line/20" />
          {presets.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted">No saved presets yet. They stay in this browser.</p>
          ) : (
            <ul className="max-h-64 overflow-y-auto">
              {presets.map((p) => (
                <li key={p.name} className="flex items-center gap-1">
                  <button type="button" onClick={() => pick(p.name)} className="flex-1 truncate rounded-xl px-3 py-2 text-left text-sm hover:bg-paper">
                    {p.name}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(p.name)}
                    className="rounded-full px-2.5 py-1 text-sm text-muted hover:bg-tangerine/20 hover:text-ink"
                    aria-label={`Delete preset ${p.name}`}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
