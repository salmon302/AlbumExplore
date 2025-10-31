"""Simple CLI utilities for manual tag relationship files.

Provides validation functions to check for unknown tags and low-frequency
entries given an optional tag index / frequency map. This is intentionally
lightweight: it does not require a database session to run and can be used by
curators to sanity-check YAML/CSV/JSON mapping files.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from albumexplore.similarity import manual as manual_mod

logger = logging.getLogger(__name__)


def summarize_relationships(path: str) -> Dict[str, int]:
    """Load relationships and return a summary with counts per tag.

    Returns a dict with keys: total_sources, total_relations
    """
    rels = manual_mod.load_relationships(path)
    total_sources = len(rels)
    total_relations = sum(len(v) for v in rels.values())
    return {"total_sources": total_sources, "total_relations": total_relations}


def validate_against_index(
    path: str, tag_index: Dict[str, int], min_count: Optional[int] = None
) -> Dict[str, List[str]]:
    """Validate mapping file against a provided tag_index (mapping tag->freq or id).

    - Reports unknown source tags
    - Reports unknown target tags
    - If min_count is provided, reports mappings ignored due to low frequency

    Returns a dict with lists of warnings under keys: unknown_source, unknown_target, low_frequency
    """
    rels = manual_mod.load_relationships(path)
    warnings = {"unknown_source": [], "unknown_target": [], "low_frequency": []}
    # tag_index may map tag->id or tag->freq. We accept either; if values look small,
    # caller can pass the proper map.
    freqs = None
    # detect if tag_index values are counts (all ints >=0)
    if tag_index and all(isinstance(v, int) for v in tag_index.values()):
        freqs = tag_index

    for src, rel_list in rels.items():
        if src not in tag_index:
            warnings["unknown_source"].append(src)
        for r in rel_list:
            tgt = r.get("tag")
            if tgt not in tag_index:
                warnings["unknown_target"].append(f"{src}->{tgt}")
            if min_count is not None and freqs is not None:
                fs = freqs.get(src, 0)
                ft = freqs.get(tgt, 0)
                if fs < min_count or ft < min_count:
                    warnings["low_frequency"].append(f"{src}->{tgt} ({fs},{ft})")

    return warnings


def load_index_json(path: str) -> Dict[str, int]:
    """Load a simple JSON mapping file (tag->count or tag->id) used for validation."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Index JSON must be a mapping of tag -> value")
    # normalize keys to lower-case for consistent matching with loader
    return {k.strip().lower(): v for k, v in data.items()}


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Validate manual tag relationship files")
    p.add_argument("file", help="Path to relationships file (CSV/JSON/YAML)")
    p.add_argument("--index-json", help="Optional JSON file mapping tag->count or tag->id for validation")
    p.add_argument("--min-count", type=int, help="Minimum frequency to accept manual mappings")
    args = p.parse_args()

    if args.index_json:
        idx = load_index_json(args.index_json)
    else:
        idx = {}

    print("Summary:", summarize_relationships(args.file))
    if idx:
        warnings = validate_against_index(args.file, idx, min_count=args.min_count)
        print("Warnings:")
        for k, vs in warnings.items():
            if vs:
                print(f"  {k}:")
                for v in vs[:50]:
                    print(f"    - {v}")
    else:
        print("No index provided; pass --index-json to validate against known tags")
