"""
ETL Orchestrator for AlbumExplore.

Unified entry point for the Extract-Transform-Load pipeline.
Supports multiple data sources: ProgArchives, Last.fm, and more.
"""
import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_module(module_name: str, args: list = None):
    """Run a python module as a subprocess."""
    cmd = [sys.executable, "-m", module_name]
    if args:
        cmd.extend(args)
    
    logger.info(f"Running module: {module_name} with args: {args}")
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Module {module_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Module {module_name} failed with exit code {e.returncode}.")
        return False


def run_progarchives_crawl(args):
    """Run the targeted ProgArchives crawler."""
    from albumexplore.scraping.progarchives.crawler import ProgArchivesCrawler
    
    logger.info(f"Starting ProgArchives crawl for genre: {args.genre}")
    
    try:
        # Default to headless=False because Cloudflare blocks headless
        headless = args.headless if hasattr(args, 'headless') else False
        
        with ProgArchivesCrawler(
            output_dir=os.path.join(args.raw_data_dir, "progarchives"),
            headless=headless
        ) as crawler:
            crawler.crawl_genre(
                args.genre, 
                limit_albums=args.limit
            )
        return True
    except Exception as e:
        logger.error(f"ProgArchives crawl failed: {e}")
        return False


def run_progarchives_parse(args):
    """Run the ProgArchives parser."""
    from albumexplore.scraping.parse_progarchives_site import parse_directory
    
    logger.info("Starting ProgArchives parse...")
    
    try:
        input_dir = os.path.join(args.raw_data_dir, "progarchives")
        output_dir = os.path.join(args.raw_data_dir, "progarchives", "parsed")
        
        parse_directory(input_dir, output_dir)
        return True
    except Exception as e:
        logger.error(f"ProgArchives parse failed: {e}")
        return False


def run_lastfm_fetch(args):
    """
    Run Last.fm data fetching for existing albums.
    
    Fetches Last.fm data for albums already in the database.
    """
    from albumexplore.scraping.lastfm import LastFmFetcher
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from albumexplore.database.models import Album
    
    logger.info("Starting Last.fm fetch...")
    
    # Get albums from database
    engine = create_engine(args.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get albums with artist names
        albums = session.query(Album).filter(
            Album.pa_artist_name_on_album != None,
            Album.title != None
        ).all()
        
        if args.limit:
            albums = albums[:args.limit]
        
        logger.info(f"Found {len(albums)} albums to fetch")
        
        # Create album list for fetcher
        album_list = [
            (album.pa_artist_name_on_album, album.title)
            for album in albums
        ]
        
        # Initialize fetcher
        fetcher = LastFmFetcher(
            raw_data_dir=os.path.join(args.raw_data_dir, "lastfm")
        )
        
        # Progress callback
        def progress(current, total, result):
            if current % 10 == 0 or current == total:
                status = "✓" if result.success else "✗"
                logger.info(f"[{current}/{total}] {status} {result.artist} - {result.album}")
        
        # Fetch data
        results = list(fetcher.fetch_albums_batch(
            album_list,
            skip_if_exists=not args.force,
            progress_callback=progress
        ))
        
        # Summary
        success = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        logger.info(f"Last.fm fetch complete: {success} success, {failed} failed")
        
        return failed == 0
        
    finally:
        session.close()


def run_lastfm_transform(args):
    """Run Last.fm data transformation."""
    from albumexplore.scraping.lastfm.transform_lastfm_data import transform_lastfm_data
    
    logger.info("Starting Last.fm transform...")
    
    success = transform_lastfm_data(
        raw_data_dir=os.path.join(args.raw_data_dir, "lastfm"),
        db_uri=args.db_uri,
        dry_run=args.dry_run,
        create_new=getattr(args, 'create_new', False),
    )
    
    return success


def main():
    parser = argparse.ArgumentParser(description="AlbumExplore ETL Pipeline")
    parser.add_argument("--mode", choices=[
        "recreate-full", "incremental", "extract-only", "transform-only", "validate-only",
        "lastfm-fetch", "lastfm-transform", "lastfm-full",
        "progarchives-crawl", "progarchives-parse"
    ], default="incremental", help="ETL operation mode")
    parser.add_argument("--source", choices=["progarchives", "lastfm", "all"],
                        default="all", help="Data source to process")
    parser.add_argument("--dry-run", action="store_true", help="Run transforms without committing to DB")
    parser.add_argument("--force", action="store_true", help="Force processing even if files haven't changed")
    parser.add_argument("--raw-data-dir", default="./raw_data", help="Directory for raw data")
    parser.add_argument("--db-uri", default="sqlite:///albumexplore.db", help="Database URI")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to process")
    parser.add_argument("--create-new", action="store_true", 
                        help="Create new albums not found in database (Last.fm only)")
    
    # ProgArchives Crawler specific args
    parser.add_argument("--genre", default="prog_metal", help="Genre to crawl (progarchives-crawl mode)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    
    args = parser.parse_args()
    
    logger.info(f"Starting ETL pipeline in {args.mode} mode")
    
    # =========================================================================
    # ProgArchives Crawler mode
    # =========================================================================
    if args.mode == "progarchives-crawl":
        if not run_progarchives_crawl(args):
            sys.exit(1)
        logger.info("ProgArchives crawl completed.")
        return

    if args.mode == "progarchives-parse":
        if not run_progarchives_parse(args):
            sys.exit(1)
        logger.info("ProgArchives parse completed.")
        return

    # =========================================================================
    # Last.fm specific modes
    # =========================================================================
    if args.mode == "lastfm-fetch":
        if not run_lastfm_fetch(args):
            logger.error("Last.fm fetch failed.")
            sys.exit(1)
        logger.info("Last.fm fetch completed.")
        return
    
    if args.mode == "lastfm-transform":
        if not run_lastfm_transform(args):
            logger.error("Last.fm transform failed.")
            sys.exit(1)
        logger.info("Last.fm transform completed.")
        return
    
    if args.mode == "lastfm-full":
        logger.info("Running full Last.fm pipeline (fetch + transform)")
        if not run_lastfm_fetch(args):
            logger.error("Last.fm fetch failed.")
            sys.exit(1)
        if not run_lastfm_transform(args):
            logger.error("Last.fm transform failed.")
            sys.exit(1)
        logger.info("Last.fm full pipeline completed.")
        return
    
    # =========================================================================
    # Standard ETL modes (ProgArchives)
    # =========================================================================
    
    # Step 1: Extract (Scrape/Parse)
    if args.mode in ["recreate-full", "incremental", "extract-only"]:
        if args.source in ["progarchives", "all"]:
            logger.info("Step 1: Extracting data from ProgArchives...")
            if not run_module("albumexplore.scraping.extract_progarchives_data"):
                logger.error("Extraction failed. Aborting.")
                sys.exit(1)
            
    # Step 2: Transform & Load
    if args.mode in ["recreate-full", "incremental", "transform-only"]:
        if args.source in ["progarchives", "all"]:
            logger.info("Step 2: Transforming and Loading ProgArchives data...")
            
            # Determine the correct raw data directory for ProgArchives
            pa_raw_dir = os.path.join(args.raw_data_dir, "progarchives", "parsed")
            if not os.path.exists(pa_raw_dir):
                # Fallback to root raw_data_dir for backward compatibility
                pa_raw_dir = args.raw_data_dir
                logger.info(f"Parsed directory not found, using root: {pa_raw_dir}")
            else:
                logger.info(f"Using parsed directory: {pa_raw_dir}")
            
            transform_args = [
                "--raw-data-dir", pa_raw_dir,
                "--db-uri", args.db_uri
            ]
            
            if args.dry_run:
                transform_args.append("--dry-run")
            
            if args.force or args.mode == "recreate-full":
                transform_args.append("--force")
                
            if not run_module("albumexplore.scraping.transform_progarchives_data", transform_args):
                logger.error("Transform/Load failed. Aborting.")
                sys.exit(1)
        
        # Last.fm transform (if source includes it)
        if args.source in ["lastfm", "all"] and args.mode != "extract-only":
            logger.info("Step 2b: Transforming Last.fm data...")
            run_lastfm_transform(args)

    # Step 3: Validation
    if args.mode in ["recreate-full", "incremental", "validate-only"] and not args.dry_run:
        logger.info("Step 3: Validating database...")
        validate_args = ["--db-uri", args.db_uri]
        if not run_module("albumexplore.data.validate_db", validate_args):
            logger.warning("Database validation found issues. Check logs.")
            # We don't exit here, just warn
            
    logger.info("ETL pipeline completed successfully.")


if __name__ == "__main__":
    main()
