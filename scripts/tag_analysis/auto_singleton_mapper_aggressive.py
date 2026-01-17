#!/usr/bin/env python3
"""
Aggressive singleton mapper: builds on `auto_singleton_mapper.py` but
also suggests mapping singletons to a single atomic component when safe
and can optionally strip geographic qualifiers more aggressively.

Usage:
  python -m tag_analysis.auto_singleton_mapper_aggressive [csv] [out_json]

This script is intentionally more aggressive and should be used with
care; always run validation after applying results.
"""
import argparse
import json
from pathlib import Path
from albumexplore.tags.normalizer.enhanced_normalizer import EnhancedTagNormalizer
from albumexplore.tags.config.tag_rules_config import TagRulesConfig
import pandas as pd
import re

GEOGRAPHIC_QUALIFIERS = {
    'african', 'american', 'british', 'french', 'german', 'italian', 'japanese',
    'korean', 'nordic', 'eastern', 'western', 'southern', 'northern', 'uk', 'us',
    'celtic', 'irish', 'scottish', 'welsh', 'gaelic', 'oriental', 'middle-eastern',
}


def strip_geographic(tag: str, aggressive: bool = False) -> str:
    parts = tag.split()
    if aggressive:
        # also drop common single-country qualifiers like 'brazil', 'persian', etc.
        extras = {'brazil', 'persian', 'latin', 'french', 'spanish'}
    else:
        extras = set()
    filtered = [p for p in parts if p.lower() not in GEOGRAPHIC_QUALIFIERS and p.lower() not in extras]
    return ' '.join(filtered).strip()


def re_split(tag: str):
    for sep in ['/', '-', ' ']:
        if sep in tag:
            return [p.strip() for p in tag.split(sep) if p.strip()]
    return [tag]


def suggest_for_tag(tag: str, normalizer: EnhancedTagNormalizer, rules: TagRulesConfig, aggressive_geo: bool, allow_single_atomic: bool):
    original = tag
    normalized_enh = normalizer.normalize_enhanced(tag)

    # 1) If enhanced normalization yields an existing mapped form, prefer it
    mapped = rules.get_normalized_form(normalized_enh)
    if mapped and mapped != normalized_enh:
        return mapped, 'rules-mapped-after-enhanced'

    # 2) Atomic decomposition
    atomic_components = normalizer.normalize_to_atomic(normalized_enh)
    if len(atomic_components) > 1:
        candidate = ' '.join(atomic_components)
        return candidate, 'atomic-decompose'

    # Aggressive: if decomposition yields a single known atomic token, map to it
    if allow_single_atomic and len(atomic_components) == 1:
        candidate = atomic_components[0]
        mapped_single = rules.get_normalized_form(candidate)
        # If the single component is a known canonical (or maps to one), suggest it
        if mapped_single:
            return mapped_single, 'single-atomic-component'
        # else still propose the single component as candidate
        return candidate, 'single-atomic-component'

    # 3) Try removing geographic qualifiers and re-normalize
    stripped = strip_geographic(normalized_enh, aggressive=aggressive_geo)
    if stripped and stripped != normalized_enh:
        mapped2 = rules.get_normalized_form(stripped)
        if mapped2 and mapped2 != stripped:
            return mapped2, 'geo-strip-and-map'
        if stripped != normalized_enh:
            return stripped, 'geo-strip'

    # 4) Split compounds and prefer known primary genres
    parts = [p for p in re_split(normalized_enh) if p]
    for p in parts:
        mapped_part = rules.get_normalized_form(p)
        if mapped_part and mapped_part != p:
            return mapped_part, f'component-map:{p}'

    # 5) Fallback
    if normalized_enh != original.lower().strip():
        return normalized_enh, 'enhanced-fallback'

    return None, 'no-suggestion'


def analyze_singletons(csv_path: Path, out_json: Path, aggressive_geo: bool, allow_single_atomic: bool):
    df = pd.read_csv(csv_path)
    singletons = df[df['Count'] == 1]['Tag'].astype(str).tolist()

    normalizer = EnhancedTagNormalizer()
    rules = TagRulesConfig()

    suggestions = {}
    stats = {'total_singletons': len(singletons), 'suggested': 0}

    for tag in singletons:
        suggestion, reason = suggest_for_tag(tag, normalizer, rules, aggressive_geo, allow_single_atomic)
        if suggestion:
            suggestions[tag] = {'suggestion': suggestion, 'reason': reason}
            stats['suggested'] += 1

    output = {'stats': stats, 'suggestions': suggestions}

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Analyzed {stats['total_singletons']} singletons; suggestions for {stats['suggested']}")
    print(f"Wrote suggestions to: {out_json}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', nargs='?', default='atomic_tags_export2.csv')
    parser.add_argument('out', nargs='?', default='tag_analysis/singleton_suggestions.json')
    parser.add_argument('--aggressive-geo', action='store_true', help='Drop additional geographic qualifiers')
    parser.add_argument('--no-single-atomic', action='store_true', help="Don't suggest mapping to a single atomic component")

    args = parser.parse_args()
    csv_path = Path(args.csv)
    out_json = Path(args.out)
    aggressive_geo = bool(args.aggressive_geo)
    allow_single_atomic = not args.no_single_atomic

    analyze_singletons(csv_path, out_json, aggressive_geo, allow_single_atomic)


if __name__ == '__main__':
    main()
