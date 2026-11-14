import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";

import "./globals.css";

const bricolage = localFont({
  src: [
    { path: "../fonts/BricolageGrotesque-Bold.ttf", weight: "700" },
    { path: "../fonts/BricolageGrotesque-Display.ttf", weight: "800" },
  ],
  variable: "--font-bricolage",
  display: "swap",
});

const space = localFont({
  src: [
    { path: "../fonts/SpaceGrotesk-Regular.ttf", weight: "400" },
    { path: "../fonts/SpaceGrotesk-SemiBold.ttf", weight: "600" },
    { path: "../fonts/SpaceGrotesk-Bold.ttf", weight: "700" },
  ],
  variable: "--font-space",
  display: "swap",
});

const dmMono = localFont({
  src: [
    { path: "../fonts/DMMono-Regular.ttf", weight: "400" },
    { path: "../fonts/DMMono-Medium.ttf", weight: "500" },
  ],
  variable: "--font-dmmono",
  display: "swap",
});

// Vercel sets VERCEL_PROJECT_PRODUCTION_URL at build time; used for absolute Open Graph URLs.
const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Prompt Forger: build, score and improve AI prompts",
    template: "%s · Prompt Forger",
  },
  description:
    "Turn a plain-language request into a structured prompt, Ralph loop, graph loop or agent profile. Score it, enhance it, and rate the AI's reply. Free web app plus Windows and Mac apps.",
  applicationName: "Prompt Forger",
  keywords: ["prompt engineering", "prompt builder", "AI prompts", "Claude", "ChatGPT", "agent profile", "Ralph loop"],
  authors: [{ name: "Prince Panwar" }],
  openGraph: {
    type: "website",
    siteName: "Prompt Forger",
    title: "Prompt Forger: build, score and improve AI prompts",
    description: "Describe what you need in plain words. Get a structured prompt, a score, and one-click fixes.",
    url: "/",
  },
  twitter: { card: "summary", title: "Prompt Forger", description: "Build, score and improve AI prompts." },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f4e9" },
    { media: "(prefers-color-scheme: dark)", color: "#17151b" },
  ],
};

// Applies the saved (or system) theme before first paint, so dark mode never flashes light.
const themeScript = `(()=>{try{var t=localStorage.getItem("pf.theme");var d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}})()`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${bricolage.variable} ${space.variable} ${dmMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-dvh bg-paper text-ink">{children}</body>
    </html>
  );
}
