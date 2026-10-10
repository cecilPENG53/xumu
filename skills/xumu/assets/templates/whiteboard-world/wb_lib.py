"""Whiteboard-world builder for HyperFrames (1920x1080): one continuous board per world under one virtual camera.

Generalized from the 一人公司介绍 film (HyperFrames 0.8.81). A project build script creates a Comp, places
worlds, screen clips, video cards and the talking-head window, then calls finish() to write comp/index.html.
All times are programme seconds; resolve them with cue.Timing (scripts/cue.py) instead of typing seconds.

    import sys; sys.path[:0] = ['<skill>/scripts', '<skill>/assets/templates/whiteboard-world']
    from cue import Timing
    from wb_lib import Comp, wob_rect, p_arrow
    T = Timing('<edit>'); C = lambda text, sec=None, off=0: T.seconds({'cue': text, 'section': sec, 'offset': off})
    comp = Comp('<edit>/comp', total=T.total())
    w = comp.new_world()
    parts = [comp.note(200, 300, '一句关键词', C('关键词', 'B01'))]
    comp.world(w, start, end, parts, cams=[(start, (0, 0, 1920, 1080), 0, 'set'), ...])
    comp.finish(voice=[(0.0, T.total(), 0.0, 'assets/voice.m4a')])

Camera kinds: set | push | pan | whip | pull | dive (into a drawn monitor) | emerge (out of a drawn monitor).
"""
import html
import json
import math
from pathlib import Path
import subprocess

TEMPLATE = Path(__file__).with_name('template.html')
EASES = {'push': 'power3.inOut', 'pan': 'power2.inOut', 'whip': 'expo.inOut', 'pull': 'power2.inOut',
         'dive': 'power4.in', 'emerge': 'power3.inOut'}
BLUR = {'whip': 7, 'dive': 5, 'emerge': 3}
MW, MH = 1504, 846   # drawn monitor screen size (16:9)


# ------------------------------------------------------------------ hand-drawn geometry (deterministic wobble)
def hsh(n, seed):
    x = math.sin(n * 127.1 + seed * 311.7) * 43758.5453
    return (x - math.floor(x)) * 2 - 1


def wob_rect(x, y, w, h, seed, r=14, a=3.0):
    o = lambda n: hsh(n, seed) * a
    X = lambda v, n: f'{x + v + o(n):.1f}'
    Y = lambda v, n: f'{y + v + o(n + 50):.1f}'
    return (f'M {X(r,1)} {Y(0,2)} L {X(w/2,3)} {Y(0,4)} L {X(w-r,5)} {Y(0,6)} Q {X(w,7)} {Y(0,8)} {X(w,9)} {Y(r,10)} '
            f'L {X(w,11)} {Y(h/2,12)} L {X(w,13)} {Y(h-r,14)} Q {X(w,15)} {Y(h,16)} {X(w-r,17)} {Y(h,18)} '
            f'L {X(w/2,19)} {Y(h,20)} L {X(r,21)} {Y(h,22)} Q {X(0,23)} {Y(h,24)} {X(0,25)} {Y(h-r,26)} '
            f'L {X(0,27)} {Y(h/2,28)} L {X(0,29)} {Y(r,30)} Q {X(0,31)} {Y(0,32)} {X(r+6,33)} {Y(-2,34)}')


def wob_ellipse(cx, cy, rx, ry, seed, w=4):
    n, pts = 14, []
    for i in range(n):
        a = i / n * 2 * math.pi - math.pi / 2
        wr = 1 + hsh(i * 13 + 5, seed) * w / 100
        pts.append((cx + math.cos(a) * rx * wr, cy + math.sin(a) * ry * wr))
    d = f'M {pts[0][0]:.1f} {pts[0][1]:.1f}'
    for j in range(n):
        p, q = pts[(j + 1) % n], pts[(j + 2) % n]
        d += f' Q {p[0]:.1f} {p[1]:.1f} {(p[0]+q[0])/2:.1f} {(p[1]+q[1])/2:.1f}'
    return d


