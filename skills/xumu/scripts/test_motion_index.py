"""Behavioral tests of motion_index: mg-styles-15 prompt parsing, index build and Chinese search."""
from pathlib import Path
import tempfile
import unittest

from motion_index import build, search, split_title

PROMPT = '''# 测试贴纸风 2.5D Test Sticker / 2.5D

**原片**：示例片「一张贴纸」 · 1080×1920 · 30 fps · 10 秒 · AI 评审终评 7.50 / 10

## 提示词

```text
You are the director.

# Style
测试贴纸风 2.5D Test Sticker / 2.5D

# Output (fixed)
- 1080×1920, 30 fps, exactly 10.000 s, H.264 MP4 with stereo AAC audio (48 kHz), mastered to −14 LUFS integrated,
  true peak ≤ −1 dBTP. Final file: video.mp4.

# Suggested technical route
HTML: SVG stickers with a white outline on a large canvas
(You may choose a better route if it clearly raises quality; say why.)

# Creative seed
A sticker lands.

# Signature features and key techniques (the result is judged against these)
知识区常见的贴纸包装。
视觉特征 照片贴纸化, 冷静底色, 大画布运镜
关键技法 抠图后加 10px 白描边
镜头沿长缓动曲线平移

# How to work
1. Treatment.
```
'''


class SplitTitleTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(split_title('液态流动 Liquid Motion'), ('液态流动', 'Liquid Motion'))

    def test_bracket_and_latin_inside_chinese_name(self):
        self.assertEqual(split_title('复古系（80s Synthwave / Y2K 千禧） Retro: 80s Synthwave'),
                         ('复古系（80s Synthwave / Y2K 千禧）', 'Retro: 80s Synthwave'))

    def test_acronyms_repeated_in_english_stay_with_chinese(self):
        self.assertEqual(split_title('等轴 2.5D Isometric / 2.5D'), ('等轴 2.5D', 'Isometric / 2.5D'))
        self.assertEqual(split_title('赛博朋克 HUD / FUI Cyberpunk HUD / FUI (Fictional UI)'),
                         ('赛博朋克 HUD / FUI', 'Cyberpunk HUD / FUI (Fictional UI)'))

    def test_english_words_are_not_moved(self):
        self.assertEqual(split_title('线条动画 Line Art / Line Animation'), ('线条动画', 'Line Art / Line Animation'))


class Mg15IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xumu-mg15-test-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / 'prompts').mkdir()
        (root / 'prompts' / '99-sticker.md').write_text(PROMPT, encoding='utf-8')
        self.index = build(None, None, root)

    def test_entry_carries_signature_features_route_and_links(self):
        self.assertEqual(self.index['counts']['mg-styles-15'], 1)
        e = self.index['entries'][0]
        self.assertEqual(e['id'], 'mg15:99-sticker')
        self.assertEqual((e['name_local'], e['name']), ('测试贴纸风 2.5D', 'Test Sticker / 2.5D'))
        self.assertEqual(e['tags'], ['照片贴纸化', '冷静底色', '大画布运镜'])
        self.assertEqual(e['techniques'], ['抠图后加 10px 白描边', '镜头沿长缓动曲线平移'])
        self.assertEqual(e['summary'], '知识区常见的贴纸包装。')
        self.assertTrue(e['route'].startswith('HTML: SVG stickers'))
        self.assertNotIn('You may choose', e['route'])
        self.assertTrue(e['output'].startswith('1080×1920'))
        self.assertIn('1080×1920', e['film'])
        self.assertTrue(e['preview_url'].endswith('#99-sticker'))
        self.assertTrue(e['source_dir'].endswith('99-sticker'))

    def test_two_character_chinese_terms_match_inside_text(self):
        hits = search(self.index, ['贴纸'])
        self.assertEqual(hits[0]['id'], 'mg15:99-sticker')
        self.assertEqual(search(self.index, ['白描边'])[0]['id'], 'mg15:99-sticker')
        self.assertEqual(search(self.index, ['水墨']), [])


if __name__ == '__main__':
    unittest.main()
