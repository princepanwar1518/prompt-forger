"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  eyebrow?: string;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

/** Native <dialog>: focus trap, Esc to close and inert background come from the browser. */
export function Dialog({ open, onClose, title, eyebrow, children, footer, wide }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose(); // click on the backdrop
      }}
      className={`m-auto max-h-[92dvh] w-[calc(100%-1.5rem)] ${wide ? "max-w-3xl" : "max-w-xl"} overflow-hidden rounded-[24px] border-2 border-line bg-paper p-0 text-ink shadow-hard-lg open:animate-pop`}
    >
      <div className="flex max-h-[92dvh] flex-col">
        <header className="flex items-start justify-between gap-4 border-b-2 border-line px-5 py-4 sm:px-6">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            <h2 id={titleId} className="font-display text-2xl font-bold">
              {title}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="pill pill-plain size-10 shrink-0 px-0" aria-label="Close">
            <span aria-hidden>✕</span>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
        {footer ? (
          <footer className="flex flex-wrap justify-end gap-3 border-t-2 border-line px-5 py-4 sm:px-6">{footer}</footer>
        ) : null}
      </div>
    </dialog>
  );
}
