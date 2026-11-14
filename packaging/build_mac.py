"""Builds macOS .app bundles and .dmg disk images for Apple Silicon (arm64) and Intel (x64).

Runs on Linux or macOS. Cross-links a Java runtime from the macOS JDK's jmods (jlink supports
linking for another platform when given that platform's jmods) and bundles a standalone Python.

Usage:
  python3 build_mac.py --jar build/mods/prompt-forger.jar --out build/dist \
      --jdk arm64=/path/to/macos-aarch64-full.jdk --jdk x64=/path/to/macos-amd64-full.jdk \
      --python arm64=/path/to/py-aarch64/python --python x64=/path/to/py-x86_64/python

Needs: jlink (JDK 21, any OS), Pillow (icon), genisoimage (Linux) or hdiutil (macOS) for the .dmg.
"""

from __future__ import annotations

import argparse
import plistlib
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from PIL import Image

APP_NAME = "Prompt Forger"
BUNDLE_ID = "com.panwarstudio.promptforger"
VERSION = "1.2.0"
MODULE = "com.panwarstudio.promptforger"
MAIN = "com.panwarstudio.promptforger.App"
ROOT = Path(__file__).resolve().parents[1]

LAUNCHER = f"""#!/bin/bash
# Starts the bundled Java runtime. The prompt engine (bundled Python) is started by the app itself.
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
exec "$CONTENTS/runtime/bin/java" \\
  -Dfile.encoding=UTF-8 \\
  -Dpromptforger.home="$CONTENTS" \\
  -Xdock:name="{APP_NAME}" \\
  -Xdock:icon="$CONTENTS/Resources/PromptForger.icns" \\
  -m {MODULE}/{MAIN} "$@"
"""

DMG_README = """Prompt Forger for macOS
=======================

Install: drag "Prompt Forger" onto the Applications folder.

Which file? Apple Silicon (M1/M2/M3/M4): the "arm64" .dmg. Older Intel Macs: the "x64" .dmg.

First launch: this build is not signed with an Apple Developer ID, so macOS blocks it once.
  - macOS 15 (Sequoia) or newer: try to open the app, click Done, then go to
    System Settings > Privacy & Security, scroll down and click "Open Anyway".
  - macOS 14 or older: right-click "Prompt Forger" in Applications, choose Open, then Open again.
  - If macOS says the app "is damaged", run this once in Terminal, then open it normally:
       xattr -dr com.apple.quarantine "/Applications/Prompt Forger.app"

Your presets are stored in ~/.config/prompt-forger.
"""

PY_SKIP_LIB = {"test", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3", "pydoc_data", "site-packages", "venv"}


def python_ignore(src_root: Path):
    def ignore(dirpath: str, names: list[str]) -> set[str]:
        d = Path(dirpath)
        skip = {"__pycache__"}
        if d == src_root:
            skip |= {"include", "share"}
        if d == src_root / "lib":
            skip |= {n for n in names if n.startswith(("tcl", "tk", "libtcl", "libtk", "itcl", "thread"))}
        if d.name.startswith("python3.") and d.parent == src_root / "lib":
            skip |= PY_SKIP_LIB
        if d.name == "lib-dynload":
            skip |= {n for n in names if n.startswith("_tkinter")}
        return skip & set(names)

    return ignore


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_app(arch: str, jdk: Path, python: Path, jar: Path, out: Path, icns: Path) -> Path:
    app = out / arch / f"{APP_NAME}.app"
    if app.exists():
        sys.exit(f"{app} already exists; use a fresh --out folder")
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir()

    subprocess.run(
        ["jlink", "--module-path", f"{jdk / 'jmods'}{':' if sys.platform != 'win32' else ';'}{jar.parent}",
         "--add-modules", MODULE, "--output", str(contents / "runtime"),
         # Java-only stripping: native strip would need Mach-O tools and must not touch Apple code signatures.
         "--strip-java-debug-attributes", "--no-header-files", "--no-man-pages", "--compress", "zip-6"],
        check=True)

    engine = contents / "engine"
    shutil.copytree(python, engine / "python", symlinks=True, ignore=python_ignore(python))
    shutil.copytree(ROOT / "engine/prompt_forger_engine", engine / "prompt_forger_engine",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "engine/engine_main.py", engine / "engine_main.py")

    launcher = contents / "MacOS" / "PromptForger"
    launcher.write_text(LAUNCHER, encoding="utf-8", newline="\n")
    make_executable(launcher)
    shutil.copy2(icns, contents / "Resources" / "PromptForger.icns")

    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "CFBundleExecutable": "PromptForger",
        "CFBundleIconFile": "PromptForger.icns",
        "CFBundlePackageType": "APPL",
        "CFBundleInfoDictionaryVersion": "6.0",
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.developer-tools",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Copyright (c) 2026 Prince Panwar",
    }
    with open(contents / "Info.plist", "wb") as fh:
        plistlib.dump(info, fh)
    (contents / "PkgInfo").write_text("APPL????", encoding="ascii")
    return app


def build_dmg(app: Path, dmg: Path) -> None:
    stage = app.parent / "dmg-root"
    stage.mkdir()
    shutil.move(str(app), stage / app.name)
    (stage / "Applications").symlink_to("/Applications")
    (stage / "READ ME FIRST.txt").write_text(DMG_README, encoding="utf-8")
    if shutil.which("hdiutil"):
        cmd = ["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(stage), "-ov", "-format", "UDZO", str(dmg)]
    else:
        # ISO 9660 + Rock Ridge keeps permissions and symlinks; macOS mounts it like any .dmg.
        cmd = ["genisoimage", "-quiet", "-V", APP_NAME, "-D", "-R", "-no-pad", "-o", str(dmg), str(stage)]
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jar", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--jdk", action="append", required=True, help="arch=path to macOS JDK home with jmods")
    p.add_argument("--python", action="append", required=True, help="arch=path to standalone python folder")
    a = p.parse_args()
    jdks = dict(x.split("=", 1) for x in a.jdk)
    pythons = dict(x.split("=", 1) for x in a.python)

    a.out.mkdir(parents=True, exist_ok=True)
    icns = a.out / "PromptForger.icns"
    Image.open(ROOT / "packaging/icon.png").save(icns)

    for arch, jdk in jdks.items():
        app = build_app(arch, Path(jdk), Path(pythons[arch]), a.jar.resolve(), a.out, icns)
        dmg = a.out / f"PromptForger-{VERSION}-mac-{arch}.dmg"
        build_dmg(app, dmg)
        print(f"built {dmg}")


if __name__ == "__main__":
    main()
