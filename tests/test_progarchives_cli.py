"""Tests for ProgArchives CLI interface."""
from pathlib import Path
from click.testing import CliRunner
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from albumexplore.cli.progarchives import cli
from albumexplore.data.models.album import Album
from albumexplore.data.models.artist import Artist

@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()

@pytest.fixture
def mock_scraper():
    """Create mock scraper."""
    with patch('albumexplore.cli.progarchives.ProgArchivesScraper') as mock:
        instance = mock.return_value
        # Set up default returns
        instance.get_bands_all.return_value = [
            {'name': 'Band 1', 'url': 'url1', 'subgenre': 'Symphonic-Prog'},
            {'name': 'Band 2', 'url': 'url2', 'subgenre': 'Prog-Metal'}
        ]
        instance.get_band_details.return_value = {
            'name': 'Test Band',
            'albums': [{'title': 'Album 1'}, {'title': 'Album 2'}]
        }
        instance.get_album_details.return_value = {
            'title': 'Test Album',
            'artist': 'Test Artist'
        }
        yield instance

@pytest.fixture
def mock_importer():
    """Create mock importer."""
    with patch('albumexplore.cli.progarchives.ProgArchivesImporter') as mock:
        instance = mock.return_value
        # Set up default returns
        instance.import_band.return_value = Artist(
            name='Test Band',
            albums=[Album(title='Album 1'), Album(title='Album 2')]
        )
        instance.import_album.return_value = Album(
            title='Test Album',
            artist_name='Test Artist'
        )
        yield instance

def test_collect_command(runner, mock_scraper, mock_importer):
    """Test collect command."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['collect', '--max-bands', '2'])
        assert result.exit_code == 0
        assert 'Successfully imported' in result.output
        assert mock_scraper.get_bands_all.called
        assert mock_importer.import_band.call_count == 2

def test_collect_with_subgenres(runner, mock_scraper, mock_importer):
    """Test collect command with subgenre filtering."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            'collect',
            '--subgenres', 'Symphonic-Prog',
            '--max-bands', '1'
        ])
        assert result.exit_code == 0
        # Should only process bands from specified subgenre
        assert mock_importer.import_band.call_count == 1

def test_collect_no_import(runner, mock_scraper):
    """Test collect command without database import."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['collect', '--no-import', '--max-bands', '1'])
        assert result.exit_code == 0
        assert mock_scraper.get_band_details.called
        assert 'bands processed' in result.output.lower()

def test_album_command(runner, mock_scraper, mock_importer):
    """Test album command."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['album', 'http://test/album/1'])
        assert result.exit_code == 0
        assert 'Successfully imported' in result.output
        assert mock_importer.import_album.called

def test_album_error_handling(runner, mock_scraper):
    """Test album command error handling."""
    mock_scraper.get_album_details.return_value = {'error': 'Test error'}
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['album', 'http://test/album/1', '--no-import'])
        assert result.exit_code != 0
        assert 'Error' in result.output

def test_band_command(runner, mock_scraper, mock_importer):
    """Test band command."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['band', 'http://test/band/1'])
        assert result.exit_code == 0
        assert 'Successfully imported' in result.output
        assert mock_importer.import_band.called

def test_band_skip_albums(runner, mock_scraper):
    """Test band command with skip-albums flag."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            'band',
            'http://test/band/1',
            '--no-import',
            '--skip-albums'
        ])
        assert result.exit_code == 0
        # Check that albums were removed from output
        details = mock_scraper.get_band_details.return_value
        assert 'albums' not in details

def test_rate_limiting(runner, mock_scraper):
    """Test rate limiting during collection."""
    import time
    real_get_bands = mock_scraper.get_bands_all
    
    def timed_get_bands(*args, **kwargs):
        time.sleep(0.1)  # Simulate network delay
        return real_get_bands(*args, **kwargs)
        
    mock_scraper.get_bands_all = timed_get_bands
    
    with runner.isolated_filesystem():
        start = time.time()
        result = runner.invoke(cli, ['collect', '--max-bands', '2', '--no-import'])
        duration = time.time() - start
        
        assert result.exit_code == 0
        # Should take at least min_request_interval * number of requests
        assert duration >= 0.2