#!/usr/bin/env python3
"""Resolve "which sentence / section + offset" time references into programme seconds and frames.

Reads from an edit directory:
  cue_chars.json  per-character times in the cut voice timeline   (voice_edit.py cues)
  sections.json   section spans in the cut voice timeline         (voice_edit.py cues)
  timing.json     optional: fps and material inserted between voice sections (openings, montages)

timing.json:
  {"fps": 30, "inserts": [{"id": "montage", "after_section": "O1", "frames": 588}], "tail_frames": 18}
An insert pushes every later voice moment back by its length, so references never need hand-shifting.

Reference forms (JSON objects; "offset" in seconds is optional everywhere):
  {"cue": "跟地图", "section": "B09"}            first char of the text, searched inside the section
  {"cue": "跟地图", "edge": "end", "occurrence": 2}  end of the last char; 2nd match
  {"section": "B02", "edge": "start" | "end"}
  {"insert": "montage", "edge": "start" | "end"}
  {"at": 0.0}                                     absolute programme seconds (titles, programme start)

Shots in visual-plan.json may carry  "anchor": {"start": <ref>, "end": <ref>}  or  {"start": <ref>, "frames": N};
`sync` recomputes from_frame / duration_frames from anchors after any re-edit.
Events inside a shot that follow words go in  "inner_cues": {"<name>": <ref>};  `sync` writes them as
"inner_frames" relative to the shot start, so the shot's code and its render key see the same numbers.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

PUNCT = set('，。？！、：；,.?!:;-—…（）()“”‘’"\' 「」《》')


class Timing:
    def __init__(self, edit_dir):
        edit_dir = Path(edit_dir)
        self.chars = json.loads((edit_dir / 'cue_chars.json').read_text(encoding='utf-8'))
        self.sections = {s['id']: s for s in json.loads((edit_dir / 'sections.json').read_text(encoding='utf-8'))}
        config_path = edit_dir / 'timing.json'
        config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
        self.fps = config.get('fps', 30)
        self.tail = config.get('tail_frames', 0) / self.fps
        self.inserts = []
        for item in config.get('inserts', []):
            if 'after_section' in item:
                position = self.sections[item['after_section']]['end']
            elif 'before_section' in item:
                position = self.sections[item['before_section']]['start']
            else:
                position = float(item['at_voice'])
            self.inserts.append({'id': item['id'], 'voice_at': position, 'seconds': item['frames'] / self.fps})
        self.inserts.sort(key=lambda i: i['voice_at'])
        self.index = [k for k, c in enumerate(self.chars) if c['c'] not in PUNCT]
        self.text = ''.join(self.chars[k]['c'] for k in self.index)
        self.warnings = []

    # ---------------------------------------------------------------- voice time -> programme time
    def programme(self, voice_t):
        shift = sum(i['seconds'] for i in self.inserts if voice_t >= i['voice_at'] - 1e-6)
        return voice_t + shift

    def voice_end(self):
        return max(s['end'] for s in self.sections.values())

    def total(self):
        """Programme length: voice end, plus inserts, plus the tail after the last word."""
        return self.programme(self.voice_end()) + self.tail

    # ---------------------------------------------------------------- references
    def _section_bounds(self, section):
        if section not in self.sections:
            raise ValueError(f'unknown section: {section}')
        positions = [n for n, k in enumerate(self.index) if self.chars[k]['sec'] == section]
        if not positions:
            raise ValueError(f'section has no characters: {section}')
        return positions[0], positions[-1] + 1

    def _find(self, text, section=None, occurrence=1):
        lo, hi = self._section_bounds(section) if section else (0, len(self.text))
        query = ''.join(c for c in text if c not in PUNCT)
        if not query:
            raise ValueError('empty cue text')
        # Prefix fallback stops at two characters; a one-character cue still matches exactly.
        for length in range(len(query), min(len(query), 2) - 1, -1):
            probe, start, hits = query[:length], lo, 0
            while True:
                i = self.text.find(probe, start, hi + length - 1)
                if i < 0 or i >= hi:
                    break
                hits += 1
                if hits == occurrence:
                    if length < len(query):
                        self.warnings.append(f'cue "{text}" matched only its prefix "{probe}"')
                    return i, i + length - 1
                start = i + 1
        where = f' in {section}' if section else ''
        raise ValueError(f'cue not found{where}: {text}')

    def seconds(self, ref):
        if not isinstance(ref, dict):
            raise ValueError(f'reference must be an object: {ref!r}')
        offset = float(ref.get('offset', 0.0))
        edge = ref.get('edge', 'start')
        if edge not in ('start', 'end'):
            raise ValueError(f'edge must be start or end: {ref!r}')
        if 'cue' in ref:
            first, last = self._find(ref['cue'], ref.get('section'), int(ref.get('occurrence', 1)))
            char = self.chars[self.index[first if edge == 'start' else last]]
            voice_t = char['t'] if edge == 'start' else char.get('e', char['t'])
            base = self.programme(voice_t)
        elif 'section' in ref:
            span = self.sections.get(ref['section'])
            if span is None:
                raise ValueError(f'unknown section: {ref["section"]}')
            base = self.programme(span[edge]) if edge == 'start' else self._end_before_inserts(span['end'])
        elif 'insert' in ref:
            base = self._insert_edge(ref['insert'], edge)
        elif 'at' in ref:
            base = float(ref['at'])
        else:
            raise ValueError(f'reference needs cue, section, insert or at: {ref!r}')
        return round(base + offset, 4)

    def _end_before_inserts(self, voice_t):
        """A section end stays before material inserted right after it."""
        shift = sum(i['seconds'] for i in self.inserts if voice_t > i['voice_at'] + 1e-6)
        return voice_t + shift

    def _insert_edge(self, insert_id, edge):
        for item in self.inserts:
            if item['id'] == insert_id:
                start = self._end_before_inserts(item['voice_at'])
                start += sum(i['seconds'] for i in self.inserts
                             if abs(i['voice_at'] - item['voice_at']) < 1e-6 and self.inserts.index(i) < self.inserts.index(item))
                return start if edge == 'start' else start + item['seconds']
        raise ValueError(f'unknown insert: {insert_id}')

    def frame(self, ref):
        return round(self.seconds(ref) * self.fps)


def sync_plan(plan, timing, revision=None):
    """Recompute frames for anchored shots and in-shot cue frames; changed verified shots drop to rendered.

    inner_cues ({name: ref}) become inner_frames ({name: frame relative to the shot start}), which the
    shot's code reads and the render key covers. With revision, the plan and its shots and sfx move to
    it; asset and narration bindings stay as they are, for plan_tools.py to judge.
    """
    plan = copy.deepcopy(plan)
    changes = []
    for shot in plan.get('shots', []):
        anchor, inner_cues = shot.get('anchor'), shot.get('inner_cues')
        if not anchor and not inner_cues:
            continue
        old = (shot.get('from_frame'), shot.get('duration_frames'))
        start, duration = old
        if anchor:
            start = timing.frame(anchor['start'])
            if 'end' in anchor:
                duration = timing.frame(anchor['end']) - start
            else:
                duration = int(anchor['frames'])
            if duration < 1:
                raise ValueError(f'{shot.get("id")}: anchor end is not after start')
        change = {'id': shot.get('id')}
        if old != (start, duration):
            shot['from_frame'], shot['duration_frames'] = start, duration
            change.update({'from': old, 'to': [start, duration],
                           'kind': 'moved' if old[1] == duration else 'retimed'})
        if inner_cues:
            inner = {name: timing.frame(ref) - start for name, ref in inner_cues.items()}
            for name, frame in inner.items():
                if not 0 <= frame <= duration:
                    timing.warnings.append(f'{shot.get("id")}: inner cue {name} falls outside the shot (local frame {frame})')
            if inner != shot.get('inner_frames'):
                change['inner_frames'] = {'from': shot.get('inner_frames'), 'to': inner}
                shot['inner_frames'] = inner
        if len(change) > 1:
            if shot.get('status') == 'verified':
                shot['status'] = 'rendered'
                change['status'] = 'verified -> rendered (re-check against the new window)'
            changes.append(change)
    if revision:
        timeline = plan.setdefault('timeline', {})
        changes.append({'revision': {'from': timeline.get('revision'), 'to': revision}})
        timeline['revision'] = revision
        for item in plan.get('shots', []) + plan.get('sfx', []):
            item['timeline_revision'] = revision
    return plan, changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--edit', type=Path, required=True, help='dir with cue_chars.json, sections.json, timing.json')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('resolve')
    p.add_argument('refs', nargs='+', help='JSON reference objects')
    sub.add_parser('sections')
    p = sub.add_parser('sync')
    p.add_argument('plan', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--revision', help='new timeline revision for the plan, its shots and sfx')
    args = parser.parse_args(argv)
    try:
        timing = Timing(args.edit)
        if args.command == 'resolve':
            rows = []
            for raw in args.refs:
                ref = json.loads(raw)
                rows.append({'ref': ref, 'seconds': timing.seconds(ref), 'frame': timing.frame(ref)})
            result = {'results': rows}
        elif args.command == 'sections':
            result = {'fps': timing.fps, 'total_seconds': round(timing.total(), 4),
                      'sections': [{'id': s, 'start': timing.seconds({'section': s}),
                                    'end': timing.seconds({'section': s, 'edge': 'end'})} for s in timing.sections],
                      'inserts': [{'id': i['id'], 'start': timing.seconds({'insert': i['id']}),
                                   'end': timing.seconds({'insert': i['id'], 'edge': 'end'})} for i in timing.inserts]}
        else:
            plan = json.loads(args.plan.read_text(encoding='utf-8-sig'))
            new_plan, changes = sync_plan(plan, timing, args.revision)
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(new_plan, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            result = {'changed': changes, 'out': str(args.out)}
        print(json.dumps({'ok': True, **result, 'warnings': timing.warnings}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
