"use client";

import { forwardRef, useImperativeHandle, useRef, useState } from "react";

import { TEXT_FIELDS, isLoop, type FieldDef } from "@/lib/form";
import type { FormKey, FormState, Meta } from "@/lib/types";

export interface FormPanelHandle {
  focusField: (key: string) => void;
}

interface Props {
  form: FormState;
  meta: Meta | null;
  errors: Record<string, string>;
  onChange: (key: FormKey, value: string) => void;
}

const FORMAT_COLORS: Record<string, string> = {
  standard: "bg-lime text-onaccent",
  ralph: "bg-violet text-white",
  graph: "bg-tangerine text-onaccent",
  agent: "bg-bubblegum text-onaccent",
};

const BASIC = TEXT_FIELDS.filter((f) => !f.advanced);
const ADVANCED = TEXT_FIELDS.filter((f) => f.advanced);

export const FormPanel = forwardRef<FormPanelHandle, Props>(function FormPanel({ form, meta, errors, onChange }, ref) {
  const [showMore, setShowMore] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const refs = useRef<Record<string, HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null>>({});

  useImperativeHandle(ref, () => ({
    focusField: (key: string) => {
      if (ADVANCED.some((f) => f.key === key)) setShowMore(true);
      // Wait a frame so a just-opened section is rendered before focusing.
      requestAnimationFrame(() => {
        const el = refs.current[key];
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
        el?.focus({ preventScroll: true });
      });
    },
  }));

  const advancedFilled = ADVANCED.filter((f) => form[f.key].trim()).length;
  const loop = isLoop(form.format);
  const modelHint = meta?.models.find((m) => m.id === form.model)?.hint;

  const renderField = (f: FieldDef) => {
    const id = `field-${f.key}`;
    const showError = (touched[f.key] ?? false) && !form[f.key].trim() && errors[f.key];
    const describedBy = [f.hint ? `${id}-hint` : "", showError ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;
    const common = {
      id,
      value: form[f.key],
      placeholder: f.placeholder,
      "aria-describedby": describedBy,
      "aria-invalid": showError ? true : undefined,
      "aria-required": !f.optional || undefined,
      onBlur: () => {
        if (form[f.key].trim()) setTouched((t) => ({ ...t, [f.key]: true }));
      },
      className: `field-input ${showError ? "border-tangerine" : ""}`,
    };
    if (f.key === "tools" && form.format !== "agent") return null;
    return (
      <div key={f.key}>
        <div className="mb-1.5 flex items-center gap-2">
          <label htmlFor={id} className="text-sm font-bold">
            {f.label}
          </label>
          {f.optional ? <span className="tag">optional</span> : null}
        </div>
        {f.rows ? (
          <textarea
            {...common}
            ref={(el) => {
              refs.current[f.key] = el;
            }}
            rows={f.rows}
            maxLength={20000}
            onChange={(e) => onChange(f.key, e.target.value)}
            className={`${common.className} resize-y`}
          />
        ) : (
          <input
            {...common}
            ref={(el) => {
              refs.current[f.key] = el;
            }}
            type="text"
            maxLength={500}
            onChange={(e) => onChange(f.key, e.target.value)}
          />
        )}
        {showError ? (
          <p id={`${id}-error`} className="mt-1 text-sm font-semibold text-tangerine">
            {errors[f.key]}
          </p>
        ) : f.hint ? (
          <p id={`${id}-hint`} className="mt-1 text-xs text-muted">
            {f.hint}
          </p>
        ) : null}
      </div>
    );
  };

  return (
    <section aria-labelledby="form-title" className="space-y-8">
      <div>
        <p className="eyebrow">02 · The brief</p>
        <h2 id="form-title" className="font-display text-2xl font-bold">
          The essentials
        </h2>
      </div>

      <div className="space-y-5">{BASIC.map(renderField)}</div>

      <div className="rounded-[22px] border-2 border-line bg-surface">
        <button
          type="button"
          onClick={() => setShowMore((v) => !v)}
          aria-expanded={showMore}
          aria-controls="more-fields"
          className="flex w-full items-center justify-between gap-3 rounded-[20px] px-5 py-4 text-left font-semibold"
        >
          <span>
            More fields{" "}
            <span className="text-sm font-normal text-muted">
              constraints, success criteria, examples, schema{advancedFilled ? ` · ${advancedFilled} filled` : ""}
            </span>
          </span>
          <span aria-hidden className={`transition-transform ${showMore ? "rotate-180" : ""}`}>
            ▾
          </span>
        </button>
        {showMore ? (
          <div id="more-fields" className="space-y-5 border-t-2 border-line px-5 pt-5 pb-6">
            {ADVANCED.map(renderField)}
          </div>
        ) : null}
      </div>

      <fieldset>
        <legend className="eyebrow">03 · Output</legend>
        <p className="mb-3 font-display text-2xl font-bold">Output format</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(meta?.formats ?? []).map((f, i) => {
            const checked = form.format === f.id;
            return (
              <label
                key={f.id}
                className={`relative cursor-pointer rounded-[18px] border-2 border-line p-4 transition-[transform,box-shadow] duration-150 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-violet ${checked ? `${FORMAT_COLORS[f.id] ?? "bg-lime"} -translate-y-0.5 shadow-hard` : "bg-surface hover:-translate-y-0.5 hover:shadow-hard-sm"}`}
              >
                <input
                  type="radio"
                  name="format"
                  value={f.id}
                  checked={checked}
                  onChange={() => onChange("format", f.id)}
                  className="sr-only"
                />
                <span className="font-mono text-[11px] opacity-70">0{i + 1}</span>
                <span className="block font-display text-lg font-bold">{f.label}</span>
                <span className="block text-sm opacity-80">{f.hint}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="field-model" className="mb-1.5 block text-sm font-bold">
            Target model
          </label>
          <select
            id="field-model"
            ref={(el) => {
              refs.current.model = el;
            }}
            value={form.model}
            onChange={(e) => onChange("model", e.target.value)}
            className="field-input"
            aria-describedby="field-model-hint"
          >
            {(meta?.models ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
          <p id="field-model-hint" className="mt-1 text-xs text-muted">
            {modelHint}
          </p>
        </div>

        <fieldset className="sm:col-span-2">
          <legend className="mb-1.5 text-sm font-bold">Verbosity</legend>
          <div className="inline-flex rounded-full border-2 border-line bg-surface p-1">
            {(meta?.verbosity ?? []).map((v) => (
              <label
                key={v.id}
                className={`cursor-pointer rounded-full px-4 py-2 text-sm font-semibold transition-colors has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-violet ${form.verbosity === v.id ? "bg-ink text-paper" : "hover:bg-paper"}`}
              >
                <input
                  type="radio"
                  name="verbosity"
                  value={v.id}
                  checked={form.verbosity === v.id}
                  onChange={() => onChange("verbosity", v.id)}
                  className="sr-only"
                />
                {v.label}
              </label>
            ))}
          </div>
        </fieldset>

        <NumberField
          id="tokenBudget"
          label="Token budget"
          hint="Response length cap, in tokens."
          placeholder="e.g. 800"
          value={form.tokenBudget}
          inputRef={(el) => {
            refs.current.tokenBudget = el;
          }}
          onChange={(v) => onChange("tokenBudget", v)}
        />
        <NumberField
          id="maxIterations"
          label="Max iterations"
          hint="Loop safety stop."
          placeholder={loop ? (form.format === "graph" ? "default 3" : "default 20") : "loops only"}
          value={form.maxIterations}
          disabled={!loop}
          inputRef={(el) => {
            refs.current.maxIterations = el;
          }}
          onChange={(v) => onChange("maxIterations", v)}
        />
      </div>
    </section>
  );
});

function NumberField(props: {
  id: string;
  label: string;
  hint: string;
  placeholder: string;
  value: string;
  disabled?: boolean;
  inputRef: (el: HTMLInputElement | null) => void;
  onChange: (v: string) => void;
}) {
  const id = `field-${props.id}`;
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2">
        <label htmlFor={id} className="text-sm font-bold">
          {props.label}
        </label>
        <span className="tag">optional</span>
      </div>
      <input
        id={id}
        ref={props.inputRef}
        inputMode="numeric"
        pattern="[0-9]*"
        value={props.value}
        disabled={props.disabled}
        placeholder={props.placeholder}
        onChange={(e) => props.onChange(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
        aria-describedby={`${id}-hint`}
        className="field-input disabled:opacity-50"
      />
      <p id={`${id}-hint`} className="mt-1 text-xs text-muted">
        {props.hint}
      </p>
    </div>
  );
}
