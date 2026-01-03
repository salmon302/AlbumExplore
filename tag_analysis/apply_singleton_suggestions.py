#!/usr/bin/env python3
"""
Apply reviewed singleton suggestions into `src/albumexplore/config/tag_rules.json`.

This script:
- Creates a timestamped backup of the config
- Loads `tag_analysis/singleton_suggestions.json`
- Merges suggestions into `single_instance_mappings` (overwriting existing keys)
- Writes updated config back to `src/albumexplore/config/tag_rules.json`
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
import shutil


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
DEFAULT_SUGGESTIONS = ROOT / 'tag_analysis' / 'singleton_suggestions.json'


def backup_config(config_path: Path):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = Path(f'tag_rules_backup_apply_singletons_{ts}.json')
    shutil.copy(config_path, backup)
    return backup


def load_json(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(p: Path, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def preview_apply(suggestions_path: Path, config_path: Path):
    suggestions = load_json(suggestions_path).get('suggestions', {})
    config = load_json(config_path)
    mappings = config.get('single_instance_mappings', {})

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

    print('Suggestions file:', suggestions_path)
    print('Total suggestions present:', len(suggestions))
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


def apply(suggestions_path: Path, config_path: Path):
    if not suggestions_path.exists():
        print(f"Suggestions file not found: {suggestions_path}")
        return False

    suggestions = load_json(suggestions_path).get('suggestions', {})
    if not suggestions:
        print('No suggestions to apply')
        return False

    config = load_json(config_path)

    # Ensure the key exists
    if 'single_instance_mappings' not in config:
        config['single_instance_mappings'] = {}

    mappings = config['single_instance_mappings']

    # Prepare simple mapping: original -> suggested
    applied = 0
    for original, info in suggestions.items():
        suggestion = info.get('suggestion')
        if suggestion and suggestion != original:
            mappings[original] = suggestion
            applied += 1

    if applied == 0:
        print('No non-trivial suggestions to apply')
        return False

    # Backup then save
    backup = backup_config(config_path)
    save_json(config_path, config)

    print(f'Applied {applied} suggestions. Backup written to {backup}')
    return True


def main():
    p = argparse.ArgumentParser(description='Apply reviewed singleton suggestions into tag_rules.json')
    p.add_argument('--suggestions', '-s', type=Path, default=DEFAULT_SUGGESTIONS, help='Path to suggestions JSON')
    p.add_argument('--config', '-c', type=Path, default=DEFAULT_CONFIG_PATH, help='Path to tag_rules.json')
    p.add_argument('--dry-run', action='store_true', help='Preview changes without writing files')
    args = p.parse_args()

    if args.dry_run:
        preview_apply(args.suggestions, args.config)
    else:
        apply(args.suggestions, args.config)


if __name__ == '__main__':
    main()
