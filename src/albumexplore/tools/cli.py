"""Command line interface for album exploration tools."""
import argparse
import logging
from pathlib import Path
from albumexplore.tools.scrape_random_albums import main as scrape_random

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Album Explorer Tools')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Scrape random albums command
    scrape_parser = subparsers.add_parser('scrape-random', help='Scrape random albums from ProgArchives')
    scrape_parser.add_argument('--max-bands', type=int, default=5,
                              help='Maximum number of bands to scrape (default: 5)')
    scrape_parser.add_argument('--output', type=Path,
                              help='Output JSON file path (default: ./progarchives_output.json)')
    scrape_parser.add_argument('--cache-dir', type=Path,
                              help='Cache directory path (default: ./cache/progarchives)')
    scrape_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Run appropriate command
    if args.command == 'scrape-random':
        scrape_random()

if __name__ == '__main__':
    main()