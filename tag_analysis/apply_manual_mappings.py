#!/usr/bin/env python3
"""
Apply manual mappings from `tag_analysis/manual_mappings.json` into
`src/albumexplore/config/tag_rules.json` with a timestamped backup.

Produces a small report JSON in `tag_analysis/manual_apply_report_*.json`.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / 'tag_analysis' / 'manual_mappings.json'
CONFIG = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
OUT_DIR = ROOT / 'tag_analysis'


def load_json(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(p: Path, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def backup_config():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / f'tag_rules_backup_manual_apply_{ts}.json'
    shutil.copy(CONFIG, backup)
    return backup


def main():
    if not MANUAL.exists():
        print('Manual mappings file not found:', MANUAL)
        return 1
    manual = load_json(MANUAL)
    config = load_json(CONFIG)

    if 'single_instance_mappings' not in config:
        config['single_instance_mappings'] = {}

    before = dict(config['single_instance_mappings'])
    before_count = len(before)

    # Merge manual mappings (overwrite any existing mapping)
    config['single_instance_mappings'].update(manual)

    backup = backup_config()
    save_json(CONFIG, config)

    after_count = len(config['single_instance_mappings'])

    report = {
        'backup': str(backup),
        'applied': manual,
        'before_single_instance_mappings': before_count,
        'after_single_instance_mappings': after_count,
        'timestamp': datetime.now().isoformat()
    }

    out = OUT_DIR / f'manual_apply_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    save_json(out, report)
    print('Manual apply complete. Report:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
