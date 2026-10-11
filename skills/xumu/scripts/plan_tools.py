#!/usr/bin/env python3
"""Offline timeline checks, render-cache keys, change impact and non-destructive handoff export. No media rendering."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys


ROUTES = ('real', 'shotcraft', 'mg', 'illustration', 'external', 'three')
ENGINES = ('remotion', 'hyperframes', 'html', 'manim', 'ffmpeg', 'external')
STATES = ('planned', 'awaiting_approval', 'waiting_external', 'rendered', 'verified')
# Shot fields that change the rendered picture. from_frame is left out on purpose: shots render
# from local frame 0, so moving one only changes where the composite places it.
RENDER_FIELDS = ('role', 'route', 'engine', 'style', 'screen_text', 'card', 'style_key',
                 'props', 'inner_frames', 'duration_frames')
# Tool and output folders skipped when an input is a directory.
SKIP_DIRS = {'node_modules', '__pycache__', 'dist', 'build', 'out'}


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def local_path(root, value):
    if not nonempty(value) or '://' in value or '\x00' in value:
        raise ValueError('expected a local file path, not a URL or empty value')
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


# ---------------------------------------------------------------- render cache keys

def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def input_digest(root, value, exclude=frozenset()):
    """Digest of one source file, or of every source file under a directory (paths included)."""
    path = local_path(root, value)
    if path.is_file():
        return file_digest(path)
    if not path.is_dir():
        raise ValueError(f'input does not exist: {value}')
    digest = hashlib.sha256()
    for folder, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in SKIP_DIRS)
        for name in sorted(files):
            item = Path(folder) / name
            if name.startswith('.') or item.resolve() in exclude:
                continue
            rel = item.relative_to(path).as_posix()
            digest.update(f'{rel}\0{file_digest(item)}\n'.encode('utf-8'))
    return digest.hexdigest()


def asset_files(plan, root):
    """Rendered outputs never count as inputs, even when they sit inside an input folder."""
    out = set()
    for shot in plan.get('shots', []) if isinstance(plan, dict) else []:
        asset = shot.get('asset') if isinstance(shot, dict) else None
        if isinstance(asset, dict):
            try:
                out.add(local_path(root, asset.get('file')))
            except (ValueError, OSError):
                pass
    return frozenset(out)


def render_parts(plan, shot, root, exclude=frozenset()):
    timeline = plan.get('timeline') or {}
    return {
        'canvas': {key: timeline.get(key) for key in ('fps', 'width', 'height')},
        # Copied, so a stamp never aliases the live props it describes.
        'fields': json.loads(json.dumps({key: shot[key] for key in RENDER_FIELDS if key in shot})),
        'inputs': {value: input_digest(root, value, exclude) for value in shot.get('inputs', [])},
    }


def render_key(parts):
    blob = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def part_changes(old, new):
    """Readable reasons why two render_parts differ."""
    reasons = []
    for key in ('fps', 'width', 'height'):
        if old.get('canvas', {}).get(key) != new['canvas'].get(key):
            reasons.append(f'canvas {key}: {old.get("canvas", {}).get(key)} -> {new["canvas"].get(key)}')
    old_fields = old.get('fields', {})
    for key in RENDER_FIELDS:
        before, after = old_fields.get(key), new['fields'].get(key)
        if before != after:
            reasons.append(f'{key}: {before} -> {after}' if key == 'duration_frames' else f'{key} changed')
    old_inputs = old.get('inputs', {})
    for value in sorted(set(old_inputs) | set(new['inputs'])):
        if value not in old_inputs:
            reasons.append(f'input added: {value}')
        elif value not in new['inputs']:
            reasons.append(f'input removed: {value}')
        elif old_inputs[value] != new['inputs'][value]:
            reasons.append(f'input changed: {value}')
    return reasons


def shot_state(plan, shot, root, exclude=frozenset()):
    """needs_render | unstamped | fresh | stale, plus reasons and the current parts."""
    asset = shot.get('asset')
    current = render_parts(plan, shot, root, exclude)
    if not isinstance(asset, dict):
        return 'needs_render', ['no rendered asset'], current
    stamp = asset.get('render_key')
    if not isinstance(stamp, dict):
        return 'unstamped', [], current
    if stamp.get('sha256') == render_key(current):
        return 'fresh', [], current
    parts = stamp.get('parts')
    return 'stale', (part_changes(parts, current) if isinstance(parts, dict) else []) or ['render inputs changed'], current


def validate(plan, root, ready=False):
    errors = []

    def fail(message):
        errors.append(message)

    def file_check(value, label):
        try:
            if not local_path(root, value).is_file():
                fail(f'{label}: file does not exist')
        except (ValueError, OSError) as exc:
            fail(f'{label}: {exc}')

    if not isinstance(plan, dict):
        return ['plan must be an object']
    if type(plan.get('schema_version')) is not int or plan['schema_version'] != 1:
        fail('schema_version must be integer 1')
    mode = plan.get('input_mode')
    if mode not in ('video', 'audio', 'text'):
        fail('input_mode must be video, audio or text')
    timeline = plan.get('timeline')
    if not isinstance(timeline, dict):
        return errors + ['timeline must be an object']
    revision = timeline.get('revision')
    if not nonempty(revision):
        fail('timeline.revision must be nonempty')
    total = timeline.get('total_frames')
    if not integer(total, 1):
        fail('timeline.total_frames must be a positive integer')
    fps = timeline.get('fps')
    if not integer(fps, 1) or fps > 120:
        fail('timeline.fps must be integer 1..120; rational fps needs a different contract')
    for dimension in ('width', 'height'):
        value = timeline.get(dimension)
        if not integer(value, 2) or value % 2:
            fail(f'timeline.{dimension} must be a positive even integer')
    if type(timeline.get('locked')) is not bool:
        fail('timeline.locked must be boolean')
    elif ready and not timeline['locked']:
        fail('timeline is not locked')

    narration = plan.get('narration')
    if not isinstance(narration, dict):
        fail('narration must be an object')
    elif narration.get('kind') not in ('original', 'tts', 'none'):
        fail('narration.kind must be original, tts or none')
    elif narration['kind'] == 'none':
        if narration.get('file'):
            fail('narration.kind=none cannot carry a narration file')
    else:
        if narration.get('timeline_revision') != revision:
            fail('narration has stale timeline_revision')
        if type(narration.get('locked')) is not bool:
            fail('narration.locked must be boolean')
        if ready:
            if narration.get('locked') is not True:
                fail('narration is not locked')
            file_check(narration.get('file'), 'narration.file')

    base = plan.get('base_video')
    has_base = base is not None
    if has_base:
        if mode != 'video':
            fail('base_video is allowed only in video mode; otherwise plan full backgrounds')
        if not isinstance(base, dict):
            fail('base_video must be an object')
        else:
            if base.get('timeline_revision') != revision:
                fail('base_video has stale timeline_revision')
            if not nonempty(base.get('file')):
                fail('base_video.file is required')
            if ready:
                if base.get('verified') is not True:
                    fail('base_video is not verified')
                file_check(base.get('file'), 'base_video.file')

    shots = plan.get('shots')
    if not isinstance(shots, list):
        return errors + ['shots must be an array']
    ids = {}
    backgrounds = []
    exclude = asset_files(plan, root)
    for i, shot in enumerate(shots):
        label = f'shots[{i}]'
        if not isinstance(shot, dict):
            fail(f'{label} must be an object')
            continue
        sid = shot.get('id')
        if not nonempty(sid):
            fail(f'{label}.id must be nonempty')
        elif sid in ids:
            fail(f'duplicate shot id: {sid}')
        else:
            ids[sid] = shot
        if shot.get('timeline_revision') != revision:
            fail(f'{label}: stale timeline_revision')
        if shot.get('role') not in ('background', 'overlay'):
            fail(f'{label}.role must be background or overlay')
        if shot.get('route') not in ROUTES:
            fail(f'{label}.route is unsupported')
        if shot.get('status') not in STATES:
            fail(f'{label}.status is unsupported')
        if not nonempty(shot.get('purpose')):
            fail(f'{label}.purpose is required')
        if shot.get('audio_policy') not in ('silent', 'separate'):
            fail(f'{label}.audio_policy must be silent or separate')
        if 'engine' in shot and shot['engine'] not in ENGINES:
            fail(f'{label}.engine is unsupported')
        if 'style' in shot and not nonempty(shot['style']):
            fail(f'{label}.style must be nonempty when present')
        anchor = shot.get('anchor')
        if anchor is not None and not (isinstance(anchor, dict) and isinstance(anchor.get('start'), dict)
                                       and (isinstance(anchor.get('end'), dict) or integer(anchor.get('frames'), 1))):
            fail(f'{label}.anchor needs a start reference and an end reference or positive frames')
        if shot.get('route') == 'shotcraft':
            for field in ('card', 'style_key'):
                if not nonempty(shot.get(field)):
                    fail(f'{label}.{field} is required for Shotcraft')
        if 'props' in shot and not isinstance(shot['props'], dict):
            fail(f'{label}.props must be an object')
        inputs = shot.get('inputs', [])
        if not (isinstance(inputs, list) and all(nonempty(v) for v in inputs)):
            fail(f'{label}.inputs must be an array of local paths')
        inner_cues = shot.get('inner_cues', {})
        if not (isinstance(inner_cues, dict) and all(isinstance(r, dict) for r in inner_cues.values())):
            fail(f'{label}.inner_cues must map names to time references')
        inner_frames = shot.get('inner_frames', {})
        if not (isinstance(inner_frames, dict) and all(integer(f) for f in inner_frames.values())):
            fail(f'{label}.inner_frames must map names to nonnegative local frames')
        start, duration = shot.get('from_frame'), shot.get('duration_frames')
        if not integer(start) or not integer(duration, 1):
            fail(f'{label}: from_frame/duration_frames must be nonnegative/positive integers')
        else:
            end = start + duration
            if integer(total, 1) and end > total:
                fail(f'{label}: shot extends beyond timeline')
            if shot.get('role') == 'background':
                backgrounds.append((start, end))
        asset = shot.get('asset')
        if asset is not None:
            if not isinstance(asset, dict):
                fail(f'{label}.asset must be an object')
            else:
                # A matching render_key proves the file still fits this shot, so it carries
                # across timeline revisions; without one the file binds to its revision.
                if 'render_key' not in asset:
                    if asset.get('timeline_revision') != revision:
                        fail(f'{label}.asset: stale timeline_revision')
                elif not (isinstance(asset['render_key'], dict) and nonempty(asset['render_key'].get('sha256'))
                          and isinstance(asset['render_key'].get('parts'), dict)):
                    fail(f'{label}.asset.render_key needs sha256 and parts (use plan_tools.py stamp)')
                elif isinstance(inputs, list) and all(nonempty(v) for v in inputs):
                    try:
                        state, reasons, _ = shot_state(plan, shot, root, exclude)
                    except (ValueError, OSError) as exc:
                        fail(f'{label}.inputs: {exc}')
                    else:
                        if state == 'stale':
                            fail(f'{label}.asset is stale, re-render: ' + '; '.join(reasons))
                if type(asset.get('alpha')) is not bool:
                    fail(f'{label}.asset.alpha must be boolean')
                if shot.get('role') == 'background' and asset.get('alpha') is True:
                    fail(f'{label}: background cannot be transparent')
        if ready:
            if shot.get('status') != 'verified':
                fail(f'{label}: shot is not verified')
            if not isinstance(asset, dict):
                fail(f'{label}: verified asset is required')
            else:
                file_check(asset.get('file'), f'{label}.asset.file')

    cursor = 0
    for start, end in sorted(backgrounds):
        if start < cursor:
            fail('background overlap: v1 supports hard cuts only')
        if not has_base and start > cursor:
            fail(f'background coverage gap: frames {cursor}..{start}')
        cursor = max(cursor, end)
    if not has_base and integer(total, 1) and cursor < total:
        fail(f'background coverage gap: frames {cursor}..{total}')

    sfx = plan.get('sfx', [])
    if not isinstance(sfx, list):
        return errors + ['sfx must be an array']
    sfx_ids, audible_shots = set(), set()
    for i, sound in enumerate(sfx):
        label = f'sfx[{i}]'
        if not isinstance(sound, dict):
            fail(f'{label} must be an object')
            continue
        sid = sound.get('id')
        if not nonempty(sid):
            fail(f'{label}.id must be nonempty')
        elif sid in sfx_ids:
            fail(f'duplicate sfx id: {sid}')
        else:
            sfx_ids.add(sid)
        shot_id = sound.get('shot_id')
        shot = ids.get(shot_id) if isinstance(shot_id, str) else None
        if shot is None:
            fail(f'{label}: unknown shot_id')
        else:
            audible_shots.add(shot_id)
            if shot.get('audio_policy') != 'separate':
                fail(f'{label}: sound attached to silent shot')
        if sound.get('timeline_revision') != revision:
            fail(f'{label}: stale timeline_revision')
        offset, duration = sound.get('offset_frames'), sound.get('duration_frames')
        if not integer(offset) or not integer(duration, 1):
            fail(f'{label}: invalid offset/duration')
        elif shot and integer(shot.get('duration_frames'), 1):
            if offset + duration > shot['duration_frames']:
                fail(f'{label}: sound extends beyond shot')
        gain = sound.get('gain')
        if type(gain) not in (int, float) or not 0 <= gain <= 4 or not math.isfinite(gain):
            fail(f'{label}.gain must be finite and in 0..4')
        if ready:
            file_check(sound.get('file'), f'{label}.file')
    for sid, shot in ids.items():
        if shot.get('audio_policy') == 'separate' and sid not in audible_shots:
            fail(f'{sid}: separate audio requested but no SFX provided')
    return errors


def export_manifest(plan, root, source_hash):
    manifest = json.loads(json.dumps(plan, ensure_ascii=False))
    manifest['source_plan_sha256'] = source_hash
    manifest['manifest_kind'] = 'vv-render-handoff-v1'
    fps = manifest['timeline']['fps']
    for key in ('narration', 'base_video'):
        item = manifest.get(key)
        if item and item.get('file'):
            item['file'] = str(local_path(root, item['file']))
    by_id = {s['id']: s for s in manifest['shots']}
    for shot in manifest['shots']:
        shot['start_seconds'] = shot['from_frame'] / fps
        shot['duration_seconds'] = shot['duration_frames'] / fps
        shot['asset']['file'] = str(local_path(root, shot['asset']['file']))
    for sound in manifest.get('sfx', []):
        sound['from_frame'] = by_id[sound['shot_id']]['from_frame'] + sound['offset_frames']
        sound['start_seconds'] = sound['from_frame'] / fps
        sound['duration_seconds'] = sound['duration_frames'] / fps
        sound['file'] = str(local_path(root, sound['file']))
    return manifest


def shots_by_id(plan):
    return {s['id']: s for s in plan.get('shots', []) if isinstance(s, dict) and nonempty(s.get('id'))}


def without_revision(item):
    if not isinstance(item, dict):
        return item
    return {k: v for k, v in item.items() if k != 'timeline_revision'}


def stale_report(plan, root):
    """Which shot files can be reused as they are and which need rendering."""
    exclude = asset_files(plan, root)
    rows = {'fresh': [], 'stale': [], 'needs_render': [], 'unstamped': []}
    for sid, shot in shots_by_id(plan).items():
        state, reasons, _ = shot_state(plan, shot, root, exclude)
        rows[state].append({'id': sid, 'reasons': reasons} if state == 'stale' else sid)
    return rows


def plan_diff(old, new, old_root, new_root):
    """Impact of going from one plan to the next: what to re-render, reuse, or only recomposite."""
    old_shots, new_shots = shots_by_id(old), shots_by_id(new)
    old_exclude, new_exclude = asset_files(old, old_root), asset_files(new, new_root)
    report = {'rerender': [], 'reuse_moved': [], 'unchanged': [], 'unverified': [],
              'added': [], 'removed': sorted(set(old_shots) - set(new_shots)), 'composite': []}
    for sid, shot in new_shots.items():
        prev = old_shots.get(sid)
        state, reasons, current = shot_state(new, shot, new_root, new_exclude)
        if prev is None:
            report['added'].append(sid)
            continue
        if state == 'unstamped':
            # No key from render time: compare plan fields only (file contents are today's on both sides).
            reasons = part_changes(render_parts(old, prev, old_root, old_exclude), current)
            state = 'stale' if reasons else 'unverified'
        if state in ('stale', 'needs_render'):
            report['rerender'].append({'id': sid, 'reasons': reasons})
            continue
        window = [prev.get('from_frame'), prev.get('duration_frames')]
        moved = window != [shot.get('from_frame'), shot.get('duration_frames')]
        if state == 'unverified':
            report['unverified'].append({'id': sid, 'moved': moved,
                                         'note': 'no render_key: source edits are invisible; confirm, or re-render and stamp'})
        elif moved:
            report['reuse_moved'].append({'id': sid, 'from': window,
                                          'to': [shot.get('from_frame'), shot.get('duration_frames')]})
        else:
            report['unchanged'].append(sid)
    for key in ('narration', 'base_video'):
        if without_revision(old.get(key)) != without_revision(new.get(key)):
            report['composite'].append(f'{key} changed')
    if (old.get('timeline') or {}).get('total_frames') != (new.get('timeline') or {}).get('total_frames'):
        report['composite'].append('total_frames changed')
    old_sfx = {s.get('id'): without_revision(s) for s in old.get('sfx', []) if isinstance(s, dict)}
    new_sfx = {s.get('id'): without_revision(s) for s in new.get('sfx', []) if isinstance(s, dict)}
    changed_sfx = sorted(str(k) for k in set(old_sfx) | set(new_sfx) if old_sfx.get(k) != new_sfx.get(k))
    if changed_sfx:
        report['composite'].append('sfx changed: ' + ', '.join(changed_sfx))
    report['recomposite'] = bool(report['rerender'] or report['reuse_moved'] or report['added']
                                 or report['removed'] or report['composite'] or report['unverified'])
    report['summary'] = (f"{len(report['rerender'])} re-render, {len(report['added'])} new, "
                         f"{len(report['reuse_moved'])} reuse (moved), {len(report['unchanged'])} unchanged, "
                         f"{len(report['unverified'])} unverified, {len(report['removed'])} removed")
    return report


def stamp_shots(plan, root, shot_ids):
    """Record the render key of freshly rendered shots; their files then carry across revisions."""
    shots, exclude = shots_by_id(plan), asset_files(plan, root)
    revision = (plan.get('timeline') or {}).get('revision')
    if not nonempty(revision):
        raise ValueError('timeline.revision must be nonempty')
    stamped = []
    for sid in shot_ids:
        shot = shots.get(sid)
        if shot is None:
            raise ValueError(f'unknown shot id: {sid}')
        if not isinstance(shot.get('asset'), dict):
            raise ValueError(f'{sid}: no asset to stamp; render the shot first')
        parts = render_parts(plan, shot, root, exclude)
        shot['asset']['render_key'] = {'sha256': render_key(parts), 'parts': parts}
        shot['asset']['timeline_revision'] = revision
        stamped.append({'id': sid, 'sha256': shot['asset']['render_key']['sha256'],
                        'inputs': len(parts['inputs'])})
    return stamped


def reject_constant(value):
    raise ValueError(f'non-finite JSON constant: {value}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('plan', type=Path)
    check.add_argument('--ready', action='store_true')
    export = sub.add_parser('export')
    export.add_argument('plan', type=Path)
    export.add_argument('--out', type=Path, required=True)
    diff = sub.add_parser('diff', help='impact of a plan revision: which shots to re-render or reuse')
    diff.add_argument('old', type=Path)
    diff.add_argument('plan', type=Path)
    stale = sub.add_parser('stale', help='which shot files still match their render inputs')
    stale.add_argument('plan', type=Path)
    stamp = sub.add_parser('stamp', help='record render keys after rendering shots')
    stamp.add_argument('plan', type=Path)
    stamp.add_argument('--shot', action='append', required=True)
    target = stamp.add_mutually_exclusive_group(required=True)
    target.add_argument('--out', type=Path)
    target.add_argument('--force', action='store_true', help='update the plan in place')
    args = parser.parse_args(argv)
    try:
        plan_path = args.plan.resolve()
        raw = plan_path.read_bytes()
        plan = json.loads(raw.decode('utf-8-sig'), parse_constant=reject_constant)
        if args.command == 'diff':
            old_path = args.old.resolve()
            old = json.loads(old_path.read_text(encoding='utf-8-sig'), parse_constant=reject_constant)
            result = plan_diff(old, plan, old_path.parent, plan_path.parent)
            print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'stale':
            print(json.dumps({'ok': True, **stale_report(plan, plan_path.parent)}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'stamp':
            stamped = stamp_shots(plan, plan_path.parent, args.shot)
            out = plan_path if args.force else args.out
            # --out creates a new file only; --force is the explicit in-place update.
            with out.open('w' if args.force else 'x', encoding='utf-8') as stream:
                json.dump(plan, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
            print(json.dumps({'ok': True, 'stamped': stamped, 'out': str(out)}, ensure_ascii=False, indent=2))
            return 0
        ready = args.command == 'export' or args.ready
        errors = validate(plan, plan_path.parent, ready)
        if errors:
            print(json.dumps({'ok': False, 'errors': errors}, ensure_ascii=False, indent=2))
            return 1
        if args.command == 'export':
            manifest = export_manifest(plan, plan_path.parent, hashlib.sha256(raw).hexdigest())
            # Exclusive creation: never replace an existing plan, manifest, or media file.
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
        print(json.dumps({'ok': True, 'stage': 'ready-structure' if ready else 'draft-structure',
                          'media_verified_by_tool': False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
