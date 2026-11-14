"""Local stand-in for the Vercel Python function: serves POST /api/engine on 127.0.0.1:5328.

`npm run dev` starts this alongside Next.js; next.config.ts proxies /api/engine here in development only.
"""

from __future__ import annotations

import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from engine import handler  # noqa: E402

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5328
    print(f"Prompt Forger dev API on http://127.0.0.1:{port}/api/engine", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