def text_w(s, fs):
    """Approximate rendered width of handwritten text (CJK = 1em, Latin = 0.55em)."""
    w = 0
    for ch in s:
        w += fs * (1.35 if ch == '→' else 0.55 if ord(ch) < 0x2E80 and ch != ' ' else (0.3 if ch == ' ' else 1.0))
    return w


# ------------------------------------------------------------------ icon paths (local coordinates)
def p_arrow(x1, y1, x2, y2, bend=0.18):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    cx, cy = mx - (y2 - y1) * bend, my + (x2 - x1) * bend
    length = max(1, math.hypot(x2 - cx, y2 - cy))
    ux, uy = (x2 - cx) / length, (y2 - cy) / length
    h = 22
    ax, ay = x2 - ux * h - uy * h * 0.6, y2 - uy * h + ux * h * 0.6
    bx, by = x2 - ux * h + uy * h * 0.6, y2 - uy * h - ux * h * 0.6
    return f'M {x1} {y1} Q {cx:.1f} {cy:.1f} {x2} {y2} M {ax:.1f} {ay:.1f} L {x2} {y2} L {bx:.1f} {by:.1f}'


def p_magnifier(cx, cy, r, seed=3):
    return wob_ellipse(cx, cy, r, r, seed, 3) + f' M {cx+r*0.72:.1f} {cy+r*0.72:.1f} L {cx+r*1.6:.1f} {cy+r*1.6:.1f}'


def p_doc(x, y, w, h, lines=4):
    f = min(w, h) * 0.22
    d = f'M {x} {y} L {x+w-f} {y} L {x+w} {y+f} L {x+w} {y+h} L {x} {y+h} Z M {x+w-f} {y} L {x+w-f} {y+f} L {x+w} {y+f}'
    for k in range(lines):
        yy = y + h * (0.28 + 0.16 * k)
        d += f' M {x+w*0.16:.0f} {yy:.0f} L {x+w*(0.84 if k % 2 == 0 else 0.62):.0f} {yy:.0f}'
    return d


def p_browser(x, y, w, h):
    d = wob_rect(x, y, w, h, 12, r=14, a=2) + f' M {x} {y+48} L {x+w} {y+48}'
    for k in range(3):
        cx = x + 26 + k * 26
        d += f' M {cx-7} {y+24} a 7 7 0 1 0 14 0 a 7 7 0 1 0 -14 0'
    return d


def p_pin(x, y, s=1.0):
    return (f'M {x} {y} C {x-8*s} {y-14*s}, {x-26*s} {y-30*s}, {x-26*s} {y-50*s} A {26*s} {26*s} 0 1 1 {x+26*s} {y-50*s} '
            f'C {x+26*s} {y-30*s}, {x+8*s} {y-14*s}, {x} {y} Z M {x-9*s} {y-50*s} a {9*s} {9*s} 0 1 0 {18*s} 0 '
            f'a {9*s} {9*s} 0 1 0 {-18*s} 0')


def p_box(x, y, s=44):
    return f'M {x} {y} L {x+s} {y+2} L {x+s-1} {y+s} L {x+1} {y+s-1} Z'


def p_check(x, y, s=44):
    return f'M {x+s*0.12} {y+s*0.52} L {x+s*0.42} {y+s*0.82} L {x+s*0.95} {y+s*0.05}'


def p_bubble(x, y, w, h, tail='left', seed=7):
    tx = x + 40 if tail == 'left' else x + w - 40
    tip = tx - 30 if tail == 'left' else tx + 30
    return wob_rect(x, y, w, h, seed, r=22, a=2) + f' M {tx-14} {y+h-2} L {tip} {y+h+30} L {tx+14} {y+h-2}'


def p_table(x, y, w, h, rows=4, cols=3):
    d = wob_rect(x, y, w, h, 9, r=8, a=2)
    for r in range(1, rows):
        yy = y + h * r / rows
        d += f' M {x} {yy:.0f} L {x+w} {yy:.0f}'
    for c in range(1, cols):
        xx = x + w * c / cols
        d += f' M {xx:.0f} {y} L {xx:.0f} {y+h}'
    return d


