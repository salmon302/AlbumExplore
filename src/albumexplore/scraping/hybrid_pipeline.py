import logging
import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure we can import from src
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir / 'src') not in sys.path:
    sys.path.insert(0, str(root_dir / 'src'))

from albumexplore.scraping.progarchives.collectors import ProgArchivesCollector
from albumexplore.scraping.lastfm.fetcher import LastFmFetcher
from albumexplore.database import session_scope
from albumexplore.database import models as db_models

# Load env vars (for LASTFM_API_KEY)
load_dotenv()

# Configure logging
log_path = Path("logs/hybrid_pipeline.log")
log_path.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("hybrid_pipeline")

def run_hybrid_collection(
    pa_output_dir: str = "raw_data/progarchives",
    lastfm_output_dir: str = "raw_data/lastfm",
    output_dir: str = None, # Alias for pa_output_dir for compatibility
    letters: str = None,
    force_reindex: bool = False,
    limit: int = 0,
    delay: float = 1.0,
    use_browser: bool = False,
    browser_headful: bool = False,
    progress_callback=None,
    stop_check=None
):
    """
    Run the Hybrid Pipeline:
    1. Scrape/Load Artist Index from ProgArchives.
    2. Hydrate Artist Data + Discography from Last.fm API.
    """
    if output_dir:
        pa_output_dir = output_dir

    # Check API Key
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        logger.error("LASTFM_API_KEY not found in environment variables. creating .env template...")
        try:
            with open(".env.example", "w") as f:
                f.write("LASTFM_API_KEY=your_key_here\nLASTFM_SHARED_SECRET=your_secret_here\n")
        except Exception:
            pass
        error_msg = "Please add your LASTFM_API_KEY to a .env file."
        logger.error(error_msg)
        if progress_callback:
            progress_callback(0, 0, f"Error: {error_msg}")
        return

    # 1. Initialize Collectors
    pa_collector = ProgArchivesCollector(
        raw_data_dir=pa_output_dir,
        delay=delay,
        use_browser=use_browser,
        browser_headful=browser_headful
    )
    lastfm_fetcher = LastFmFetcher(
        api_key=api_key,
        raw_data_dir=lastfm_output_dir,
        requests_per_second=2.0 # Conservative rate limit
    )

    # 2. Get Artist List (Phase 1)
    logger.info("--- Phase 1: Obtaining Artist List from ProgArchives ---")
    artists = []
    
    if stop_check and stop_check(): return

    # We use the existing collector to get the master list
    # If cache exists and force_reindex is False, this is instant.
    # Otherwise it scrapes the alpha pages (which usually don't have strict captchas).
    
    # We'll just collect them all into a list first for the hybrid approach
    # In a huge scale, we might generator-pipeline this, but PA has maybe 10-20k artists, it fits in memory.
    try:
        iterator = pa_collector.fetch_all_artists(cache_index=not force_reindex)
        for i, artist in enumerate(iterator):
            if stop_check and stop_check(): return
            
            # Letter filter
            if letters:
                first_char = artist.name[0].lower() if artist.name else ''
                allowed = set(letters.lower())
                if first_char not in allowed:
                    if not (first_char.isnumeric() == False and '0' in allowed): # Handle '0' for numbers if needed, simplistic check
                         if not (not first_char.isalpha() and '0' in allowed): # better check
                            continue
            
            artists.append(artist)
            if i % 100 == 0:
                logger.info(f"Loaded {i} artists so far...")
                if progress_callback:
                    progress_callback(i, 0, f"Loading Artist Index: {len(artists)} found...")

    except Exception as e:
        logger.error(f"Error during Phase 1 (Index Collection): {e}")
        return

    total_artists = len(artists)
    if limit > 0:
        artists = artists[:limit]
        total_artists = limit
        logger.info(f"Limiting to first {limit} artists for testing.")

    logger.info(f"--- Phase 1 Complete. Found {total_artists} artists to process. ---")

    # 3. Last.fm Hydration (Phase 2)
    logger.info("--- Phase 2: Hydrating via Last.fm API ---")
    
    success_count = 0
    fail_count = 0

    for i, artist in enumerate(artists):
        if stop_check and stop_check(): 
            logger.info("Pipeline stopped by user.")
            break

        try:
            msg = f"Fetching Last.fm: {artist.name}"
            logger.info(msg)
            if progress_callback:
                progress_callback(i + 1, total_artists, msg)
            
            # Skip if DB already has Last.fm enrichment for this artist/albums
            if not force_reindex:
                try:
                    with session_scope() as session:
                        # Check Artist record for lastfm_url
                        artist_row = session.query(db_models.Artist).filter(db_models.Artist.name == artist.name).first()
                        if artist_row and artist_row.lastfm_url:
                            logger.info(f"Skipping {artist.name}: artist already enriched in DB (lastfm_url present).")
                            success_count += 1
                            continue

                        # Check any album for this PA artist name that has lastfm_playcount
                        album_row = session.query(db_models.Album).filter(
                            db_models.Album.pa_artist_name_on_album == artist.name,
                            db_models.Album.lastfm_playcount != None
                        ).first()
                        if album_row:
                            logger.info(f"Skipping {artist.name}: album(s) already enriched in DB.")
                            success_count += 1
                            continue
                except Exception:
                    # If DB check fails, fall back to network fetch to avoid blocking pipeline
                    logger.debug("DB enrichment check failed; proceeding with Last.fm fetch")

            # Fetch Artist + Top Albums
            # We try variations of the name to handle PA's "Lastname, Firstname" format
            success = False
            error_msg = ""
            
            # Name variations generator
            candidates = [artist.name]
            
            # 1. Handle "Band, The" -> "The Band"
            if ", THE" in artist.name.upper():
                # Case insensitive replace for cleaner handling
                idx = artist.name.upper().rfind(", THE")
                if idx != -1:
                    clean = "The " + artist.name[:idx] + artist.name[idx+5:]
                    candidates.append(clean.strip())
            
            # 2. Handle "Lastname, Firstname" -> "Firstname Lastname"
            if ", " in artist.name:
                parts = artist.name.split(", ")
                if len(parts) == 2:
                    swapped = f"{parts[1]} {parts[0]}"
                    candidates.append(swapped)
            
            # Try each candidate until one works
            for candidate_name in candidates:
                if candidate_name != artist.name:
                    logger.info(f"  > Trying variation: '{candidate_name}'")
                    
                result = lastfm_fetcher.fetch_artist(
                    candidate_name,
                    skip_if_exists=True,
                    include_top_albums=True,
                    include_similar=False # Skip similar for speed
                )
                
                if result.success:
                    success = True
                    break
                else:
                    # Keep the last error
                    error_msg = result.error
                    # If error is NOT "not found", it might be a network/rate limit, so we might stop?
                    # But for now we assume error 6 (not found) implies try next name.
            
            if success:
                success_count += 1
            else:
                logger.warning(f"Failed to fetch {artist.name} (and variations): {error_msg}")
                fail_count += 1
                
        except Exception as e:
            logger.error(f"Unexpected error processing {artist.name}: {e}")
            fail_count += 1
            
    logger.info(f"Hybrid Pipeline Complete. Success: {success_count}, Failed: {fail_count}")

def main():
    parser = argparse.ArgumentParser(description="Hybrid PA + Last.fm Scraper")
    parser.add_argument("--letters", help="Limit to specific start letters (e.g. 'a')")
    parser.add_argument("--force-reindex", action="store_true", help="Rescrape PA index")
    parser.add_argument("--limit", type=int, default=0, help="Max artists to process (0=all)")
    
    args = parser.parse_args()
    
    run_hybrid_collection(
        letters=args.letters,
        force_reindex=args.force_reindex,
        limit=args.limit
    )

if __name__ == "__main__":
    main()
