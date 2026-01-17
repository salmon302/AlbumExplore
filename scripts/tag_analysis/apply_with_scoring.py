#!/usr/bin/env python3
"""
Apply suggestions automatically based on score and export manual-review CSV for the rest.

Behavior:
 - Loads suggestions (expects `score` field; if missing, scores using simple heuristic)
 - Auto-applies suggestions with score >= `--auto-score`
 - Writes `--manual-out` CSV containing medium-confidence suggestions for review
 - Supports `--dry-run` to preview actions without writing configs
"""
import argparse
import json
from pathlib import Path
from difflib import SequenceMatcher
import csv


def score_pair(orig: str, sugg: str):
    o = orig.lower().strip()
    s = sugg.lower().strip()
    seq = SequenceMatcher(None, o, s).ratio()
    o_tokens = set(o.replace('-', ' ').split())
    s_tokens = set(s.replace('-', ' ').split())
    if not o_tokens:
        token_overlap = 0.0
    else:
        token_overlap = len(o_tokens & s_tokens) / len(o_tokens)
    score = 0.6 * seq + 0.4 * token_overlap
    return round(score, 4)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--suggestions', '-s', default='tag_analysis/singleton_suggestions.json')
    p.add_argument('--auto-score', type=float, default=0.9, help='Score threshold to auto-apply')
    p.add_argument('--manual-out', default='tag_analysis/manual_review_auto.csv')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--config', default='src/albumexplore/config/tag_rules.json')
    args = p.parse_args()

    s_path = Path(args.suggestions)
    if not s_path.exists():
        print('Suggestions file not found:', s_path)
        return 2

    data = json.loads(s_path.read_text(encoding='utf-8'))
    suggestions = data.get('suggestions', {})

    auto = {}
    manual = {}
    ignored = {}

    for orig, info in suggestions.items():
        target = info.get('suggestion')
        if not target or target == orig:
            ignored[orig] = info
            continue
        score = info.get('score')
        if score is None:
            score = score_pair(orig, target)
            info['score'] = score

        if score >= args.auto_score:
            auto[orig] = info
        elif score >= 0.6:
            manual[orig] = info
        else:
            ignored[orig] = info

    print('Total suggestions:', len(suggestions))
    print('Auto-apply count:', len(auto))
    print('Manual-review count:', len(manual))
    print('Ignored count:', len(ignored))

    # Write manual CSV
    manual_out = Path(args.manual_out)
    manual_out.parent.mkdir(parents=True, exist_ok=True)
    with manual_out.open('w', encoding='utf-8', newline='') as csvf:
        w = csv.writer(csvf)
        w.writerow(['original', 'suggestion', 'reason', 'score'])
        for k, v in sorted(manual.items()):
            w.writerow([k, v.get('suggestion'), v.get('reason'), v.get('score')])

    # Prepare auto suggestions JSON
    auto_blob = {'stats': {'total_singletons': data.get('stats', {}).get('total_singletons')}, 'suggestions': auto}
    auto_path = Path(s_path.parent) / 'singleton_suggestions_auto_apply.json'
    auto_path.write_text(json.dumps(auto_blob, indent=2, ensure_ascii=False), encoding='utf-8')

    # Either perform dry-run preview or call apply_singleton_suggestions
    import subprocess
    import sys

    apply_script = Path('tag_analysis') / 'apply_singleton_suggestions.py'
    if args.dry_run:
        cmd = [sys.executable, str(apply_script), '--suggestions', str(auto_path), '--config', args.config, '--dry-run']
        print('Running dry-run:', ' '.join(cmd))
        subprocess.run(cmd, check=True)
        print('Dry-run complete. Manual-review CSV:', manual_out)
        return 0

    # Perform actual apply
    cmd = [sys.executable, str(apply_script), '--suggestions', str(auto_path), '--config', args.config]
    print('Running apply:', ' '.join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print('Auto-apply done. Manual-review CSV:', manual_out)
    else:
        print('Apply script exited with code', res.returncode)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
