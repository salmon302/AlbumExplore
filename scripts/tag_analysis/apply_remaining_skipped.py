#!/usr/bin/env python3
"""
Generate conservative manual mappings from `skipped_for_review.csv`, merge into
`manual_mappings.json`, apply them (via apply_manual_mappings.py), and validate.

Rules used:
- For `blocked-generic-target` or `skipped_reason_geo-strip`: preserve the original tag (map -> original).
- For `skipped_reason_enhanced-fallback`: apply curated typo correction from `typo_corrections.json` if present; otherwise preserve original.
- For `atomic-components-not-validated`: preserve original.

This script is conservative to avoid introducing generic mappings.
"""
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIPPED_CSV = ROOT / 'tag_analysis' / 'skipped_for_review.csv'
MANUAL = ROOT / 'tag_analysis' / 'manual_mappings.json'
TYPO_MAP = ROOT / 'tag_analysis' / 'typo_corrections.json'
APPLY_SCRIPT = ROOT / 'tag_analysis' / 'apply_manual_mappings.py'
VALIDATE_SCRIPT = ROOT / 'tag_analysis' / 'validate_normalization.py'
ATOMIC_CSV = ROOT / 'atomic_tags_export2.csv'


def load_json(p: Path):
    if not p.exists():
        return {}
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(p: Path, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    if not SKIPPED_CSV.exists():
        print('Skipped CSV not found:', SKIPPED_CSV)
        return 1

    typo_map = load_json(TYPO_MAP)
    typo_map = {k.strip().lower(): v.strip() for k, v in typo_map.items()} if typo_map else {}

    manual = load_json(MANUAL)
    manual = {k: v for k, v in manual.items()} if manual else {}

    new = {}
    with open(SKIPPED_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original = row.get('original', '').strip()
            reason = row.get('reason', '').strip()
            if not original:
                continue
            key = original
            if key in manual:
                continue

            key_l = key.lower()
            if reason.startswith('blocked-generic-target') or reason == 'skipped_reason_geo-strip':
                # preserve geo-qualified originals
                mapping = original
            elif reason == 'skipped_reason_enhanced-fallback':
                if key_l in typo_map:
                    mapping = typo_map[key_l]
                else:
                    mapping = original
            else:
                # atomic-components-not-validated and others -> preserve
                mapping = original

            new[key] = mapping

    if not new:
        print('No new manual mappings to add.')
        return 0

    # Merge into manual and save
    manual.update(new)
    save_json(MANUAL, manual)
    print(f'Added {len(new)} mappings to {MANUAL}')

    # Apply mappings (this will backup tag_rules.json)
    print('Applying manual mappings...')
    subprocess.check_call([str(Path().joinpath(ROOT, '.venv-1', 'Scripts', 'python.exe') )])
    # Instead, run using current python interpreter
    import sys
    subprocess.check_call([sys.executable, str(APPLY_SCRIPT)])

    # Run validation
    out_report = ROOT / 'tag_analysis' / f'normalization_validation_after_manual_round_2.json'
    subprocess.check_call([sys.executable, str(VALIDATE_SCRIPT), str(ATOMIC_CSV), str(out_report)])
    print('Validation written to:', out_report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
