#!/usr/bin/env python3
"""
Simple test to check vocal tags in database
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from albumexplore.database import session_scope
    from albumexplore.database.models import Album, Tag
    
    print("=== Simple Vocal Tags Test ===")
    
    with session_scope() as session:
        # Count total albums
        total_albums = session.query(Album).count()
        print(f"Total albums: {total_albums}")
        
        # Count vocal style tags
        vocal_tag_names = ['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.']
        vocal_tags = session.query(Tag).filter(Tag.name.in_(vocal_tag_names)).all()
        
        print(f"Vocal style tags found: {len(vocal_tags)}")
        
        for tag in vocal_tags:
            album_count = session.query(Album).join(Album.tags).filter(Tag.id == tag.id).count()
            print(f"  {tag.name}: {album_count} albums")
            
        # Show a few examples
        if vocal_tags:
            sample_albums = session.query(Album).join(Album.tags).filter(
                Tag.name.in_(vocal_tag_names)
            ).limit(3).all()
            
            print(f"\nSample albums with vocal tags:")
            for album in sample_albums:
                vocal_tags_for_album = [tag.name for tag in album.tags if tag.name in vocal_tag_names]
                print(f"  {album.artist} - {album.title}: {vocal_tags_for_album}")
            
            print("\n✅ SUCCESS: Vocal style tags are working!")
        else:
            print("\n❌ No vocal style tags found")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
