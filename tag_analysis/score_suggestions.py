#!/usr/bin/env python3
"""
Score singleton suggestions with simple heuristics.

Produces `singleton_suggestions_scored.json` next to the input file.
Heuristics:
 - sequence matcher ratio between original and suggestion (0..1)
 - token overlap ratio
 Combined score = 0.6 * seq_ratio + 0.4 * token_overlap
"""
import json
from pathlib import Path
from difflib import SequenceMatcher
import argparse
import json
from pathlib import Path


def load_atomic_decomposition():
    cfg = Path('src/albumexplore/config/tag_rules.json')
    if not cfg.exists():
        return {}
    j = json.loads(cfg.read_text(encoding='utf-8'))
    return j.get('atomic_decomposition', {})


def score_pair(orig: str, sugg: str, atomic_decomp: dict = None):
    o = orig.lower().strip()
    s = sugg.lower().strip()
    seq = SequenceMatcher(None, o, s).ratio()
    o_tokens = set(o.replace('-', ' ').split())
    s_tokens = set(s.replace('-', ' ').split())
    if not o_tokens:
        token_overlap = 0.0
    else:
        token_overlap = len(o_tokens & s_tokens) / len(o_tokens)

    atomic_overlap = 0.0
    if atomic_decomp:
        # try to get decomposition for suggestion; fallback to suggestion tokens
        decomp = atomic_decomp.get(s)
        if decomp:
            decomp_tokens = set([t.lower().strip() for t in decomp])
        else:
            decomp_tokens = s_tokens
        if o_tokens:
            atomic_overlap = len(o_tokens & decomp_tokens) / len(o_tokens)

    # Weighted combination: make scoring slightly more conservative by
    # favoring strict sequence similarity over token overlap. This reduces
    # cases where token overlap alone (many shared small words) produces
    # high scores that may be unsafe to auto-apply.
    score = 0.6 * seq + 0.25 * token_overlap + 0.15 * atomic_overlap
    return round(score, 4)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('input', nargs='?', default='tag_analysis/singleton_suggestions.json')
    args = p.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print('Input suggestions file not found:', inp)
        return 2

    data = json.loads(inp.read_text(encoding='utf-8'))
    suggestions = data.get('suggestions', {})

    out = {'stats': data.get('stats', {}), 'suggestions': {}}

    atomic = load_atomic_decomposition()
    for orig, info in suggestions.items():
        sugg = info.get('suggestion')
        score = None
        if sugg and sugg != orig:
            score = score_pair(orig, sugg, atomic_decomp=atomic)
        new_info = dict(info)
        if score is not None:
            new_info['score'] = score
        out['suggestions'][orig] = new_info

    out_path = inp.parent / 'singleton_suggestions_scored.json'
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote scored suggestions to', out_path)


if __name__ == '__main__':
    main()
