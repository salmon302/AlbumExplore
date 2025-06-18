"""Tests for ProgArchives CLI interface (local file processing)."""
from pathlib import Path
from click.testing import CliRunner
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from albumexplore.cli.scraper_cli import cli
from albumexplore.database.models import Album
from albumexplore.database.models import Artist

@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()

@pytest.fixture
def mock_scraper():
    """Create mock scraper for local file processing."""
    with patch('albumexplore.cli.scraper_cli.ProgArchivesScraper') as mock:
        instance = mock.return_value
        # Set up default returns for local file processing
        instance.get_album_data.return_value = {
            'title': 'Test Album',
            'artist': 'Test Artist',
            'year': 2023,
            'genre': 'Progressive Rock',
            'local_path': 'test_album.html'
        }
        instance.get_band_details.return_value = {
            'name': 'Test Band',
            'genre': 'Progressive Rock',
            'country': 'Test Country',
            'biography': 'Test biography',
            'albums': [
                {'title': 'Album 1', 'year': 2020, 'local_path': 'album1.html'},
                {'title': 'Album 2', 'year': 2022, 'local_path': 'album2.html'}
            ],
            'local_path': 'test_band.html'
        }
        yield instance

@pytest.fixture
def mock_importer():
    """Create mock importer."""
    with patch('albumexplore.cli.scraper_cli.ProgArchivesImporter') as mock:
        instance = mock.return_value
        # Set up default returns
        instance.import_artist_from_data.return_value = Artist(
            name='Test Band'
        )
        instance.import_album_from_data.return_value = Album(
            title='Test Album',
            artist='Test Artist'  # Changed from artist_name to artist
        )
        yield instance

def test_process_album_command(runner, mock_scraper, mock_importer, tmp_path):
    """Test process_album command with a test file."""
    # Create a dummy test file
    test_file = tmp_path / "test_album.html"
    test_file.write_text("<html><body>Test HTML</body></html>")
    
    result = runner.invoke(cli, ['process-album', str(test_file)])
    assert result.exit_code == 0
    assert 'Test Album' in result.output
    assert mock_scraper.get_album_data.called
    # The scraper should be called with the Path object
    assert isinstance(mock_scraper.get_album_data.call_args[0][0], Path)
    
    # Test with import option
    result = runner.invoke(cli, ['process-album', str(test_file), '--import-db'])
    assert result.exit_code == 0
    assert 'Successfully imported' in result.output
    assert mock_importer.import_album_from_data.called

def test_process_artist_command(runner, mock_scraper, mock_importer, tmp_path):
    """Test process_artist command with a test file."""
    # Create a dummy test file
    test_file = tmp_path / "test_band.html"
    test_file.write_text("<html><body>Test HTML</body></html>")
    
    result = runner.invoke(cli, ['process-artist', str(test_file)])
    assert result.exit_code == 0
    assert 'Test Band' in result.output
    assert mock_scraper.get_band_details.called
    assert isinstance(mock_scraper.get_band_details.call_args[0][0], Path)
    
    # Test with import option
    result = runner.invoke(cli, ['process-artist', str(test_file), '--import-db'])
    assert result.exit_code == 0
    assert 'Successfully imported' in result.output
    assert mock_importer.import_artist_from_data.called

def test_import_local_dump(runner, mock_scraper, mock_importer, tmp_path):
    """Test import_local_dump command."""
    # Create dummy directory structure with HTML files
    base_dir = tmp_path / "data"
    albums_dir = base_dir / "albums"
    artists_dir = base_dir / "artists"
    albums_dir.mkdir(parents=True)
    artists_dir.mkdir(parents=True)
    
    # Create dummy album files
    (albums_dir / "album1.html").write_text("<html><body>Test Album 1</body></html>")
    (albums_dir / "album2.html").write_text("<html><body>Test Album 2</body></html>")
    
    # Create dummy artist files
    (artists_dir / "artist1.html").write_text("<html><body>Test Artist 1</body></html>")
    (artists_dir / "artist2.html").write_text("<html><body>Test Artist 2</body></html>")
    
    # Test with basic options
    result = runner.invoke(cli, [
        'import-local-dump', 
        str(base_dir),
        '--album-dir', 'albums',
        '--artist-dir', 'artists'
    ])
    
    assert result.exit_code == 0
    assert 'Processing complete' in result.output
    
    # Check the scraper was called multiple times
    process_calls = mock_scraper.get_album_data.call_count + mock_scraper.get_band_details.call_count
    assert process_calls > 0
    
    # Test with import and limit
    result = runner.invoke(cli, [
        'import-local-dump', 
        str(base_dir),
        '--album-dir', 'albums',
        '--artist-dir', 'artists',
        '--import-db',
        '--limit', '1'
    ])
    
    assert result.exit_code == 0
    assert 'Processing complete' in result.output
    assert mock_importer.import_album_from_data.called or mock_importer.import_artist_from_data.called

def test_error_handling(runner, mock_scraper, tmp_path):
    """Test error handling in CLI commands."""
    # Create a dummy test file
    test_file = tmp_path / "test_album.html"
    test_file.write_text("<html><body>Test HTML</body></html>")
    
    # Set up error response
    mock_scraper.get_album_data.return_value = {'error': 'Test error message'}
    
    result = runner.invoke(cli, ['process-album', str(test_file)])
    assert result.exit_code != 0
    assert 'Test error message' in result.output
    
    # Test exception handling
    mock_scraper.get_album_data.side_effect = Exception("Unexpected error")
    
    result = runner.invoke(cli, ['process-album', str(test_file)])
    assert result.exit_code != 0
    assert 'Unexpected error' in result.output