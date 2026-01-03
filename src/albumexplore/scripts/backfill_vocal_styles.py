#!/usr/bin/env python3
"""Backfill vocal style information for existing albums."""

import csv
import uuid
from pathlib import Path
from typing import List, Tuple

from albumexplore.database import session_scope
from albumexplore.database.models import Album, Tag
from albumexplore.database.csv_loader import (
    extract_vocal_style_tags,
    build_raw_tags_string,
    normalize_tag,
)

CSV_DIR = Path("csv")
HEADER_PREFIX = "Artist,Album,Release Date"


def _find_header_line(path: Path) -> int:
    """Locate the header row index in the Reddit-format CSV files."""
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if line.strip().startswith(HEADER_PREFIX):
                return index
    raise ValueError(f"Could not find header row in {path.name}")


def _read_csv_rows(path: Path) -> List[dict]:
    header_row = _find_header_line(path)

    with path.open("r", encoding="utf-8") as handle:
        for _ in range(header_row):
            next(handle)
        reader = csv.DictReader(handle)
        return [row for row in reader if row]


def _ensure_vocal_tag(session, tag_name: str) -> Tag:
    normalized = normalize_tag(tag_name)
    tag = session.query(Tag).filter(Tag.normalized_name == normalized).first()
    if tag:
        return tag

    tag = Tag(
        id=str(uuid.uuid4()),
        name=normalized,
        normalized_name=normalized,
        is_canonical=1,
    )
    session.add(tag)
    session.flush()
    return tag


def _update_album_from_row(session, row: dict) -> Tuple[bool, bool]:
    artist = (row.get("Artist") or "").strip()
    album_title = (row.get("Album") or "").strip()
    genre_string = (row.get("Genre / Subgenres") or row.get("Genre") or "").strip()
    vocal_style_raw = (row.get("Vocal Style") or row.get("Vocal") or "").strip()

    if not artist or not album_title:
        return False, False

    album = (
        session.query(Album)
        .filter(Album.pa_artist_name_on_album == artist)
        .filter(Album.title == album_title)
        .first()
    )
    if not album:
        return False, False

    vocal_style_tags = extract_vocal_style_tags(vocal_style_raw)
    if not vocal_style_tags:
        return False, False

    vocal_style_display = ", ".join(vocal_style_tags)
    album.vocal_style = vocal_style_display
    if genre_string:
        album.genre = genre_string

    if genre_string:
        base_components = [part.strip() for part in genre_string.split(",") if part.strip()]
    else:
        base_components = [part.strip() for part in (album.raw_tags or "").split(",") if part.strip()]

    components: List[str] = []
    for part in base_components:
        if part and part not in components:
            components.append(part)

    for tag in vocal_style_tags:
        if tag not in components:
            components.append(tag)

    album.raw_tags = ", ".join(components)

    updated = False
    for tag_name in vocal_style_tags:
        tag = _ensure_vocal_tag(session, tag_name)
        if tag not in album.tags:
            album.tags.append(tag)
            updated = True

    return True, updated


def backfill_vocals(csv_dir: Path = CSV_DIR) -> None:
    processed_albums = 0
    updated_tags = 0

    with session_scope() as session:
        for csv_path in sorted(csv_dir.glob("*.csv")):
            try:
                rows = _read_csv_rows(csv_path)
            except Exception as exc:
                print(f"Skipping {csv_path.name}: {exc}")
                continue

            for row in rows:
                found, updated = _update_album_from_row(session, row)
                if found:
                    processed_albums += 1
                    if updated:
                        updated_tags += 1

        session.commit()

    print(f"Albums with vocal styles updated: {processed_albums}")
    print(f"Albums with new vocal tags appended: {updated_tags}")


if __name__ == "__main__":
    backfill_vocals()
