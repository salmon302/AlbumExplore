import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from albumexplore.database.models import Album, Tag, album_tags
# from albumexplore.database import get_db_engine # Removed unused import
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.utils import generate_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_metalarchives_tags(dry_run=False):
    """
    Process existing albums with 'genre' strings and populate the 'tags' table.
    """
    # 1. Setup DB
    # We'll rely on environment variable or default
    from dotenv import load_dotenv
    load_dotenv()
    
    import os
    db_uri = os.getenv("DATABASE_URL", "sqlite:///albumexplore.db")
    engine = create_engine(db_uri) # Basic engine
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. Setup Normalizer
    normalizer = TagNormalizer()
    
    try:
        # 3. Fetch target albums
        # We target albums that have a genre string but might be missing tags.
        # Or simply all albums with a genre string to ensure consistency.
        # Since the user complained about low tag counts, we can process all.
        logger.info("Fetching albums with genre data...")
        albums = session.query(Album).filter(Album.genre != None).all()
        
        logger.info(f"Found {len(albums)} albums with genre data.")
        
        # Cache tags to avoid constant DB lookups
        tag_cache = {}
        all_tags = session.query(Tag).all()
        for t in all_tags:
            tag_cache[t.name] = t
            
        updated_count = 0
        
        for album in tqdm(albums, desc="Processing tags"):
            if not album.genre:
                continue
                
            # Parse tags from genre string
            # MetalArchives genres are often: "Death Metal", "Power/Speed Metal", "Heavy Metal (early); Power Metal (later)"
            # split_multi_tags handles '/' but maybe not ';', let's handle that first.
            raw_genre = album.genre.replace(';', '/')
            
            # Use normalizer to split and clean
            tag_names = normalizer.split_multi_tags(raw_genre)
            
            # Link tags
            current_tags = set(t.name for t in album.tags)
            modified = False
            
            for tag_name in tag_names:
                if not tag_name:
                    continue
                    
                # Ensure tag exists
                if tag_name not in tag_cache:
                    new_tag = Tag(
                        id=generate_id('tag_'),
                        name=tag_name,
                        normalized_name=normalizer.normalize(tag_name),
                        is_canonical=1, # Default to 1 for now
                        frequency=0
                    )
                    session.add(new_tag)
                    tag_cache[tag_name] = new_tag
                    # flush to generate ID if needed? No, we generated it.
                
                tag_obj = tag_cache[tag_name]
                
                if tag_name not in current_tags:
                    album.tags.append(tag_obj)
                    tag_obj.frequency = (tag_obj.frequency or 0) + 1
                    modified = True
            
            if modified:
                updated_count += 1
                
        if dry_run:
            logger.info("Dry run complete. Rolling back.")
            session.rollback()
        else:
            logger.info(f"Committing changes for {updated_count} albums...")
            session.commit()
            logger.info("Done.")
            
    except Exception as e:
        logger.error(f"Error processing tags: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    process_metalarchives_tags(dry_run=args.dry_run)
