"""Behavioral tests of the technique-card library commands."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from library_tools import main


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-library-test-')
        self.addCleanup(self.temp.cleanup)
        self.library = Path(self.temp.name)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(['--library', str(self.library), *args])
        return code, json.loads(out.getvalue())

    def fill(self, path, triggers='[前后对比, 步骤流程]', tags='[擦除, 弹簧]'):
        text = path.read_text(encoding='utf-8')
        text = text.replace('triggers: []', f'triggers: {triggers}')
        text = text.replace('tags: []', f'tags: {tags}')
        text = text.replace('sources: []', 'sources: [https://example.com/case]')
        path.write_text(text, encoding='utf-8')

    def new_card(self, name='前后对比擦除', kind='motion'):
        code, result = self.run_cli('new', '--name', name, '--kind', kind)
        self.assertEqual(code, 0)
        return result['id'], Path(result['path'])

    def test_new_allocates_sequential_ids_in_inbox(self):
        first, path = self.new_card()
        second, _ = self.new_card('金句大字')
        self.assertEqual((first, second), ('L0001', 'L0002'))
        self.assertEqual(path.parent.name, 'inbox')

    def test_unknown_kind_rejected(self):
        code, result = self.run_cli('new', '--name', 'x', '--kind', 'magic')
        self.assertEqual(code, 1)

    def test_confirm_requires_triggers_and_sources(self):
        card_id, _ = self.new_card()
        code, result = self.run_cli('confirm', card_id)
        self.assertEqual(code, 1)
        self.assertTrue(any('triggers' in e for e in result['errors']))

    def test_confirm_moves_card_and_sets_status(self):
        card_id, path = self.new_card()
        self.fill(path)
        code, result = self.run_cli('confirm', card_id)
        self.assertEqual(code, 0)
        target = Path(result['path'])
        self.assertEqual(target.parent.name, 'cards')
        self.assertFalse(path.exists())
        self.assertIn('status: confirmed', target.read_text(encoding='utf-8'))
        self.assertEqual(self.run_cli('check')[0], 0)

    def test_search_ignores_inbox_by_default_and_ranks_triggers(self):
        draft_id, draft = self.new_card()
        self.fill(draft)
        kept_id, kept = self.new_card('数据跳变')
        self.fill(kept, triggers='[数据跳变]', tags='[前后对比]')
        self.run_cli('confirm', kept_id)
        _, result = self.run_cli('search', '前后对比')
        self.assertEqual([r['id'] for r in result['results']], [kept_id])
        _, result = self.run_cli('search', '前后对比', '--include-inbox')
        self.assertEqual(result['results'][0]['id'], draft_id)

    def test_check_flags_status_mismatch(self):
        card_id, path = self.new_card()
        self.fill(path)
        text = path.read_text(encoding='utf-8').replace('status: draft', 'status: confirmed')
        path.write_text(text, encoding='utf-8')
        code, result = self.run_cli('check')
        self.assertEqual(code, 1)
        self.assertTrue(any('status must be draft' in e for e in result['errors']))


if __name__ == '__main__':
    unittest.main()
