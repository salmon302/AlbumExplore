import logging
import argparse
import sys
from pathlib import Path
from tqdm import tqdm
from typing import Callable, Optional
from .collectors import ProgArchivesCollector
from albumexplore.database import session_scope
from albumexplore.database import models as db_models

# Configure main log file
log_path = Path("logs/scraper_pipeline.log")
log_path.parent.mkdir(parents=True, exist_ok=True)

# We configure the root logger here so dependencies (urllib3, etc) also log if needed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_collection(output_dir: str, letters: str = None, delay: float = 1.0, 
                   mode: str = "full", force_reindex: bool = False,
                   use_browser: bool = False, browser_headful: bool = False,
                   progress_callback: Optional[Callable[[int, int, str], None]] = None,
                   stop_check: Optional[Callable[[], bool]] = None,
                   save_failures_path: Optional[str] = None):
    """
    Run the collection pipeline with enhanced control.
    
    Args:
        output_dir: Directory to store raw data
        letters: Optional string of letters to scrape (e.g. "abc").
        delay: Delay between requests
        mode: 'index', 'download', or 'full'
        force_reindex: If True, ignores existing CSV index and rescrapes.
        use_browser: Enable Selenium fallback for 403s
        browser_headful: Run browser visibly
        progress_callback: Function(current, total, message) called on progress
        stop_check: Function returning True if execution should stop
    """
    collector = ProgArchivesCollector(
        raw_data_dir=output_dir, 
        delay=delay,
        use_browser=use_browser,
        browser_headful=browser_headful
    )
    
    # --- PHASE 1: INDEXING ---
    if mode in ["index", "full"]:
        if stop_check and stop_check():
            logger.info("Pipeline stopped by user before Phase 1.")
            return

        logger.info("Step 1: Collecting Artists Index...")
        artist_count = 0
        # Iterate to trigger collection
        # We could add progress here too but it's only 27 requests
        for i, _ in enumerate(collector.fetch_all_artists(cache_index=not force_reindex)):
            artist_count += 1
            if stop_check and stop_check():
                logger.info("Pipeline stopped by user during Phase 1.")
                return
            if progress_callback and i % 5 == 0:
                 progress_callback(i, 27, f"Indexing artist list {i}/27...")
                 
        logger.info(f"Index complete. Found {artist_count} artists.")

    if mode == "index":
        return

    # --- PHASE 2: DOWNLOADING ---
    logger.info("Step 2: Processing Discographies...")
    
    # Reload from index (guaranteed to check cache now since mode is handled)
    artists_to_process = list(collector.fetch_all_artists(cache_index=True))
    
    if not artists_to_process:
        logger.error("No artists found in index! Run with --mode index or --mode full first.")
        return

    # Apply letter filtering
    if letters:
        allowed = set(letters.lower())
        logger.info(f"Filtering for letters: {allowed}")
        artists_to_process = [
            a for a in artists_to_process 
            if (a.name and a.name[0].lower() in allowed)
            or (a.name and not a.name[0].isalnum() and '0' in allowed)
        ]

    total_artists = len(artists_to_process)
    logger.info(f"Processing {total_artists} artists...")
    
    success_count = 0
    fail_count = 0
    failed_artists = []
    
    # Use tqdm for CLI, callback for GUI
    pbar = None
    if not progress_callback:
        pbar = tqdm(total=total_artists, unit="artist")

    for i, artist in enumerate(artists_to_process):
        if stop_check and stop_check():
            logger.info("Pipeline stopped by user.")
            break
            
        try:
            # Skip fetching artist page if DB already has Last.fm enrichment for this artist
            if not force_reindex:
                try:
                    with session_scope() as session:
                        album_row = session.query(db_models.Album).filter(
                            db_models.Album.pa_artist_name_on_album == artist.name,
                            db_models.Album.lastfm_playcount != None
                        ).first()
                        if album_row:
                            logger.info(f"Skipping fetch for {artist.name}: album(s) already enriched in DB.")
                            success_count += 1
                            continue
                except Exception:
                    logger.debug("DB enrichment check failed; proceeding with fetch")

            msg = f"GET {artist.name[:30]}"
            if pbar:
                pbar.set_description(msg)
            
            if collector.fetch_artist_page(artist):
                success_count += 1
            else:
                fail_count += 1
                failed_artists.append(f"{artist.name}")
                
        except Exception as e:
            logger.error(f"Failed to fetch page for {artist.name}: {e}")
            fail_count += 1
            # Record the failure with exception detail
            try:
                failed_artists.append(f"{artist.name}: {e}")
            except Exception:
                failed_artists.append(f"{artist.name}: <error capturing exception>")
        finally:
            if pbar:
                pbar.update(1)
            if progress_callback:
                progress_callback(i + 1, total_artists, f"Processing: {artist.name}")

    if pbar:
        pbar.close()

    logger.info(f"Collection complete. Success: {success_count}, Failed: {fail_count}")
    # Optionally save failed artist list to a file
    if save_failures_path and failed_artists:
        try:
            p = Path(save_failures_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('w', encoding='utf-8') as fh:
                for line in failed_artists:
                    fh.write(line + "\n")
            logger.info(f"Saved {len(failed_artists)} failed artist entries to {save_failures_path}")
        except Exception as e:
            logger.error(f"Failed to save failures to {save_failures_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="ProgArchives Data Pipeline V2")
    parser.add_argument("--output-dir", default="raw_data/progarchives", help="Output directory")
    parser.add_argument("--letters", help="Limit to specific start letters (e.g. 'a' or 'abc')")
    parser.add_argument("--delay", type=float, default=1.0, help="Request delay in seconds")
    parser.add_argument("--mode", choices=["index", "download", "full"], default="full", 
                        help="Pipeline stage to run")
    parser.add_argument("--force-reindex", action="store_true", help="Force re-scraping of artist lists")
    parser.add_argument("--use-browser", action="store_true", help="Enable Selenium browser fallback (for 403s)")
    parser.add_argument("--headful", action="store_true", help="Run browser visibly (good for manual captcha solving)")
    parser.add_argument("--save-failures", help="Path to save failed artist list (one entry per line)")
    
    args = parser.parse_args()
    
    run_collection(args.output_dir, args.letters, args.delay, args.mode, 
                   args.force_reindex, args.use_browser, args.headful,
                   save_failures_path=args.save_failures)

if __name__ == "__main__":
    main()
