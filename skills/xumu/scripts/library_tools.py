#!/usr/bin/env python3
"""Technique-card library: create, confirm, search and check cards. Text only, no media processing."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys


SKILL_ROOT = Path(__file__).resolve().parent.parent
KINDS = ('structure', 'edit', 'motion', 'style', 'type', 'sound', 'workflow')
STATUSES = ('draft', 'confirmed')
REQUIRED = ('id', 'name', 'status', 'kind', 'triggers', 'tags', 'sources', 'created', 'updated')
LIST_FIELDS = ('triggers', 'tags', 'engine', 'shotcraft', 'sources', 'media')
ID_PATTERN = re.compile(r'^L\d{4}$')

TEMPLATE = """---
id: {id}
name: {name}
status: draft
kind: {kind}
triggers: []
tags: []
style:
engine: []
shotcraft: []
sources: []
media: []
created: {today}
updated: {today}
---

## 一句话

## 适用 / 不适用

## 为什么有效

## 做法与参数

## 在序幕里怎么实现

## 原案例拆解

## 使用记录
"""


def parse_value(raw):
    raw = raw.strip()
    if raw.startswith('[') and raw.endswith(']'):
        return [item.strip() for item in raw[1:-1].split(',') if item.strip()]
    return raw


def read_card(path):
    text = path.read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise ValueError(f'{path.name}: missing frontmatter')
    meta = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            body = '\n'.join(lines[index + 1:])
            return meta, body
        if ':' in line:
            key, value = line.split(':', 1)
            meta[key.strip()] = parse_value(value)
    raise ValueError(f'{path.name}: unterminated frontmatter')


def write_meta(path, updates):
    """Rewrite only the given frontmatter keys, keeping every other line as written."""
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            break
        key = line.split(':', 1)[0].strip()
        if key in updates:
            lines[index] = f'{key}: {updates[key]}'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def card_files(library, include_inbox=False):
    folders = ['cards'] + (['inbox'] if include_inbox else [])
    files = []
    for folder in folders:
        directory = library / folder
        if directory.is_dir():
            files.extend(sorted(directory.glob('L*.md')))
    return files


def find_card(library, card_id):
    matches = [p for p in card_files(library, True) if p.name.split('-', 1)[0] == card_id]
    if not matches:
        raise ValueError(f'card not found: {card_id}')
    return matches[0]


def next_id(library):
    numbers = [int(p.name[1:5]) for p in card_files(library, True) if ID_PATTERN.match(p.name[:5])]
    return f'L{max(numbers, default=0) + 1:04d}'


def slugify(name):
    slug = re.sub(r'[\\/:*?"<>|\s]+', '-', name.strip()).strip('-')
    return slug[:40] or 'card'


def media_root():
    env = os.environ.get('XUMU_LIBRARY_MEDIA')
    if env:
        return Path(env)
    config = SKILL_ROOT / 'backends.local.json'
    try:
        value = json.loads(config.read_text(encoding='utf-8')).get('learning', {}).get('media_root')
    except (OSError, ValueError):
        return None
    return Path(value) if value else None


def score(meta, body, terms):
    total = 0.0
    fields = (('triggers', 3), ('tags', 2), ('style', 2), ('name', 1.5), ('kind', 1))
    for term in terms:
        for field, weight in fields:
            value = meta.get(field, '')
            values = value if isinstance(value, list) else [value]
            if any(term in v or v and v in term for v in values if v):
                total += weight
        if term in body:
            total += 0.5
    return total


def cmd_new(library, args):
    if args.kind not in KINDS:
        raise ValueError(f'kind must be one of {", ".join(KINDS)}')
    card_id = next_id(library)
    inbox = library / 'inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f'{card_id}-{slugify(args.name)}.md'
    with path.open('x', encoding='utf-8') as stream:
        stream.write(TEMPLATE.format(id=card_id, name=args.name.strip(), kind=args.kind,
                                     today=date.today().isoformat()))
    return {'ok': True, 'id': card_id, 'path': str(path)}


def cmd_confirm(library, args):
    path = find_card(library, args.id)
    if path.parent.name == 'cards':
        raise ValueError(f'{args.id} is already confirmed')
    errors = check_card(path, require_status=False)
    if errors:
        return {'ok': False, 'errors': errors}
    target = library / 'cards' / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError(f'target already exists: {target}')
    write_meta(path, {'status': 'confirmed', 'updated': date.today().isoformat()})
    path.replace(target)
    return {'ok': True, 'id': args.id, 'path': str(target)}


def cmd_search(library, args):
    terms = [t for t in re.split(r'[\s,，、]+', ' '.join(args.terms)) if t]
    results = []
    for path in card_files(library, args.include_inbox):
        meta, body = read_card(path)
        value = score(meta, body, terms)
        if value > 0:
            results.append({'id': meta.get('id'), 'name': meta.get('name'), 'score': value,
                            'status': meta.get('status'), 'kind': meta.get('kind'),
                            'triggers': meta.get('triggers'), 'style': meta.get('style'),
                            'path': str(path)})
    results.sort(key=lambda r: (-r['score'], r['id'] or ''))
    return {'ok': True, 'results': results[:args.limit]}


def cmd_list(library, args):
    cards = []
    for path in card_files(library, args.include_inbox):
        meta, _ = read_card(path)
        cards.append({'id': meta.get('id'), 'name': meta.get('name'), 'status': meta.get('status'),
                      'kind': meta.get('kind'), 'path': str(path)})
    return {'ok': True, 'cards': cards}


def check_card(path, require_status=True):
    errors = []
    try:
        meta, _ = read_card(path)
    except ValueError as exc:
        return [str(exc)]
    for field in REQUIRED:
        if field not in meta:
            errors.append(f'{path.name}: missing {field}')
    for field in LIST_FIELDS:
        if field in meta and not isinstance(meta[field], list):
            errors.append(f'{path.name}: {field} must be a [list]')
    card_id = meta.get('id', '')
    if not ID_PATTERN.match(str(card_id)) or not path.name.startswith(f'{card_id}-'):
        errors.append(f'{path.name}: id must be L#### and match the file name')
    if meta.get('kind') not in KINDS:
        errors.append(f'{path.name}: kind must be one of {", ".join(KINDS)}')
    if not meta.get('triggers'):
        errors.append(f'{path.name}: triggers must list at least one content feature')
    if not meta.get('sources'):
        errors.append(f'{path.name}: sources must not be empty')
    if require_status:
        expected = 'confirmed' if path.parent.name == 'cards' else 'draft'
        if meta.get('status') != expected:
            errors.append(f'{path.name}: status must be {expected} in {path.parent.name}/')
    root = media_root()
    if root is not None and root.is_dir():
        for item in meta.get('media', []) if isinstance(meta.get('media'), list) else []:
            if not (root / item).is_file():
                errors.append(f'{path.name}: media file missing: {item}')
    return errors


def cmd_check(library, args):
    errors, seen = [], {}
    for path in card_files(library, True):
        errors.extend(check_card(path))
        card_id = path.name.split('-', 1)[0]
        if card_id in seen:
            errors.append(f'duplicate id {card_id}: {seen[card_id]} and {path.name}')
        seen[card_id] = path.name
    return {'ok': not errors, 'cards': len(seen), 'errors': errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=SKILL_ROOT / 'library')
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('new')
    new.add_argument('--name', required=True)
    new.add_argument('--kind', required=True)
    confirm = sub.add_parser('confirm')
    confirm.add_argument('id')
    search = sub.add_parser('search')
    search.add_argument('terms', nargs='+')
    search.add_argument('--include-inbox', action='store_true')
    search.add_argument('--limit', type=int, default=10)
    listing = sub.add_parser('list')
    listing.add_argument('--include-inbox', action='store_true')
    sub.add_parser('check')
    args = parser.parse_args(argv)
    commands = {'new': cmd_new, 'confirm': cmd_confirm, 'search': cmd_search,
                'list': cmd_list, 'check': cmd_check}
    try:
        result = commands[args.command](args.library.resolve(), args)
    except (OSError, ValueError) as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
