# Prompt Forger: website and web app

This folder holds the Next.js site: a landing page with the desktop downloads at `/`, and the full web app at `/app`. It is hosted on Vercel.

## Architecture

```
browser ──POST /api/engine──▶ api/engine.py  (Vercel Python function)
                                  └─ api/_dispatch.py  → api/_vendor/prompt_forger_engine
                                                         (exact copy of ../engine/prompt_forger_engine)
```

- **One engine.** The web app and the desktop app run the same Python engine, so there is no second implementation that can drift. `npm run sync-engine` copies `../engine` into `api/_vendor`. `npm run build` fails if the copy is out of date.
- **One endpoint.** `POST /api/engine` takes `{"method": "...", "params": {...}}`. The available methods are `meta`, `forge`, `describe`, `enhance`, `rate` and `run`. Keychain methods and Ollama are not available on the web.
- **API keys.**
  - The user's Claude or OpenAI key is kept in their browser: in sessionStorage by default, or in localStorage if they tick "Remember on this device".
  - It is sent in the `X-PF-Key` header with each AI request and passed straight to the provider for that one request.
  - It is never stored or logged on the server.
- **Guards:**
  - a 256 KB body limit
  - a per-client rate limit (240 requests a minute for forge/meta, 30 for AI methods)
  - generic 500 errors that leak no detail
  - strict security headers, including a CSP that allows only connections back to this site

```
web/
├─ api/engine.py          Vercel function (stdlib only)
├─ api/_dispatch.py       method routing, key scoping, limits
├─ api/_vendor/           synced engine copy (don't edit; run npm run sync-engine)
├─ src/app/               landing (page.tsx), web app (app/page.tsx), SEO routes
├─ src/components/forger  Describe, form, output/score, Enhance, Test + rating, settings
├─ src/lib/               typed engine client, form model, browser storage
├─ scripts/               dev runner, local API server, engine sync
└─ tests/                 pytest for the dispatcher
```

## Develop

```bash
cd web
npm install
npm run dev        # Next.js on :3000 + local Python API on :5328 (proxied in dev only)
npm run typecheck
npm run test:api   # needs pytest
```

After changing the engine, run `npm run sync-engine` and commit `api/_vendor`.

## Deploy

The Vercel project uses Root Directory `web`. The framework (Next.js) is detected automatically, and `api/engine.py` is deployed as a Python function (see `vercel.json`). Every push to `main` deploys to production.
