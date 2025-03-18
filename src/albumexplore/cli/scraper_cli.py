"""Command line interface for ProgArchives scraper."""
import click
import json
from pathlib import Path
from ..data.scrapers.progarchives_scraper import ProgArchivesScraper
from ..data.importers.progarchives_importer import ProgArchivesImporter
from ..database import get_session
import logging

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """ProgArchives.com data collection tools."""
    pass

@cli.command()
@click.argument('url')
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--import-db', is_flag=True, help='Import data into database')
def scrape(url: str, output: str, no_cache: bool, import_db: bool):
    """Scrape album data from a ProgArchives.com album page."""
    try:
        scraper = ProgArchivesScraper()
        data = scraper.get_album_data(url, use_cache=not no_cache)
        
        if data:
            if import_db:
                session = get_session()
                importer = ProgArchivesImporter(session)
                album = importer.import_album(url, use_cache=not no_cache)
                if album:
                    click.echo(f"Successfully imported album '{album.title}' to database")
                else:
                    click.echo("Failed to import album to database", err=True)
                    exit(1)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                click.echo(f"Data saved to {output}")
            else:
                click.echo(json.dumps(data, indent=2))
        else:
            click.echo("Failed to scrape album data", err=True)
            exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

@cli.command()
@click.argument('query')
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
@click.option('--import-db', is_flag=True, help='Import results into database')
def search(query: str, output: str, import_db: bool):
    """Search for albums on ProgArchives.com."""
    try:
        scraper = ProgArchivesScraper()
        results = scraper.search_albums(query)

        if import_db:
            session = get_session()
            importer = ProgArchivesImporter(session)
            albums = importer.import_search_results(query)
            click.echo(f"Successfully imported {len(albums)} albums to database")
        
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            click.echo(f"Results saved to {output}")
        else:
            click.echo(json.dumps(results, indent=2))
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

@cli.command()
@click.argument('urls', nargs=-1)
@click.option('--from-file', type=click.Path(exists=True), help='File containing URLs, one per line')
def import_albums(urls, from_file):
    """Import one or more albums into the database."""
    try:
        all_urls = list(urls)
        if from_file:
            with open(from_file) as f:
                file_urls = [line.strip() for line in f if line.strip()]
                all_urls.extend(file_urls)

        if not all_urls:
            click.echo("No URLs provided")
            exit(1)

        session = get_session()
        importer = ProgArchivesImporter(session)
        
        successful = 0
        failed = 0
        
        with click.progressbar(all_urls, label='Importing albums') as bar:
            for url in bar:
                if album := importer.import_album(url):
                    successful += 1
                else:
                    failed += 1
                    click.echo(f"Failed to import: {url}", err=True)

        click.echo(f"Import complete: {successful} successful, {failed} failed")
        if failed > 0:
            exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

if __name__ == '__main__':
    cli()