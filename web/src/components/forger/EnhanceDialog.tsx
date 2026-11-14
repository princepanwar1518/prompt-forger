"use client";

import { FIELD_LABELS } from "@/lib/form";
import type { EnhanceResult } from "@/lib/types";

import { Dialog } from "../ui/Dialog";

interface Props {
  result: EnhanceResult | null;
  onApply: () => void;
  onDiscard: () => void;
}

const SOURCE_LABEL: Record<string, string> = {
  offline: "Offline fixes",
  anthropic: "Claude rewrite + offline fixes",
  openai: "OpenAI rewrite + offline fixes",
};

export function EnhanceDialog({ result, onApply, onDiscard }: Props) {
  const nothing = result !== null && result.changes.length === 0;
  return (
    <Dialog
      open={result !== null}
      onClose={onDiscard}
      eyebrow="✦ Enhance"
      title={nothing ? "Already in good shape" : "Suggested improvements"}
      wide
      footer={
        nothing ? (
          <button type="button" onClick={onDiscard} className="pill pill-ink">
            Close
          </button>
        ) : (
          <>
            <button type="button" onClick={onDiscard} className="pill pill-plain">
              Discard
            </button>
            <button type="button" onClick={onApply} className="pill pill-lime">
              Apply changes
            </button>
          </>
        )
      }
    >
      {result ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-display text-5xl font-bold text-muted" aria-label={`Score before: ${result.before}`}>
              {result.before}
            </span>
            <span aria-hidden className="text-3xl">
              →
            </span>
            <span className="font-display text-6xl font-extrabold" aria-label={`Score after: ${result.after}`}>
              {result.after}
            </span>
            <span className="tag ml-auto">{SOURCE_LABEL[result.source] ?? result.source}</span>
          </div>

          {result.changes.length ? (
            <ul className="space-y-3">
              {result.changes.map((c, i) => (
                <li key={`${c.field}-${i}`} className="rounded-2xl border-2 border-line bg-surface p-4">
                  <p className="eyebrow">
                    {FIELD_LABELS[c.field] ?? c.field} · {c.action}
                  </p>
                  <p className="mt-1 font-semibold">{c.summary}</p>
                  {c.before ? (
                    <p className="mt-2 font-mono text-xs whitespace-pre-wrap text-muted line-through">{c.before}</p>
                  ) : null}
                  {c.after ? (
                    <p className="mt-1 rounded-lg bg-lime/25 px-2 py-1 font-mono text-xs whitespace-pre-wrap">{c.after}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">Nothing to change automatically.</p>
          )}

          {result.needsYou.length ? (
            <div className="rounded-2xl border-2 border-tangerine bg-tangerine/10 p-4">
              <p className="font-bold">Needs you</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {result.needsYou.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.notes.length ? (
            <ul className="space-y-1 text-sm text-muted">
              {result.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </Dialog>
  );
}