def p_bars(x, y, w, h, values=(0.35, 0.55, 0.45, 0.8)):
    bw = w / (len(values) * 1.4 + 1.4)
    d = f'M {x} {y} L {x} {y+h} L {x+w} {y+h}'
    for k, f in enumerate(values):
        bx = x + bw * (1 + k * 1.4)
        d += f' M {bx:.0f} {y+h} L {bx:.0f} {y+h*(1-f):.0f} L {bx+bw:.0f} {y+h*(1-f):.0f} L {bx+bw:.0f} {y+h}'
    return d


def p_scale(cx, y, w):
    return (f'M {cx} {y} L {cx} {y+w*0.95} M {cx-w*0.3} {y+w*0.95} L {cx+w*0.3} {y+w*0.95} '
            f'M {cx-w*0.5} {y+w*0.18} L {cx+w*0.5} {y+w*0.12} '
            f'M {cx-w*0.5} {y+w*0.18} L {cx-w*0.66} {y+w*0.5} L {cx-w*0.34} {y+w*0.5} Z '
            f'M {cx+w*0.5} {y+w*0.12} L {cx+w*0.34} {y+w*0.44} L {cx+w*0.66} {y+w*0.44} Z')


def p_clipboard(x, y, w, h):
    return wob_rect(x, y, w, h, 15, r=16, a=2) + f' M {x+w*0.35} {y-14} L {x+w*0.65} {y-14} L {x+w*0.65} {y+22} L {x+w*0.35} {y+22} Z'


def p_megaphone(x, y, s=1.0):
    return (f'M {x} {y+30*s} L {x+40*s} {y+30*s} L {x+110*s} {y} L {x+110*s} {y+100*s} L {x+40*s} {y+70*s} L {x} {y+70*s} Z '
            f'M {x+20*s} {y+70*s} L {x+34*s} {y+110*s} M {x+130*s} {y+30*s} Q {x+150*s} {y+50*s} {x+130*s} {y+70*s}')


def p_phone(x, y, w, h):
    return wob_rect(x, y, w, h, 19, r=26, a=2) + f' M {x+w*0.4} {y+h-24} L {x+w*0.6} {y+h-24}'


def p_folder(x, y, w, h):
    return f'M {x} {y+20} L {x+w*0.36} {y+20} L {x+w*0.44} {y} L {x+w} {y} L {x+w} {y+h} L {x} {y+h} Z'


def p_loop(cx, cy, r):
    return f'M {cx+r} {cy} A {r} {r} 0 1 1 {cx} {cy-r} M {cx-14} {cy-r-14} L {cx} {cy-r} L {cx-14} {cy-r+14}'


def p_underline(x, y, w):
    return f'M {x} {y} C {x+w*0.4:.0f} {y-6}, {x+w*0.7:.0f} {y+4}, {x+w:.0f} {y-2}'


ROBOT = ('<svg width="{s}" height="{s}" viewBox="0 0 52 52"><path d="M 26 4 L 26 12" stroke="#2b2b2b" stroke-width="3" '
         'stroke-linecap="round"/><circle cx="26" cy="4" r="3.5" fill="#c93b3b"/><rect x="6" y="12" width="40" height="32" '
         'rx="8" fill="#dfe9f7" stroke="#2b2b2b" stroke-width="3"/><circle cx="19" cy="26" r="3.5" fill="#2b2b2b"/>'
         '<circle cx="33" cy="26" r="3.5" fill="#2b2b2b"/><path d="M 19 35 L 33 35" stroke="#2b2b2b" stroke-width="3" '
         'stroke-linecap="round"/></svg>')
