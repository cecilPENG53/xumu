"""Behavioral tests of the timeline contract; synthetic files are not media QA."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from plan_tools import export_manifest, main, plan_diff, stale_report, stamp_shots, validate


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

    def test_engine_and_style_are_optional(self):
        self.assertNotIn('engine', self.plan['shots'][0])
        self.assertEqual(self.errors(True), [])

    def test_known_engine_and_style_pass_and_export(self):
        self.plan['shots'][0].update(engine='remotion', style='flat-diagram')
        self.assertEqual(self.errors(True), [])
        result = export_manifest(self.plan, self.root, 'test-sha')
        self.assertEqual(result['shots'][0]['engine'], 'remotion')
        self.assertEqual(result['shots'][0]['style'], 'flat-diagram')

    def test_unknown_engine_rejected(self):
        self.plan['shots'][0]['engine'] = 'after-effects'
        self.assertTrue(any('engine is unsupported' in e for e in self.errors()))

    def test_anchor_shape(self):
        self.plan['shots'][0]['anchor'] = {'start': {'cue': '分类'}, 'frames': 90}
        self.assertEqual(self.errors(True), [])
        self.plan['shots'][0]['anchor'] = {'start': {'cue': '分类'}}
        self.assertTrue(any('anchor' in e for e in self.errors()))

    def test_empty_style_rejected(self):
        self.plan['shots'][0]['style'] = ' '
        self.assertTrue(any('style must be nonempty' in e for e in self.errors()))

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


class RenderCacheTests(unittest.TestCase):
    """Render keys decide which shot files survive an edit; only re-rendered shots should change."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-cache-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        source = self.root / 'shots' / 's1'
        (source / 'node_modules').mkdir(parents=True)
        (source / 'scene.tsx').write_text('export const Scene = 1;', encoding='utf-8')
        (source / 'node_modules' / 'dep.js').write_text('v1', encoding='utf-8')
        # The rendered file sits inside the input folder on purpose: it must not count as input.
        (source / 'render.mp4').write_bytes(b'synthetic render')
        self.plan = example()
        shot = self.plan['shots'][0]
        shot.update(inputs=['shots/s1'], props={'title': '收集 → 分类'})
        shot['asset']['file'] = 'shots/s1/render.mp4'

    def stamped(self):
        stamp_shots(self.plan, self.root, ['s1'])
        return copy.deepcopy(self.plan)

    def test_stamped_asset_survives_revision_bump(self):
        self.stamped()
        self.plan['timeline']['revision'] = 'v2'
        self.plan['shots'][0]['timeline_revision'] = 'v2'
        self.assertEqual(validate(self.plan, self.root, True), [])
        self.assertEqual(stale_report(self.plan, self.root)['fresh'], ['s1'])

    def test_outputs_and_tool_folders_do_not_change_key(self):
        self.stamped()
        (self.root / 'shots' / 's1' / 'render.mp4').write_bytes(b're-encoded render')
        (self.root / 'shots' / 's1' / 'node_modules' / 'dep.js').write_text('v2', encoding='utf-8')
        self.assertEqual(stale_report(self.plan, self.root)['fresh'], ['s1'])

    def test_source_edit_makes_asset_stale(self):
        self.stamped()
        (self.root / 'shots' / 's1' / 'scene.tsx').write_text('export const Scene = 2;', encoding='utf-8')
        stale = stale_report(self.plan, self.root)['stale']
        self.assertEqual(stale, [{'id': 's1', 'reasons': ['input changed: shots/s1']}])
        self.assertTrue(any('stale, re-render' in e for e in validate(self.plan, self.root, True)))

    def test_props_and_inner_frames_are_render_inputs(self):
        self.stamped()
        self.plan['shots'][0]['props']['title'] = '收集 → 归档'
        self.plan['shots'][0]['inner_frames'] = {'hit': 12}
        reasons = stale_report(self.plan, self.root)['stale'][0]['reasons']
        self.assertEqual(reasons, ['props changed', 'inner_frames changed'])

    def test_missing_input_is_reported(self):
        self.stamped()
        self.plan['shots'][0]['inputs'] = ['shots/absent']
        self.assertTrue(any('input does not exist' in e for e in validate(self.plan, self.root)))

    def test_diff_separates_reuse_from_rerender(self):
        old = self.stamped()
        second = copy.deepcopy(old['shots'][0])
        second.update(id='s2', role='overlay', from_frame=10, duration_frames=45, inputs=[])
        second['asset'] = {'file': 'shots/s1/render.mp4', 'timeline_revision': 'v1', 'alpha': True}
        old['shots'].append(second)
        self.plan = old
        stamp_shots(self.plan, self.root, ['s2'])
        old = copy.deepcopy(self.plan)
        new = copy.deepcopy(old)
        new['shots'][0]['from_frame'] = 5                                   # moved, same length
        new['shots'][1]['duration_frames'] = 60                             # longer: render again
        new['shots'].append(dict(copy.deepcopy(second), id='s3'))
        new['sfx'] = [{'id': 'fx1', 'shot_id': 's1'}]
        report = plan_diff(old, new, self.root, self.root)
        self.assertEqual(report['reuse_moved'], [{'id': 's1', 'from': [0, 90], 'to': [5, 90]}])
        self.assertEqual(report['rerender'], [{'id': 's2', 'reasons': ['duration_frames: 45 -> 60']}])
        self.assertEqual(report['added'], ['s3'])
        self.assertEqual(report['composite'], ['sfx changed: fx1'])
        self.assertTrue(report['recomposite'])

    def test_diff_without_key_compares_plan_fields_only(self):
        old = copy.deepcopy(self.plan)
        new = copy.deepcopy(old)
        report = plan_diff(old, new, self.root, self.root)
        self.assertEqual(report['unverified'][0]['id'], 's1')
        self.assertTrue(report['recomposite'])
        new['shots'][0]['screen_text'] = '新文案'
        report = plan_diff(old, new, self.root, self.root)
        self.assertEqual(report['rerender'], [{'id': 's1', 'reasons': ['screen_text changed']}])

    def test_diff_of_identical_stamped_plans_needs_nothing(self):
        old = self.stamped()
        report = plan_diff(old, copy.deepcopy(old), self.root, self.root)
        self.assertEqual(report['unchanged'], ['s1'])
        self.assertFalse(report['recomposite'])

    def test_cli_stamp_needs_out_or_force(self):
        source, output = self.root / 'plan.json', self.root / 'stamped.json'
        source.write_text(json.dumps(self.plan, ensure_ascii=False), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['stamp', str(source), '--shot', 's1', '--out', str(output)]), 0)
            self.assertEqual(main(['stamp', str(source), '--shot', 's1', '--out', str(output)]), 1)
            self.assertNotIn('render_key', json.loads(source.read_text(encoding='utf-8'))['shots'][0]['asset'])
            self.assertEqual(main(['stamp', str(source), '--shot', 's1', '--force']), 0)
            self.assertEqual(main(['stamp', str(source), '--shot', 'absent', '--force']), 1)
        self.assertIn('render_key', json.loads(source.read_text(encoding='utf-8'))['shots'][0]['asset'])


if __name__ == '__main__':
    unittest.main()
