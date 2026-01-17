#!/usr/bin/env python3
"""
Analyze single-instance tags and suggest aggressive normalizations.

Produces a `singleton_suggestions.json` file with suggested mappings and a short report.
Uses `EnhancedTagNormalizer` where available and falls back to `TagNormalizer` heuristics.
"""
import json
from pathlib import Path
import pandas as pd
from albumexplore.tags.normalizer.enhanced_normalizer import EnhancedTagNormalizer
from albumexplore.tags.config.tag_rules_config import TagRulesConfig
import re


GEOGRAPHIC_QUALIFIERS = {
    'african', 'american', 'british', 'french', 'german', 'italian', 'japanese',
    'korean', 'nordic', 'eastern', 'western', 'southern', 'northern', 'uk', 'us',
    'celtic', 'irish', 'scottish', 'welsh', 'gaelic', 'oriental', 'middle-eastern',
}


def strip_geographic(tag: str) -> str:
    parts = tag.split()
    filtered = [p for p in parts if p.lower() not in GEOGRAPHIC_QUALIFIERS]
    return ' '.join(filtered).strip()


def suggest_for_tag(tag: str, normalizer: EnhancedTagNormalizer, rules: TagRulesConfig):
    """Return a suggested normalized form and reason for a single tag."""
    original = tag
    normalized_enh = normalizer.normalize_enhanced(tag)

    # 1) If enhanced normalization yields an existing mapped form, prefer it
    mapped = rules.get_normalized_form(normalized_enh)
    if mapped and mapped != normalized_enh:
        return mapped, 'rules-mapped-after-enhanced'

    # 2) If enhanced normalization reduces to a known atomic decomposition, prefer decomposition
    atomic_components = normalizer.normalize_to_atomic(normalized_enh)
    # If decomposition yields multiple atomic tokens, propose the joined canonical
    if len(atomic_components) > 1:
        candidate = ' '.join(atomic_components)
        return candidate, 'atomic-decompose'

    # 3) Try removing geographic qualifiers and re-normalize
    stripped = strip_geographic(normalized_enh)
    if stripped and stripped != normalized_enh:
        mapped2 = rules.get_normalized_form(stripped)
        if mapped2 and mapped2 != stripped:
            return mapped2, 'geo-strip-and-map'
        if stripped != normalized_enh:
            return stripped, 'geo-strip'

    # 4) Split compounds and prefer known primary genres
    parts = [p for p in re_split(normalized_enh) if p]
    for p in parts:
        # If any part maps to a normalized form, suggest that
        mapped_part = rules.get_normalized_form(p)
        if mapped_part and mapped_part != p:
            return mapped_part, f'component-map:{p}'

    # 5) Fallback to enhanced normalized form if different
    if normalized_enh != original.lower().strip():
        return normalized_enh, 'enhanced-fallback'

    # No suggestion
    return None, 'no-suggestion'


def re_split(tag: str):
    # simple split by hyphen/space/slash
    for sep in ['/', '-', ' ']:
        if sep in tag:
            return [p.strip() for p in tag.split(sep) if p.strip()]
    return [tag]


def analyze_singletons(csv_path: Path, out_json: Path):
    df = pd.read_csv(csv_path)
    singletons = df[df['Count'] == 1]['Tag'].astype(str).tolist()

    normalizer = EnhancedTagNormalizer()
    rules = TagRulesConfig()

    suggestions = {}
    stats = {'total_singletons': len(singletons), 'suggested': 0}

    for tag in singletons:
        suggestion, reason = suggest_for_tag(tag, normalizer, rules)
        if suggestion:
            suggestions[tag] = {'suggestion': suggestion, 'reason': reason}
            stats['suggested'] += 1

    output = {'stats': stats, 'suggestions': suggestions}

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Analyzed {stats['total_singletons']} singletons; suggestions for {stats['suggested']}")
    print(f"Wrote suggestions to: {out_json}")


if __name__ == '__main__':
    import sys
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('atomic_tags_export2.csv')
    out_json = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('tag_analysis/singleton_suggestions.json')

    analyze_singletons(csv_path, out_json)
