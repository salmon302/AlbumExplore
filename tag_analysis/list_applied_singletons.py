#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / 'tag_rules_backup_apply_singletons_20251114_135633.json'
CURRENT = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
OUT = ROOT / 'tag_analysis' / 'applied_singleton_mappings.json'

def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    before = load(BACKUP)
    after = load(CURRENT)

    before_map = before.get('single_instance_mappings', {})
    after_map = after.get('single_instance_mappings', {})

    applied = {}
    for k, v in after_map.items():
        if k not in before_map and v:
            applied[k] = v
        elif k in before_map and before_map[k] != v:
            applied[k] = v

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'applied_count': len(applied), 'mappings': applied}, f, indent=2, ensure_ascii=False)

    print(f'Wrote {OUT} with {len(applied)} applied mappings')

if __name__ == '__main__':
    main()
