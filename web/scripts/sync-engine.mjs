// Copies the desktop engine (../engine/prompt_forger_engine) into api/_vendor so the Vercel
// Python function ships the exact same code. `--check` fails if the copy has drifted.
// Usage: node scripts/sync-engine.mjs [--check]
import { createHash } from "node:crypto";
import { cpSync, existsSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(webRoot, "..", "engine", "prompt_forger_engine");
const target = join(webRoot, "api", "_vendor", "prompt_forger_engine");
const skip = (name) => name === "__pycache__" || name.endsWith(".pyc");

function digest(dir) {
  const files = [];
  const walk = (d) => {
    for (const name of readdirSync(d).sort()) {
      if (skip(name)) continue;
      const p = join(d, name);
      if (statSync(p).isDirectory()) walk(p);
      else files.push(p);
    }
  };
  walk(dir);
  const h = createHash("sha256");
  for (const f of files) h.update(relative(dir, f)).update("\0").update(readFileSync(f));
  return h.digest("hex");
}

if (!existsSync(source)) {
  // Builds that only see web/ (no monorepo checkout) use the committed copy as-is.
  console.warn("sync-engine: ../engine not found; using the committed api/_vendor copy.");
  process.exit(0);
}

if (process.argv.includes("--check")) {
  if (!existsSync(target) || digest(source) !== digest(target)) {
    console.error("sync-engine: api/_vendor is out of date. Run `npm run sync-engine` and commit.");
    process.exit(1);
  }
  console.log("sync-engine: vendored engine matches ../engine.");
} else {
  rmSync(target, { recursive: true, force: true });
  cpSync(source, target, { recursive: true, filter: (src) => !skip(src.split(/[\\/]/).pop() ?? "") });
  console.log(`sync-engine: copied engine -> ${relative(webRoot, target)}`);
}
