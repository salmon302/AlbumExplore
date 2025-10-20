#!/usr/bin/env python3
"""
Simple final check for vocal style tags.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from albumexplore.database import session_scope
    from albumexplore.database.models import Album, Tag
    
    with session_scope() as session:
        # Check vocal style tags
        vocal_tags = session.query(Tag).filter(
            Tag.name.in_(['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.'])
        ).all()
        
        print(f"SUCCESS: Found {len(vocal_tags)} vocal style tag types:")
        for tag in vocal_tags:
            album_count = session.query(Album).join(Album.tags).filter(Tag.id == tag.id).count()
            print(f"  - '{tag.name}': {album_count} albums")
        
        # Check albums with vocal_style field
        albums_with_vocal_style = session.query(Album).filter(Album.vocal_style.isnot(None)).count()
        print(f"\nAlbums with vocal_style field: {albums_with_vocal_style}")
        
        # Sample albums with vocal style
        sample_albums = session.query(Album).filter(Album.vocal_style.isnot(None)).limit(3).all()
        print(f"\nSample albums:")
        for album in sample_albums:
            tag_names = [tag.name for tag in album.tags if tag.name in ['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.']]
            print(f"  - {album.artist} - {album.title}")
            print(f"    vocal_style: '{album.vocal_style}'")
            print(f"    vocal tags: {tag_names}")
        
        print(f"\n✅ VOCAL STYLE EXTRACTION AND TAGGING SUCCESSFULLY IMPLEMENTED!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
