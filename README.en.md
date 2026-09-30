# 序幕 (Xumu) · Talking-Head Video Director Skill

![GitHub stars](https://img.shields.io/github/stars/cecilPENG53/vv-narrative-video?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Version](https://img.shields.io/badge/version-0.4.2-orange?style=flat-square)
![Skill](https://img.shields.io/badge/Skill-Agent-111111?style=flat-square)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Supported-6B5B95?style=flat-square)
![Codex](https://img.shields.io/badge/Codex-Supported-222222?style=flat-square)

> 🌏 **中文版：[README.md](./README.md)** · 📘 **Usage guide (Chinese): [docs/USAGE.md](./docs/USAGE.md)**

An agent skill pack for Claude Code / Claude Cowork / Codex that turns a **talking-head video, a voice recording, or a script** into a finished narrated video. The agent first decides *platform × content × style × length*, then edits, picks shots, builds custom motion graphics (MG), adds captions, composites, and delivers **the final video plus an editable project**.

It is a director workflow with confirmation points, not a one-click black box:

- **Plan before cutting** — a production profile drives narrative structure, edit strategy and shot intensity.
- **Not everything becomes a card** — keeping the speaker on screen is a valid choice; only segments that need motion get shots.
- **Shots with provenance** — compare candidates from 157 cinematic shot-recipe cards; write custom MG only when there is a real gap.
- **Verifiable** — one master timeline, per-shot test renders, a plan checker, and review of real renders.

Built by **VVAI**, integrating and adapting [Video Use](https://github.com/browser-use/video-use) (MIT) and [Video Shotcraft](https://github.com/Vincentwei1021/video-shotcraft) (Apache-2.0).

## Quick start

**Claude Code (plugin — installs all three skills):**

```text
/plugin marketplace add cecilPENG53/vv-narrative-video
/plugin install vv-narrative-video@vvai
```

**Manual (Claude Code / Codex):**

```bash
git clone https://github.com/cecilPENG53/vv-narrative-video.git
cp -r vv-narrative-video/skills/* ~/.claude/skills/   # Codex: ~/.codex/skills/
```

> ⚠️ All three skill folders must live in the **same** `skills/` directory — the director skill finds its siblings by relative location.

Then ask:

```text
Use the 序幕 (vv-narrative-video) skill to turn ./talk.mp4 into a 3-minute 16:9 explainer for YouTube. Show me the production plan first.
```

## What's inside

| Skill | Role |
|---|---|
| `vv-narrative-video` | **Director entry point**: production profile, edit strategy, shot selection, master timeline, QA, delivery |
| `video-use` | Editing helpers: transcription, cutting, grading, subtitle burn-in (from browser-use/video-use) |
| `video-shotcraft` | 157 shot-recipe cards, Remotion components & template, motion workbench (from Vincentwei1021/video-shotcraft) |

In Claude Code plugin mode the entry command is `/vv-narrative-video:vv-narrative-video` (plugin name before the colon, skill name after).

## Workflow

0. **Production profile** — audience, platform, content type, style, target length
1. **Edit / narration strategy** — ✅ user confirms before any cut
2. **Lock narration and master timeline**
3. **Shot selection + pacing** — ✅ user confirms the visual plan
4. **Production** — each shot test-rendered before the final render
5. **Composite, QA, deliver** — final video + editable `edit/` project

## Requirements

Python 3.10+, FFmpeg/ffprobe, faster-whisper (auto-installed by `skills/vv-narrative-video/scripts/setup_env.py`), Node.js 18+ for Remotion shots. `ELEVENLABS_API_KEY` is optional (cloud transcription with speaker diarization); without it, local faster-whisper is used.

## Boundaries

- Publishing, voice cloning, uploading media to external services and paid generation each require explicit user approval.
- **No third-party music or SFX ship with this repo** — Mixkit audio from the upstream Shotcraft project is excluded because its license forbids redistribution. Bring your own licensed audio.
- A passing `plan_tools.py check` validates structure only; final quality is judged on real renders.

## License

- VV original work (`skills/vv-narrative-video/`, root docs and config): [MIT](./LICENSE)
- `skills/video-use/`: MIT, © Browser Use
- `skills/video-shotcraft/`: Apache-2.0, © original authors

See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md). Contributions welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md).
