#!/usr/bin/env python3
"""
List mappings applied between a backup and the current `tag_rules.json`.
Usage: run from repo root with the venv python:
  .\.venv-1\Scripts\python.exe .\tag_analysis\list_applied_mappings.py
It looks for the most recent `tag_rules_backup_apply_singletons_*.json` in repo root
and compares its `single_instance_mappings` section against the current config.
"""
import json
from pathlib import Path
import sys
import glob


def load_json(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_latest_backup():
    files = sorted(glob.glob('tag_rules_backup_apply_singletons_*.json'))
    if not files:
        return None
    return Path(files[-1])


def main():
    repo = Path('.').resolve()
    backup = find_latest_backup()
    if not backup:
        print('No backup file found matching tag_rules_backup_apply_singletons_*.json')
        sys.exit(1)

    current = repo / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
    if not current.exists():
        print('Current config not found at', current)
        sys.exit(1)

    b = load_json(backup)
    c = load_json(current)

    bm = b.get('single_instance_mappings', {})
    cm = c.get('single_instance_mappings', {})

    added = {k: cm[k] for k in cm.keys() - bm.keys()} if cm else {}
    removed = {k: bm[k] for k in bm.keys() - cm.keys()} if bm else {}
    changed = {k: {'before': bm[k], 'after': cm[k]} for k in cm.keys() & bm.keys() if bm.get(k) != cm.get(k)}

    out = {
        'backup_file': str(backup),
        'current_file': str(current),
        'added_count': len(added),
        'changed_count': len(changed),
        'removed_count': len(removed),
        'added': added,
        'changed': changed,
        'removed': removed,
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
