"use client";

import { useEffect, useState } from "react";

import { themeStore } from "@/lib/storage";

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);

  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    themeStore.save(next ? "dark" : "light");
    setDark(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="pill pill-plain size-11 px-0"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
    >
      <span aria-hidden className="text-lg leading-none">
        {dark === null ? "◐" : dark ? "☀" : "☾"}
      </span>
    </button>
  );
}
