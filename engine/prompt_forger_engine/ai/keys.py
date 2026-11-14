"""API keys in the OS keychain: Windows Credential Manager, macOS Keychain; a 0600 file elsewhere.

Keys never go into the app's JSON settings or logs. Only the engine reads them, at request time.
Set PROMPT_FORGER_KEYSTORE=file:<path> to force the file store (tests, Linux).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROVIDERS = ("anthropic", "openai")
_SERVICE = "PromptForger"
_ACCOUNT = "promptforger"
# API keys are URL-safe tokens; validating also rules out shell/command injection in the macOS path.
_KEY_RE = re.compile(r"^[A-Za-z0-9_\-.]{16,400}$")


class KeyStoreError(Exception):
    pass


def validate_key(provider: str, key: str) -> str:
    if provider not in PROVIDERS:
        raise KeyStoreError(f"Unknown provider: {provider!r}")
    key = key.strip()
    if not _KEY_RE.match(key):
        raise KeyStoreError("That doesn't look like an API key (letters, digits, - _ . only, 16+ characters).")
    return key


def _target(provider: str) -> str:
    return f"{_SERVICE}:{provider}"


# ---------------------------------------------------------------- Windows Credential Manager

def _win():
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    adv.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
    adv.CredWriteW.restype = wintypes.BOOL
    adv.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    adv.CredReadW.restype = wintypes.BOOL
    adv.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    adv.CredDeleteW.restype = wintypes.BOOL
    adv.CredFree.argtypes = [ctypes.c_void_p]
    return ctypes, CREDENTIAL, adv


_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


def _win_set(provider: str, key: str) -> None:
    ctypes, CREDENTIAL, adv = _win()
    blob = key.encode("utf-8")
    buf = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    cred = CREDENTIAL()
    cred.Type = _CRED_TYPE_GENERIC
    cred.TargetName = _target(provider)
    cred.UserName = _ACCOUNT
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = _CRED_PERSIST_LOCAL_MACHINE
    if not adv.CredWriteW(ctypes.byref(cred), 0):
        raise KeyStoreError(f"Windows Credential Manager refused the key (error {ctypes.get_last_error()}).")


def _win_get(provider: str) -> str | None:
    ctypes, CREDENTIAL, adv = _win()
    ptr = ctypes.POINTER(CREDENTIAL)()
    if not adv.CredReadW(_target(provider), _CRED_TYPE_GENERIC, 0, ctypes.byref(ptr)):
        if ctypes.get_last_error() == _ERROR_NOT_FOUND:
            return None
        raise KeyStoreError(f"Could not read from Windows Credential Manager (error {ctypes.get_last_error()}).")
    try:
        c = ptr.contents
        return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode("utf-8")
    finally:
        adv.CredFree(ptr)


def _win_delete(provider: str) -> None:
    ctypes, _, adv = _win()
    if not adv.CredDeleteW(_target(provider), _CRED_TYPE_GENERIC, 0) and ctypes.get_last_error() != _ERROR_NOT_FOUND:
        raise KeyStoreError(f"Could not delete from Windows Credential Manager (error {ctypes.get_last_error()}).")


# ---------------------------------------------------------------- macOS Keychain

def _mac_set(provider: str, key: str) -> None:
    # `security -i` reads the command from stdin, so the key never appears in the process list.
    cmd = f"add-generic-password -U -a {_ACCOUNT} -s {_target(provider)} -w {key}\n"
    r = subprocess.run(["security", "-i"], input=cmd, text=True, capture_output=True, timeout=15)
    if r.returncode != 0 or "error" in (r.stderr or "").lower():
        raise KeyStoreError("macOS Keychain refused the key.")


def _mac_get(provider: str) -> str | None:
    r = subprocess.run(["security", "find-generic-password", "-a", _ACCOUNT, "-s", _target(provider), "-w"],
                       capture_output=True, text=True, timeout=15)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _mac_delete(provider: str) -> None:
    subprocess.run(["security", "delete-generic-password", "-a", _ACCOUNT, "-s", _target(provider)],
                   capture_output=True, timeout=15)


# ---------------------------------------------------------------- file fallback

def _file_path() -> Path:
    env = os.environ.get("PROMPT_FORGER_KEYSTORE", "")
    if env.startswith("file:"):
        return Path(env[5:])
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "prompt-forger" / "keys.json"


def _file_load() -> dict[str, str]:
    try:
        return json.loads(_file_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _file_save(data: dict[str, str]) -> None:
    path = _file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


# ---------------------------------------------------------------- public API

def _backend() -> str:
    if os.environ.get("PROMPT_FORGER_KEYSTORE", "").startswith("file:"):
        return "file"
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "file"


def backend_label() -> str:
    return {"windows": "Windows Credential Manager", "macos": "macOS Keychain", "file": "a private file"}[_backend()]


def set_key(provider: str, key: str) -> None:
    key = validate_key(provider, key)
    b = _backend()
    if b == "windows":
        _win_set(provider, key)
    elif b == "macos":
        _mac_set(provider, key)
    else:
        data = _file_load()
        data[provider] = key
        _file_save(data)


def get_key(provider: str) -> str | None:
    if provider not in PROVIDERS:
        return None
    env = os.environ.get(f"PROMPT_FORGER_{provider.upper()}_KEY")
    if env:
        return env.strip()
    b = _backend()
    if b == "windows":
        return _win_get(provider)
    if b == "macos":
        return _mac_get(provider)
    return _file_load().get(provider)


def delete_key(provider: str) -> None:
    if provider not in PROVIDERS:
        raise KeyStoreError(f"Unknown provider: {provider!r}")
    b = _backend()
    if b == "windows":
        _win_delete(provider)
    elif b == "macos":
        _mac_delete(provider)
    else:
        data = _file_load()
        data.pop(provider, None)
        _file_save(data)


def status() -> dict[str, object]:
    out: dict[str, object] = {"store": backend_label()}
    for p in PROVIDERS:
        try:
            out[p] = get_key(p) is not None
        except KeyStoreError:
            out[p] = False
    return out
