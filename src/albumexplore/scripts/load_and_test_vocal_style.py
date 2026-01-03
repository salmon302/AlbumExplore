"""
Load CSV data and test vocal style implementation.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pathlib import Path
from albumexplore.database.csv_loader import load_csv_data
from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag

def load_and_test_vocal_style():
    """Load CSV data and test if vocal style is working."""
    
    csv_dir = Path("csv")
    if not csv_dir.exists():
        print("❌ CSV directory not found")
        return
    
    print("🔄 Loading CSV data...")
    try:
        load_csv_data(csv_dir)
        print("✅ CSV data loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading CSV data: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🔍 Checking vocal style data...")
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
                # Get vocal style tags for this album
                vocal_tags = [tag.name for tag in album.tags if 'vocal' in tag.name.lower() or tag.name == 'instrumental']
                print(f"  {album.pa_artist_name_on_album} - {album.title}")
                print(f"    Vocal Style: {album.vocal_style}")
                print(f"    Vocal Tags: {vocal_tags}")
                print()
        
        # Check for vocal style tags
        vocal_tags = session.query(Tag).filter(
            Tag.name.like('%vocal%')
        ).all()
        
        if vocal_tags:
            print(f"\nFound {len(vocal_tags)} vocal-related tags:")
            for tag in vocal_tags:
                albums_count = len(tag.albums)
                print(f"  - {tag.name} (used by {albums_count} albums)")
        
        # Check for instrumental tags
        instrumental_tags = session.query(Tag).filter(
            Tag.name == 'instrumental'
        ).all()
        
        if instrumental_tags:
            print(f"\nInstrumental tags:")
            for tag in instrumental_tags:
                albums_count = len(tag.albums)
                print(f"  - {tag.name} (used by {albums_count} albums)")
                
    except Exception as e:
        print(f"❌ Error checking data: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    load_and_test_vocal_style()
