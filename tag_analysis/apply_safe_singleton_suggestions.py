#!/usr/bin/env python3
"""
Apply only safe, high-confidence singleton suggestions.

Rules:
- Auto-apply suggestions whose reason == 'rules-mapped-after-enhanced'.
- Auto-apply suggestions whose reason == 'atomic-decompose' AND the suggested canonical exists in atomic_tags (valid_atomic_tags from config).
- Block suggestions that map to overly-generic targets (music, rock, pop, folk, etc.) unless explicitly allowed.

Produces a JSON report of applied and skipped suggestions.
"""
import json
from pathlib import Path
import argparse
from albumexplore.tags.config.tag_rules_config import TagRulesConfig
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from datetime import datetime
import shutil
import os

ROOT = Path(__file__).resolve().parent.parent
SUGGESTIONS = ROOT / 'tag_analysis' / 'singleton_suggestions.json'
CONFIG_PATH = ROOT / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
TYPO_MAP_PATH = ROOT / 'tag_analysis' / 'typo_corrections.json'

GENERIC_BLOCKLIST = {'music', 'rock', 'pop', 'folk', 'metal', 'jazz'}


def backup_config():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / f'tag_rules_backup_safe_apply_{ts}.json'
    shutil.copy(CONFIG_PATH, backup)
    return backup


def load_json(p: Path):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(p: Path, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, lb + 1):
            cur = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[lb]


def is_safe_target(target: str, geo_strip_mode: str = 'block') -> bool:
    t = target.strip().lower()
    if t in GENERIC_BLOCKLIST:
        return False
    # block very short generic tokens
    if len(t) <= 3 and t.isalpha():
        return False
    # if caller explicitly allows geo stripping, relax generic blocking
    if geo_strip_mode == 'allow':
        return True
    return True


