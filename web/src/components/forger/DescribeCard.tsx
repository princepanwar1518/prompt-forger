"use client";

import { useId, useState } from "react";

import { EngineError, engine } from "@/lib/engine";
import type { AiSettings, DescribeResult, FormState } from "@/lib/types";

import { useToast } from "../ui/Toast";

interface Props {
  form: FormState;
  ai: AiSettings;
  onFill: (result: DescribeResult) => void;
  onOpenSettings: () => void;
}

const PROVIDER_LABEL: Record<AiSettings["provider"], string> = {
  rules: "Offline rules",
  anthropic: "Claude",
  openai: "OpenAI",
};

export function DescribeCard({ form, ai, onFill, onOpenSettings }: Props) {
  const toast = useToast();
  const inputId = useId();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);

  const submit = async () => {
    const request = text.trim();
    if (!request) {
      toast("Describe what you need first.", "error");
      return;
    }
    setBusy(true);
    try {
      const qa = questions
        .map((question, i) => ({ question, answer: (answers[i] ?? "").trim() }))
        .filter((x) => x.answer);
      const res = await engine.describe(request, form, qa, ai);
      onFill(res);
      if (res.questions.length && qa.length === 0) {
        setQuestions(res.questions);
        setAnswers(res.questions.map(() => ""));
        toast("Filled what I could. Answer a question or two for a better prompt.");
      } else {
        setQuestions([]);
        setAnswers([]);
        toast(`Filled ${res.filled.length} field${res.filled.length === 1 ? "" : "s"}.`, "success");
      }
    } catch (err) {
      toast(err instanceof EngineError ? err.message : "Couldn't fill the form. Try again.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby={`${inputId}-title`} className="rounded-[22px] border-2 border-line bg-lime p-5 text-onaccent shadow-hard sm:p-6">
      <p className="font-mono text-[11px] tracking-[0.12em] uppercase opacity-70">01 · Start here</p>
      <h2 id={`${inputId}-title`} className="mt-1 font-display text-2xl font-bold sm:text-3xl">
        Describe it in plain words
      </h2>
      <p className="mt-1 text-sm opacity-80">Hindi, Hinglish or English. The form fills itself, and you stay in control.</p>

      <label htmlFor={inputId} className="sr-only">
        What do you need?
      </label>
      <textarea
        id={inputId}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void submit();
        }}
        rows={3}
        maxLength={4000}
        placeholder="e.g. write a polite mail to chase clients who haven't paid"
        className="mt-4 w-full resize-y rounded-2xl border-2 border-line bg-[#fffdf7] px-4 py-3 text-[15px] text-[#17151b] placeholder:text-[#6b6575] focus:shadow-hard-sm focus:outline-none"
      />

      {questions.length > 0 ? (
        <fieldset className="mt-4 space-y-3 rounded-2xl border-2 border-line bg-[#fffdf7] p-4 text-[#17151b]">
          <legend className="px-1 text-sm font-bold">A few quick questions (optional)</legend>
          {questions.map((q, i) => (
            <label key={q} className="block text-sm">
              <span className="font-semibold">{q}</span>
              <input
                value={answers[i] ?? ""}
                onChange={(e) => setAnswers((a) => a.map((v, j) => (j === i ? e.target.value : v)))}
                maxLength={500}
                className="mt-1 w-full rounded-xl border-2 border-line bg-white px-3 py-2 focus:shadow-hard-sm focus:outline-none"
              />
            </label>
          ))}
        </fieldset>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onOpenSettings}
          className="pill bg-[#fffdf7] text-[#17151b]"
          title="Change how the form is filled"
        >
          {PROVIDER_LABEL[ai.provider]} <span aria-hidden>▾</span>
        </button>
        <button type="button" onClick={() => void submit()} disabled={busy} className="pill bg-[#17151b] text-[#f8f4e9]" aria-busy={busy}>
          {busy ? "Filling…" : questions.length ? "Fill again" : "Fill the form"} <span aria-hidden>→</span>
        </button>
      </div>
    </section>
  );
}
