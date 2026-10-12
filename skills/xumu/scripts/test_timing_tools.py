"""Behavioral tests of voice_edit (EDL + cues, without audio refinement) and cue (references, inserts, sync)."""
import json
from pathlib import Path
import tempfile
import unittest

from cue import Timing, sync_plan
from voice_edit import build_cues, build_edl, listen_windows, parse_clock, split_silences


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
        self.assertIn('S2: 大家好结束', report.split('\n\n'))
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

    def stumble(self, transcript, keeps):
        (self.root / 'transcripts' / 'b.json').write_text(json.dumps({'words': transcript}), encoding='utf-8')
        spec = {'sources': {'b': 'unused.mp4'}, 'sections': [{'id': 'C1', 'source': 'b', 'keeps': keeps}]}
        return build_edl(spec, self.root / 'transcripts', refine=False)

    def test_drop_removes_voiced_false_start_inside_keep(self):
        transcript = words(('这一段', 0.0, 0.6), ('剪', 0.7, 0.85), ('剪辑', 1.1, 1.5), ('很快', 1.5, 1.9))
        edl, report = self.stumble(transcript, [{'from': '这一段', 'to': '很快', 'drop': [[0.66, 1.05]]}])
        segs = edl['segments']
        self.assertEqual([s['join'] for s in segs], ['section', 'drop'])
        self.assertLessEqual(segs[0]['end'], 0.66)              # never rounds up into the dropped sound
        self.assertEqual(segs[1]['start'], 1.05)
        self.assertIn('删去 0.66–1.05s：剪', report)              # whole word inside the drop
        chars, _ = build_cues(edl, self.root / 'transcripts')
        self.assertEqual(''.join(c['c'] for c in chars), '这一段剪辑很快')
        times = [c['t'] for c in chars]
        self.assertEqual(times, sorted(times))

    def test_drop_inside_merged_word_keeps_its_characters(self):
        # ASR merged the restart: one word "剪辑" spans the false start and the real one.
        transcript = words(('这一段', 0.0, 0.6), ('剪辑', 0.7, 1.6), ('很快', 1.6, 2.0))
        edl, _ = self.stumble(transcript, [{'from': '这一段', 'to': '很快', 'drop': [[0.66, 1.2]]}])
        chars, _ = build_cues(edl, self.root / 'transcripts')
        self.assertEqual(''.join(c['c'] for c in chars), '这一段剪辑很快')
        cut_start = next(c['t'] for c in chars if c['c'] == '剪')
        self.assertGreaterEqual(cut_start, edl['segments'][1]['start'] - edl['segments'][1]['start'])

    def test_drop_outside_keep_is_rejected(self):
        transcript = words(('这一段', 0.0, 0.6), ('很快', 0.7, 1.1))
        with self.assertRaisesRegex(ValueError, 'outside keep'):
            self.stumble(transcript, [{'from': '这一段', 'to': '很快', 'drop': [[5.0, 5.5]]}])

    def test_suspects_flag_repeats_long_syllables_and_fillers(self):
        transcript = words(('我们', 0.0, 0.4), ('我们', 0.45, 0.85), ('嗯', 0.9, 1.1), ('剪', 1.15, 1.3),
                           ('剪辑', 1.5, 1.9), ('段', 2.0, 2.6), ('结束', 2.65, 3.0))
        edl, report = self.stumble(transcript, [['我们', '结束']])
        kinds = {(f['kind'], f['context'].split('[')[1].split(']')[0]) for f in edl['suspects']}
        self.assertIn(('repeat', '我们我们'), kinds)
        self.assertIn(('repeat', '剪剪'), kinds)
        self.assertIn(('filler', '嗯'), kinds)
        self.assertIn(('long', '段'), kinds)
        self.assertIn('其他疑点', report)
        cut = [f['cut_t'] for f in edl['suspects']]
        self.assertEqual(cut, sorted(cut))

    def test_pause_folded_into_word_timing_is_split_from_audio(self):
        class Quiet:      # stands in for Audio: one 1.0 s silence inside, one at the span start
            def quiet_runs(self, name, t0, t1, frames):
                return [r for r in [(0.05, 0.9), (5.0, 6.0)] if r[0] >= t0 - 0.05 and r[1] <= t1 and
                        (r[1] - r[0]) * 100 >= frames]
        spans = split_silences(Quiet(), 'b', [(0.0, 10.0, 'section', None)], gap_max=0.75, pause_keep=0.45)
        self.assertEqual(len(spans), 2)
        self.assertAlmostEqual(spans[0][0], 0.84)                # leading silence trimmed, not split
        self.assertAlmostEqual(spans[0][1], 5.225)
        self.assertEqual(spans[1][2:], ('pause', 1.0))
        self.assertAlmostEqual(spans[1][0], 5.775)

    def test_natural_reduplication_is_not_flagged(self):
        transcript = words(('看', 0.0, 0.18), ('看', 0.19, 0.37), ('这个', 0.4, 0.8))
        edl, _ = self.stumble(transcript, [['看', '这个']])
        self.assertEqual([f for f in edl['suspects'] if f['kind'] == 'repeat'], [])

    def test_listen_windows_cover_edits_and_suspects_not_pause_joins(self):
        transcript = words(('这一段', 0.0, 0.6), ('剪', 0.7, 0.85), ('剪辑', 1.1, 1.5), ('很快', 1.5, 1.9),
                           ('然后', 4.0, 4.4), ('结束', 4.4, 4.8))
        edl, _ = self.stumble(transcript, [{'from': '这一段', 'to': '结束', 'drop': [[0.66, 1.05]]}])
        self.assertIn('pause', [s['join'] for s in edl['segments']])
        windows = listen_windows(edl, pad=0.3)
        reasons = ' '.join(r for w in windows for r in w['reasons'])
        self.assertIn('删片段', reasons)
        self.assertNotIn('缩停顿', reasons)
        self.assertIn('缩停顿', ' '.join(r for w in listen_windows(edl, pad=0.3, all_cuts=True) for r in w['reasons']))
        merged = listen_windows(edl, pad=5.0, at=[parse_clock('0:01')])
        self.assertEqual(len(merged), 1)                          # overlapping windows merge
        self.assertEqual(merged[0]['source']['source'], 'b')
        self.assertEqual(parse_clock('1:02.5'), 62.5)

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

    def test_single_character_cue(self):
        t = self.timing()
        self.assertEqual(t.seconds({'cue': '图', 'section': 'B1', 'occurrence': 2}), 5.5)
        self.assertFalse(t.warnings)

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
        self.assertEqual(changes[0]['kind'], 'retimed')
        self.assertEqual(plan['shots'][0]['from_frame'], 0)

    def test_sync_resolves_inner_cues_relative_to_shot(self):
        plan = {'shots': [{'id': 's1', 'status': 'verified', 'from_frame': 0, 'duration_frames': 10,
                           'anchor': {'start': {'cue': '看地图'}, 'frames': 120},
                           'inner_cues': {'second_map': {'cue': '看地图', 'occurrence': 2}}}]}
        new, changes = sync_plan(plan, self.timing())
        self.assertEqual(new['shots'][0]['from_frame'], 60)
        self.assertEqual(new['shots'][0]['inner_frames'], {'second_map': 75})
        # A cut that only shifts the whole shot keeps its inner frames, so the render key holds.
        timing = self.timing({'fps': 30, 'inserts': [{'id': 'm', 'after_section': 'O1', 'frames': 30}]})
        again, changes = sync_plan(new, timing)
        self.assertEqual(again['shots'][0]['from_frame'], 90)
        self.assertEqual(again['shots'][0]['inner_frames'], {'second_map': 75})
        self.assertEqual(changes[0]['kind'], 'moved')
        self.assertNotIn('inner_frames', changes[0])

    def test_sync_revision_moves_plan_not_media_bindings(self):
        plan = {'timeline': {'revision': 'r1'},
                'shots': [{'id': 's1', 'timeline_revision': 'r1',
                           'asset': {'file': 'a.mp4', 'timeline_revision': 'r1', 'alpha': False}}],
                'sfx': [{'id': 'fx', 'timeline_revision': 'r1'}]}
        new, changes = sync_plan(plan, self.timing(), revision='r2')
        self.assertEqual(new['timeline']['revision'], 'r2')
        self.assertEqual(new['shots'][0]['timeline_revision'], 'r2')
        self.assertEqual(new['sfx'][0]['timeline_revision'], 'r2')
        self.assertEqual(new['shots'][0]['asset']['timeline_revision'], 'r1')
        self.assertEqual(changes[-1]['revision'], {'from': 'r1', 'to': 'r2'})


if __name__ == '__main__':
    unittest.main()
