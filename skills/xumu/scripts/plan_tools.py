#!/usr/bin/env python3
"""Offline timeline checks and non-destructive handoff export. No media rendering."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


ROUTES = ('real', 'shotcraft', 'mg', 'illustration', 'external', 'three')
STATES = ('planned', 'awaiting_approval', 'waiting_external', 'rendered', 'verified')


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def local_path(root, value):
    if not nonempty(value) or '://' in value or '\x00' in value:
        raise ValueError('expected a local file path, not a URL or empty value')
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


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
        if shot.get('route') == 'shotcraft':
            for field in ('card', 'style_key'):
                if not nonempty(shot.get(field)):
                    fail(f'{label}.{field} is required for Shotcraft')
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
                if asset.get('timeline_revision') != revision:
                    fail(f'{label}.asset: stale timeline_revision')
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
    args = parser.parse_args(argv)
    try:
        plan_path = args.plan.resolve()
        raw = plan_path.read_bytes()
        plan = json.loads(raw.decode('utf-8-sig'), parse_constant=reject_constant)
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
