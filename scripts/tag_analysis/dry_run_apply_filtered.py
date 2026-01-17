#!/usr/bin/env python3
"""
Dry-run preview of applying `singleton_suggestions_filtered.json`.

This script loads the filtered suggestions and the current
`src/albumexplore/config/tag_rules.json` and prints a compact report
showing which mappings would be added and which existing mappings
would be overwritten.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
FILTERED_PATH = ROOT / 'tag_analysis' / 'singleton_suggestions_filtered.json'
FALLBACK_PATH = ROOT / 'tag_analysis' / 'singleton_suggestions.json'


def load_json(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    if FILTERED_PATH.exists():
        suggestions_file = FILTERED_PATH
    elif FALLBACK_PATH.exists():
        suggestions_file = FALLBACK_PATH
    else:
        print('No suggestions file found (filtered or fallback).')
        return 2

    suggestions_blob = load_json(suggestions_file)
    suggestions = suggestions_blob.get('suggestions', {})

    config = load_json(CONFIG_PATH)
    mappings = config.get('single_instance_mappings', {})

    total = suggestions_blob.get('stats', {}).get('total_singletons', None)
    suggested_count = len(suggestions)

    # Compute non-trivial suggestions and conflicts
    non_trivial = []
    overwrites = []
    for original, info in sorted(suggestions.items()):
        suggestion = info.get('suggestion')
        if not suggestion or suggestion == original:
            continue
        existing = mappings.get(original)
        non_trivial.append((original, suggestion, existing))
        if existing is not None and existing != suggestion:
            overwrites.append((original, existing, suggestion))

    print('Suggestions file:', suggestions_file)
    if total is not None:
        print('Total singletons in input:', total)
    print('Total suggestions present:', suggested_count)
    print('Non-trivial suggestions to apply:', len(non_trivial))
    print('Existing mappings that would be overwritten:', len(overwrites))
    print('')

    if overwrites:
        print('Overwrites (existing -> new):')
        for orig, before, after in overwrites:
            print(f'  {orig!r}: {before!r} -> {after!r}')
        print('')

    print('Mappings (original -> suggestion)')
    for orig, sugg, existing in non_trivial:
        note = ''
        if existing is not None:
            note = f'  [will overwrite existing {existing!r}]'
        print(f'  {orig!r} -> {sugg!r}{note}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
