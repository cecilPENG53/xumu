#!/usr/bin/env python3
"""按用途和强度筛选定制 MG 灵感索引，只输出入围条目，避免整份读取。

用法：
  python mg_inspiration.py --use concept --use mechanism --max-energy 中等
  python mg_inspiration.py --slug gdgtify-929495
  python mg_inspiration.py --list-uses
"""
import argparse
import json
import sys
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "references" / "mg-inspiration-index.json"
ENERGY = ["克制", "中等", "强"]


def load(path=INDEX):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def select(data, uses=(), max_energy=None, slugs=(), limit=4):
    entries = data["entries"]
    if slugs:
        return [e for e in entries if e["slug"] in slugs]
    cap = ENERGY.index(max_energy) if max_energy else len(ENERGY) - 1
    out = []
    for e in entries:
        if ENERGY.index(e["energy"]) > cap:
            continue
        hits = len(set(uses) & set(e["vv_uses"])) if uses else 1
        if hits:
            out.append((hits, e))
    out.sort(key=lambda t: -t[0])  # stable: keeps index order within same score
    return [e for _, e in out[:limit]]


def fmt(e):
    lines = [
        f"## {e['slug']}  [{e['energy']} · {e['prompt_quality']}]  用途: {', '.join(e['vv_uses'])}",
        f"摘要: {e['summary_zh']}",
        f"借鉴: {e['borrow_zh']}",
    ]
    if e.get("caveats_zh"):
        lines.append(f"注意: {e['caveats_zh']}")
    lines.append(f"样片: {e['preview_url']}")
    lines.append(f"原文: {e['raw_prompt_url']}")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--use", action="append", default=[], help="用途标签，可重复")
    p.add_argument("--max-energy", choices=ENERGY, help="允许的最高强度")
    p.add_argument("--slug", action="append", default=[], help="按 slug 直接取")
    p.add_argument("--limit", type=int, default=4)
    p.add_argument("--list-uses", action="store_true", help="列出用途标签")
    p.add_argument("--index", default=str(INDEX))
    a = p.parse_args(argv)
    data = load(a.index)
    if a.list_uses:
        for k, v in data["use_tags"].items():
            print(f"{k}\t{v}")
        return 0
    unknown = set(a.use) - set(data["use_tags"])
    if unknown:
        print(f"未知用途标签: {', '.join(sorted(unknown))}；用 --list-uses 查看", file=sys.stderr)
        return 2
    res = select(data, a.use, a.max_energy, a.slug, a.limit)
    if not res:
        print("无匹配条目：按 directing.md 如实记录“无合适灵感参考”，直接按模板写 brief。")
        return 0
    print("\n\n".join(fmt(e) for e in res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
