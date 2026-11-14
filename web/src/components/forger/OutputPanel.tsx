"use client";

import { useEffect, useState } from "react";

import { FIELD_LABELS } from "@/lib/form";
import type { ForgeOk, Quality } from "@/lib/types";

import { useToast } from "../ui/Toast";

interface Props {
  result: ForgeOk | null;
  busy: boolean;
  missing: string[];
  onEnhance: () => void;
  enhancing: boolean;
  onTest: () => void;
  onFocusField: (key: string) => void;
}

const estimateTokens = (text: string) => Math.max(1, Math.round(text.length / 4));

export function OutputPanel({ result, busy, missing, onEnhance, enhancing, onTest, onFocusField }: Props) {
  const toast = useToast();
  const [active, setActive] = useState(0);
  const [plain, setPlain] = useState(false);

  const files = result?.files ?? [];
  const file = files[Math.min(active, Math.max(files.length - 1, 0))];

  useEffect(() => {
    if (active >= files.length) setActive(0);
  }, [files.length, active]);

  const copy = async () => {
    if (!file) return;
    try {
      await navigator.clipboard.writeText(file.content);
      toast(`Copied ${file.path}.`, "success");
    } catch {
      toast("Copy failed. Select the text and copy it manually.", "error");
    }
  };

  const download = () => {
    if (!file) return;
    const url = URL.createObjectURL(new Blob([file.content], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = file.path.split("/").pop() || "prompt.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const totalChars = files.reduce((n, f) => n + f.content.length, 0);

  return (
    <section aria-labelledby="output-title" className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">04 · Result</p>
          <h2 id="output-title" className="font-display text-2xl font-bold">
            Your prompt
          </h2>
        </div>
        {result ? (
          <p className="font-mono text-xs text-muted" aria-live="polite">
            ≈ {estimateTokens(files.map((f) => f.content).join("")).toLocaleString()} tokens ·{" "}
            {totalChars.toLocaleString()} chars{busy ? " · updating…" : ""}
          </p>
        ) : null}
      </div>

      {!result ? (
        <div className="card flex min-h-80 flex-col items-center justify-center p-8 text-center">
          <span aria-hidden className="mb-4 block size-12 rounded-full border-2 border-line bg-lime" />
          <p className="font-display text-3xl font-bold">Nothing forged yet.</p>
          <p className="mt-2 max-w-sm text-muted">
            {missing.length
              ? `Fill in ${missing.map((m) => FIELD_LABELS[m] ?? m).join(" and ")} and the prompt builds live as you type.`
              : "Describe what you need, or fill in Role and Task."}
          </p>
        </div>
      ) : (
        <>
          <QualityCard quality={result.quality} onEnhance={onEnhance} enhancing={enhancing} onFocusField={onFocusField} />

          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setPlain((v) => !v)} aria-pressed={plain} className={`pill ${plain ? "pill-ink" : "pill-plain"}`}>
              Plain English
            </button>
            <button type="button" onClick={onTest} className="pill pill-violet">
              Test it
            </button>
            <span className="grow" />
            <button type="button" onClick={download} className="pill pill-plain" aria-label={`Download ${file?.path ?? "file"}`}>
              <span aria-hidden>↓</span> Save
            </button>
            <button type="button" onClick={() => void copy()} className="pill pill-lime">
              Copy
            </button>
          </div>

          {plain ? (
            <p className="card bg-paper p-5 text-[15px] leading-relaxed">{result.explanation}</p>
          ) : null}

          {result.warnings.length ? (
            <ul className="space-y-1 rounded-2xl border-2 border-tangerine bg-tangerine/10 p-4 text-sm">
              {result.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          ) : null}

          <div className="card overflow-hidden">
            {files.length > 1 ? (
              <div role="tablist" aria-label="Generated files" className="flex gap-1 overflow-x-auto border-b-2 border-line p-2">
                {files.map((f, i) => (
                  <button
                    key={f.path}
                    role="tab"
                    type="button"
                    aria-selected={i === active}
                    aria-controls="file-panel"
                    onClick={() => setActive(i)}
                    className={`shrink-0 rounded-full px-4 py-1.5 font-mono text-xs transition-colors ${i === active ? "bg-lime text-onaccent ring-2 ring-line" : "hover:bg-paper"}`}
                  >
                    {f.path}
                  </button>
                ))}
              </div>
            ) : null}
            {file ? (
              <div id="file-panel" role={files.length > 1 ? "tabpanel" : undefined}>
                <p className="border-b-2 border-dashed border-line/25 px-5 py-2.5 text-xs text-muted">
                  <span className="font-mono text-ink">{file.path}</span> · {file.description}
                </p>
                <pre className="max-h-[70vh] overflow-auto bg-code px-5 py-4 font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words">
                  {file.content}
                </pre>
              </div>
            ) : null}
          </div>
        </>
      )}
    </section>
  );
}

function barColor(score: number) {
  if (score >= 85) return "bg-lime";
  if (score >= 60) return "bg-violet";
  return "bg-tangerine";
}

function QualityCard({
  quality,
  onEnhance,
  enhancing,
  onFocusField,
}: {
  quality: Quality;
  onEnhance: () => void;
  enhancing: boolean;
  onFocusField: (key: string) => void;
}) {
  return (
    <div className="card grid gap-6 p-5 sm:p-6 lg:grid-cols-[auto_1fr]">
      <div className="flex flex-row items-center gap-4 lg:flex-col lg:items-start">
        <div>
          <p className="eyebrow">Prompt score</p>
          <p className="font-display text-6xl leading-none font-extrabold" aria-label={`Score ${quality.score} out of 100`}>
            {quality.score}
          </p>
        </div>
        <span className={`rounded-full border-2 border-line px-3 py-0.5 text-xs font-bold ${barColor(quality.score)} ${quality.score >= 60 && quality.score < 85 ? "text-white" : "text-onaccent"}`}>
          {quality.grade}
        </span>
        <button type="button" onClick={onEnhance} disabled={enhancing} className="pill pill-ink ml-auto lg:ml-0" aria-busy={enhancing}>
          ✦ {enhancing ? "Enhancing…" : "Enhance"}
        </button>
      </div>

      <div className="space-y-5">
        <ul className="space-y-2.5" aria-label="Score breakdown">
          {quality.dimensions.map((d) => (
            <li key={d.name} className="grid grid-cols-[6.5rem_1fr_2rem] items-center gap-3 text-sm" title={d.hint}>
              <span className="font-semibold">{d.name}</span>
              <span
                className="h-3 overflow-hidden rounded-full border-2 border-line bg-paper"
                role="meter"
                aria-label={d.name}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={d.score}
              >
                <span className={`block h-full transition-[width] duration-500 ${barColor(d.score)}`} style={{ width: `${d.score}%` }} />
              </span>
              <span className="text-right font-mono text-xs">{d.score}</span>
            </li>
          ))}
        </ul>

        {quality.findings.length ? (
          <ul className="space-y-1.5">
            {quality.findings.map((f) => (
              <li key={`${f.field}-${f.message}`}>
                <button
                  type="button"
                  onClick={() => onFocusField(f.field)}
                  className="group flex w-full items-start gap-2 rounded-xl px-2 py-1.5 text-left text-sm hover:bg-paper"
                >
                  <span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${f.level === "warning" ? "bg-tangerine" : "bg-violet"}`} />
                  <span>
                    <span className="font-semibold">{FIELD_LABELS[f.field] ?? f.field}:</span> {f.message}
                    <span className="ml-1 text-muted opacity-0 transition-opacity group-hover:opacity-100">Fix →</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">Nothing to fix. This prompt is specific, checkable and well-shaped.</p>
        )}
      </div>
    </div>
  );
}
