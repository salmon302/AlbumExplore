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

def is_all_caps(name):
    # Allow some non-letters, but mostly check if it has letters and no lowercase
    if not name: return False
    # Check if it has any letter
    if not any(c.isalpha() for c in name): return False
    # Check if it has any lowercase
    if any(c.islower() for c in name): return False
    return True

def fix_casing(dry_run=True):
    """
    Scan DB for artists with ALL CAPS names and try to fix them using the manifest.
    """
    mapping = load_canonical_names_from_manifest()
    if not mapping:
        logger.warning("No mapping available. Aborting.")
        return

    with session_scope() as session:
        albums = session.query(models.Album).all()
        
        updates = {} # current_caps_name -> new_proper_name
        
        distinct_names = set(a.pa_artist_name_on_album for a in albums if a.pa_artist_name_on_album)
        
        logger.info(f"Checking {len(distinct_names)} distinct artist names in DB...")
        
        all_caps_count = 0
        fixable_count = 0
        
        for name in tqdm(distinct_names, desc="Analyzing Artists"):
            if is_all_caps(name):
                all_caps_count += 1
                lower_name = name.lower()
                
                if lower_name in mapping:
                    canonical = mapping[lower_name]
                    # Only apply if canonical is NOT all caps
                    # e.g. "PINK FLOYD" -> "Pink Floyd" (Update)
                    # "OHHMS" -> "OHHMS" (No change)
                    if not is_all_caps(canonical):
                        updates[name] = canonical
                        fixable_count += 1
                    else:
                        logger.info(f"Last.fm also has ALL CAPS for: {name}")
                else:
                    # Fallback: Title Case heuristic for unknowns
                    # e.g. "UNKNOWN BAND" -> "Unknown Band"
                    if len(name) > 3:
                        title_cased = name.title()
                        updates[name] = title_cased
                    else:
                        logger.warning(f"Skipping short ALL CAPS name: {name}")

        
        logger.info(f"Found {all_caps_count} ALL CAPS names.")
        logger.info(f"Proposed fixes for {len(updates)} names.")
        
        if not updates:
            return

        # Apply updates
        if dry_run:
            logger.info("DRY RUN: Samples of changes:")
            count = 0
            # Sort for stable output
            for old in sorted(updates.keys()):
                if count < 20: 
                    logger.info(f"  '{old}' -> '{updates[old]}'")
                    count += 1
            logger.info("To apply, run with dry_run=False")
        else:
            logger.info("Applying updates to database...")
            for old, new in tqdm(updates.items(), desc="Updating DB"):
                session.query(models.Album).filter(
                    models.Album.pa_artist_name_on_album == old
                ).update({models.Album.pa_artist_name_on_album: new}, synchronize_session=False)
            
            logger.info("Updates committed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply changes to DB")
    args = parser.parse_args()
    
    fix_casing(dry_run=not args.apply)
