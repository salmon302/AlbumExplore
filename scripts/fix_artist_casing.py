import json
import logging
import sys
from pathlib import Path
from sqlalchemy import func
from tqdm import tqdm

from albumexplore.database import session_scope, models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def load_canonical_names_from_manifest():
    """
    Load mapping of lowercase name -> canonical name from Last.fm manifest.
    """
    manifest_path = Path("raw_data/lastfm/MANIFEST.json")
    if not manifest_path.exists():
        logger.error(f"Manifest not found at {manifest_path}")
        return {}
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading manifest: {e}")
        return {}

    mapping = {}
    
    # Process artists explicitly fetched
    artists_fetched = data.get("artists_fetched", {})
    for info in artists_fetched.values():
        name = info.get("artist")
        if name:
            mapping[name.lower()] = name
            
    # Also process albums fetched, as they store artist name too
    albums_fetched = data.get("albums_fetched", {})
    for info in albums_fetched.values():
        name = info.get("artist")
        if name:
            mapping[name.lower()] = name
            
    logger.info(f"Loaded {len(mapping)} canonical artist names from manifest.")
    return mapping

def fix_casing(dry_run=True):
    """
    Scan DB for artists with ALL CAPS names and try to fix them using the manifest.
    """
    mapping = load_canonical_names_from_manifest()
    if not mapping:
        logger.warning("No mapping available. Aborting.")
        return

    with session_scope() as session:
        # Find all distinct artist names currently on albums
        # Only target those that look like ALL CAPS (simple heuristic: isupper and len > 2)
        # We fetch ALL names and filter in python to be safe and cross-check everything
        
        albums = session.query(models.Album).all()
        
        # Group by artist name to update efficiently?
        # Better: iterate distinct names, keep set of updates
        
        updates = {} # current_caps_name -> new_proper_name
        
        distinct_names = set(a.pa_artist_name_on_album for a in albums if a.pa_artist_name_on_album)
        
        logger.info(f"Checking {len(distinct_names)} distinct artist names in DB...")
        
        fixed_count = 0
        unknown_count = 0
        
        for name in tqdm(distinct_names, desc="Analyzing Artists"):
            # Check if it looks bad (ALL CAPS)
            # OR simple case-insensitive check against our canonical list
            
            lower_name = name.lower()
            
            if lower_name in mapping:
                canonical = mapping[lower_name]
                
                # If current name differs from canonical (and canonical isn't just ALL CAPS itself)
                if name != canonical:
                    # Special check: If lookup name is same but just casing, we fix it.
                    # If lookup name is totally different (e.g. variation), we might fix it too?
                    # The user mentioned "correction to the case".
                    
                    updates[name] = canonical
                    fixed_count += 1
            else:
                # User mentioned "ProgArchives employs all caps"
                # If we don't have it in Last.fm, maybe attempt Title Case for purely ALL CAPS names?
                if name.isupper() and len(name) > 3:
                    # Simple heuristic: TITLE CASE
                    title_cased = name.title()
                    # Log this as a heuristic fix
                    # updates[name] = title_cased 
                    # Actually, let's be conservative. If not in Last.fm, leave it or log it.
                    unknown_count += 1

        logger.info(f"Found {len(updates)} artists to rename.")
        
        if not updates:
            return

        # Apply updates
        if dry_run:
            logger.info("DRY RUN: Samples of changes:")
            for i, (old, new) in enumerate(updates.items()):
                if i < 10:
                    logger.info(f"  '{old}' -> '{new}'")
            logger.info("To apply, run with dry_run=False")
        else:
            logger.info("Applying updates to database...")
            # We must update all albums with these names
            
            # This could be slow if we iterate one by one.
            # Batch update via SQL is better.
            
            # For SqlAlchemy, we can iterate:
            for old, new in tqdm(updates.items(), desc="Updating DB"):
                session.query(models.Album).filter(
                    models.Album.pa_artist_name_on_album == old
                ).update({models.Album.pa_artist_name_on_album: new}, synchronize_session=False)
            
            # Also update any created Artists? (None exist yet per previous check)
            
            logger.info("Updates committed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply changes to DB")
    args = parser.parse_args()
    
    fix_casing(dry_run=not args.apply)
