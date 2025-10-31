"""Automatic inference of tag relationships from tag data.

This module provides helpers to infer candidate relationships from tag
co-occurrence and context similarity. The primary exported function is
`infer_relationships(session, ...)` which returns a normalized mapping ready
to be written to YAML/JSON by the curator tools.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional

from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


def _cosine_dict(a: dict, b: dict) -> float:
    dot = 0.0
    for k, v in a.items():
        if k in b:
            dot += v * b[k]
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def infer_relationships(
    session,
    min_count: int = 5,
    min_sim: float = 0.6,
    max_pairs: int = 500,
    limit_tags: Optional[int] = 1000,
    method: str = "context_cosine",
) -> Dict[str, List[Dict[str, object]]]:
    """Infer relationships from database tag data.

    Returns a mapping of source_tag -> list of relation dicts in the same
    normalized format used by the manual loader (tag, type, weight, note).

    Currently only supports context_cosine which uses tag-context vectors
    derived from co-occurrence on albums.
    """
    # Lazy imports to avoid import cycles
    from albumexplore.database.models import Tag, Album

    # Load tags filtered by frequency
    tags_q = session.query(Tag).filter(Tag.frequency >= min_count).order_by(Tag.frequency.desc())
    if limit_tags:
        tags_list = tags_q.limit(limit_tags).all()
    else:
        tags_list = tags_q.all()

    tag_names = [t.name.strip().lower() for t in tags_list if t.name]
    tag_name_set = set(tag_names)

    # Build album -> tag names mapping for albums that include these tags
    albums = session.query(Album).join(Album.tags).filter(Tag.id.in_([t.id for t in tags_list])).distinct().all()
    album_tags = {}
    for alb in albums:
        names = [t.name.strip().lower() for t in getattr(alb, 'tags', []) if t.name and t.name.strip().lower() in tag_name_set]
        if names:
            album_tags[alb.id] = list(set(names))

    # Build co-occurrence counts
    co_counts = defaultdict(Counter)
    for tags in album_tags.values():
        for i, a in enumerate(tags):
            for b in tags[i+1:]:
                co_counts[a][b] += 1
                co_counts[b][a] += 1

    vectors = {tag: dict(counter) for tag, counter in co_counts.items()}

    # Compute candidate pairs based on method
    candidates = []
    keys = list(vectors.keys())
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            va = vectors[a]
            vb = vectors[b]
            if method == "context_cosine":
                sim = _cosine_dict(va, vb)
            else:
                sim = _cosine_dict(va, vb)
            direct = co_counts.get(a, {}).get(b, 0)
            if sim >= min_sim:
                candidates.append((a, b, sim, direct))

    # sort and limit
    candidates.sort(key=lambda x: x[2], reverse=True)
    candidates = candidates[:max_pairs]

    # Map similarity to relation types and weights
    mapping: Dict[str, List[Dict[str, object]]] = {}
    for a, b, sim, direct in candidates:
        # heuristic mapping
        if sim >= 0.85:
            rtype = "close_related"
            weight = float(min(1.0, sim))
        elif sim >= 0.75:
            rtype = "related"
            weight = float(sim)
        else:
            rtype = "related"
            weight = float(sim)

        mapping.setdefault(a, []).append({"tag": b, "type": rtype, "weight": weight, "note": f"auto:{method}"})
        mapping.setdefault(b, []).append({"tag": a, "type": rtype, "weight": weight, "note": f"auto:{method}"})

    return mapping
