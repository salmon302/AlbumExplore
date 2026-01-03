#!/usr/bin/env python3
"""
Enrich the manual-review CSV with tag counts and current mapping info.

Reads:
 - `tag_analysis/manual_review_auto.csv`
 - `atomic_tags_export2.csv` (Tag,Count)
 - `src/albumexplore/config/tag_rules.json` (to see existing mappings)

Writes `tag_analysis/manual_review_auto_enriched.csv` with extra columns:
 original_count, suggestion_count, current_mapping
"""
import csv
import json
from pathlib import Path


ROOT = Path('.').resolve()
ATOMIC = ROOT / 'atomic_tags_export2.csv'
MANUAL = ROOT / 'tag_analysis' / 'manual_review_auto.csv'
OUT = ROOT / 'tag_analysis' / 'manual_review_auto_enriched.csv'
CONFIG = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'


def load_counts():
    counts = {}
    if not ATOMIC.exists():
        return counts
    with ATOMIC.open('r', encoding='utf-8') as f:
        # Skip header
        next(f)
        for line in f:
            parts = [p.strip().strip("'\"") for p in line.split(',')]
            if not parts:
                continue
            tag = parts[0]
            try:
                cnt = int(parts[1])
            except Exception:
                cnt = 0
            counts[tag.lower()] = cnt
    return counts


def load_current_mappings():
    if not CONFIG.exists():
        return {}
    j = json.loads(CONFIG.read_text(encoding='utf-8'))
    return j.get('single_instance_mappings', {})


def main():
    counts = load_counts()
    mappings = load_current_mappings()

    if not MANUAL.exists():
        print('Manual review CSV not found:', MANUAL)
        return 2

    with MANUAL.open('r', encoding='utf-8', newline='') as inf, OUT.open('w', encoding='utf-8', newline='') as outf:
        r = csv.DictReader(inf)
        fieldnames = r.fieldnames + ['original_count', 'suggestion_count', 'current_mapping']
        w = csv.DictWriter(outf, fieldnames=fieldnames)
        w.writeheader()
        for row in r:
            orig = row.get('original', '').lower().strip()
            sugg = row.get('suggestion', '').lower().strip()
            row['original_count'] = counts.get(orig, 0)
            row['suggestion_count'] = counts.get(sugg, 0)
            row['current_mapping'] = mappings.get(row.get('original'), '')
            w.writerow(row)

    print('Wrote enriched manual review CSV to', OUT)


if __name__ == '__main__':
    raise SystemExit(main())
