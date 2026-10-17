#!/usr/bin/env python3
"""Controlled HyperFrames upgrade check: render the whiteboard-world demo with the pinned and a candidate version,
then compare the two renders frame by frame.

  python hf_upgrade_check.py --work <empty dir> [--old <pinned>] [--new latest] [--ssim-min 0.97]

Steps: build assets/templates/whiteboard-world/example_build.py once; copy it per version; run
`npx --yes hyperframes@<v> check` and `render`; compare duration, fps, audio, and per-frame SSIM; save the worst
frames side by side. Writes <work>/report.json and <work>/report.md. Exit 0 = pass, 2 = needs a human look,
1 = could not run. Nothing outside --work is touched; existing projects keep their pinned version.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_ROOT / 'assets' / 'templates' / 'whiteboard-world'
DEFAULT_OLD = '0.8.166'   # the verified, pinned version; update together with references/production.md


def tool(name):
    found = shutil.which(name) or shutil.which(name + '.cmd')
    if not found:
        raise FileNotFoundError(f'{name} not found on PATH')
    return found


def run(cmd, cwd=None, timeout=1800):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=timeout)
    return p.returncode, (p.stdout + p.stderr), round(time.time() - t0, 1)


def latest_version():
    rc, out, _ = run([tool('npm'), 'view', 'hyperframes', 'version'])
    if rc:
        raise RuntimeError(f'npm view failed: {out[-300:]}')
    return out.strip().splitlines()[-1]


def probe(path):
    rc, out, _ = run([tool('ffprobe'), '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,r_frame_rate',
                      '-of', 'json', str(path)])
    info = json.loads(out) if rc == 0 else {}
    streams = info.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), {})
    num, _, den = (video.get('r_frame_rate') or '0/1').partition('/')
    return {'duration': round(float(info.get('format', {}).get('duration', 0)), 3),
            'fps': round(float(num) / float(den or 1), 3) if float(den or 1) else 0,
            'audio': any(s.get('codec_type') == 'audio' for s in streams)}


def ssim_frames(a, b, work):
    """Per-frame SSIM (All) between two renders, scaled to the smaller size first."""
    stats = work / 'ssim.log'
    run([tool('ffmpeg'), '-v', 'error', '-i', str(a), '-i', str(b), '-lavfi',
         f"[0:v]scale=960:-2,setpts=PTS-STARTPTS[x];[1:v]scale=960:-2,setpts=PTS-STARTPTS[y];"
         f"[x][y]ssim=stats_file='{stats.name}'", '-f', 'null', '-'], cwd=work)
    frames = []
    for line in stats.read_text(encoding='utf-8').splitlines():
        n, s = re.search(r'n:(\d+)', line), re.search(r'All:([0-9.]+)', line)
        if n and s:
            frames.append((int(n.group(1)), float(s.group(1))))
    return frames


def side_by_side(a, b, t, out):
    run([tool('ffmpeg'), '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(a), '-ss', f'{t:.3f}', '-i', str(b),
         '-filter_complex', '[0:v]scale=640:-2[x];[1:v]scale=640:-2[y];[x][y]hstack', '-frames:v', '1', str(out)])


def check(work, old, new, ssim_min):
    work.mkdir(parents=True, exist_ok=True)
    src = work / 'comp_src'
    if not (src / 'index.html').exists():
        rc, out, _ = run([sys.executable, str(TEMPLATE / 'example_build.py'), str(src)])
        if rc:
            raise RuntimeError(f'example_build failed: {out[-500:]}')
    result = {'old': old, 'new': new, 'versions': {}}
    for v in (old, new):
        comp = work / f'comp_{v}'
        if not comp.exists():
            shutil.copytree(src, comp)
        out_mp4 = work / f'render_{v}.mp4'
        rc_c, log_c, t_c = run([tool('npx'), '--yes', f'hyperframes@{v}', 'check'], cwd=comp)
        rc_r, log_r, t_r = (0, 'reused existing render', 0.0) if out_mp4.exists() else \
            run([tool('npx'), '--yes', f'hyperframes@{v}', 'render', '--output', str(out_mp4)], cwd=comp)
        (work / f'log_{v}.txt').write_text(f'$ check (rc={rc_c}, {t_c}s)\n{log_c}\n\n$ render (rc={rc_r}, {t_r}s)\n{log_r}',
                                           encoding='utf-8')
        result['versions'][v] = {'check_rc': rc_c, 'render_rc': rc_r, 'render_seconds': t_r,
                                 'output': str(out_mp4) if out_mp4.exists() else None,
                                 **(probe(out_mp4) if out_mp4.exists() else {})}
    a, b = (result['versions'][v]['output'] for v in (old, new))
    problems, known = [], []
    ro, rn = result['versions'][old], result['versions'][new]
    if rn['check_rc'] and not ro['check_rc']:
        problems.append(f'{new}: check fails where {old} passed (see log_{new}.txt)')
    elif rn['check_rc']:
        known.append(f'check fails on both versions: an existing issue, not an upgrade regression (see log_{old}.txt)')
    for v in (old, new):
        r = result['versions'][v]
        if r['render_rc'] or not r['output']:
            problems.append(f'{v}: render failed (rc {r["render_rc"]})')
    if a and b:
        ra, rb = result['versions'][old], result['versions'][new]
        fps = ra.get('fps') or 30
        if abs(ra['duration'] - rb['duration']) > 1.5 / fps:
            problems.append(f'duration {ra["duration"]}s → {rb["duration"]}s')
        if ra['fps'] != rb['fps']:
            problems.append(f'fps {ra["fps"]} → {rb["fps"]}')
        if ra['audio'] != rb['audio']:
            problems.append(f'audio stream {ra["audio"]} → {rb["audio"]}')
        frames = ssim_frames(a, b, work)
        if frames:
            mean = sum(s for _, s in frames) / len(frames)
            worst = sorted(frames, key=lambda f: f[1])[:5]
            result['ssim'] = {'frames': len(frames), 'mean': round(mean, 4), 'min': round(worst[0][1], 4),
                              'below_min': sum(1 for _, s in frames if s < ssim_min),
                              'worst': [{'frame': n, 't': round((n - 1) / fps, 3), 'ssim': round(s, 4)} for n, s in worst]}
            for k, w in enumerate(result['ssim']['worst'][:3]):
                side_by_side(a, b, w['t'], work / f'worst_{k + 1}_{w["t"]:.2f}s.jpg')
            if result['ssim']['min'] < ssim_min:
                problems.append(f'{result["ssim"]["below_min"]} frames below SSIM {ssim_min} (min {result["ssim"]["min"]})')
    result['problems'], result['known_issues'] = problems, known
    result['verdict'] = 'pass' if not problems else ('review' if a and b else 'failed')
    return result


def report_md(r):
    lines = [f'# HyperFrames 升级检查：{r["old"]} → {r["new"]}', '', f'结论：**{r["verdict"]}**', '',
             '| 版本 | check | render | 渲染耗时 | 时长 | fps | 音轨 |', '|---|---|---|---|---|---|---|']
    for v, x in r['versions'].items():
        lines.append(f'| {v} | {x["check_rc"]} | {x["render_rc"]} | {x["render_seconds"]}s | {x.get("duration")} | '
                     f'{x.get("fps")} | {x.get("audio")} |')
    if 'ssim' in r:
        s = r['ssim']
        lines += ['', f'逐帧 SSIM（1.0 = 完全相同）：平均 {s["mean"]}，最低 {s["min"]}，低于阈值 {s["below_min"]} 帧 / 共 {s["frames"]} 帧',
                  '最低的几帧（左旧右新，图在本目录 worst_*.jpg）：' + '，'.join(f'{w["t"]}s={w["ssim"]}' for w in s['worst'])]
    if r['problems']:
        lines += ['', '升级带来的问题：'] + [f'- {p}' for p in r['problems']]
    if r.get('known_issues'):
        lines += ['', '两个版本都有的已知问题：'] + [f'- {p}' for p in r['known_issues']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--old', default=DEFAULT_OLD, help='currently pinned version')
    parser.add_argument('--new', default='latest', help='candidate version, or "latest" from npm')
    parser.add_argument('--ssim-min', type=float, default=0.97)
    args = parser.parse_args(argv)
    try:
        new = latest_version() if args.new == 'latest' else args.new
        if new == args.old:
            print(json.dumps({'ok': True, 'verdict': 'up-to-date', 'version': new}))
            return 0
        r = check(args.work, args.old, new, args.ssim_min)
        (args.work / 'report.json').write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
        (args.work / 'report.md').write_text(report_md(r), encoding='utf-8')
        print(json.dumps({'ok': True, 'verdict': r['verdict'], 'new': new, 'problems': r['problems'],
                          'ssim': r.get('ssim', {}).get('mean'), 'report': str(args.work / 'report.md')}, ensure_ascii=False))
        return 0 if r['verdict'] == 'pass' else 2
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
