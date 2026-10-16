"""Behavioral tests of media_tools deliver-check with mocked ffprobe output (no media files needed)."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import media_tools
from media_tools import deliver_check, main


def probe_json(width, height, fps='30/1', bitrate=17_000_000, duration=168.0, transfer='bt709', channels=2,
               rotation=None):
    video = {'codec_type': 'video', 'codec_name': 'h264', 'width': width, 'height': height,
             'avg_frame_rate': fps, 'r_frame_rate': fps, 'bit_rate': str(bitrate), 'color_transfer': transfer,
             'pix_fmt': 'yuv420p'}
    if rotation is not None:
        video['side_data_list'] = [{'side_data_type': 'Display Matrix', 'rotation': rotation}]
    streams = [video]
    if channels:
        streams.append({'codec_type': 'audio', 'codec_name': 'aac', 'channels': channels})
    return {'streams': streams, 'format': {'duration': str(duration), 'bit_rate': str(bitrate + 192_000)}}


SOURCE = probe_json(1080, 1920)
GOOD = probe_json(1080, 1920, bitrate=9_000_000, duration=104.0)
INCIDENT = probe_json(720, 1280, bitrate=2_100_000, duration=104.0)


def fake_probe(table):
    return lambda path: table[Path(path).name]


class DeliverCheckTests(unittest.TestCase):
    def test_full_size_deliverable_passes(self):
        report = deliver_check('final.mp4', 'source.mov', probe=fake_probe({'final.mp4': GOOD, 'source.mov': SOURCE}))
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['required_size'], '1080x1920')
        self.assertEqual(report['deliverable']['bitrate_mbps'], 9.0)
        self.assertEqual(report['deliverable']['audio_channels'], 2)
        self.assertTrue(any('duration' in w for w in report['warnings']))

    def test_720p_incident_fails(self):
        report = deliver_check('final.mp4', 'source.mov',
                               probe=fake_probe({'final.mp4': INCIDENT, 'source.mov': SOURCE}))
        self.assertFalse(report['ok'])
        self.assertTrue(any('resolution dropped' in e and '720x1280' in e for e in report['errors']))

    def test_spec_overrides_source(self):
        table = {'final.mp4': probe_json(1080, 1920), 'source.mov': probe_json(2160, 3840)}
        self.assertFalse(deliver_check('final.mp4', 'source.mov', probe=fake_probe(table))['ok'])
        self.assertTrue(deliver_check('final.mp4', 'source.mov', spec='1080x1920', probe=fake_probe(table))['ok'])

    def test_spec_without_source(self):
        report = deliver_check('final.mp4', spec='1080×1920', probe=fake_probe({'final.mp4': INCIDENT}))
        self.assertFalse(report['ok'])
        with self.assertRaises(ValueError):
            deliver_check('final.mp4', probe=fake_probe({'final.mp4': GOOD}))

    def test_rotation_metadata_is_applied(self):
        rotated = probe_json(1920, 1080, rotation=-90)
        report = deliver_check('final.mp4', 'source.mov', probe=fake_probe({'final.mp4': GOOD, 'source.mov': rotated}))
        self.assertTrue(report['ok'], report)
        self.assertEqual((report['source']['width'], report['source']['height']), (1080, 1920))

    def test_orientation_change_fails(self):
        report = deliver_check('final.mp4', 'source.mov',
                               probe=fake_probe({'final.mp4': probe_json(1920, 1080), 'source.mov': SOURCE}))
        self.assertTrue(any('orientation' in e for e in report['errors']))

    def test_draft_and_preview_names_fail(self):
        for name in ('成片_草稿.mp4', 'final_preview.mp4', 'cut-DRAFT.mp4', '预览.mp4'):
            report = deliver_check(name, 'source.mov', probe=fake_probe({name: GOOD, 'source.mov': SOURCE}))
            self.assertTrue(any('draft/preview' in e for e in report['errors']), name)

    def test_hdr_source_without_tone_mapping_warns(self):
        hdr = probe_json(1080, 1920, transfer='arib-std-b67')
        kept = deliver_check('final.mp4', 'source.mov',
                             probe=fake_probe({'final.mp4': probe_json(1080, 1920, transfer='arib-std-b67'),
                                               'source.mov': hdr}))
        self.assertTrue(kept['ok'])
        self.assertTrue(any('HDR' in w for w in kept['warnings']))
        mapped = deliver_check('final.mp4', 'source.mov', probe=fake_probe({'final.mp4': GOOD, 'source.mov': hdr}))
        self.assertFalse(any('HDR' in w for w in mapped['warnings']))

    def test_lower_fps_channels_and_starved_bitrate_warn(self):
        out = probe_json(1080, 1920, fps='25/1', bitrate=1_500_000, channels=1)
        report = deliver_check('final.mp4', 'source.mov', probe=fake_probe({'final.mp4': out, 'source.mov': SOURCE}))
        self.assertTrue(report['ok'])
        joined = ' '.join(report['warnings'])
        for needle in ('frame rate dropped', 'audio channels dropped', 'bits/pixel'):
            self.assertIn(needle, joined)

    def test_missing_audio_fails(self):
        report = deliver_check('final.mp4', 'source.mov',
                               probe=fake_probe({'final.mp4': probe_json(1080, 1920, channels=0), 'source.mov': SOURCE}))
        self.assertIn('deliverable has no audio track', report['errors'])


class DeliverCheckCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-media-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, final_probe, *extra):
        table = {'final.mp4': final_probe, 'source.mov': SOURCE}

        def fake_run(cmd, capture=False):
            return mock.Mock(stdout=json.dumps(table[Path(cmd[-1]).name]))

        buffer = io.StringIO()
        with mock.patch.object(media_tools, 'run', side_effect=fake_run), contextlib.redirect_stdout(buffer):
            code = main(['deliver-check', 'final.mp4', '--source', 'source.mov', *extra])
        return code, json.loads(buffer.getvalue())

    def test_exit_code_and_report_file(self):
        report_path = self.root / 'verify' / 'deliver_check.json'
        code, report = self.cli(INCIDENT, '--report', str(report_path))
        self.assertEqual(code, 1)
        self.assertFalse(report['ok'])
        self.assertEqual(json.loads(report_path.read_text(encoding='utf-8'))['errors'], report['errors'])
        code, _ = self.cli(GOOD, '--report', str(self.root / 'verify' / 'ok.json'))
        self.assertEqual(code, 0)

    def test_existing_report_needs_force(self):
        report_path = self.root / 'deliver_check.json'
        report_path.write_text('{}', encoding='utf-8')
        code, report = self.cli(GOOD, '--report', str(report_path))
        self.assertEqual(code, 1)
        self.assertIn('exists', report['errors'][0])


if __name__ == '__main__':
    unittest.main()
