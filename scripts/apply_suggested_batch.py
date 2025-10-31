"""Apply a suggested atomic batch to a temporary rules file and run export in dry-run/no-db mode.

Usage:
  python scripts/apply_suggested_batch.py --suggestions scripts/suggested_atomic_batch_20251021T230239Z.json --select 1-20

This will:
- Load the suggestions JSON
- Build a temp copy of src/.../tag_rules.json with selected suggestions merged into the "atomic_decomposition" section
- Invoke the export CLI with --rules-file pointing at the temp file and --no-db --dry-run
- Print the export CLI output for review

This does not modify the real rules file.
"""
import argparse
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
EXPORT_CLI = ROOT / '.venv-1' / 'Scripts' / 'python.exe'
EXPORT_MODULE = ' -m albumexplore.cli.export_tags'


def parse_select_range(s):
    # Accept forms like '1-20' or '1,3,5' or '1-3,7,9-12'
    parts = s.split(',')
    idxs = set()
    for p in parts:
        p = p.strip()
        if '-' in p:
            a, b = p.split('-', 1)
            a = int(a); b = int(b)
            for i in range(a, b+1):
                idxs.add(i-1)
        else:
            idxs.add(int(p)-1)
    return sorted(i for i in idxs if i >= 0)


def merge_suggestions_to_temp_rules(suggestions_file: Path, selected_indices: list):
    with open(suggestions_file, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    suggestions = data.get('suggestions', [])

    # Read original rules
    with open(RULES_PATH, 'r', encoding='utf-8') as fh:
        rules = json.load(fh)

    atomic = rules.get('atomic_decomposition', {})

    for idx in selected_indices:
        if idx < 0 or idx >= len(suggestions):
            continue
        s = suggestions[idx]
        tag = s['tag']
        decomposition = s['decomposition']
        # Only add if not present
        if tag not in atomic:
            atomic[tag] = decomposition

    rules['atomic_decomposition'] = atomic

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json', prefix='tag_rules_tmp_', dir=str(ROOT / 'scripts'))
    tmp_path = Path(tmp.name)
    with open(tmp_path, 'w', encoding='utf-8') as fh:
        json.dump(rules, fh, ensure_ascii=False, indent=2)

    return tmp_path


def run_export_dry_run(rules_file: Path, input_csv: Path = None):
    cmd = [str(EXPORT_CLI), '-m', 'albumexplore.cli.export_tags']
    cmd += ['--no-db', '--dry-run', '--rules-file', str(rules_file), '--output-dir', str(ROOT / 'tagoutput')]
    if input_csv:
        cmd += ['--input-csv', str(input_csv)]
    # Run
    print('Running:', ' '.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suggestions', type=Path, required=True)
    parser.add_argument('--select', type=str, default='1-20', help='Indices to select (1-based, ranges allowed)')
    parser.add_argument('--apply', action='store_true', help='Apply selected suggestions to the real tag_rules.json (backup created)')
    parser.add_argument('--yes', action='store_true', help='Assume yes for confirmations when --apply is used')
    args = parser.parse_args()

    selected = parse_select_range(args.select)
    tmp_rules = merge_suggestions_to_temp_rules(args.suggestions, selected)
    print(f'Created temp rules file: {tmp_rules}')
    run_export_dry_run(tmp_rules, input_csv=ROOT / 'tagoutput' / 'raw_tags_singles.csv')
    print('Dry-run complete. Temp rules file left at:', tmp_rules)

    if args.apply:
        # Confirm
        if not args.yes:
            ans = input('Apply these changes to the real tag_rules.json? This will create a timestamped backup. [y/N]: ')
            if ans.lower() not in ('y', 'yes'):
                print('Aborting apply.')
                sys.exit(0)

        # Create backup
        import datetime
        backup_name = RULES_PATH.with_suffix(f".backup-{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json")
        shutil.copy2(RULES_PATH, backup_name)
        print(f'Backup of original rules created at: {backup_name}')

        # Overwrite real rules with tmp_rules content
        shutil.copy2(tmp_rules, RULES_PATH)
        print(f'Applied suggested rules to {RULES_PATH}')
        print('You may want to run the full export (without --dry-run) to persist CSV outputs.')