ARROW_INLINE = ('<svg width="1.1em" height="0.8em" viewBox="0 0 44 32" style="display:inline-block;vertical-align:-0.05em;'
                'margin:0 0.12em"><path d="M3 17 C 14 15, 26 18, 38 16 M 28 6 L 40 16 L 28 27" stroke="currentColor" '
                'stroke-width="4.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
PERSON = ('<path class="k" d="{head}"/><path class="k" d="M 50 24 Q 60 4 74 18 Q 84 2 98 22"/>'
          '<path class="k" d="M 75 104 L 75 152 M 75 120 L 38 142 M 75 120 L 112 142 M 75 152 L 50 190 M 75 152 L 100 190"/>'
          '<path class="k" d="M 57 74 Q 75 92 93 74"/><circle cx="60" cy="56" r="5" fill="#2b2b2b"/>'
          '<circle cx="90" cy="56" r="5" fill="#2b2b2b"/>')


def inline_arrows(text):
    """Handwriting fonts often lack →; draw it as inline SVG instead."""
    return text.replace('→', ARROW_INLINE)


class Comp:
    def __init__(self, comp_dir, total, fps=30, font_url='assets/fonts/hand-sub.woff2'):
        self.comp, self.total, self.fps, self.font_url = Path(comp_dir), float(total), fps, font_url
        self.body, self.js, self.uid = [], [], 0
        self.st = {'dx': 0, 'dy': 0, 'cam': None}     # current world id + station offset inside that world
        self.screens, self.emphasis_windows, self.face_windows = [], [], []

    # -------------------------------------------------------------- ids and state
    def nid(self, prefix):
        self.uid += 1
        return f'{prefix}{self.uid}'

    def new_world(self):
        """Start a whiteboard world; returns its id (also its camera id)."""
        wid = self.nid('w')
        self.st.update(dx=0, dy=0, cam=wid)
        return wid

    def station(self, dx, dy):
        """Offset following parts inside the current world (stations zig-zag across one big board)."""
        self.st.update(dx=dx, dy=dy)

    def flat(self):
        """Following parts go on a flat, camera-less board."""
        self.st.update(dx=0, dy=0, cam=None)

    def _cam(self):
        return json.dumps(self.st['cam']) if self.st['cam'] else 'false'

    def _flags(self, hand):
        return f'{{hand:{str(hand).lower()}, cam:{self._cam()}}}'

    def clip(self, start, end, inner, track=2, cls='stage', style='', cid=None):
        i = cid or self.nid('c')
        self.body.append(f'<div id="{i}" class="clip {cls}" data-start="{start:.3f}" data-duration="{end-start:.3f}" '
                         f'data-track-index="{track}" style="{style}">{inner}</div>')
        return i

    # -------------------------------------------------------------- board parts (return HTML/SVG fragments)
    def note(self, x, y, txt, at, fs=44, color='ink', dur=None, hand=True, w=None):
        """Handwritten text revealed left to right while the pen hand writes along it."""
        x, y = x + self.st['dx'], y + self.st['dy']
        i = self.nid('t')
        w = w or text_w(html.unescape(txt), fs) + 10
        dur = dur or max(0.35, min(1.6, len(txt) * 0.07))
        self.js.append(f'write("#{i}", {at:.3f}, {dur:.2f}, {{x:{x},y:{y},w:{w:.0f},h:{fs*1.15:.0f}}}, {self._flags(hand)});')
        return (f'<div id="{i}" class="hand-t {color}" style="left:{x}px;top:{y}px;width:{w:.0f}px;font-size:{fs}px">'
                f'{inline_arrows(txt)}</div>')

    def doodle(self, d, at, dur=0.5, cls='k', hand=True):
        """A stroked path drawn on over `dur` seconds; the pen hand follows it."""
        i = self.nid('p')
        self.js.append(f'draw("#{i}", {at:.3f}, {dur:.2f}, {{hand:{str(hand).lower()}, cam:{self._cam()}, '
                       f'ox:{self.st["dx"]}, oy:{self.st["dy"]}}});')
        return f'<g transform="translate({self.st["dx"]} {self.st["dy"]})"><path id="{i}" class="{cls}" d="{d}"/></g>'

    def pop(self, inner, x, y, at, w=None, h=None, cid=None, style=''):
        x, y = x + self.st['dx'], y + self.st['dy']
        i = cid or self.nid('o')
        size = (f'width:{w}px;' if w else '') + (f'height:{h}px;' if h else '')
        self.js.append(f'pop("#{i}", {at:.3f});')
        return f'<div id="{i}" class="abs" style="left:{x}px;top:{y}px;{size}{style}">{inner}</div>'

    def tape_card(self, img, x, y, w, h, at, rot=-1.5, cap='', cid=None):
        """A photo or screenshot taped to the board (img is a path relative to comp/)."""
        x, y = x + self.st['dx'], y + self.st['dy']
        i = cid or self.nid('n')
        self.js.append(f'card("#{i}", {at:.3f}, {rot});')
        capd = f'<div class="cap">{cap}</div>' if cap else ''
        return (f'<div id="{i}" class="note" style="left:{x}px;top:{y}px;width:{w}px"><div class="tape"></div>'
                f'<div class="ph" style="height:{h}px"><img src="{img}" alt=""/></div>{capd}</div>')

    def person(self, x, y, at, scale=1.0, dur=0.9):
        """Stick figure drawn stroke by stroke (the viewer, a user, a customer)."""
        x, y = x + self.st['dx'], y + self.st['dy']
        i = self.nid('y')
        self.js.append(f'drawGroup("#{i}", {at:.3f}, {dur}, {x}, {y}, {scale}, {self._cam()});')
        head = wob_ellipse(75, 58, 43, 44, 5, 3)
        return (f'<svg id="{i}" class="loc" style="left:{x}px;top:{y}px;width:{150*scale:.0f}px;height:{196*scale:.0f}px" '
                f'viewBox="0 0 150 196">{PERSON.format(head=head)}</svg>')

    def robot(self, x, y, at, s=150, cid=None):
        return self.pop(ROBOT.format(s=s), x, y, at, cid=cid)

    def role_head(self, x, y, name, at, sub=None, s=150, color='ink'):
        """Opening beat of a role/agent animation: robot + title + blue underline + grey subtitle."""
        tw = text_w(name, 58)
        ty = y + s * 0.25
        parts = [self.robot(x, y, at, s), self.note(x + s + 20, ty, name, at + 0.25, fs=58, color=color, dur=0.8),
                 self.doodle(p_underline(x + s + 20, ty + 76, tw), at + 1.05, 0.3, 'k blue')]
        if sub:
            parts.append(self.note(x + s + 22, ty + 96, sub, at + 1.3, fs=34, color='grey', dur=0.7))
        return parts

    def sticky(self, x, y, txt, at, fs=36, color='ink', w=None):
        """Paper sticky note in screen space (use over screen clips via screen_clip(stickies=...))."""
        i = self.nid('k')
        w = w or text_w(txt, fs) + 44
        self.js.append(f'pop("#{i}", {at:.3f});')
        return (f'<div id="{i}" class="sticky" style="left:{x}px;top:{y}px;width:{w:.0f}px">'
                f'<div class="hand-t {color}" style="position:relative;font-size:{fs}px">{inline_arrows(txt)}</div></div>')

    # -------------------------------------------------------------- worlds and the camera
    def world(self, wid, start, end, parts, cams, w=8000, h=3200):
        """One continuous whiteboard world viewed through its own camera (one take).
        cams: [(time, (x, y, w, h) world rect to frame, duration, kind)]; kind in set|push|pan|whip|pull|dive|emerge.
        A rect is converted to camera state s = 1920 / w, x = -rx * s, y = -ry * s."""
        flat = [q for p in parts for q in (p if isinstance(p, list) else [p])]
        svg = [p for p in flat if p.startswith('<g transform')]
        rest = [p for p in flat if not p.startswith('<g transform')]
        smudges = ''.join(f'<div class="ghost-smudge" style="left:{gx}px;top:{gy}px;width:{gw}px;height:{gh}px"></div>'
                          for gx, gy, gw, gh in [((300 + k * 1370) % w, (k * 977) % h, 650 + (k * 131) % 300,
                                                  200 + (k * 53) % 80) for k in range(int(w * h / 2.2e6))])
        inner = (f'<div id="{wid}" class="world" data-layout-allow-overflow style="position:absolute;left:0;top:0;width:{w}px;height:{h}px;'
                 f'transform-origin:0 0">{smudges}<svg style="position:absolute;left:0;top:0;width:{w}px;height:{h}px;'
                 f'overflow:visible" viewBox="0 0 {w} {h}">{"".join(svg)}</svg>{"".join(rest)}</div>')
        self.clip(start, end, inner, track=2, cls='stage worldclip')
        cam = f'CAMS.{wid}'
        self.js.append(f'mkcam("{wid}");')
        for n, (t, (x, y, rw, rh), d, kind) in enumerate(cams):
            s = 1920 / rw
            state = f's:{s:.5f}, x:{-x*s:.1f}, y:{-y*s:.1f}'
            if kind == 'set':
                still = n + 1 < len(cams) and cams[n + 1][3] == 'emerge'   # framed on a monitor: no drift until emerge
                self.js.append(f'tl.set({cam}, {{{state}, d:{0 if still else 1}}}, {t:.3f});')
                continue
            if kind not in EASES:
                raise ValueError(f'unknown camera kind: {kind}')
            self.js.append(f'tl.to({cam}, {{{state}, duration:{d:.2f}, ease:"{EASES[kind]}"}}, {t:.3f});')
            if kind == 'dive':   # handheld drift fades out so the monitor frame matches the clip exactly
                self.js.append(f'tl.to({cam}, {{d:0, duration:{d*0.8:.2f}, ease:"power2.out"}}, {t:.3f});')
            if kind in ('emerge', 'whip'):
                self.js.append(f'tl.to({cam}, {{d:1, duration:{d:.2f}, ease:"power2.in"}}, {t:.3f});')
            if kind in BLUR:
                self.js.append(f'tl.to({cam}, {{b:{BLUR[kind]}, duration:{d*0.4:.2f}, ease:"power2.in"}}, {t:.3f});')
                self.js.append(f'tl.to({cam}, {{b:0, duration:{d*0.6:.2f}, ease:"power2.out"}}, {t+d*0.4:.3f});')

    # -------------------------------------------------------------- monitors: board <-> screen hand-off
    def still_at(self, clip_rel, t):
        """Frame of comp/<clip_rel> at media time t (frame-exact select), saved as png beside it; returns its path."""
        src = self.comp / clip_rel
        out = src.with_name(f'{src.stem}_{t:.2f}.png')
        if not out.exists():
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-vf',
                            f'select=gte(n\\,{round(t * self.fps)})', '-frames:v', '1', str(out)], check=True)
        return out.relative_to(self.comp).as_posix()

    def monitor(self, x, y, img, at, show=True, seed=31):
        """Hand-drawn monitor whose screen shows img. Returns (parts, world rect of the screen) for dive/emerge cams.
        Dive: cam 'dive' to the rect, then cut to the clip whose first frame is img.
        Emerge: cam 'set' on the rect at the clip's end (img = its last frame), then 'emerge' to a wider rect."""
        d0, d1 = (0.01, 0.01) if show else (0.9, 0.5)
        parts = [self.doodle(wob_rect(x - 40, y - 40, MW + 80, MH + 80, seed, r=26, a=4), at, d0, 'k', hand=False),
                 self.doodle(f'M {x+MW/2-60} {y+MH+40} L {x+MW/2-90} {y+MH+170} M {x+MW/2+60} {y+MH+40} '
                             f'L {x+MW/2+90} {y+MH+170} M {x+MW/2-260} {y+MH+172} C {x+MW/2-80} {y+MH+165}, '
                             f'{x+MW/2+80} {y+MH+178}, {x+MW/2+260} {y+MH+170}', at + (0 if show else 0.8), d1, 'k',
                             hand=False)]
        i = self.nid('mon')
        if not show:
            self.js.append(f'tl.fromTo("#{i}", {{opacity:0}}, {{opacity:1, duration:0.5, ease:"power2.out"}}, {at+0.5:.3f});')
        X, Y = x + self.st['dx'], y + self.st['dy']
        parts.append(f'<div id="{i}" class="abs" style="left:{X}px;top:{Y}px;width:{MW}px;height:{MH}px;'
                     f'background:#fff;overflow:hidden"><img src="{img}" style="width:100%;height:100%;display:block" alt=""/></div>')
        return parts, (X, Y, MW, MH)

    # -------------------------------------------------------------- video cards pinned to a world
    def video_card(self, name, x, y, a, b, rot=0.0, w=1280, audio=True, volume=0.9):
        """Taped video card on the current world: shows assets/cards/<name>_first.png until a, plays the clip
        (a top-level <video> whose wrapper follows the world camera) during [a, b], then holds <name>_last.png."""
        X, Y = x + self.st['dx'], y + self.st['dy']
        h = w * 9 / 16
        last, pid = self.nid('vl'), self.nid('pin')
        self.js.append(f'tl.set("#{last}", {{opacity:1}}, {b:.3f});')
        self.js.append(f'tl.set("#{pid}", {{opacity:1}}, {a:.3f}); tl.set("#{pid}", {{opacity:0}}, {b:.3f});')
        self.body.append(f'<div id="{pid}" class="pinwrap" data-pin="{self.st["cam"]}" data-x="{X}" data-y="{Y}" '
                         f'data-w="{w}" data-r="{rot}"><video id="{pid}v" class="clip" src="assets/cards/{name}.mp4" muted '
                         f'playsinline data-start="{a:.3f}" data-duration="{b-a:.3f}" data-media-start="0" '
                         f'data-track-index="3"></video></div>')
        if audio:
            self.body.append(f'<audio id="{pid}a" src="assets/cards/{name}.m4a" data-start="{a:.3f}" '
                             f'data-duration="{b-a:.3f}" data-media-start="0" data-volume="{volume}"></audio>')
        return (f'<div class="abs" style="left:{X}px;top:{Y}px;width:{w}px;height:{h:.0f}px;transform:rotate({rot}deg);'
                f'transform-origin:0 0"><div class="vframe"></div><div class="tape"></div>'
                f'<img class="vimg" src="assets/cards/{name}_first.png" alt=""/>'
                f'<img id="{last}" class="vimg" src="assets/cards/{name}_last.png" alt="" style="opacity:0"/></div>')

    # -------------------------------------------------------------- real screen clips
    def screen_clip(self, src, start, end, cams=(), marks=(), stickies=(), media_start=0.0):
        """Full-frame clip (1920x1080 asset). cams: [(time, (x, y, w, h) rect in video coords, duration)], the first
        entry sets the opening framing. marks: (kind box|ring|line|cross, at, rect, color='blue', hide_at=None).
        Return to full frame at least 1 s before `end` when a monitor emerge follows."""
        i = self.nid('r')
        svg = ''
        for m in marks:
            kind, at, (x, y, w, h) = m[0], m[1], m[2]
            color = m[3] if len(m) > 3 else 'blue'
            mid = self.nid('m')
            if kind == 'box':
                d = wob_rect(x, y, w, h, self.uid % 17 + 3, r=10, a=3)
            elif kind == 'ring':
                d = wob_ellipse(x + w / 2, y + h / 2, w / 2 + 14, h / 2 + 12, self.uid % 13 + 2)
            elif kind == 'line':
                d = f'M {x} {y+h} C {x+w*0.3} {y+h-4}, {x+w*0.7} {y+h+4}, {x+w} {y+h-2}'
            elif kind == 'cross':
                d = f'M {x} {y} L {x+w} {y+h} M {x+w} {y} L {x} {y+h}'
            else:
                raise ValueError(f'unknown mark kind: {kind}')
            svg += f'<path id="{mid}" class="k {color} mark" d="{d}"/>'
            self.js.append(f'draw("#{mid}", {at:.3f}, 0.4, {{hand:false}});')
            if len(m) > 4 and m[4]:
                self.js.append(f'tl.to("#{mid}", {{opacity:0, duration:0.25}}, {m[4]:.3f});')
        self.body.append(f'<div id="{i}" class="recwrap"><video id="{i}v" class="clip" src="{src}" muted playsinline '
                         f'data-start="{start:.3f}" data-duration="{end-start:.3f}" data-media-start="{media_start:.3f}" '
                         f'data-track-index="3"></video><svg viewBox="0 0 1920 1080">{svg}</svg></div>')
        self.js.append(f'tl.set("#{i}", {{opacity:1}}, {start:.3f}); tl.set("#{i}", {{opacity:0}}, {end:.3f});')
        if stickies:
            self.clip(start, end, ''.join(stickies), track=4, style='z-index:6')
        for n, (t, (x, y, rw, rh), d) in enumerate(cams):
            s = 1920 / rw
            state = f'scale:{s:.4f}, x:{-x*s:.1f}, y:{-y*s:.1f}'
            self.js.append(f'tl.set("#{i}", {{{state}}}, 0);' if n == 0 else
                           f'tl.to("#{i}", {{{state}, duration:{d:.2f}, ease:"power3.inOut"}}, {t:.3f});')
        self.screens.append({'src': src, 'start': start, 'end': end})

    # -------------------------------------------------------------- circular talking head
    def face(self, src, start, end, media_start=0.0):
        """Talking-head video shown in the bottom-right circle during [start, end]."""
        self.face_windows.append((start, end, media_start, src))

    def emphasis(self, a, b, cut_in=False, cut_out=False):
        """Grow the circle to full size for [a, b] (key statements); default is the 0.47 corner window."""
        self.emphasis_windows.append((a, b, cut_in, cut_out))

    def _face_js(self):
        if not self.face_windows:
            return
        vids = ''.join(f'<video id="fv{k}" class="clip facev" src="{src}" muted playsinline data-start="{a:.3f}" '
                       f'data-duration="{min(b, self.total)-a:.3f}" data-media-start="{ms:.3f}" data-track-index="7"></video>'
                       for k, (a, b, ms, src) in enumerate(self.face_windows) if a < self.total)
        self.body.append(f'<div id="facewrap">{vids}</div>')
        first, last = min(w[0] for w in self.face_windows), max(w[1] for w in self.face_windows)
        self.js.append(f'tl.set("#facewrap", {{opacity:0, scale:0.1}}, 0);')
        self.js.append(f'tl.to("#facewrap", {{opacity:1, scale:0.47, duration:0.5, ease:"back.out(1.6)"}}, {first:.3f});')
        ordered = sorted(self.face_windows)
        for (_, b, _, _), (a2, _, _, _) in zip(ordered, ordered[1:]):   # hide between separate windows
            if a2 - b > 0.05:
                self.js.append(f'tl.set("#facewrap", {{opacity:0}}, {b:.3f}); tl.to("#facewrap", '
                               f'{{opacity:1, scale:0.47, duration:0.5, ease:"back.out(1.6)"}}, {a2:.3f});')
        for a, b, cin, cout in self.emphasis_windows:
            self.js.append(f'tl.set("#facewrap", {{scale:1}}, {a:.3f});' if cin else
                           f'tl.to("#facewrap", {{scale:1, duration:0.6, ease:"back.out(1.3)"}}, {a:.3f});')
            self.js.append(f'tl.set("#facewrap", {{scale:0.47}}, {b:.3f});' if cout else
                           f'tl.to("#facewrap", {{scale:0.47, duration:0.5, ease:"power3.inOut"}}, {b-0.25:.3f});')
        if last < self.total:   # fade out with the last word instead of leaving an empty circle
            self.js.append(f'tl.to("#facewrap", {{opacity:0, scale:0.2, duration:0.35, ease:"power2.in"}}, {last-0.35:.3f});')

    # -------------------------------------------------------------- output
    def finish(self, voice=(), out='index.html', plan_out='wb-layout.json'):
        """Write comp/<out>. voice: [(start, end, media_start, src)] narration audio windows (programme seconds)."""
        self._face_js()
        for k, (a, b, ms, src) in enumerate(voice):
            self.body.append(f'<audio id="voice{k}" src="{src}" data-start="{a:.3f}" data-duration="{min(b, self.total)-a:.3f}" '
                             f'data-media-start="{ms:.3f}"></audio>')
        tpl = TEMPLATE.read_text(encoding='utf-8')
        page = (tpl.replace('%%TOTAL%%', f'{self.total:.3f}').replace('%%FONT_URL%%', self.font_url)
                .replace('%%BODY%%', '\n'.join(self.body)).replace('%%JS%%', '\n'.join(self.js)))
        self.comp.mkdir(parents=True, exist_ok=True)
        (self.comp / out).write_text(page, encoding='utf-8')
        layout = {'fps': self.fps, 'total': self.total, 'screens': self.screens,
                  'emphasis': self.emphasis_windows, 'face': [w[:3] for w in self.face_windows]}
        (self.comp / plan_out).write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding='utf-8')
        return {'out': str(self.comp / out), 'total': self.total, 'js_lines': len(self.js), 'screens': len(self.screens)}
