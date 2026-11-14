# Prompt Forger

A Windows desktop app that forges structured prompts for AI models.

- **UI:** Java 21 + JavaFX
- **Engine:** Python 3.11+, no third-party dependencies

You fill in **Role, Task, Steps, Context, Output format, Target model, Verbosity, Token budget** (plus Max iterations for loops). The output updates as you type.

| Output format | What you get |
|---|---|
| **Standard prompt** | `prompt.md`: one prompt for any chat or API call |
| **Ralph loop** | `PROMPT.md`, `fix_plan.md`, `ralph.ps1`, `ralph.sh`: an agent loop that runs until it prints `<promise>COMPLETE</promise>` |
| **Graph loop** | `graph-prompt.md` (the model walks the graph itself) and `graph.json` (nodes, edges and state for an orchestrator such as LangGraph) |
| **Agent profile** | `.claude/agents/<name>.md` (Claude Code subagent) for Claude models, or `agents/<name>.md` for other models |

The target model changes three things:
- **Prompt style:** XML tags for Claude, Markdown for GPT, Gemini and open-source models.
- **Ralph runner CLI:** Claude Code, Codex CLI, Gemini CLI, or Aider.
- **Subagent `model:` field** in agent profiles.

## Architecture

```
┌──────────────────────────── JavaFX UI (Java 21) ─────────────────────────────┐
│  FormPane ──change──▶ debounce 180 ms ──▶ EngineClient ──▶ OutputPane (tabs) │
│  PresetStore / SettingsStore (%APPDATA%\PromptForger\*.json, atomic writes)  │
│  OutputWriter (Save / Save all, path-traversal safe)                         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ JSON lines over stdin/stdout (one long-lived process)
┌───────────────────────────────▼──────────────────────────────────────────────┐
│  Python engine: schema (validation) → formats/{standard,ralph,graph,agent}   │
│  Pure functions, no I/O except the stdio server. Frozen with PyInstaller.    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Why it is built this way**
- **The engine owns all validation and option lists** (`meta`). The UI never re-implements the rules, so the two can't drift apart.
- **The engine is one long-lived process** instead of one process per keystroke. A frozen Python exe takes about 0.5–1 s to start on Windows, which would make the live preview stutter. The client restarts the engine if it crashes (at most 3 restarts per minute).
- **The protocol output is ASCII-only JSON** (`\u` escapes). Windows console code pages can't corrupt it.
- **The Java side has zero third-party dependencies** (it ships its own small JSON codec). Releases build with plain `javac` and `jpackage`, so nothing has to be fetched from Maven.

### Protocol

```jsonc
→ {"id": 1, "method": "forge", "params": {"role": "...", "task": "...", "format": "ralph", ...}}
← {"id": 1, "result": {"ok": true, "files": [{"path", "language", "description", "content"}], "warnings": []}}
← {"id": 1, "result": {"ok": false, "errors": {"task": "Task is required."}}}
```

The methods are `forge`, `meta`, `ping` and `shutdown`. Errors come back as `{"id", "error": {"code", "message"}}`.

## Folder structure

```
prompt-forger/
├─ engine/                         Python engine
│  ├─ prompt_forger_engine/
│  │  ├─ schema.py                 form contract + validation
│  │  ├─ models.py                 per-model style + loop CLI
│  │  ├─ sections.py, text.py      rendering helpers
│  │  ├─ formats/                  standard.py, ralph.py, graph.py, agent.py
│  │  ├─ forge.py                  forge() + meta()
│  │  └─ server.py                 JSON-lines stdio server
│  ├─ engine_main.py               PyInstaller entry
│  └─ tests/test_forge.py          29 tests
├─ app/                            JavaFX UI (module com.panwarstudio.promptforger)
│  ├─ src/main/java/.../
│  │  ├─ App.java                  startup, engine connect, window
│  │  ├─ engine/                   EngineClient, EngineLocator, result records
│  │  ├─ json/Json.java            strict JSON codec
│  │  ├─ model/                    FormState, Preset
│  │  ├─ storage/                  presets, settings/draft, safe file writer
│  │  └─ ui/                       MainView, FormPane, OutputPane, Toast, theme
│  ├─ src/main/resources/.../app.css   light + dark themes
│  ├─ src/test/java/...            JUnit 5 tests (JSON, file safety, presets, engine round trip)
│  └─ pom.xml                      for IDE use / mvn javafx:run
├─ packaging/
│  ├─ build-windows.ps1            builds the portable zip + installer
│  ├─ make_icon.py, icon.ico, icon.png
└─ .github/workflows/build-windows.yml   CI build on windows-latest
```

## Build the Windows app

**Easiest route: GitHub Actions.** Push the repo, then go to **Actions → Build Windows app → Run workflow**. Download the `PromptForger-windows` artifact. It contains the portable zip and the `.exe` installer.

**On your own PC:**

1. Install **BellSoft Liberica Full JDK 21**. "Full" includes JavaFX. Make sure `java -version` shows it.
2. Install **Python 3.11+** from python.org.
3. Optional, for the installer: install **WiX Toolset 3**, e.g. with `choco install wixtoolset`.
4. From the repo root:

   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
   ```

