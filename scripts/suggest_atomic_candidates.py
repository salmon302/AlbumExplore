"""Suggest conservative atomic_decomposition entries from raw single-instance tags.

Produces a JSON file `scripts/suggested_atomic_batch_<timestamp>.json` with ranked suggestions.

Heuristics (conservative):
- Only consider multi-word tags (contains space or '/' or ' and ' or '&').
- Prefer 2-3 token splits.
- Split on '/', ' / ', ' and ', '&', then fall back to simple space split for 2-3 words.
- Exclude tags that already exist in `atomic_decomposition` keys.
- Score suggestions higher when the proposed tokens are already present as atoms in existing rules.

Usage: run from repo root (project venv recommended):
  python scripts/suggest_atomic_candidates.py --top 25
"""
import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
SINGLES_CSV = ROOT / 'tagoutput' / 'raw_tags_singles.csv'
OUT_DIR = ROOT / 'scripts'

SEPARATORS = [' / ', '/', ' and ', ' & ', ' &amp; ', '&']


def load_rules():
    with open(RULES_PATH, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    atomic = data.get('atomic_decomposition', {})
    atomic_keys = set(k.strip() for k in atomic.keys())
    # flatten existing atom tokens for scoring
    atom_tokens = set()
    for vals in atomic.values():
        for v in vals:
            atom_tokens.add(v.strip())
    return atomic_keys, atom_tokens


def read_singles():
    if not SINGLES_CSV.exists():
        raise SystemExit(f"Missing expected file: {SINGLES_CSV}. Run export first.")
    rows = []
    with open(SINGLES_CSV, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            # Expect columns: Tag, Count, Normalized Form, Filter State
            tag = r.get('Tag') or r.get('tag')
            count = int(r.get('Count') or r.get('count') or 0)
            if tag:
                rows.append({'tag': tag.strip(), 'count': count})
    # sort by count desc
    rows.sort(key=lambda x: x['count'], reverse=True)
    return rows


def propose_decomposition(tag):
    t = tag.strip()
    # skip single-word
    if ' ' not in t and all(sep not in t for sep in SEPARATORS):
        return None
    # try explicit separators first
    for sep in SEPARATORS:
        if sep in t:
            parts = [p.strip() for p in t.split(sep) if p.strip()]
            if 2 <= len(parts) <= 4:
                return parts
    # fallback: whitespace split
    tokens = [p.strip() for p in t.split() if p.strip()]
    if 2 <= len(tokens) <= 3:
        return tokens
    return None


def is_conservative(tokens):
    # conservative filter: tokens must be alphabetic-ish and length>1
    for tok in tokens:
        # avoid tokens that are punctuation, single char (except common 'n' or 'n\'')
        if len(tok) <= 1 and tok.lower() not in ("n", "'", "a"):
            return False
        # skip tokens that contain many non-alphanum characters
        cleaned = ''.join(ch for ch in tok if ch.isalnum())
        if len(cleaned) < max(2, len(tok) - 2):
            # too many non-alnum removed
            return False
    return True


def score_suggestion(tokens, atom_tokens):
    # base score from matching existing atom tokens
    score = 0
    for tok in tokens:
        if tok in atom_tokens:
            score += 10
        # partial match: lowercase
        if tok.lower() in atom_tokens:
            score += 5
    # prefer 2-token splits slightly
    if len(tokens) == 2:
        score += 2
    return score


def main(top=25, out_limit=50):
    atomic_keys, atom_tokens = load_rules()
    rows = read_singles()

    suggestions = []
    seen = set()
    for r in rows:
        tag = r['tag']
        if tag in atomic_keys or tag.lower() in (k.lower() for k in atomic_keys):
            continue
        if tag in seen:
            continue
        seen.add(tag)
        decomposed = propose_decomposition(tag)
        if not decomposed:
            continue
        if not is_conservative(decomposed):
            continue
        score = score_suggestion(decomposed, atom_tokens)
        suggestions.append({
            'tag': tag,
            'count': r['count'],
            'decomposition': decomposed,
            'score': score
        })

    # sort by (score desc, count desc)
    suggestions.sort(key=lambda x: (x['score'], x['count']), reverse=True)
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_file = OUT_DIR / f'suggested_atomic_batch_{timestamp}.json'
    # write top-N suggestions
    to_write = suggestions[:out_limit]
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump({'generated': timestamp, 'suggestions': to_write}, fh, ensure_ascii=False, indent=2)

    print(f"Wrote {len(to_write)} suggestions to {out_file}")
    print('\nTop suggestions:')
    for i, s in enumerate(to_write[:top], 1):
        print(f"{i:2d}. {s['tag']} -> {s['decomposition']} (count={s['count']}, score={s['score']})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', type=int, default=25, help='How many top suggestions to print')
    parser.add_argument('--limit', type=int, default=50, help='How many suggestions to write')
    args = parser.parse_args()
    main(top=args.top, out_limit=args.limit)
