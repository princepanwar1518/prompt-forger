import Link from "next/link";

import { Logo } from "@/components/ui/Logo";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { CHECKSUMS_URL, DOWNLOADS, REPO_URL, VERSION } from "@/lib/site";

const FEATURES = [
  {
    color: "bg-lime",
    title: "Describe it in plain words",
    body: "Type what you need in English, Hindi or Hinglish. The form fills itself, and asks up to three questions when a request is vague.",
  },
  {
    color: "bg-violet text-white",
    title: "Four output formats",
    body: "A standard prompt, a Ralph loop for coding agents, a node/edge graph loop, or a reusable agent profile.",
  },
  {
    color: "bg-tangerine",
    title: "Score with a breakdown",
    body: "Every prompt gets a 0–100 score and five bars: Clarity, Specificity, Structure, Checkability and Fit.",
  },
  {
    color: "bg-bubblegum",
    title: "One-click Enhance",
    body: "Fixes weak roles, vague criteria and broken schemas. Shows the before and after score and every change. Apply or discard.",
  },
  {
    color: "bg-lime",
    title: "Rate the AI's reply",
    body: "Test the prompt on Claude or OpenAI, then check the reply against your own success criteria for an accuracy score.",
  },
  {
    color: "bg-surface",
    title: "Your key stays yours",
    body: "API keys stay in your browser (or the OS keychain on desktop), go straight to the provider per request and are never stored.",
  },
];

const STEPS = [
  { n: "01", title: "Say what you need", body: "\"Write a polite mail to chase clients who haven't paid\" is enough." },
  { n: "02", title: "Check the score", body: "See what's missing: success criteria, an output shape, a clearer role." },
  { n: "03", title: "Enhance and copy", body: "Apply the fixes, copy the prompt, or test it and rate the reply." },
];

