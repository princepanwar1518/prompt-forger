import type { Metadata } from "next";

import { Forger } from "@/components/forger/Forger";

export const metadata: Metadata = {
  title: "Web app",
  description: "Build, score, enhance and test structured AI prompts in your browser. Free, no sign-up.",
  alternates: { canonical: "/app" },
};

export default function AppPage() {
  return <Forger />;
}
