"""Tests of hf_upgrade_check that need neither npm nor a render: early exit and report wording."""
from pathlib import Path
import tempfile
import unittest

from hf_upgrade_check import main, report_md


class UpgradeCheckTests(unittest.TestCase):
    def test_same_version_is_up_to_date_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'work'
            self.assertEqual(main(['--work', str(work), '--old', '1.0.0', '--new', '1.0.0']), 0)
            self.assertFalse(work.exists())

    def test_report_separates_regressions_from_known_issues(self):
        r = {'old': '1.0.0', 'new': '1.1.0', 'verdict': 'pass',
             'versions': {'1.0.0': {'check_rc': 1, 'render_rc': 0, 'render_seconds': 20, 'duration': 16.0, 'fps': 30.0,
                                    'audio': True},
                          '1.1.0': {'check_rc': 1, 'render_rc': 0, 'render_seconds': 21, 'duration': 16.0, 'fps': 30.0,
                                    'audio': True}},
             'ssim': {'frames': 480, 'mean': 0.999, 'min': 0.998, 'below_min': 0,
                      'worst': [{'frame': 134, 't': 4.433, 'ssim': 0.998}]},
             'problems': [], 'known_issues': ['check fails on both versions']}
        text = report_md(r)
        self.assertIn('结论：**pass**', text)
        self.assertIn('两个版本都有的已知问题', text)
        self.assertNotIn('升级带来的问题', text)
        self.assertIn('4.433s=0.998', text)


if __name__ == '__main__':
    unittest.main()