5. The output goes to `build\dist\`:
   - `PromptForger\PromptForger.exe` — portable
   - `PromptForger-1.0.0-portable.zip`
   - `PromptForger-1.0.0.exe` — installer, only if WiX is installed

The build script runs the engine tests, freezes the engine, smoke-tests the frozen exe, and compiles with `-Werror`. It then packages a trimmed Java runtime with the engine bundled.

## Cross-build Windows + macOS from Linux (how the v1.0.0 release was made)

No Windows or Mac machine is needed:

- **Java runtime:** `jlink` links a trimmed runtime from the *target* OS's jmods (BellSoft Liberica Full JDK 21 for Windows / macOS).
- **Python:** each build bundles a standalone CPython 3.12 (python-build-standalone). The app runs `engine/python/... engine_main.py` with `-E -s`, so the user's own Python install doesn't matter.
- **Windows:** NSIS (`makensis`) builds a tiny `PromptForger.exe` launcher (`packaging/nsis/launcher.nsi`) and a per-user installer with no admin rights needed (`packaging/nsis/installer.nsi`).
- **macOS:** `packaging/build_mac.py` assembles `Prompt Forger.app` and a `.dmg` for arm64 and x64. The app isn't signed with an Apple Developer ID, so the first launch needs "Open Anyway" (see `READ ME FIRST.txt` inside the DMG).

**Installed locations**
- Windows: `%LOCALAPPDATA%\Programs\Prompt Forger`. Uninstall from Settings → Apps; presets in `%APPDATA%\PromptForger` are kept.
- macOS: drag the app to Applications. Presets are stored in `~/.config/prompt-forger`.

## Run in development

```powershell
cd app
mvn javafx:run            # finds ../engine/engine_main.py and runs it with your local Python
mvn verify                # Java unit + integration tests
cd ..\engine
py -3 -m pytest -q        # engine tests
```

You can point the app at a different engine with `-Dpromptforger.engine=C:\path\to\engine.exe` (or a `.py` file), or with the `PROMPT_FORGER_ENGINE` environment variable.

## Keyboard shortcuts

| Keys | Action |
|---|---|
| Ctrl+Shift+C | Copy current file |
| Ctrl+S | Save current file |
| Ctrl+Shift+S | Save all files into a folder |

## Security notes

- **Save all** rejects absolute paths and `..` segments, and checks every path before writing anything. It asks before overwriting existing files.
- The engine only reads stdin and writes stdout. It has no network access, no file I/O and no `eval`.
- Generated Ralph runners use the agents' skip-permission flags (`--dangerously-skip-permissions`, `--full-auto`, `--yolo`). The scripts warn about this. **Run loops in a VM, container or Windows Sandbox**, never on your main machine.

## Add a new output format

1. Add `engine/prompt_forger_engine/formats/<name>.py` exposing `forge_<name>(inp, profile) -> list[ForgeFile]`.
2. Register it in `forge.py` (`_GENERATORS` and `meta()["formats"]`), and add the name to `OutputFormat` in `schema.py`.
3. Add tests. The UI picks up the new format card automatically from `meta`.
