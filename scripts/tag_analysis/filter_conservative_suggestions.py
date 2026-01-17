#!/usr/bin/env python3
"""
Filter singleton suggestions conservatively.

Keeps suggestions where reason is one of the safe reasons and the suggested
target is not in a blacklist of overly-generic targets. Writes a filtered
`singleton_suggestions_filtered.json` file for review or application.

Usage:
  .\.venv-1\Scripts\python.exe .\tag_analysis\filter_conservative_suggestions.py
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SUGGESTIONS = ROOT / 'tag_analysis' / 'singleton_suggestions.json'
OUT = ROOT / 'tag_analysis' / 'singleton_suggestions_filtered.json'
 
# Reasons considered safe for conservative auto-apply
SAFE_REASONS = {'rules-mapped-after-enhanced', 'atomic-decompose'}
# Small generic blacklist (keep minimal). More specific genre-like tokens are allowed
# via GENRE_WHITELIST so we don't erroneously block legitimate genres like "jazz".
GENERIC_BLACKLIST = {'music'}
# Genre whitelist: tokens that look like genres and should NOT be treated as generic/forbidden.
GENRE_WHITELIST = {
    'jazz', 'blues', 'classical', 'country', 'electronic', 'folk',
    'rock', 'pop', 'metal', 'soul', 'hip-hop', 'hip hop', 'rnb', 'rap'
}


def load(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save(p: Path, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def backup_original():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / 'tag_analysis' / f'singleton_suggestions_backup_{ts}.json'
    backup.write_text(SUGGESTIONS.read_text(encoding='utf-8'), encoding='utf-8')
    return backup


def main():
    if not SUGGESTIONS.exists():
        print('No suggestions file found at', SUGGESTIONS)
        return

    data = load(SUGGESTIONS)
    suggestions = data.get('suggestions', {})

    backup = backup_original()
    print('Backed up original suggestions to', backup)

    filtered = {}
    for orig, info in suggestions.items():
        sug = info.get('suggestion')
        reason = info.get('reason')
        if not sug:
            continue
        s_norm = sug.lower().strip()
        # Skip overly generic targets unless they are known genre-like tokens
        if s_norm in GENERIC_BLACKLIST and s_norm not in GENRE_WHITELIST:
            continue
        # Accept only safe reasons
        if reason in SAFE_REASONS:
            # also avoid trivial identity mappings
            if s_norm != orig.strip().lower():
                filtered[orig] = info

    out = {'stats': {'total_singletons': data.get('stats', {}).get('total_singletons', 0), 'suggested': len(filtered)}, 'suggestions': filtered}
    save(OUT, out)
    print(f'Wrote filtered suggestions to: {OUT} ({len(filtered)} suggestions)')


if __name__ == '__main__':
    main()
