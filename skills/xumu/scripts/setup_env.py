#!/usr/bin/env python3
"""One-shot environment setup for the xumu (序幕) plugin.

Checks and, where possible, installs everything the three skills need to actually cut a film:
  - FFmpeg / ffprobe          (apt-get, dnf, apk or brew)
  - Python deps for Video Use (requests librosa matplotlib pillow numpy + faster-whisper)
  - Node.js >= 18 + npm       (for Remotion / Shotcraft animation shots)
  - Optional: warm the npm cache with Remotion (--remotion) so project installs are fast
  - Optional: pre-download the local whisper model (--whisper-model small|medium|large-v3)
  - Local transcription runtime probe: loads a whisper model in a separate process; ctranslate2 4.7/4.8
    crash on load on some Windows PCs, so a crash is repaired by pinning the verified ctranslate2 4.6.0

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
from pathlib import Path
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


def pip_install(packages: list[str]) -> bool:
    """pip into this interpreter; environments created by uv have no pip, so fall back to `uv pip`."""
    if importlib.util.find_spec("pip") is not None:
        return run([sys.executable, "-m", "pip", "install", "-q", *pip_flags(), *packages], quiet=False)
    if shutil.which("uv"):
        return run(["uv", "pip", "install", "-q", "--python", sys.executable, *packages], quiet=False)
    return False


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
    ok = pip_install(missing)
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


CT2_PIN = ["ctranslate2==4.6.0", "setuptools<81"]   # 4.6.0 still imports pkg_resources


def cached_whisper_model() -> str | None:
    """Smallest faster-whisper model already in the Hugging Face cache, so --check can test offline."""
    hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    if os.environ.get("HF_HUB_CACHE"):
        hub = Path(os.environ["HF_HUB_CACHE"])
    for size in ("tiny", "base", "small", "medium", "large-v3"):
        if (hub / f"models--Systran--faster-whisper-{size}").is_dir():
            return size
    return None


def whisper_probe(model: str, offline: bool) -> tuple[str, str]:
    """Load the model in a child process: a native crash kills the child, not this script."""
    code = ("from faster_whisper import WhisperModel; "
            f"WhisperModel({model!r}, device='cpu', compute_type='int8', local_files_only={offline}); "
            "print('LOAD_OK')")
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return "error", "timed out (model download?)"
    if "LOAD_OK" in r.stdout:
        return "ok", ""
    if "Traceback" in r.stderr:
        return "error", r.stderr.strip().splitlines()[-1][:160]
    return "crash", f"process exited with code {r.returncode} and no Python error"


def check_whisper_runtime(model_arg: str | None, check: bool) -> None:
    if importlib.util.find_spec("faster_whisper") is None:
        return
    name = "Local transcription runtime"
    cached = cached_whisper_model()
    model = model_arg or cached
    if not model:
        if check:
            results.append((name, True, "not tested: no model cached (run without --check to test with 'tiny')"))
            return
        model = "tiny"
    offline = check or (model == cached and not model_arg)
    status, detail = whisper_probe(model, offline)
    if status == "crash" and not check:
        pinned = pip_install(CT2_PIN)   # judge by the re-probe: installers can report errors after installing
        status, detail = whisper_probe(model, offline)
        if status == "crash" and not pinned:
            detail = "pinning ctranslate2 4.6.0 failed"
        if status == "ok":
            results.append((name, True, f"model '{model}' loads after pinning ctranslate2 4.6.0"))
            return
    if status == "ok":
        results.append((name, True, f"model '{model}' loads"))
    elif status == "crash":
        results.append((name, False, f"crashes on model load ({detail}); known ctranslate2 4.7/4.8 issue on some "
                                     f"Windows PCs - run without --check to pin ctranslate2 4.6.0, or use a cloud engine"))
    else:
        results.append((name, False, detail))


def report_optional() -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    local_broken = any(n.startswith("Local transcription") and not ok for n, ok, _ in results)
    if key:
        results.append(("Transcription engine", True, "ElevenLabs Scribe (key found)"))
    elif local_broken:
        results.append(("Transcription engine", False,
                        "none usable yet: repair the local runtime (run without --check) or set ELEVENLABS_API_KEY"))
    else:
        results.append(("Transcription engine", True,
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
    check_whisper_runtime(a.whisper_model, a.check)
    report_optional()

    width = max(len(n) for n, _, _ in results)
    for name, ok, note in results:
        print(f"[{'OK' if ok else '!!'}] {name.ljust(width)}  {note}")
    required_fail = [n for n, ok, _ in results if not ok and not n.startswith(("Node", "Remotion", "Local transcription", "Transcription engine"))]
    return 1 if required_fail else 0


if __name__ == "__main__":
    sys.exit(main())
