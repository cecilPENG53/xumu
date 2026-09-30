#!/usr/bin/env python3
"""One-shot environment setup for the VV narrative-video plugin.

Checks and, where possible, installs everything the three skills need to actually cut a film:
  - FFmpeg / ffprobe          (apt-get, dnf, apk or brew)
  - Python deps for Video Use (requests librosa matplotlib pillow numpy + faster-whisper)
  - Node.js >= 18 + npm       (for Remotion / Shotcraft animation shots)
  - Optional: warm the npm cache with Remotion (--remotion) so project installs are fast
  - Optional: pre-download the local whisper model (--whisper-model small|medium|large-v3)

Idempotent: anything already present is skipped. Safe to run at the start of every
production session. Never writes into the plugin/skill directories.

Usage:
    python3 setup_env.py              # check + install missing
    python3 setup_env.py --check      # report only, change nothing
    python3 setup_env.py --remotion --whisper-model small
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys

PY_DEPS = {  # import name -> pip name
    "requests": "requests",
    "librosa": "librosa",
    "matplotlib": "matplotlib",
    "PIL": "pillow",
    "numpy": "numpy",
    "faster_whisper": "faster-whisper",
}

results: list[tuple[str, bool, str]] = []


def run(cmd: list[str], quiet: bool = True) -> bool:
    try:
        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL if quiet else None,
                       stderr=subprocess.DEVNULL if quiet else None)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def sudo() -> list[str]:
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo"):
        return ["sudo", "-n"]
    return []


def system_install(apt: str, brew: str, dnf: str | None = None, apk: str | None = None) -> bool:
    if shutil.which("apt-get"):
        return (run(sudo() + ["apt-get", "install", "-y", "-qq", apt])
                or (run(sudo() + ["apt-get", "update", "-qq"])
                    and run(sudo() + ["apt-get", "install", "-y", "-qq", apt])))
    if shutil.which("dnf"):
        return run(sudo() + ["dnf", "install", "-y", "-q", dnf or apt])
    if shutil.which("apk"):
        return run(sudo() + ["apk", "add", "--no-cache", apk or apt])
    if shutil.which("brew"):
        return run(["brew", "install", brew])
    if os.name == "nt" and shutil.which("winget"):
        return run(["winget", "install", "-e", "--silent", "--id", brew])
    return False


def ensure_ffmpeg(check: bool) -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        results.append(("FFmpeg / ffprobe", True, "present"))
        return
    if check:
        results.append(("FFmpeg / ffprobe", False, "missing"))
        return
    ok = system_install("ffmpeg", "ffmpeg" if os.name != "nt" else "Gyan.FFmpeg")
    ok = ok and bool(shutil.which("ffmpeg"))
    if not ok:  # last resort: static binary via pip, exposed on PATH through a shim dir
        if run([sys.executable, "-m", "pip", "install", "-q", *pip_flags(), "static-ffmpeg"]):
            try:
                import static_ffmpeg  # type: ignore
                static_ffmpeg.add_paths()
                ok = bool(shutil.which("ffmpeg"))
                if ok:
                    results.append(("FFmpeg / ffprobe", True,
                                    f"installed static build: {os.path.dirname(shutil.which('ffmpeg'))} "
                                    "(add to PATH, or run `python -m static_ffmpeg -version` once per shell)"))
                    return
            except Exception:
                pass
    results.append(("FFmpeg / ffprobe", ok, "installed" if ok else
                    "could not install automatically - install from https://ffmpeg.org/download.html"))


def pip_flags() -> list[str]:
    flags = []
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not in_venv:
        # PEP 668 distros refuse plain pip installs; --break-system-packages is the documented escape.
        probe = subprocess.run([sys.executable, "-m", "pip", "install", "--help"],
                               capture_output=True, text=True)
        if "--break-system-packages" in probe.stdout:
            flags.append("--break-system-packages")
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            flags.append("--user")
    return flags


def ensure_python(check: bool) -> None:
    if sys.version_info < (3, 10):
        results.append(("Python >= 3.10", False, f"found {platform.python_version()}"))
        return
    results.append(("Python >= 3.10", True, platform.python_version()))
    missing = [pip for mod, pip in PY_DEPS.items() if importlib.util.find_spec(mod) is None]
    if not missing:
        results.append(("Python deps (Video Use + local transcription)", True, "present"))
        return
    if check:
        results.append(("Python deps (Video Use + local transcription)", False, "missing: " + ", ".join(missing)))
        return
    ok = run([sys.executable, "-m", "pip", "install", "-q", *pip_flags(), *missing], quiet=False)
    results.append(("Python deps (Video Use + local transcription)", ok,
                    ("installed: " if ok else "failed: ") + ", ".join(missing)))


def node_major() -> int:
    node = shutil.which("node")
    if not node:
        return 0
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        return int(out.lstrip("v").split(".")[0])
    except Exception:
        return 0


def ensure_node(check: bool) -> None:
    if node_major() >= 18 and shutil.which("npm") and shutil.which("npx"):
        results.append(("Node.js >= 18 + npm", True, f"v{node_major()}"))
        return
    if not check:
        system_install("nodejs", "node" if os.name != "nt" else "OpenJS.NodeJS.LTS")
        if shutil.which("apt-get") and not shutil.which("npm"):
            system_install("npm", "node")
    ok = node_major() >= 18 and bool(shutil.which("npm"))
    results.append(("Node.js >= 18 + npm", ok,
                    f"v{node_major()}" if ok else
                    "missing/too old - install Node 20 LTS from https://nodejs.org (only needed for animation shots)"))


def warm_remotion(check: bool) -> None:
    if check or node_major() < 18:
        return
    ok = run(["npm", "cache", "add", "remotion", "@remotion/cli", "@remotion/bundler",
              "@remotion/renderer", "react", "react-dom"])
    results.append(("Remotion npm cache", ok, "warmed" if ok else "skipped (network?)"))
    # Chrome Headless Shell is fetched by Remotion on first render; Linux needs these libs.
    if shutil.which("apt-get"):
        libs = ("libnss3 libdbus-1-3 libatk1.0-0 libgbm1 libasound2 libxrandr2 libxkbcommon0 "
                "libxfixes3 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2")
        run(sudo() + ["apt-get", "install", "-y", "-qq", *libs.split()])


def warm_whisper(model: str | None, check: bool) -> None:
    if not model or check or importlib.util.find_spec("faster_whisper") is None:
        return
    try:
        from faster_whisper import WhisperModel
        WhisperModel(model, device="cpu", compute_type="int8")
        results.append((f"Whisper model '{model}'", True, "downloaded"))
    except Exception as e:  # noqa: BLE001
        results.append((f"Whisper model '{model}'", False, str(e)[:120]))


def report_optional() -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    results.append(("Transcription engine", True,
                    "ElevenLabs Scribe (key found)" if key else
                    "local faster-whisper (free; set ELEVENLABS_API_KEY for Scribe diarization)"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only, install nothing")
    ap.add_argument("--remotion", action="store_true", help="pre-fetch Remotion packages + Linux render libs")
    ap.add_argument("--whisper-model", default=None, help="pre-download a faster-whisper model (e.g. small)")
    a = ap.parse_args()

    ensure_ffmpeg(a.check)
    ensure_python(a.check)
    ensure_node(a.check)
    if a.remotion:
        warm_remotion(a.check)
    warm_whisper(a.whisper_model, a.check)
    report_optional()

    width = max(len(n) for n, _, _ in results)
    for name, ok, note in results:
        print(f"[{'OK' if ok else '!!'}] {name.ljust(width)}  {note}")
    required_fail = [n for n, ok, _ in results if not ok and not n.startswith(("Node", "Remotion", "Whisper"))]
    return 1 if required_fail else 0


if __name__ == "__main__":
    sys.exit(main())
