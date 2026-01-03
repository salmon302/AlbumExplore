#!/usr/bin/env python3
"""
Check current database state for vocal style data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import session_scope
from albumexplore.database.models import Album, Tag

def main():
    try:
        with session_scope() as session:
            # Check total albums and tags
            total_albums = session.query(Album).count()
            total_tags = session.query(Tag).count()
            print(f"Total albums: {total_albums}")
            print(f"Total tags: {total_tags}")
            
            # Check vocal style tags specifically
            vocal_tags = session.query(Tag).filter(
                Tag.name.in_(['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.'])
            ).all()
            
            print(f"Vocal style tags found: {len(vocal_tags)}")
            for tag in vocal_tags:
                album_count = session.query(Album).join(Album.tags).filter(Tag.id == tag.id).count()
                print(f"  - {tag.name}: {album_count} albums")
            
            # Check albums with vocal_style field
            albums_with_vocal_style = session.query(Album).filter(Album.vocal_style.isnot(None)).count()
            print(f"Albums with vocal_style field: {albums_with_vocal_style}")
            
            if total_albums == 0:
                print("Database is empty - need to reload data")
            elif len(vocal_tags) == 0:
                print("No vocal style tags found - vocal extraction may not be working")
            else:
                print("Database has vocal style data - checking visualization layer...")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
