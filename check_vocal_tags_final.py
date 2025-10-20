#!/usr/bin/env python3
"""Final check for vocal style tags in database and visualization."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag
from albumexplore.visualization.data_interface import DataInterface, DataConfig

def main():
    print("=== FINAL VOCAL STYLE TAG CHECK ===\n")
    
    # Check database
    print("1. Checking database for vocal style tags...")
    session = get_session()
    vocal_tags = session.query(Tag).filter(
        Tag.name.in_(['harsh vocals', 'clean vocals', 'mixed vocals', 'instru.'])
    ).all()
    
    print(f"Found {len(vocal_tags)} vocal style tags:")
    for tag in vocal_tags:
        print(f"  '{tag.name}': {len(tag.albums)} albums")
    
    # Check specific albums
    print("\n2. Checking specific albums with vocal styles...")
    albums_with_vocal = session.query(Album).filter(
        Album.vocal_style.isnot(None)
    ).limit(5).all()
    
    for album in albums_with_vocal:
        print(f"  {album.artist} - {album.title}")
        print(f"    Vocal style: '{album.vocal_style}'")
        print(f"    Tags: {[tag.name for tag in album.tags]}")
        print()
    
    # Check visualization
    print("3. Checking visualization node data...")
    config = DataConfig()
    data_interface = DataInterface(config)
    node_data = data_interface.get_node_data()
    
    print(f"Total nodes in visualization: {len(node_data)}")
    
    # Find nodes with vocal style tags
    vocal_nodes = []
    for node in node_data:
        tags = node.get('tags', [])
        vocal_tags_in_node = [tag for tag in tags if tag in ['harsh vocals', 'clean vocals', 'mixed vocals', 'instru.']]
        if vocal_tags_in_node:
            vocal_nodes.append((node, vocal_tags_in_node))
    
    print(f"Nodes with vocal style tags: {len(vocal_nodes)}")
    
    # Show first few examples
    for i, (node, vocal_tags) in enumerate(vocal_nodes[:5]):
        print(f"  {node.get('artist')} - {node.get('title')}")
        print(f"    Vocal tags: {vocal_tags}")
        print(f"    All tags: {node.get('tags', [])}")
        print()
    
    # Summary
    print("4. Summary:")
    print(f"  - Vocal style tags in database: {len(vocal_tags)}")
    print(f"  - Albums with vocal_style field: {len(albums_with_vocal)}")
    print(f"  - Nodes with vocal tags in visualization: {len(vocal_nodes)}")
    
    if len(vocal_nodes) > 0:
        print("\n✅ SUCCESS: Vocal style tags are present in the visualization!")
    else:
        print("\n❌ ISSUE: No vocal style tags found in visualization nodes")
    
    session.close()

if __name__ == "__main__":
    main()
