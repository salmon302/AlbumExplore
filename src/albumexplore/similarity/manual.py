"""Manual/curated tag relationships loader and utilities.

Supports loading CSV and JSON mapping files out of the box. If PyYAML is
installed it will also support YAML files. The loader validates entries
against a provided tag index/frequency map and can filter low-frequency tags
used in manual mappings.

The module exposes a small API used by higher-level similarity code:
- load_relationships(path)
- validate_relationships(relationships, tag_index, tag_freqs, min_count)
- manual_score(relationships, tag_a, tag_b)
- merge_manual_with_auto(manual_weight, auto_score, manual_score, alpha_manual)
"""
from __future__ import annotations

import csv
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


DEFAULT_TYPE_WEIGHTS = {
    "synonym": 1.0,
    "close_related": 0.9,
    "related": 0.75,
    "historic": 0.6,
    "parent_child": 0.9,
    "influence": 0.6,
    "exclude": -1.0,
}


def _try_import_yaml():
    try:
        import yaml  # type: ignore

        return yaml
    except Exception:
        return None


def load_relationships(path: str) -> Dict[str, List[Dict]]:
    """Load relationships from a file.

    Supports .csv and .json by default. If PyYAML is available, also supports
    .yml/.yaml. Returned structure maps source_tag -> list of relation dicts:

    {"rnb": [{"tag":"jazz","type":"historic","weight":0.7, "note": "..."}, ...]}
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".json",):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return _normalize_loaded(data)

    if ext in (".csv",):
        out: Dict[str, List[Dict]] = {}
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                a = row.get("tag_a") or row.get("tag") or row.get("source")
                b = row.get("tag_b") or row.get("tag_to") or row.get("target")
                if not a or not b:
                    continue
                a_n = a.strip().lower()
                b_n = b.strip().lower()
                rel = {
                    "tag": b_n,
                    "type": (row.get("type") or "related").strip(),
                }
                weight = row.get("weight")
                if weight:
                    try:
                        rel["weight"] = float(weight)
                    except Exception:
                        pass
                note = row.get("note")
                if note:
                    rel["note"] = note
                out.setdefault(a_n, []).append(rel)
        return out

    if ext in (".yml", ".yaml"):
        yaml = _try_import_yaml()
        if yaml is None:
            raise RuntimeError("PyYAML is not installed; install it or provide JSON/CSV")
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return _normalize_loaded(data)

    raise ValueError(f"Unsupported relationships file extension: {ext}")


def _normalize_loaded(data) -> Dict[str, List[Dict]]:
    """Normalize JSON/YAML loaded structure into canonical mapping.

    Expected top-level mapping of canonical_tag -> list of relation dicts.
    """
    out: Dict[str, List[Dict]] = {}
    if not isinstance(data, dict):
        raise ValueError("relationships data must be a mapping of tag -> list")
    for src, rels in data.items():
        if rels is None:
            continue
        if not isinstance(rels, list):
            raise ValueError(f"Expected list of relations for '{src}'")
        good: List[Dict] = []
        for entry in rels:
            if not isinstance(entry, dict):
                continue
            tag = entry.get("tag") or entry.get("target") or entry.get("to")
            if not tag:
                continue
            rel = {"tag": tag.strip().lower(), "type": (entry.get("type") or "related").strip()}
            if "weight" in entry:
                try:
                    rel["weight"] = float(entry["weight"])
                except Exception:
                    pass
            if "note" in entry:
                rel["note"] = entry["note"]
            good.append(rel)
        if good:
            out[str(src).strip().lower()] = good
    return out


def validate_relationships(
    relationships: Dict[str, List[Dict]],
    tag_index: Dict[str, int],
    tag_freqs: Optional[Dict[str, int]] = None,
    min_count: int = 5,
) -> Tuple[Dict[str, List[Dict]], List[str]]:
    """Validate relationships against known tags and optional frequencies.

    - Unknown tags (not in tag_index) are reported in warnings and removed.
    - If tag_freqs provided, relations are removed when either side is below
      `min_count` (per your preference to ignore low-frequency tags for manual mappings)

    Returns (cleaned_relationships, warnings)
    """
    cleaned: Dict[str, List[Dict]] = {}
    warnings: List[str] = []
    for src, rels in relationships.items():
        if src not in tag_index:
            warnings.append(f"Unknown source tag in manual mappings: '{src}'")
            continue
        for r in rels:
            tgt = r.get("tag")
            if tgt not in tag_index:
                warnings.append(f"Unknown target tag in manual mappings: '{tgt}' (from {src})")
                continue
            if tag_freqs is not None:
                fs = tag_freqs.get(src, 0)
                ft = tag_freqs.get(tgt, 0)
                if fs < min_count or ft < min_count:
                    warnings.append(
                        f"Ignoring manual mapping {src} -> {tgt} due to low frequency ({fs},{ft} < {min_count})"
                    )
                    continue
            cleaned.setdefault(src, []).append(r)
    return cleaned, warnings


def manual_score(relationships: Dict[str, List[Dict]], tag_a: str, tag_b: str) -> Optional[float]:
    """Return manual weight for (tag_a -> tag_b) if present, else None.

    This respects directionality: parent_child etc. are directional.
    """
    rels = relationships.get(tag_a, [])
    for r in rels:
        if r.get("tag") == tag_b:
            if "weight" in r:
                return float(r["weight"])
            return float(DEFAULT_TYPE_WEIGHTS.get(r.get("type"), 0.75))
    return None


def normalize_manual_weight(raw: float) -> float:
    """Normalize manual weight into [0,1] for combination.

    Negative values (exclude) are mapped to 0 but callers can inspect raw to
    handle exclude semantics.
    """
    if raw is None:
        return 0.0
    if raw < 0:
        return 0.0
    return max(0.0, min(1.0, float(raw)))


def merge_manual_with_auto(
    manual_raw: Optional[float], auto_score: float, alpha_manual: float = 0.5
) -> float:
    """Merge manual and automated scores into a single combined score in [0,1].

    manual_raw: raw weight from manual mappings (may be None)
    auto_score: automated similarity normalized to [0,1]
    alpha_manual: weight given to manual signal (0..1)
    """
    auto = float(max(0.0, min(1.0, auto_score)))
    if manual_raw is None:
        return auto
    manual_norm = normalize_manual_weight(manual_raw)
    combined = alpha_manual * manual_norm + (1.0 - alpha_manual) * auto
    return float(max(0.0, min(1.0, combined)))


def relation_label(relationships: Dict[str, List[Dict]], tag_a: str, tag_b: str) -> Optional[str]:
    """Return the relation type label if present for tag_a -> tag_b.
    """
    rels = relationships.get(tag_a, [])
    for r in rels:
        if r.get("tag") == tag_b:
            return r.get("type")
    return None


def suggest_candidates_from_db(
    session,
    min_count: int = 5,
    min_sim: float = 0.6,
    max_pairs: int = 200,
    limit_tags: Optional[int] = 500,
):
    """Suggest candidate related tag pairs from the database.

    Algorithm (approximate):
    - Load tags with frequency >= min_count
    - Build co-occurrence counts between tags using album membership: for each album,
      increment count for each pair of tags that appear on that album.
    - Build tag-context vectors where context is counts of co-occurrence with other tags.
    - Compute cosine similarity between tag-context sparse vectors; return pairs with
      similarity >= min_sim but with relatively low direct co-occurrence (candidate
      for related-but-distinct).

    This is intentionally conservative and runs in-memory; it may be slow on very
    large DBs. Use limit_tags to restrict to the most frequent tags.
    """
    # Lazy import Tag and Album to avoid circular imports at module load
    from albumexplore.database.models import Tag, Album

    # 1) load tags with frequency
    tags_q = session.query(Tag).filter(Tag.frequency >= min_count).order_by(Tag.frequency.desc())
    if limit_tags:
        tags_list = tags_q.limit(limit_tags).all()
    else:
        tags_list = tags_q.all()

    tag_names = [t.name.strip().lower() for t in tags_list if t.name]
    tag_id_map = {t.id: t.name.strip().lower() for t in tags_list}
    tag_name_set = set(tag_names)

    # build album -> tags mapping for these tags
    album_tags = {}
    # Query albums that have at least one of these tags
    albums = session.query(Album).join(Album.tags).filter(Tag.id.in_([t.id for t in tags_list])).distinct().all()
    for alb in albums:
        names = [t.name.strip().lower() for t in getattr(alb, 'tags', []) if t.name and t.name.strip().lower() in tag_name_set]
        if len(names) < 1:
            continue
        album_tags[alb.id] = names

    # cooccurrence counts: tag -> Counter of other_tag -> count
    from collections import defaultdict, Counter

    co_counts = defaultdict(Counter)
    for tags in album_tags.values():
        unique = list(set(tags))
        for i, a in enumerate(unique):
            for b in unique[i+1:]:
                co_counts[a][b] += 1
                co_counts[b][a] += 1

    # Build sparse vectors as dicts
    vectors = {tag: dict(counter) for tag, counter in co_counts.items()}

    # Compute cosine similarity between context vectors
    def cosine_dict(a: dict, b: dict) -> float:
        # dot product
        dot = 0.0
        for k, v in a.items():
            if k in b:
                dot += v * b[k]
        norm_a = sum(v * v for v in a.values()) ** 0.5
        norm_b = sum(v * v for v in b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # produce candidate pairs
    candidates = []
    tag_keys = list(vectors.keys())
    for i, a in enumerate(tag_keys):
        va = vectors[a]
        for b in tag_keys[i+1:]:
            vb = vectors[b]
            sim = cosine_dict(va, vb)
            direct = co_counts.get(a, {}).get(b, 0)
            # Suggest pairs with high context similarity but low direct cooccurrence
            if sim >= min_sim and direct <= max(1, int(min_count / 2)):
                candidates.append((a, b, sim, direct))

    # sort by similarity desc and limit
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:max_pairs]
