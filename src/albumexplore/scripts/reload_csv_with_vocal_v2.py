#!/usr/bin/env python3
"""
Reload CSV data with vocal style extraction enabled.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import init_db, session_scope
from albumexplore.database.csv_loader import _process_csv_file
from albumexplore.database.models import Album, Tag
from pathlib import Path

def main():
    print("=== Reloading CSV Data with Vocal Style Extraction ===\n")
    
    # Initialize database (this will clear existing data)
    init_db()
    print("Database initialized successfully.")
    
    # Load one CSV file with vocal extraction
    csv_path = "csv/_r_ProgMetal _ Yearly Albums - 2023 Prog-metal.csv"
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file {csv_path} not found")
        return
    
    print(f"Loading data from {csv_path}...")
    
    try:
        with session_scope() as session:
            # Use the internal _process_csv_file function directly
            _process_csv_file(Path(csv_path), 2023, session)
            print(f"Successfully loaded data from {csv_path}")
            
            # Check results
            total_albums = session.query(Album).count()
            total_tags = session.query(Tag).count()
            print(f"Total albums: {total_albums}")
            print(f"Total tags: {total_tags}")
            
            # Check vocal style tags specifically
            vocal_tags = session.query(Tag).filter(
                Tag.name.in_(['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.'])
            ).all()
            
            print(f"\nVocal style tags found: {len(vocal_tags)}")
            for tag in vocal_tags:
                album_count = session.query(Album).join(Album.tags).filter(Tag.id == tag.id).count()
                print(f"  - {tag.name}: {album_count} albums")
            
            # Show a few sample albums with vocal style
            sample_albums = session.query(Album).filter(Album.vocal_style.isnot(None)).limit(3).all()
            print(f"\nSample albums with vocal style:")
            for album in sample_albums:
                tag_names = [tag.name for tag in album.tags if tag.name in ['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.']]
                print(f"  - {album.artist} - {album.title}")
                print(f"    vocal_style: '{album.vocal_style}'")
                print(f"    vocal tags: {tag_names}")
                print(f"    all tags: {[tag.name for tag in album.tags]}")
                
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
