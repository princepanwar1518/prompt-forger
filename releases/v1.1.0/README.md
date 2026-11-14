## Prompt Forger 1.1.0

Desktop app that forges structured AI prompts: standard prompts, Ralph loops, graph loops and agent profiles.

### Downloads
| File | For |
|---|---|
| `PromptForger-Setup-1.1.0.exe` | Windows installer (per-user, no admin rights needed; upgrades 1.0 in place) |
| `PromptForger-1.1.0-windows-portable.zip` | Windows, no install: unzip and run `PromptForger.exe` |
| `PromptForger-1.1.0-mac-arm64.zip` | Mac with Apple Silicon (M1–M4): unzip, drag "Prompt Forger" to Applications |
| `PromptForger-1.1.0-mac-x64.zip` | Intel Mac: unzip, drag "Prompt Forger" to Applications |
| `SHA256SUMS.txt` | Checksums |

Java and Python are bundled; nothing else to install.

### New in 1.1
- **Describe it**: type what you need in plain English, Hindi or Hinglish and the form fills itself. Offline rules, Claude, OpenAI or Ollama. Asks up to 3 questions when a request is vague.
- **Prompt score** (0–100) with clickable suggestions, **Plain English** explanation, **Test it** button.
- New fields: constraints, success criteria, examples, output schema, variables (`{{name}}`), agent tools.
- API keys stored in Windows Credential Manager / macOS Keychain.
- New UI with bundled fonts, light and dark themes; preset import/export; log files.

### First launch
These builds are not code-signed yet.
- **Windows**: if you see "Windows protected your PC", click **More info → Run anyway**.
- **macOS**: open the app once, then **System Settings → Privacy & Security → Open Anyway**. See `READ ME FIRST.txt` inside the zip.

> The Mac apps are shipped as zips here because GitHub doesn't accept files over 100 MB in a repository.
> Download a file from this folder on GitHub with the **Download raw file** button.
