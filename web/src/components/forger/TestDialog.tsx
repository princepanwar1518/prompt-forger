"use client";

import { useEffect, useState } from "react";

import { EngineError, engine } from "@/lib/engine";
import type { AiSettings, FormState, RateResult } from "@/lib/types";

import { Dialog } from "../ui/Dialog";

interface Props {
  open: boolean;
  onClose: () => void;
  prompt: string;
  form: FormState;
  ai: AiSettings;
  onOpenSettings: () => void;
}

type Phase = "idle" | "running" | "rating" | "done";

export function TestDialog({ open, onClose, prompt, form, ai, onOpenSettings }: Props) {
  const [input, setInput] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [reply, setReply] = useState("");
  const [rating, setRating] = useState<RateResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setPhase("idle");
      setReply("");
      setRating(null);
      setError("");
    }
  }, [open]);

  const ready = ai.provider !== "rules" && ai.apiKey.trim().length > 0;

  const send = async () => {
    setError("");
    setRating(null);
    setPhase("running");
    try {
      const res = await engine.run(prompt, input, ai);
      setReply(res.reply);
      setPhase("rating");
      try {
        setRating(await engine.rate(form, res.reply, ai));
      } catch (err) {
        setError(err instanceof EngineError ? `Couldn't rate the reply: ${err.message}` : "Couldn't rate the reply.");
      }
      setPhase("done");
    } catch (err) {
      setError(err instanceof EngineError ? err.message : "The test failed. Try again.");
      setPhase("idle");
    }
  };

  const busy = phase === "running" || phase === "rating";

  return (
    <Dialog open={open} onClose={onClose} eyebrow="Test it" title="Run this prompt and rate the reply" wide>
      {!ready ? (
        <div className="space-y-4">
          <p>
            Testing sends your prompt to Claude or OpenAI using <strong>your own API key</strong>. The key stays in this browser
            and is never stored on our server.
          </p>
          <button type="button" onClick={onOpenSettings} className="pill pill-violet">
            Open AI settings
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <div>
            <label htmlFor="test-input" className="mb-1.5 block text-sm font-bold">
              Your message to the model <span className="tag ml-1">optional</span>
            </label>
            <textarea
              id="test-input"
              rows={3}
              value={input}
              maxLength={8000}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Leave empty to just say “Please begin.”"
              className="field-input resize-y"
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => void send()} disabled={busy} className="pill pill-violet" aria-busy={busy}>
              {phase === "running" ? "Waiting for the model…" : phase === "rating" ? "Rating the reply…" : reply ? "Send again" : "Send"}
            </button>
            <span className="text-sm text-muted">
              Using {ai.provider === "anthropic" ? "Claude" : "OpenAI"}
              {ai.model ? ` · ${ai.model}` : ""}
            </span>
          </div>

          {error ? (
            <p role="alert" className="rounded-2xl border-2 border-tangerine bg-tangerine/10 p-3 text-sm font-semibold">
              {error}
            </p>
          ) : null}

          {reply ? (
            <div>
              <p className="eyebrow mb-2">Reply</p>
              <pre className="max-h-72 overflow-auto rounded-2xl border-2 border-line bg-code p-4 font-mono text-[13px] whitespace-pre-wrap">
                {reply}
              </pre>
            </div>
          ) : null}

          {rating ? <RatingPanel rating={rating} /> : null}
        </div>
      )}
    </Dialog>
  );
}

function RatingPanel({ rating }: { rating: RateResult }) {
  const tone =
    rating.accuracy === null ? "bg-surface" : rating.accuracy >= 90 ? "bg-lime text-onaccent" : rating.accuracy >= 60 ? "bg-violet text-white" : "bg-tangerine text-onaccent";
  return (
    <section aria-label="Reply rating" className="card overflow-hidden">
      <div className={`flex flex-wrap items-end gap-4 border-b-2 border-line p-5 ${tone}`}>
        <div>
          <p className="font-mono text-[11px] tracking-[0.12em] uppercase opacity-75">Accuracy</p>
          <p className="font-display text-6xl leading-none font-extrabold">
            {rating.accuracy === null ? "—" : `${rating.accuracy}%`}
          </p>
        </div>
        <div className="pb-1">
          <p className="font-display text-xl font-bold">{rating.verdict}</p>
          <p className="text-sm opacity-80">
            {rating.passed} of {rating.checked} checks passed
            {rating.total > rating.checked ? ` · ${rating.total - rating.checked} not rated` : ""}
          </p>
        </div>
      </div>
      {rating.summary ? <p className="border-b-2 border-dashed border-line/25 px-5 py-3 text-sm">{rating.summary}</p> : null}
      <ul className="divide-y divide-line/15">
        {rating.checks.map((c, i) => (
          <li key={`${c.item}-${i}`} className="flex gap-3 px-5 py-3 text-sm">
            <span
              aria-label={c.passed === null ? "Not rated" : c.passed ? "Passed" : "Failed"}
              className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border-2 border-line text-xs font-bold ${c.passed === null ? "bg-surface" : c.passed ? "bg-lime text-onaccent" : "bg-tangerine text-onaccent"}`}
            >
              {c.passed === null ? "○" : c.passed ? "✓" : "✕"}
            </span>
            <span>
              <span className="font-semibold">{c.item}</span>
              <span className="block text-muted">
                {c.reason} <span className="tag ml-1">{c.kind}</span>
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
