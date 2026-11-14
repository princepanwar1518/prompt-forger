// `npm run dev`: starts the local Python API (scripts/dev_api.py) and `next dev` together.
import { spawn } from "node:child_process";

const python = process.platform === "win32" ? "python" : "python3";
const children = [
  spawn(python, ["scripts/dev_api.py", "5328"], { stdio: "inherit" }),
  spawn(process.platform === "win32" ? "npx.cmd" : "npx", ["next", "dev"], { stdio: "inherit" }),
];

const stop = () => {
  for (const c of children) c.kill();
  process.exit();
};
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
for (const c of children) c.on("exit", (code) => code && stop());
