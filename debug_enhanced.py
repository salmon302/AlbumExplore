"""
Enhanced debugging tool for AlbumExplore CSV loading.
This script helps detect and fix issues with problematic albums.
"""
import logging
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# List of problematic albums to test
PROBLEMATIC_ALBUMS = [
    {"artist": "Empire State Bastard", "album": "-", "year": 2023},
    {"artist": "Rusty Bonez", "album": "Mat 4", "year": 2023},
    {"artist": "Ihsahn", "album": "2LP", "year": 2024},
    {"artist": "Black Country Communion", "album": "Early 2024", "year": 2024},
    {"artist": "Moron Police", "album": "2LP", "year": 2025},
]

def test_problematic_albums():
    """Test loading the problematic albums specifically."""
    logger.info("Testing problematic albums...")
    
    # Import here to avoid circular imports
    from albumexplore.database.csv_loader import load_csv_data
    from albumexplore.database import get_session, init_db  # IMPORTANT: Using init_db not init_database
    from albumexplore.database.models import Album
    
    # First initialize the database with a clean slate
    logger.info("Initializing clean database...")
    db_path = Path("albumexplore.db")
    if db_path.exists():
        os.remove(db_path)
    
    # Initialize the database
    init_db(f"sqlite:///{db_path}")
    
    # Get CSV directory
    csv_dir = Path("csv")
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return
    
    # Load CSV data
    logger.info(f"Loading CSV data from {csv_dir}...")
    load_csv_data(csv_dir)
    
    # Now check if our problematic albums were loaded
    session = get_session()
    for album_info in PROBLEMATIC_ALBUMS:
        artist = album_info["artist"]
        album_title = album_info["album"]
        year = album_info["year"]
        
        # Search for the album in the database
        albums = session.query(Album).filter(
            Album.artist.like(f"%{artist}%"),
            Album.release_year == year
        ).all()
        
        if albums:
            logger.info(f"✅ Found {len(albums)} albums for artist '{artist}' in year {year}:")
            for album in albums:
                logger.info(f"  - {album.title} (Release date: {album.release_date})")
        else:
            logger.error(f"❌ No albums found for artist '{artist}' in year {year}")
    
    session.close()

if __name__ == "__main__":
    logger.info("Starting enhanced debug application for AlbumExplore")
    
    try:
        # Using the correct function name from your module
        from albumexplore.database import init_db, get_session
        
        # Rebuild database and test problematic albums
        test_problematic_albums()
        
    except Exception as e:
        logger.error(f"Error in enhanced debug application: {str(e)}", exc_info=True)
