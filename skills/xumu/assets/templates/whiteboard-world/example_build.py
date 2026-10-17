#!/usr/bin/env python3
"""Runnable demo of the whiteboard-world template (about 16 s): two stations on one board, a role animation,
a dive into a drawn monitor that cuts to a screen clip, an emerge back out, and the circular talking head.

  python example_build.py <empty comp dir>   # writes placeholder media + index.html, then run HyperFrames check/snapshot

Times here are literal seconds only because the demo has no narration. In a real project every time comes from
cue.Timing references (see references/whiteboard-world.md).
"""
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wb_lib import Comp, p_arrow, p_doc, p_magnifier, wob_rect  # noqa: E402


def placeholder_media(comp):
    """Synthetic clips so the demo renders without project assets."""
    rec = comp / 'assets' / 'rec'
    rec.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *a], check=True)
    run('-f', 'lavfi', '-i', 'testsrc2=size=1920x1080:rate=30', '-t', '5', '-g', '15', '-pix_fmt', 'yuv420p',
        str(rec / 'demo.mp4'))
    run('-f', 'lavfi', '-i', 'smptebars=size=1080x1080:rate=30', '-t', '16', '-g', '15', '-pix_fmt', 'yuv420p',
        str(comp / 'assets' / 'face.mp4'))
    run('-f', 'lavfi', '-i', 'sine=frequency=220:sample_rate=48000', '-t', '16', '-af', 'volume=0.05',
        str(comp / 'assets' / 'voice.m4a'))


def build(comp_dir, font=None):
    comp = Path(comp_dir)
    placeholder_media(comp)
    if font:
        (comp / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)
        shutil.copy(font, comp / 'assets' / 'fonts' / Path(font).name)
    c = Comp(comp, total=16.0, font_url=f'assets/fonts/{Path(font).name}' if font else None)

    # ---- world 1: two stations on one board, then a dive into a monitor showing the clip's first frame
    w = c.new_world()
    parts = c.role_head(160, 200, '市场研究', 0.6, sub='先把市场和目的地调查清楚')
    parts += [c.doodle(p_magnifier(330, 620, 90), 2.4, 0.7, 'k blue'),
              c.note(520, 600, '调查', 3.0, fs=56)]
    c.station(2400, 300)
    parts += [c.doodle(p_doc(160, 120, 260, 330), 5.0, 0.8),
              c.note(480, 220, '研究报告', 5.6, fs=56, color='blue'),
              c.doodle(p_arrow(-1500, 300, 120, 260), 4.2, 0.6, 'k grey', hand=False)]
    c.station(1200, 1500)
    first = c.still_at('assets/rec/demo.mp4', 0.0)
    mon, rect = c.monitor(0, 0, first, 6.6, show=False)
    parts += mon
    c.world(w, 0.0, 9.0, parts, cams=[
        (0.0, (0, 0, 1920, 1080), 0, 'set'),
        (2.2, (80, 360, 1500, 844), 1.2, 'push'),
        (4.0, (2300, 200, 1920, 1080), 0.9, 'whip'),
        (6.2, (900, 1200, 2600, 1462), 0.9, 'pull'),
        (7.6, rect, 1.4, 'dive'),
    ])
    # ---- screen clip: starts exactly when the dive fills the frame; returns to full frame 1 s before its end
    c.screen_clip('assets/rec/demo.mp4', 9.0, 13.0, cams=[(9.0, (0, 0, 1920, 1080), 0), (9.6, (480, 270, 960, 540), 1.0),
                                                       (11.4, (0, 0, 1920, 1080), 0.6)],
                  marks=[('ring', 10.0, (700, 400, 520, 280), 'red', 11.3)])
    # ---- world 2: start framed on a monitor showing the clip's last frame, emerge back onto the board
    w2 = c.new_world()
    last = c.still_at('assets/rec/demo.mp4', 3.95)
    mon2, rect2 = c.monitor(400, 300, last, 13.0)
    parts2 = mon2 + [c.note(2050, 520, '回到白板', 14.2, fs=60)]
    c.world(w2, 13.0, 16.0, parts2, cams=[(13.0, rect2, 0, 'set'), (13.1, (0, 0, 3000, 1688), 1.2, 'emerge')])
    # ---- talking head: corner circle, one emphasis window
    c.face('assets/face.mp4', 0.0, 15.6)
    c.emphasis(3.4, 4.6)
    return c.finish(voice=[(0.0, 16.0, 0.0, 'assets/voice.m4a')])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