export default function Home() {
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 pill pill-lime">
        Skip to content
      </a>

      <header className="sticky top-0 z-40 border-b-2 border-line bg-paper/90 backdrop-blur">
        <nav className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6" aria-label="Main">
          <Logo />
          <div className="flex items-center gap-2 sm:gap-3">
            <a href="#features" className="hidden rounded-full px-3 py-2 text-sm font-semibold hover:underline md:inline">
              Features
            </a>
            <a href="#download" className="hidden rounded-full px-3 py-2 text-sm font-semibold hover:underline md:inline">
              Download
            </a>
            <ThemeToggle />
            <Link href="/app" className="pill pill-ink">
              Open app <span aria-hidden>→</span>
            </Link>
          </div>
        </nav>
      </header>

      <main id="main">
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 md:grid-cols-[1.1fr_0.9fr] md:pt-20 md:pb-24">
          <div className="animate-rise">
            <p className="eyebrow mb-4">
              <span className="mr-2 inline-block size-2 rounded-full bg-lime align-middle ring-2 ring-line" />
              Free · Web, Windows and Mac · v{VERSION}
            </p>
            <h1 className="font-display text-5xl leading-[0.95] font-extrabold tracking-tight text-balance sm:text-6xl lg:text-7xl">
              Say it plainly. <span className="rounded-2xl bg-lime px-2 text-onaccent">Get a prompt</span> that works.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted text-pretty">
              Prompt Forger turns a rough request into a structured prompt for Claude, GPT, Gemini or any model. It scores
              it, fixes the weak spots, and checks whether the AI&apos;s answer actually met your brief.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/app" className="pill pill-lime h-13 px-7 text-base">
                Start forging, free <span aria-hidden>→</span>
              </Link>
              <a href="#download" className="pill pill-plain h-13 px-7 text-base">
                Download the app
              </a>
            </div>
            <p className="mt-4 text-sm text-muted">No sign-up. Works with offline rules; add your own Claude or OpenAI key for AI features.</p>
          </div>

          <ScorePreview />
        </section>

        <section id="features" aria-labelledby="features-title" className="border-y-2 border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
            <p className="eyebrow">What it does</p>
            <h2 id="features-title" className="mt-2 max-w-2xl font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
              From &ldquo;make me a thing&rdquo; to a prompt you can trust.
            </h2>
            <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((f) => (
                <li key={f.title} className="card p-6 transition-transform duration-200 hover:-translate-y-1">
                  <span aria-hidden className={`mb-4 block size-9 rounded-full border-2 border-line ${f.color}`} />
                  <h3 className="font-display text-xl font-bold">{f.title}</h3>
                  <p className="mt-2 text-muted">{f.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="how-title" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
          <p className="eyebrow">How it works</p>
          <h2 id="how-title" className="mt-2 font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
            Three steps. About a minute.
          </h2>
          <ol className="mt-10 grid gap-5 md:grid-cols-3">
            {STEPS.map((s) => (
              <li key={s.n} className="card bg-paper p-6">
                <span className="font-mono text-sm text-violet">{s.n}</span>
                <h3 className="mt-2 font-display text-2xl font-bold">{s.title}</h3>
                <p className="mt-2 text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="download" aria-labelledby="download-title" className="border-t-2 border-line bg-ink text-paper">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
            <p className="font-mono text-[11px] tracking-[0.12em] text-lime uppercase">Desktop app · v{VERSION}</p>
            <h2 id="download-title" className="mt-2 font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
              Prefer an app? Take it offline.
            </h2>
            <p className="mt-3 max-w-2xl text-paper/70">
              Same engine as the web app, plus Ollama for fully local AI and keys stored in your OS keychain. Java and Python
              are bundled, so there&apos;s nothing else to install.
            </p>
            <ul className="mt-10 grid gap-5 sm:grid-cols-2">
              {DOWNLOADS.map((d) => (
                <li key={d.id}>
                  <a
                    href={d.href}
                    className={`group flex h-full flex-col rounded-[22px] border-2 border-paper p-6 transition-transform duration-200 hover:-translate-y-1 ${d.primary ? "bg-lime text-onaccent" : "bg-ink text-paper"}`}
                    download
                  >
                    <span className="font-mono text-xs uppercase opacity-70">
                      {d.os} · {d.size}
                    </span>
                    <span className="mt-1 font-display text-2xl font-bold">{d.title}</span>
                    <span className="mt-2 text-sm opacity-80">{d.detail}</span>
                    <span className="mt-4 inline-flex items-center gap-2 font-semibold">
                      Download <span aria-hidden className="transition-transform group-hover:translate-y-0.5">↓</span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
            <div className="mt-8 grid gap-4 text-sm text-paper/70 md:grid-cols-2">
              <p>
                <strong className="text-paper">First launch on Windows:</strong> the app isn&apos;t code-signed yet, so if you see
                &ldquo;Windows protected your PC&rdquo;, click <em>More info → Run anyway</em>.
              </p>
              <p>
                <strong className="text-paper">First launch on Mac:</strong> open it once, then go to{" "}
                <em>System Settings → Privacy &amp; Security → Open Anyway</em>.
              </p>
            </div>
            <p className="mt-6 text-sm text-paper/60">
              Verify downloads with the{" "}
              <a className="underline hover:text-lime" href={CHECKSUMS_URL}>
                SHA-256 checksums
              </a>
              .
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t-2 border-line">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:px-6">
          <p>© {new Date().getFullYear()} Prince Panwar · Panwar Studio</p>
          <div className="flex gap-5">
            <Link href="/app" className="hover:text-ink hover:underline">
              Web app
            </Link>
            <a href={REPO_URL} className="hover:text-ink hover:underline" rel="noopener">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </>
  );
}

function ScorePreview() {
  const bars = [
    { name: "Clarity", from: 65, to: 100 },
    { name: "Specificity", from: 50, to: 100 },
    { name: "Structure", from: 85, to: 100 },
    { name: "Checkability", from: 30, to: 100 },
    { name: "Fit", from: 30, to: 100 },
  ];
  return (
    <figure className="card relative animate-rise p-6 [animation-delay:120ms] sm:p-8" aria-label="Example: Enhance raises a prompt score from 44 to 100">
      <span aria-hidden className="absolute -top-4 -right-3 rotate-6 rounded-full border-2 border-line bg-bubblegum px-3 py-1 text-xs font-bold text-onaccent shadow-hard-sm">
        ✦ Enhanced
      </span>
      <p className="eyebrow">Prompt score</p>
      <div className="mt-2 flex items-end gap-4">
        <span className="font-display text-4xl font-bold text-muted line-through decoration-2">44</span>
        <span aria-hidden className="pb-2 text-2xl">→</span>
        <span className="font-display text-7xl leading-none font-extrabold">100</span>
        <span className="mb-2 rounded-full border-2 border-line bg-lime px-3 py-0.5 text-xs font-bold text-onaccent">Excellent</span>
      </div>
      <ul className="mt-6 space-y-3">
        {bars.map((b) => (
          <li key={b.name} className="grid grid-cols-[6.5rem_1fr_2rem] items-center gap-3 text-sm">
            <span className="font-semibold">{b.name}</span>
            <span className="relative h-3 overflow-hidden rounded-full border-2 border-line bg-paper">
              <span className="absolute inset-y-0 left-0 bg-tangerine/40" style={{ width: `${b.from}%` }} />
              <span className="absolute inset-y-0 left-0 bg-lime" style={{ width: `${b.to}%` }} />
            </span>
            <span className="text-right font-mono text-xs">{b.to}</span>
          </li>
        ))}
      </ul>
      <figcaption className="mt-6 rounded-2xl border-2 border-dashed border-line/40 p-3 font-mono text-xs text-muted">
        role: assistant → professional business writer
        <br />+ success criteria · + output schema · + token budget
      </figcaption>
    </figure>
  );
}
