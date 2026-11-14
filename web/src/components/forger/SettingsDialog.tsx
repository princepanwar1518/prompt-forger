"use client";

import { useEffect, useState } from "react";

import type { AiSettings, Provider } from "@/lib/types";

import { Dialog } from "../ui/Dialog";

interface Props {
  open: boolean;
  settings: AiSettings;
  onSave: (s: AiSettings) => void;
  onClose: () => void;
}

const OPTIONS: { id: Provider; label: string; hint: string; model: string }[] = [
  { id: "rules", label: "Offline rules", hint: "Free and instant. No key needed.", model: "" },
  { id: "anthropic", label: "Claude", hint: "Best results. Needs an Anthropic API key.", model: "claude-haiku-5-5" },
  { id: "openai", label: "OpenAI", hint: "Needs an OpenAI API key.", model: "gpt-4o-mini" },
];

const KEY_RE = /^[A-Za-z0-9_\-.]{16,400}$/;

export function SettingsDialog({ open, settings, onSave, onClose }: Props) {
  const [draft, setDraft] = useState(settings);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (open) {
      setDraft(settings);
      setShow(false);
    }
  }, [open, settings]);

  const option = OPTIONS.find((o) => o.id === draft.provider) ?? OPTIONS[0]!;
  const needsKey = draft.provider !== "rules";
  const keyInvalid = needsKey && draft.apiKey.trim() !== "" && !KEY_RE.test(draft.apiKey.trim());

  return (
    <Dialog
      open={open}
      onClose={onClose}
      eyebrow="Settings"
      title="AI settings"
      footer={
        <>
          <button type="button" onClick={onClose} className="pill pill-plain">
            Cancel
          </button>
          <button
            type="button"
            disabled={keyInvalid}
            onClick={() => onSave({ ...draft, apiKey: draft.apiKey.trim(), model: draft.model.trim() })}
            className="pill pill-lime"
          >
            Save
          </button>
        </>
      }
    >
      <div className="space-y-6">
        <fieldset>
          <legend className="mb-2 text-sm font-bold">Who fills the form, enhances and judges replies</legend>
          <div className="grid gap-2">
            {OPTIONS.map((o) => (
              <label
                key={o.id}
                className={`flex cursor-pointer items-start gap-3 rounded-2xl border-2 border-line p-3 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-violet ${draft.provider === o.id ? "bg-lime text-onaccent shadow-hard-sm" : "bg-surface"}`}
              >
                <input
                  type="radio"
                  name="provider"
                  checked={draft.provider === o.id}
                  onChange={() => setDraft((d) => ({ ...d, provider: o.id, model: "" }))}
                  className="mt-1 accent-[#17151b]"
                />
                <span>
                  <span className="block font-semibold">{o.label}</span>
                  <span className="block text-sm opacity-80">{o.hint}</span>
                </span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">Ollama (local models) is available in the desktop app.</p>
        </fieldset>

        {needsKey ? (
          <>
            <div>
              <label htmlFor="ai-key" className="mb-1.5 block text-sm font-bold">
                {option.label} API key
              </label>
              <div className="flex gap-2">
                <input
                  id="ai-key"
                  type={show ? "text" : "password"}
                  autoComplete="off"
                  spellCheck={false}
                  value={draft.apiKey}
                  onChange={(e) => setDraft((d) => ({ ...d, apiKey: e.target.value }))}
                  placeholder={draft.provider === "anthropic" ? "sk-ant-…" : "sk-…"}
                  aria-invalid={keyInvalid || undefined}
                  aria-describedby="ai-key-note"
                  className="field-input font-mono"
                />
                <button type="button" onClick={() => setShow((v) => !v)} className="pill pill-plain shrink-0" aria-pressed={show}>
                  {show ? "Hide" : "Show"}
                </button>
              </div>
              {keyInvalid ? (
                <p className="mt-1 text-sm font-semibold text-tangerine">That doesn&apos;t look like an API key.</p>
              ) : null}
              <p id="ai-key-note" className="mt-2 text-xs text-muted">
                Your key stays in this browser. It&apos;s sent over HTTPS with each AI request, passed straight to {option.label},
                and never stored or logged on our server.
              </p>
            </div>

            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={draft.rememberKey}
                onChange={(e) => setDraft((d) => ({ ...d, rememberKey: e.target.checked }))}
                className="mt-1 size-4 accent-[#6554f4]"
              />
              <span>
                <span className="font-semibold">Remember on this device</span>
                <span className="block text-muted">Off: the key is forgotten when you close this tab. Don&apos;t turn on for shared computers.</span>
              </span>
            </label>

            <div>
              <label htmlFor="ai-model" className="mb-1.5 block text-sm font-bold">
                Model <span className="tag ml-1">optional</span>
              </label>
              <input
                id="ai-model"
                value={draft.model}
                maxLength={100}
                onChange={(e) => setDraft((d) => ({ ...d, model: e.target.value }))}
                placeholder={`Default: ${option.model}`}
                className="field-input font-mono"
              />
            </div>
          </>
        ) : null}
      </div>
    </Dialog>
  );
}
