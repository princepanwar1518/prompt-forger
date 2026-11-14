import Link from "next/link";

export function Logo({ version }: { version?: string }) {
  return (
    <Link href="/" className="group inline-flex items-center gap-2.5 rounded-full" aria-label="Prompt Forger home">
      <span
        aria-hidden
        className="size-6 rounded-full border-2 border-line bg-lime transition-transform duration-300 group-hover:rotate-180 group-hover:scale-110"
      />
      <span className="font-display text-xl font-bold tracking-tight sm:text-2xl">Prompt Forger</span>
      {version ? (
        <span className="rounded-full bg-violet px-2 py-0.5 font-mono text-[11px] text-white">v{version}</span>
      ) : null}
    </Link>
  );
}
