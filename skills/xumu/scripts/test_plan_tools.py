"""Behavioral tests of the timeline contract; synthetic files are not media QA."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from plan_tools import export_manifest, main, validate


def example():
    return {
        'schema_version': 1,
        'input_mode': 'text',
        'timeline': {'revision': 'v1', 'locked': True, 'fps': 30,
                     'total_frames': 90, 'width': 1080, 'height': 1920},
        'narration': {'kind': 'none'},
        'shots': [{'id': 's1', 'timeline_revision': 'v1', 'role': 'background',
                   'route': 'mg', 'from_frame': 0, 'duration_frames': 90,
                   'purpose': 'Explain source aggregation', 'audio_policy': 'silent',
                   'status': 'verified',
                   'asset': {'file': '画面.bin', 'timeline_revision': 'v1', 'alpha': False}}],
        'sfx': [],
    }


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vv-narrative-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        # These are existence fixtures, deliberately not decodable video/audio.
        (self.root / '画面.bin').write_bytes(b'synthetic fixture')
        (self.root / '声音.bin').write_bytes(b'synthetic fixture')
        self.plan = example()

    def errors(self, ready=False):
        return validate(self.plan, self.root, ready)

    def test_complete_silent_text(self):
        self.assertEqual(self.errors(True), [])

    def test_audio_input_with_locked_narration(self):
        self.plan['input_mode'] = 'audio'
        self.plan['narration'] = {'kind': 'original', 'file': '声音.bin',
                                  'locked': True, 'timeline_revision': 'v1'}
        self.assertEqual(self.errors(True), [])

    def test_no_background_audio(self):
        self.plan['input_mode'] = 'audio'
        self.plan['shots'][0]['role'] = 'overlay'
        self.assertTrue(any('coverage gap' in e for e in self.errors()))

    def test_background_gap(self):
        self.plan['shots'][0]['from_frame'] = 1
        self.plan['shots'][0]['duration_frames'] = 89
        self.assertTrue(any('coverage gap' in e for e in self.errors()))

    def test_background_overlap(self):
        second = copy.deepcopy(self.plan['shots'][0])
        second.update(id='s2', from_frame=50, duration_frames=40)
        self.plan['shots'].append(second)
        self.assertTrue(any('overlap' in e for e in self.errors()))

    def test_overlay_overlap_is_allowed(self):
        second = copy.deepcopy(self.plan['shots'][0])
        second.update(id='s2', role='overlay', from_frame=50, duration_frames=40)
        second['asset']['alpha'] = True
        self.plan['shots'].append(second)
        self.assertEqual(self.errors(True), [])

    def test_video_base_allows_no_enhancement(self):
        self.plan['input_mode'] = 'video'
        self.plan['base_video'] = {'file': '画面.bin', 'timeline_revision': 'v1', 'verified': True}
        self.plan['shots'] = []
        self.assertEqual(self.errors(True), [])

    def test_audio_cannot_claim_video_base(self):
        self.plan['input_mode'] = 'audio'
        self.plan['base_video'] = {'file': '画面.bin', 'timeline_revision': 'v1', 'verified': True}
        self.assertTrue(self.errors(True))

    def test_stale_shot_and_asset(self):
        self.plan['timeline']['revision'] = 'v2'
        errors = self.errors(True)
        self.assertGreaterEqual(sum('stale' in e for e in errors), 2)

    def test_unlocked_narration_not_ready(self):
        self.plan['narration'] = {'kind': 'tts', 'file': '声音.bin',
                                  'timeline_revision': 'v1', 'locked': False}
        self.assertTrue(any('narration is not locked' in e for e in self.errors(True)))

    def test_missing_media(self):
        self.plan['shots'][0]['asset']['file'] = 'missing.mp4'
        self.assertEqual(self.errors(), [])
        self.assertTrue(any('file does not exist' in e for e in self.errors(True)))

    def test_waiting_external_not_ready(self):
        self.plan['shots'][0]['status'] = 'waiting_external'
        self.assertTrue(any('not verified' in e for e in self.errors(True)))

    def test_awaiting_approval_is_valid_draft_not_ready(self):
        self.plan['shots'][0]['status'] = 'awaiting_approval'
        self.assertEqual(self.errors(), [])
        self.assertTrue(any('not verified' in e for e in self.errors(True)))

    def test_extreme_gain_returns_error(self):
        self.sound()
        self.plan['sfx'][0]['gain'] = 10 ** 1000
        self.assertTrue(any('finite' in e for e in self.errors()))

    def test_shot_bounds(self):
        self.plan['shots'][0]['duration_frames'] = 91
        self.assertTrue(any('beyond timeline' in e for e in self.errors()))

    def test_frame_types(self):
        self.plan['shots'][0]['from_frame'] = True
        self.plan['timeline']['fps'] = 29.97
        self.assertGreaterEqual(len(self.errors()), 2)

    def test_duplicate_ids(self):
        second = copy.deepcopy(self.plan['shots'][0])
        second['role'] = 'overlay'
        self.plan['shots'].append(second)
        self.assertTrue(any('duplicate shot' in e for e in self.errors()))

    def test_shotcraft_requires_card_and_style(self):
        self.plan['shots'][0]['route'] = 'shotcraft'
        self.assertGreaterEqual(len(self.errors()), 2)

    def test_transparent_background_rejected(self):
        self.plan['shots'][0]['asset']['alpha'] = True
        self.assertTrue(any('transparent' in e for e in self.errors()))

    def sound(self):
        self.plan['shots'][0]['audio_policy'] = 'separate'
        self.plan['sfx'] = [{'id': 'fx1', 'shot_id': 's1', 'timeline_revision': 'v1',
                             'offset_frames': 30, 'duration_frames': 15,
                             'file': '声音.bin', 'gain': 0.5}]

    def test_sound_timing(self):
        self.sound()
        self.assertEqual(self.errors(True), [])
        result = export_manifest(self.plan, self.root, 'test-sha')
        self.assertEqual(result['sfx'][0]['from_frame'], 30)
        self.assertEqual(result['sfx'][0]['start_seconds'], 1)
        self.assertEqual(result['sfx'][0]['duration_seconds'], 0.5)

    def test_orphan_sound(self):
        self.sound()
        self.plan['sfx'][0]['shot_id'] = 'absent'
        self.assertTrue(any('unknown shot_id' in e for e in self.errors()))

    def test_sound_must_fit_shot(self):
        self.sound()
        self.plan['sfx'][0]['duration_frames'] = 61
        self.assertTrue(any('beyond shot' in e for e in self.errors()))

    def test_silent_shot_cannot_add_sound(self):
        self.sound()
        self.plan['shots'][0]['audio_policy'] = 'silent'
        self.assertTrue(any('silent shot' in e for e in self.errors()))

    def test_separate_sound_cannot_disappear(self):
        self.plan['shots'][0]['audio_policy'] = 'separate'
        self.assertTrue(any('no SFX' in e for e in self.errors()))

    def test_nonfinite_gain(self):
        self.sound()
        self.plan['sfx'][0]['gain'] = float('nan')
        self.assertTrue(any('finite' in e for e in self.errors()))

    def test_export_uses_plan_root_and_does_not_mutate(self):
        before = copy.deepcopy(self.plan)
        result = export_manifest(self.plan, self.root, 'test-sha')
        self.assertEqual(result['shots'][0]['asset']['file'], str((self.root / '画面.bin').resolve()))
        self.assertEqual(result['shots'][0]['duration_seconds'], 3)
        self.assertEqual(self.plan, before)

    def test_urls_not_ready(self):
        self.plan['shots'][0]['asset']['file'] = 'https://example.com/shot.mp4'
        self.assertTrue(any('local file' in e for e in self.errors(True)))

    def test_cli_export_refuses_overwrite(self):
        source, output = self.root / 'plan.json', self.root / 'out.json'
        source.write_text(json.dumps(self.plan, ensure_ascii=False), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['export', str(source), '--out', str(output)]), 0)
            before = output.read_bytes()
            self.assertEqual(main(['export', str(source), '--out', str(output)]), 1)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(main(['export', str(source), '--out', str(source)]), 1)
        self.assertEqual(json.loads(source.read_text(encoding='utf-8')), self.plan)

    def test_invalid_root_returns_diagnostic(self):
        self.assertTrue(validate([], self.root))
        self.plan['shots'][0]['route'] = []
        self.assertTrue(self.errors())

    def test_no_narration_cannot_reference_audio(self):
        self.plan['narration']['file'] = '声音.bin'
        self.assertTrue(self.errors(True))


if __name__ == '__main__':
    unittest.main()
