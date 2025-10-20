#!/usr/bin/env python3
"""Force fresh reload of CSV data with vocal style extraction."""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database.csv_loader import _process_csv_file
from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag

def main():
    print("=== FORCE RELOAD TEST ===\n")
    
    # Process one CSV file manually to test vocal extraction
    print("1. Processing a single CSV file with vocal extraction...")
    session = get_session()
    
    # Find a CSV file to process
    csv_dir = Path("csv")
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        print("No CSV files found!")
        return
    
    # Use the 2023 Prog-metal file which has vocal style data
    test_file = None
    for file in csv_files:
        if "2023" in file.name and "Prog-metal" in file.name:
            test_file = file
            break
    
    if not test_file:
        test_file = csv_files[0]  # Fall back to any file
    
    print(f"Processing file: {test_file}")
    
    # Clear any existing albums first to test fresh load
    session.query(Album).delete()
    session.query(Tag).delete()
    session.commit()
    
    # Process the file
    year = 2023  # Set explicit year
    _process_csv_file(test_file, year, session)
    
    # Check results
    print("\n2. Checking results...")
    
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
        print("SUCCESS: Vocal style tags have been created and assigned!")
    else:
        print("ISSUE: No vocal style tags found")

if __name__ == "__main__":
    main()
