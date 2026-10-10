"""Behavioral tests of voice_edit (EDL + cues, without audio refinement) and cue (references, inserts, sync)."""
import json
from pathlib import Path
import tempfile
import unittest

from cue import Timing, sync_plan
from voice_edit import build_cues, build_edl


def words(*items):
    """items: (text, start, end) -> Scribe-style word list with spacing entries."""
    out = []
    for text, start, end in items:
        out.append({'text': text, 'start': start, 'end': end, 'type': 'word'})
        out.append({'text': ' ', 'start': end, 'end': end, 'type': 'spacing'})
    return out


class VoiceEditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-timing-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'transcripts').mkdir()
        transcript = words(('大家', 0.0, 0.4), ('好', 0.4, 0.6), ('今天', 2.0, 2.4), ('讲', 2.4, 2.6),
                           ('大家', 3.0, 3.4), ('好', 3.4, 3.6), ('结束', 5.0, 5.5))
        (self.root / 'transcripts' / 'a.json').write_text(json.dumps({'words': transcript}), encoding='utf-8')
        self.spec = {'sources': {'a': 'unused.mp4'},
                     'sections': [{'id': 'S1', 'source': 'a', 'keeps': [['大家', '讲']]},
                                  {'id': 'S2', 'source': 'a', 'keeps': [['大家', '结束']]}]}

    def edl(self, **kw):
        return build_edl(self.spec, self.root / 'transcripts', refine=False, **kw)

    def test_repeated_phrase_resolves_in_reading_order(self):
        edl, report = self.edl()
        self.assertEqual(report.splitlines()[0], 'S1: 大家好今天讲')
        self.assertTrue(report.endswith('S2: 大家好结束'))
        s2 = [s for s in edl['segments'] if s['section'] == 'S2']
        self.assertGreaterEqual(s2[0]['start'], 2.9)

    def test_long_pause_split_and_frame_aligned(self):
        edl, _ = self.edl()
        s1 = [s for s in edl['segments'] if s['section'] == 'S1']
        self.assertEqual(len(s1), 2)                           # 0.6 -> 2.0 gap exceeds 0.75 s
        for seg in edl['segments']:
            frames = (seg['end'] - seg['start']) * 30
            self.assertAlmostEqual(frames, round(frames), places=2)

    def test_force_seconds_override(self):
        self.spec['sections'][0]['keeps'] = [['大家', '讲', 0.05, 2.7]]
        edl, _ = self.edl()
        s1 = [s for s in edl['segments'] if s['section'] == 'S1']
        self.assertEqual(s1[0]['start'], 0.05)

    def test_missing_anchor_reports_section(self):
        self.spec['sections'][1]['keeps'] = [['不存在', '结束']]
        with self.assertRaisesRegex(ValueError, 'S2'):
            self.edl()

    def test_cues_follow_cut_timeline(self):
        edl, _ = self.edl()
        chars, sections = build_cues(edl, self.root / 'transcripts')
        self.assertEqual(''.join(c['c'] for c in chars), '大家好今天讲大家好结束')
        self.assertEqual(sections[0]['start'], 0)
        self.assertAlmostEqual(sections[1]['start'], sections[0]['end'])
        times = [c['t'] for c in chars]
        self.assertEqual(times, sorted(times))


class CueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-cue-test-')
        self.addCleanup(self.temp.cleanup)
        self.edit = Path(self.temp.name)
        chars = [{'sec': 'O1', 'c': c, 't': i * 0.5, 'e': i * 0.5 + 0.4} for i, c in enumerate('开场白。')]
        chars += [{'sec': 'B1', 'c': c, 't': 2.0 + i * 0.5, 'e': 2.4 + i * 0.5} for i, c in enumerate('看地图，再看地图')]
        sections = [{'id': 'O1', 'start': 0.0, 'end': 2.0}, {'id': 'B1', 'start': 2.0, 'end': 6.0}]
        (self.edit / 'cue_chars.json').write_text(json.dumps(chars, ensure_ascii=False), encoding='utf-8')
        (self.edit / 'sections.json').write_text(json.dumps(sections), encoding='utf-8')

    def timing(self, config=None):
        if config is not None:
            (self.edit / 'timing.json').write_text(json.dumps(config), encoding='utf-8')
        return Timing(self.edit)

    def test_cue_ignores_punctuation_and_scopes_section(self):
        t = self.timing()
        self.assertEqual(t.seconds({'cue': '看地图', 'section': 'B1'}), 2.0)
        self.assertEqual(t.seconds({'cue': '看地图', 'occurrence': 2}), 4.5)
        self.assertEqual(t.seconds({'cue': '地图', 'section': 'B1', 'edge': 'end'}), 3.4)

    def test_insert_shifts_later_references_only(self):
        t = self.timing({'fps': 30, 'inserts': [{'id': 'montage', 'after_section': 'O1', 'frames': 90}],
                         'tail_frames': 15})
        self.assertEqual(t.seconds({'cue': '开场'}), 0.0)
        self.assertEqual(t.seconds({'section': 'O1', 'edge': 'end'}), 2.0)
        self.assertEqual(t.seconds({'insert': 'montage'}), 2.0)
        self.assertEqual(t.seconds({'insert': 'montage', 'edge': 'end'}), 5.0)
        self.assertEqual(t.seconds({'cue': '看地图', 'offset': 0.5}), 5.5)
        self.assertAlmostEqual(t.total(), 9.5)

    def test_prefix_fallback_warns(self):
        t = self.timing()
        self.assertEqual(t.seconds({'cue': '看地铁'}), 2.0)
        self.assertTrue(t.warnings)

    def test_unknown_cue_raises(self):
        with self.assertRaises(ValueError):
            self.timing().seconds({'cue': '没有这句', 'section': 'O1'})

    def test_sync_moves_frames_and_downgrades_verified(self):
        plan = {'shots': [{'id': 's1', 'status': 'verified', 'from_frame': 0, 'duration_frames': 10,
                           'anchor': {'start': {'cue': '看地图'}, 'end': {'section': 'B1', 'edge': 'end'}}},
                          {'id': 's2', 'status': 'verified', 'from_frame': 0, 'duration_frames': 30}]}
        timing = self.timing({'fps': 30, 'inserts': [{'id': 'm', 'after_section': 'O1', 'frames': 30}]})
        new, changes = sync_plan(plan, timing)
        self.assertEqual(new['shots'][0]['from_frame'], 90)
        self.assertEqual(new['shots'][0]['duration_frames'], 120)
        self.assertEqual(new['shots'][0]['status'], 'rendered')
        self.assertEqual(new['shots'][1], plan['shots'][1])
        self.assertEqual([c['id'] for c in changes], ['s1'])
        self.assertEqual(plan['shots'][0]['from_frame'], 0)


if __name__ == '__main__':
    unittest.main()
