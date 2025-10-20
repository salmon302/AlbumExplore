#!/usr/bin/env python3
"""
Final verification script for vocal style tags after successful reload.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import get_session, session_scope
from albumexplore.database.models import Album, Tag
from albumexplore.visualization.data_interface import DataInterface, DataConfig
from sqlalchemy import func

def main():
    print("=== Final Vocal Style Tags Verification ===\n")
    
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
        
        print(f"\nVocal style tags found: {len(vocal_tags)}")
        for tag in vocal_tags:
            album_count = session.query(Album).join(Album.tags).filter(Tag.id == tag.id).count()
            print(f"  - {tag.name}: {album_count} albums")
        
        # Check albums with vocal_style field set
        albums_with_vocal_style = session.query(Album).filter(Album.vocal_style.isnot(None)).count()
        print(f"\nAlbums with vocal_style field: {albums_with_vocal_style}")
        
        # Sample albums with vocal style
        sample_albums = session.query(Album).filter(Album.vocal_style.isnot(None)).limit(5).all()
        print(f"\nSample albums with vocal style:")
        for album in sample_albums:
            tag_names = [tag.name for tag in album.tags if tag.name in ['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.']]
            print(f"  - {album.artist} - {album.title}: vocal_style='{album.vocal_style}', vocal tags: {tag_names}")
    
    # Test visualization layer
    print(f"\n=== Testing Visualization Layer ===")
    try:
        data_interface = DataInterface()
        config = DataConfig(limit=50)  # Get first 50 albums
        node_data = data_interface.get_visible_data(config)
        
        print(f"Retrieved {len(node_data)} nodes from visualization layer")
        
        # Check for vocal style tags in node data
        vocal_tag_count = 0
        sample_vocal_nodes = []
        
        for node in node_data:
            node_tags = node.get('tags', [])
            vocal_tags_in_node = [tag for tag in node_tags if tag in ['clean vocals', 'harsh vocals', 'mixed vocals', 'instru.']]
            if vocal_tags_in_node:
                vocal_tag_count += 1
                if len(sample_vocal_nodes) < 5:
                    sample_vocal_nodes.append({
                        'artist': node.get('artist', 'Unknown'),
                        'title': node.get('title', 'Unknown'),
                        'vocal_tags': vocal_tags_in_node
                    })
        
        print(f"Nodes with vocal style tags: {vocal_tag_count}")
        print(f"Sample nodes with vocal tags:")
        for node in sample_vocal_nodes:
            print(f"  - {node['artist']} - {node['title']}: {node['vocal_tags']}")
        
        if vocal_tag_count > 0:
            print(f"\n✅ SUCCESS: Vocal style tags are present in both database and visualization layer!")
        else:
            print(f"\n❌ WARNING: No vocal style tags found in visualization layer")
            
    except Exception as e:
        print(f"Error testing visualization layer: {e}")

if __name__ == "__main__":
    main()