def apply(apply_typo_fixes: bool = False, allow_atomic_relax: bool = False, geo_strip_mode: str = 'block', dry_run: bool = False):
    if not SUGGESTIONS.exists():
        print(f"Suggestions file not found: {SUGGESTIONS}")
        return False

    suggestions_file = load_json(SUGGESTIONS)
    suggestions = suggestions_file.get('suggestions', {})
    if not suggestions:
        print('No suggestions found')
        return False

    # Load current config and normalizer (to get valid atomic tags)
    config = load_json(CONFIG_PATH)
    normalizer = TagNormalizer()
    valid_atomic = set(normalizer._valid_atomic_tags)

    # Load typo corrections map if present
    typo_map = {}
    if TYPO_MAP_PATH.exists():
        try:
            typo_map = load_json(TYPO_MAP_PATH)
            # normalize keys to lower-case
            typo_map = {k.strip().lower(): v.strip() for k, v in typo_map.items()}
        except Exception:
            typo_map = {}

    applied = {}
    skipped = {}

    for original, info in suggestions.items():
        suggestion = info.get('suggestion')
        reason = info.get('reason')
        if not suggestion:
            skipped[original] = {'reason': 'no-suggestion'}
            continue

        suggestion_norm = suggestion.strip().lower()
        original_norm = original.strip().lower()

        # Decision logic
        reason_key = reason
        if reason_key == 'rules-mapped-after-enhanced':
            # safe to apply if target not overly generic
            if not is_safe_target(suggestion_norm, geo_strip_mode=geo_strip_mode):
                # if preserving geo-qualified originals is desired, map to original instead of skipping
                if geo_strip_mode == 'preserve':
                    applied[original] = original
                    continue
                skipped[original] = {'reason': 'blocked-generic-target', 'target': suggestion_norm}
                continue
            applied[original] = suggestion
            continue

        if reason_key == 'atomic-decompose':
            # apply only if all components are valid atomic tags OR the suggested canonical is in atomic set
            parts = [p.strip() for p in suggestion_norm.split() if p.strip()]
            parts_valid = [p in valid_atomic for p in parts]
            if suggestion_norm in valid_atomic or all(parts_valid):
                if not is_safe_target(suggestion_norm, geo_strip_mode=geo_strip_mode):
                    if geo_strip_mode == 'preserve':
                        applied[original] = original
                        continue
                    skipped[original] = {'reason': 'blocked-generic-target', 'target': suggestion_norm}
                    continue
                applied[original] = suggestion
            else:
                if allow_atomic_relax:
                    # allow if majority of components valid or suggestion close to an atomic tag
                    if parts and (sum(parts_valid) / len(parts) >= 0.66 or any(levenshtein(suggestion_norm, v) <= 2 for v in valid_atomic)):
                        if not is_safe_target(suggestion_norm, geo_strip_mode=geo_strip_mode):
                            if geo_strip_mode == 'preserve':
                                applied[original] = original
                            else:
                                skipped[original] = {'reason': 'blocked-generic-target', 'target': suggestion_norm}
                        else:
                            applied[original] = suggestion
                    else:
                        skipped[original] = {'reason': 'atomic-components-not-validated', 'target': suggestion_norm}
                else:
                    skipped[original] = {'reason': 'atomic-components-not-validated', 'target': suggestion_norm}
            continue

        # Handle enhanced-fallback typos optionally
        if apply_typo_fixes:
            # first consult curated typo map
            if original_norm in typo_map:
                candidate = typo_map[original_norm]
                candidate_norm = candidate.strip().lower()
                if is_safe_target(candidate_norm, geo_strip_mode=geo_strip_mode):
                    applied[original] = candidate
                    continue
                else:
                    skipped[original] = {'reason': 'blocked-generic-target', 'target': candidate_norm}
                    continue

            if reason_key == 'skipped_reason_enhanced-fallback':
                # if suggestion is close to a known atomic tag, apply it
                if suggestion_norm in valid_atomic:
                    applied[original] = suggestion
                    continue
                # check single-token close matches
                tokens = [t for t in suggestion_norm.split() if t]
                if len(tokens) == 1:
                    cand = tokens[0]
                    close = None
                    for v in valid_atomic:
                        if levenshtein(cand, v) <= 2:
                            close = v
                            break
                    if close:
                        applied[original] = close
                        continue

        # For other reasons, skip for now
        skipped[original] = {'reason': f'skipped_reason_{reason}', 'target': suggestion_norm}

    # Merge applied into config single_instance_mappings
    if 'single_instance_mappings' not in config:
        config['single_instance_mappings'] = {}

    before_count = len(config['single_instance_mappings'])
    # If dry_run, do not modify files; just compute what would change
    if not dry_run:
        config['single_instance_mappings'].update(applied)
        backup = backup_config()
        save_json(CONFIG_PATH, config)
    else:
        hypothetical = dict(config['single_instance_mappings'])
        hypothetical.update(applied)
        backup = None

    report = {
        'backup': str(backup),
        'applied_count': len(applied),
        'skipped_count': len(skipped),
        'applied': applied,
        'skipped': skipped,
        'before_single_instance_mappings': before_count,
        'after_single_instance_mappings': len(config['single_instance_mappings'])
    }

    out = ROOT / 'tag_analysis' / f'safe_apply_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    save_json(out, report)
    if dry_run:
        print(f"Dry run — would apply {len(applied)} mappings, would skip {len(skipped)} mappings")
    else:
        print(f"Safe apply complete — applied {len(applied)} mappings, skipped {len(skipped)} mappings")
    print(f"Report: {out}")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply safe singleton suggestions with optional relaxations')
    parser.add_argument('--apply-typo-fixes', action='store_true', help='Attempt to auto-fix simple typos from enhanced-fallback suggestions')
    parser.add_argument('--allow-atomic-relax', action='store_true', help='Allow relaxed acceptance of atomic-decompose suggestions when majority of components validate')
    parser.add_argument('--geo-strip-mode', choices=['block', 'allow', 'preserve'], default='block', help='How to handle geo->generic strip suggestions')
    parser.add_argument('--dry-run', action='store_true', help='Do not write changes; only report what would be applied')
    args = parser.parse_args()
    apply(apply_typo_fixes=args.apply_typo_fixes, allow_atomic_relax=args.allow_atomic_relax, geo_strip_mode=args.geo_strip_mode, dry_run=args.dry_run)
