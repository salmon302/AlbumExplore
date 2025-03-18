"""Tests for ProgArchives scraper CLI interface."""
import pytest
from click.testing import CliRunner
from pathlib import Path
import json
from unittest.mock import patch, Mock
from albumexplore.cli.scraper_cli import cli

@pytest.fixture
def mock_scraper():
    """Mock the ProgArchivesScraper class."""
    with patch('albumexplore.cli.scraper_cli.ProgArchivesScraper') as mock:
        instance = Mock()
        mock.return_value = instance
        # Setup mock data
        instance.get_album_data.return_value = {
            'title': 'Test Album',
            'artist': 'Test Artist',
            'release_date': '2025-01-01',
            'genres': ['Progressive Metal'],
            'rating': '4.5/5'
        }
        instance.search_albums.return_value = [{
            'title': 'Found Album',
            'artist': 'Found Artist',
            'url': '/album/1234',
            'year': '2025'
        }]
        yield instance

@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()

def test_scrape_command_stdout(runner, mock_scraper):
    """Test scraping an album and printing to stdout."""
    result = runner.invoke(cli, ['scrape', 'https://progarchives.com/album/1234'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data['title'] == 'Test Album'
    assert data['artist'] == 'Test Artist'

def test_scrape_command_file_output(runner, mock_scraper, tmp_path):
    """Test scraping an album and saving to file."""
    output_file = tmp_path / 'output.json'
    result = runner.invoke(cli, [
        'scrape',
        'https://progarchives.com/album/1234',
        '--output', str(output_file)
    ])
    assert result.exit_code == 0
    assert output_file.exists()
    with open(output_file) as f:
        data = json.load(f)
    assert data['title'] == 'Test Album'
    assert data['genres'] == ['Progressive Metal']

def test_scrape_command_no_cache(runner, mock_scraper):
    """Test scraping with cache disabled."""
    result = runner.invoke(cli, [
        'scrape',
        'https://progarchives.com/album/1234',
        '--no-cache'
    ])
    assert result.exit_code == 0
    mock_scraper.get_album_data.assert_called_with(
        'https://progarchives.com/album/1234',
        use_cache=False
    )

def test_search_command_stdout(runner, mock_scraper):
    """Test searching for albums and printing to stdout."""
    result = runner.invoke(cli, ['search', 'test query'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]['title'] == 'Found Album'
    assert data[0]['artist'] == 'Found Artist'

def test_search_command_file_output(runner, mock_scraper, tmp_path):
    """Test searching for albums and saving to file."""
    output_file = tmp_path / 'search_results.json'
    result = runner.invoke(cli, [
        'search',
        'test query',
        '--output', str(output_file)
    ])
    assert result.exit_code == 0
    assert output_file.exists()
    with open(output_file) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]['url'] == '/album/1234'
    assert data[0]['year'] == '2025'

def test_scrape_command_error(runner, mock_scraper):
    """Test error handling in scrape command."""
    mock_scraper.get_album_data.return_value = None
    result = runner.invoke(cli, ['scrape', 'https://invalid'])
    assert result.exit_code == 1
    assert 'Failed to scrape album data' in result.output

def test_search_command_error(runner, mock_scraper):
    """Test error handling in search command."""
    mock_scraper.search_albums.side_effect = Exception('Search failed')
    result = runner.invoke(cli, ['search', 'invalid'])
    assert result.exit_code == 1
    assert 'Error: Search failed' in result.output