#!/usr/bin/env python3
"""Searchable index over external motion libraries (read-only references), queried in Chinese or English.

  fetch   download the read-only references into the refs dir (git clone + registry metadata; needs network)
  build   gongnyang/awesome-ai-motion index.json + HyperFrames registry item metadata  ->  motion-index.json
  search  Chinese or English keywords -> ranked effects, recipes, blocks and components
  show    one entry with its parameters, usage notes and local/online paths

Refs dir: env XUMU_REFS, else backends.local.json "refs", else <skills dir>/_refs.
Sources:
  gn:<slug>        gongnyang effect card (definition, conveys, use/avoid, params, HyperFrames notes)  MIT
  gn-recipe:<slug> gongnyang recipe (ordered effect sequence)                                          MIT
  hf:<name>        HyperFrames registry block/component (install into a HyperFrames project)          Apache-2.0
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

SKILL_ROOT = Path(__file__).resolve().parent.parent

PURPOSES = {'주목 끌기': '吸引注意', '설명': '解释', '비교': '对比', '순서·흐름': '顺序流程', '강조': '强调',
            '전환': '转场', '데이터 증명': '数据证据', '피드백': '反馈', '분위기': '氛围', '브랜딩': '品牌'}
MEDIA = {'설명 영상': '解说视频', '숏폼': '短视频', '스크롤덱': '滚动页', '발표': '演示', '제품 시연': '产品演示',
         '데이터 스토리': '数据故事', '웹 UI': '网页界面', '썸네일': '封面'}
FAMILIES = {'principles': '运动原理', 'entrance': '入场退场', 'emphasis': '强调', 'type': '文字', 'transitions': '转场',
            'camera': '镜头', 'data': '数据', 'ui': '界面', 'explainer': '解说图解', 'shape': '形状',
            'texture': '质感', 'generative': '生成艺术', 'depth': '空间纵深', 'loop': '循环', 'caption': '字幕'}

# Chinese query word -> terms that appear in the English/Korean source text and tags.
SYNONYMS = {
    '对比': ['compare', 'comparison', 'before', 'after', 'split', 'versus', '비교'],
    '前后': ['before', 'after', 'before-after'], '分屏': ['split', 'split-screen'],
    '因果': ['cause', 'flow', 'arrow', 'process', 'chain'], '流程': ['flow', 'flowchart', 'process', 'pipeline', 'step', 'steps', '순서·흐름'],
    '步骤': ['step', 'steps', 'stepper', 'walkthrough', 'sequence'], '顺序': ['sequence', 'stagger', 'order', '순서·흐름'],
    '列举': ['list', 'checklist', 'stagger', 'cascade'], '清单': ['checklist', 'list', 'check'],
    '数据': ['data', 'chart', 'stat', 'number', 'graph', '데이터 증명'], '数字': ['number', 'count', 'counter', 'stat', 'digits'],
    '图表': ['chart', 'graph', 'bar', 'line', 'pie', 'donut'], '增长': ['grow', 'rise', 'count-up', 'bar-grow', 'line'],
    '下降': ['decline', 'drop', 'fall'], '排名': ['rank', 'ranking', 'race'], '占比': ['pie', 'donut', 'percent', 'fraction', 'unit'],
    '地图': ['map', 'geography', 'route', 'globe', 'world'], '路线': ['route', 'path', 'map', 'flight', 'travel'],
    '时间线': ['timeline', 'chronology', 'date', 'history'], '历史': ['history', 'timeline', 'retro', 'archive', 'vintage'],
    '强调': ['emphasis', 'emphasize', 'highlight', 'accent', '강조'], '重点': ['highlight', 'emphasis', 'focus', 'spotlight'],
    '高亮': ['highlight', 'marker', 'sweep'], '标注': ['annotation', 'annotate', 'callout', 'label', 'arrow'],
    '圈注': ['circle', 'callout', 'circumscribe'], '箭头': ['arrow'], '下划线': ['underline', 'squiggle'],
    '手绘': ['hand-drawn', 'handwritten', 'hw', 'sketch', 'scribble', 'boil', 'whiteboard', 'marker', 'doodle'],
    '手写': ['handwriting', 'handwritten', 'write-on', 'write'], '白板': ['whiteboard', 'marker', 'hand-drawn', 'ink'],
    '涂鸦': ['scribble', 'doodle', 'sketch'], '粉笔': ['chalk', 'chalkboard'], '水墨': ['ink', 'ink-bleed', 'brush', 'fluid-ink'],
    '墨': ['ink'], '纸': ['paper', 'collage', 'papercut', 'page'], '拼贴': ['collage', 'cutout', 'scrapbook', 'sticker'],
    '剪纸': ['papercut', 'cutout', 'paper'], '撕纸': ['tear', 'torn', 'perforated'], '贴纸': ['sticker', 'badge', 'pop'],
    '标题': ['title', 'headline', 'titlecard', 'type'], '文字': ['text', 'type', 'typography', 'word', 'caption'],
    '大字': ['headline', 'kinetic', 'slam', 'giant', 'type'], '打字': ['typing', 'typewriter', 'typed'], '金句': ['quote', 'headline', 'kinetic'],
    '引用': ['quote', 'testimonial', 'source'], '字幕': ['caption', 'subtitle', 'karaoke', 'lower-third'],
    '人名条': ['lower-third'], '转场': ['transition', 'wipe', 'cut', '전환'], '擦除': ['wipe'], '遮罩': ['mask', 'reveal', 'iris'],
    '揭示': ['reveal', 'disclosure', 'unveil'], '入场': ['entrance', 'in', 'reveal', 'pop'], '退场': ['exit', 'out'],
    '镜头': ['camera', 'push', 'pan', 'zoom', 'dolly'], '推近': ['push-in', 'zoom', 'punch-in', 'zoom-to-detail'],
    '拉远': ['pull-back', 'unzoom', 'zoom-out'], '平移': ['pan', 'stations', 'slide'], '甩镜': ['whip', 'whip-pan'],
    '一镜到底': ['continuous', 'infinite-pan', 'one take', 'stations', 'camera-flight'], '视差': ['parallax', 'depth'],
    '纵深': ['depth', '3d', 'parallax'], '三维': ['3d', 'three', 'extrude', 'orbit', 'depth'], '立体': ['3d', 'extrude', 'extrusion'],
    '旋转': ['rotate', 'orbit', 'spin', 'turntable'], '爆炸图': ['exploded', 'layer-separation', 'assembly'],
    '等距': ['isometric'], '粒子': ['particle', 'particles'], '故障': ['glitch', 'datamosh', 'rgb'], '霓虹': ['neon', 'glow'],
    '复古': ['retro', 'vintage', 'vhs', 'crt', 'film', 'analog'], '老电视': ['crt', 'scanline', 'vhs', 'tv'],
    '胶片': ['film', 'grain', 'dust', 'gate', 'light-leak'], '颗粒': ['grain', 'noise', 'dither'], '网点': ['halftone', 'dither'],
    '像素': ['pixel', 'dither', 'pixelate', 'ascii'], '终端': ['terminal', 'code', 'ascii'], '代码': ['code', 'terminal', 'diff'],
    '界面': ['ui', 'mock-ui', 'app', 'screen', 'device'], '手机': ['phone', 'iphone', 'mobile', 'device'],
    '电脑': ['macbook', 'browser', 'desktop', 'device'], '光标': ['cursor', 'pointer'], '点击': ['click', 'tap', 'press', 'cursor'],
    '对话': ['chat', 'message', 'speech-bubble', 'conversation'], '气泡': ['bubble', 'speech-bubble'], '通知': ['notification', 'toast'],
    '社交': ['social', 'tiktok', 'instagram', 'x-post', 'reddit', 'comment'], '评论': ['comment', 'reddit', 'testimonial'],
    '角色': ['character', 'mascot', 'puppet', 'walk-cycle', 'articulation'], '人物': ['character', 'avatar', 'portrait'],
    '图标': ['icon'], '节拍': ['beat', 'rhythm', 'music'], '卡点': ['beat', 'cut'], '循环': ['loop'], '背景': ['background', 'ambient', 'gradient'],
    '渐变': ['gradient', 'mesh', 'aurora'], '光': ['light', 'glow', 'flare', 'rays', 'leak'], '玻璃': ['glass', 'liquid-glass', 'refraction'],
    '开场': ['intro', 'opener', 'hook', 'title', 'logo'], '钩子': ['hook', 'attention', '주목 끌기'], '结尾': ['outro', 'end-card', 'cta', 'close'],
    '章节': ['chapter', 'title-card', 'interstitial', 'section'], '解释': ['explainer', 'explain', '설명'], '原理': ['principle', 'explainer', 'mechanism'],
    'AI': ['ai', 'token', 'embedding', 'attention', 'chat'], '规模': ['scale', 'grid', 'unit', 'repeat', 'overwhelm'],
    '压力': ['overwhelm', 'pressure', 'pileup', 'surround'], '问题': ['problem', 'question'], '证据': ['proof', 'evidence', 'source', '데이터 증명'],
    '新闻': ['news', 'editorial', 'ticker', 'journalism'], '杂志': ['editorial', 'magazine'], '电影': ['cinematic', 'film', 'anamorphic'],
    '品牌': ['brand', 'logo', 'wordmark', '브랜딩'], '氛围': ['ambient', 'atmosphere', '분위기'], '数学': ['math', 'geometry', 'vector', 'fourier', 'plane'],
}

TOKEN = re.compile(r'[a-z0-9][a-z0-9\-]*|[ㄱ-힝]+|[一-鿿]+', re.I)


def refs_config():
    try:
        return json.loads((SKILL_ROOT / 'backends.local.json').read_text(encoding='utf-8')).get('refs', {})
    except (OSError, ValueError):
        return {}


REPOS = {'awesome-ai-motion': 'https://github.com/gongnyang/awesome-ai-motion.git',
         'bang-motion': 'https://github.com/bangtutorial/bang-motion.git'}
HF_RAW = 'https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry'


def refs_dir():
    if os.environ.get('XUMU_REFS'):
        return Path(os.environ['XUMU_REFS'])
    cfg = refs_config()
    if cfg.get('dir'):
        return Path(cfg['dir'])
    if cfg.get('gongnyang'):
        return Path(cfg['gongnyang']).parent
    return SKILL_ROOT.parent / '_refs'


def default_index_path():
    return Path(refs_config().get('motion_index') or refs_dir() / 'motion-index.json')


def source_paths():
    cfg, root = refs_config(), refs_dir()
    gn = Path(cfg['gongnyang']) if cfg.get('gongnyang') else root / 'awesome-ai-motion'
    hf = Path(cfg['hyperframes_registry']) if cfg.get('hyperframes_registry') else root / 'hyperframes-registry'
    return gn, hf


def fetch(root):
    """Shallow-clone the two reference repos and download HyperFrames registry item metadata (small JSON only)."""
    root.mkdir(parents=True, exist_ok=True)
    done = {}
    for name, url in REPOS.items():
        target = root / name
        if (target / '.git').exists():
            subprocess.run(['git', '-C', str(target), 'pull', '--ff-only', '-q'], check=True)
            done[name] = 'updated'
        else:
            subprocess.run(['git', 'clone', '--depth', '1', '-q', url, str(target)], check=True)
            done[name] = 'cloned'
    hf = root / 'hyperframes-registry'
    (hf / 'items').mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f'{HF_RAW}/registry.json', timeout=60) as r:
        registry = json.loads(r.read().decode('utf-8'))
    (hf / 'registry.json').write_text(json.dumps(registry, ensure_ascii=False), encoding='utf-8')
    folders = {'hyperframes:block': 'blocks', 'hyperframes:component': 'components'}
    wanted = [(folders[i['type']], i['name']) for i in registry.get('items', []) if i.get('type') in folders]

    def get(item):
        folder, name = item
        try:
            with urllib.request.urlopen(f'{HF_RAW}/{folder}/{name}/registry-item.json', timeout=60) as r:
                (hf / 'items' / f'{folder}_{name}.json').write_bytes(r.read())
            return None
        except OSError as exc:
            return f'{folder}/{name}: {exc}'

    with ThreadPoolExecutor(max_workers=16) as pool:
        failures = [f for f in pool.map(get, wanted) if f]
    done['hyperframes-registry'] = f'{len(wanted) - len(failures)}/{len(wanted)} items'
    return {'refs': str(root), 'sources': done, 'failures': failures[:10]}


def build(gn_root, hf_root):
    entries = []
    if gn_root:
        data = json.loads((gn_root / 'index.json').read_text(encoding='utf-8'))
        for e in data['effects']:
            card = gn_root / 'effects' / e['slug']
            clip = next((str(card / n) for n in ('clip.mp4', 'preview.gif') if (card / n).exists()), None)
            entries.append({
                'id': f'gn:{e["slug"]}', 'source': 'gongnyang', 'kind': 'effect',
                'name': e.get('en'), 'name_local': e.get('ko'), 'family': FAMILIES.get(e.get('family'), e.get('family')),
                'purposes': [PURPOSES.get(p, p) for p in e.get('purposes', [])],
                'media': [MEDIA.get(m, m) for m in e.get('media', [])],
                'tags': e.get('aka', []), 'summary': e.get('oneLiner'), 'conveys': e.get('conveys'),
                'use_when': e.get('useWhen', []), 'avoid': e.get('avoid', []), 'params': e.get('params', []),
                'ease': e.get('ease'), 'pairs_with': e.get('pairsWith', []),
                'hyperframes_note': (e.get('engines') or {}).get('hyperframes'),
                'doc': str(card / 'README.md'), 'clip': clip,
            })
        for r in data.get('recipes', []):
            slug = r.get('slug')
            entries.append({
                'id': f'gn-recipe:{slug}', 'source': 'gongnyang', 'kind': 'recipe',
                'name': r.get('en'), 'name_local': r.get('ko'),
                'summary': r.get('oneLinerEn') or r.get('oneLiner'), 'conveys': r.get('styleEn') or r.get('style'),
                'media': [MEDIA.get(m, m) for m in r.get('media', [])], 'duration': r.get('duration'),
                'steps': r.get('steps', []), 'avoid': r.get('avoid', []),
                'tags': [s.get('effect') for s in r.get('steps', []) if s.get('effect')],
                'doc': str(gn_root / 'recipes' / str(slug) / 'README.md'),
            })
    if hf_root:
        for path in sorted((hf_root / 'items').glob('*.json')):
            j = json.loads(path.read_text(encoding='utf-8'))
            folder = 'blocks' if j['type'].endswith('block') else 'components'
            entries.append({
                'id': f'hf:{j["name"]}', 'source': 'hyperframes', 'kind': folder[:-1],
                'name': j.get('title'), 'summary': j.get('description'), 'tags': j.get('tags', []),
                'controls': [c.get('name') for c in j.get('controls', []) if isinstance(c, dict)],
                'doc': f'https://github.com/heygen-com/hyperframes/tree/main/registry/{folder}/{j["name"]}',
            })
    return {'version': 1, 'counts': {s: sum(e['source'] == s for e in entries) for s in ('gongnyang', 'hyperframes')},
            'entries': entries}


def haystack(e):
    parts = [e['id'], e.get('name') or '', e.get('name_local') or '', e.get('family') or '', e.get('summary') or '',
             e.get('conveys') or '', ' '.join(e.get('tags', [])), ' '.join(e.get('purposes', [])),
             ' '.join(e.get('media', [])), ' '.join(e.get('use_when', []) if isinstance(e.get('use_when'), list) else [])]
    return ' '.join(parts).lower()


def expand(term):
    t = term.lower()
    out = {t}
    for zh, words in SYNONYMS.items():
        if zh.lower() == t or (len(t) > 1 and zh in term):
            out.update(w.lower() for w in words)
    return out


def search(index, terms, source=None, kind=None, limit=15):
    groups = [expand(t) for t in terms if t.strip()]
    rows = []
    for e in index['entries']:
        if source and e['source'] != source and not e['id'].startswith(source):
            continue
        if kind and e['kind'] != kind:
            continue
        text = haystack(e)
        tokens = set(TOKEN.findall(text))
        name = ((e.get('name') or '') + ' ' + e['id']).lower()
        purposes = set(e.get('purposes') or [])
        tags = ' '.join(e.get('tags', [])).lower()
        score, matched = 0.0, 0
        for group in groups:
            best, hits = 0.0, 0
            for w in group:
                if w in tokens or (len(w) > 3 and w in text):
                    hits += 1
                    weight = 3.0 if (w in name or w in purposes) else (2.0 if w in tags else 1.0)
                    best = max(best, weight)
            if best:
                matched += 1
                score += best + min(2.0, 0.5 * (hits - 1))   # several synonyms hit: more specific match
        if matched:
            score += 2.0 * (matched == len(groups))
            rows.append((score, e))
    rows.sort(key=lambda r: (-r[0], r[1]['id']))
    return [{'id': e['id'], 'score': s, 'kind': e['kind'], 'name': e.get('name'), 'family': e.get('family'),
             'purposes': e.get('purposes'), 'summary': (e.get('summary') or '')[:160]} for s, e in rows[:limit]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--index', type=Path, help='default: <refs dir>/motion-index.json')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--dest', type=Path, help='default: env XUMU_REFS or <skills dir>/_refs')
    p = sub.add_parser('build')
    p.add_argument('--gongnyang', type=Path)
    p.add_argument('--hyperframes', type=Path, help='dir with items/*.json (registry-item metadata)')
    p.add_argument('--force', action='store_true')
    p = sub.add_parser('search')
    p.add_argument('terms', nargs='+')
    p.add_argument('--source', choices=['gongnyang', 'hyperframes', 'gn', 'gn-recipe', 'hf'])
    p.add_argument('--kind', choices=['effect', 'recipe', 'block', 'component'])
    p.add_argument('--limit', type=int, default=15)
    p = sub.add_parser('show')
    p.add_argument('ids', nargs='+')
    args = parser.parse_args(argv)
    index_path = args.index or default_index_path()
    try:
        if args.command == 'fetch':
            result = fetch(args.dest or refs_dir())
        elif args.command == 'build':
            default_gn, default_hf = source_paths()
            gn = args.gongnyang or (default_gn if (default_gn / 'index.json').exists() else None)
            hf = args.hyperframes or (default_hf if (default_hf / 'items').is_dir() else None)
            if not gn and not hf:
                raise ValueError(f'no reference sources under {refs_dir()}; run: motion_index.py fetch')
            index = build(gn, hf)
            with index_path.open('w' if args.force else 'x', encoding='utf-8') as stream:
                json.dump(index, stream, ensure_ascii=False)
            result = {'index': str(index_path), 'counts': index['counts'], 'entries': len(index['entries'])}
        else:
            index = json.loads(index_path.read_text(encoding='utf-8'))
            if args.command == 'search':
                source = {'gn': 'gn:', 'gn-recipe': 'gn-recipe:', 'hf': 'hf:'}.get(args.source, args.source)
                result = {'results': search(index, args.terms, source, args.kind, args.limit)}
            else:
                by_id = {e['id']: e for e in index['entries']}
                missing = [i for i in args.ids if i not in by_id]
                if missing:
                    raise ValueError(f'unknown ids: {", ".join(missing)}')
                result = {'entries': [by_id[i] for i in args.ids]}
        print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
