"""Simple script to check vocal style data without reinitializing database."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag

def check_vocal_data():
    """Quick check for vocal data."""
    with get_session() as session:
        # Check if we have any albums
        total_albums = session.query(Album).count()
        print(f"Total albums in database: {total_albums}")
        
        # Check if we have any vocal style tags
        vocal_tags = session.query(Tag).filter(
            Tag.name.ilike('%vocal%')
        ).all()
        print(f"Vocal tags found: {[tag.name for tag in vocal_tags]}")
        
        # Check albums with vocal_style field
        albums_with_vocal_field = session.query(Album).filter(
            Album.vocal_style.isnot(None)
        ).all()
        print(f"Albums with vocal_style field: {len(albums_with_vocal_field)}")
        
        if albums_with_vocal_field:
            for album in albums_with_vocal_field[:5]:
                print(f"  {album.pa_artist_name_on_album} - {album.title}: {album.vocal_style}")
        
        # Check for any albums that have vocal tags
        albums_with_vocal_tags = session.query(Album).join(Album.tags).filter(
            Tag.name.ilike('%vocal%')
        ).all()
        print(f"Albums with vocal tags: {len(albums_with_vocal_tags)}")
        
        if albums_with_vocal_tags:
            for album in albums_with_vocal_tags[:5]:
                vocal_tags = [tag.name for tag in album.tags if 'vocal' in tag.name.lower()]
                print(f"  {album.pa_artist_name_on_album} - {album.title}: {vocal_tags}")
        
        # Check for instrumental tags
        instrumental_tags = session.query(Tag).filter(
            Tag.name.ilike('%instru%')
        ).all()
        print(f"Instrumental tags found: {[tag.name for tag in instrumental_tags]}")

if __name__ == "__main__":
    check_vocal_data()
