#!/usr/bin/env python3
"""Simple test to load CSV data and check for vocal style tags."""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database.csv_loader import load_csv_data
from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag

def main():
    print("=== LOADING CSV AND CHECKING VOCAL TAGS ===\n")
    
    # Load CSV data
    print("1. Loading CSV files...")
    csv_dir = Path("csv")
    load_csv_data(csv_dir)
    print("   CSV loading complete\n")
    
    # Check database
    print("2. Checking database for vocal style tags...")
    session = get_session()
    
    # Check vocal tags
    vocal_tags = session.query(Tag).filter(
        Tag.name.in_(['harsh vocals', 'clean vocals', 'mixed vocals', 'instru.'])
    ).all()
    
    print(f"Found {len(vocal_tags)} vocal style tags:")
    for tag in vocal_tags:
        print(f"  '{tag.name}': {len(tag.albums)} albums")
    
    # Check albums with vocal styles
    albums_with_vocal = session.query(Album).filter(
        Album.vocal_style.isnot(None)
    ).limit(10).all()
    
    print(f"\nFound {len(albums_with_vocal)} albums with vocal_style field:")
    for album in albums_with_vocal:
        print(f"  {album.artist} - {album.title}")
        print(f"    Vocal style: '{album.vocal_style}'")
        vocal_style_tags = [tag.name for tag in album.tags if tag.name in ['harsh vocals', 'clean vocals', 'mixed vocals', 'instru.']]
        print(f"    Vocal tags: {vocal_style_tags}")
        print()
    
    session.close()
    
    if len(vocal_tags) > 0:
        print("✅ SUCCESS: Vocal style tags have been created and assigned!")
    else:
        print("❌ ISSUE: No vocal style tags found")

if __name__ == "__main__":
    main()
