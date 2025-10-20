"""
Check existing data in the database to see if vocal style is populated.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag

def check_existing_vocal_style_data():
    """Check if any existing albums have vocal style data."""
    
    session = get_session()
    try:
        # Check total albums
        total_albums = session.query(Album).count()
        print(f"Total albums in database: {total_albums}")
        
        # Check albums with vocal style data
        albums_with_vocal_style = session.query(Album).filter(
            Album.vocal_style.isnot(None),
            Album.vocal_style != ''
        ).count()
        print(f"Albums with vocal style data: {albums_with_vocal_style}")
        
        # Sample albums with vocal style
        sample_albums = session.query(Album).filter(
            Album.vocal_style.isnot(None),
            Album.vocal_style != ''
        ).limit(10).all()
        
        if sample_albums:
            print("\nSample albums with vocal style data:")
            for album in sample_albums:
                print(f"  {album.pa_artist_name_on_album} - {album.title}: {album.vocal_style}")
        else:
            print("\n❌ No albums found with vocal style data")
        
        # Check for vocal style tags
        vocal_tags = session.query(Tag).filter(
            Tag.name.like('%vocal%')
        ).all()
        
        if vocal_tags:
            print(f"\nFound {len(vocal_tags)} vocal-related tags:")
            for tag in vocal_tags:
                print(f"  - {tag.name}")
        else:
            print("\n❌ No vocal-related tags found")
            
        # Check for instrumental tags
        instrumental_tags = session.query(Tag).filter(
            Tag.name == 'instrumental'
        ).all()
        
        if instrumental_tags:
            print(f"\nFound instrumental tags:")
            for tag in instrumental_tags:
                albums_count = len(tag.albums)
                print(f"  - {tag.name} (used by {albums_count} albums)")
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_existing_vocal_style_data()
