## Prompt Forger 1.2.0

Desktop app that forges structured AI prompts: standard prompts, Ralph loops, graph loops and agent profiles.

### Downloads
| File | For |
|---|---|
| `PromptForger-Setup-1.2.0.exe` | Windows installer (per-user, no admin rights needed; upgrades 1.0 and 1.1 in place) |
| `PromptForger-1.2.0-windows-portable.zip` | Windows, no install: unzip and run `PromptForger.exe` |
| `PromptForger-1.2.0-mac-arm64.zip` | Mac with Apple Silicon (M1–M4): unzip, drag "Prompt Forger" to Applications |
| `PromptForger-1.2.0-mac-x64.zip` | Intel Mac: unzip, drag "Prompt Forger" to Applications |
| `SHA256SUMS.txt` | Checksums |

Java and Python are bundled; nothing else to install.

### New in 1.2
- **Score breakdown**: every prompt gets a 0–100 score plus five bars: Clarity, Specificity, Structure, Checkability and Fit.
- **✦ Enhance**: fixes weak prompts offline (role, constraints, measurable success criteria, JSON schema, token budget). With an AI provider set, it also asks for an AI rewrite and keeps whichever scores higher. Shows before → after and every change; Apply or Discard.
- **Reply rating**: after **Test it**, the model's reply is checked against your success criteria and constraints, with an accuracy %, a verdict and a ✓/✕ line for each check.

### First launch
These builds are not code-signed yet.
- **Windows**: if you see "Windows protected your PC", click **More info → Run anyway**.
- **macOS**: open the app once, then **System Settings → Privacy & Security → Open Anyway**. See `READ ME FIRST.txt` inside the zip.

> The Mac apps are shipped as zips here because GitHub doesn't accept files over 100 MB in a repository.
> Download a file from this folder on GitHub with the **Download raw file** button.
