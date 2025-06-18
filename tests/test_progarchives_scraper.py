"""Tests for ProgArchives scraper implementation (local file parsing)."""
import pytest
import json
import logging
from pathlib import Path
# from datetime import datetime # Not used for now, can be re-added if saving test outputs with timestamp
from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a base path for test HTML files
TEST_DATA_ROOT = Path(__file__).parent / "sample_html" / "progarchives"
# Ensure this directory exists and contains sample files for testing, e.g.:
# TEST_DATA_ROOT / "album1.html"
# TEST_DATA_ROOT / "artist1.html"
# TEST_DATA_ROOT / "album_with_reviews_link.html"
# TEST_DATA_ROOT / "album-reviews1.html" (if testing separate review page parsing)

@pytest.fixture
def local_scraper() -> ProgArchivesScraper:
    """Initialize scraper for local file parsing."""
    # Initialize the scraper with the test data root
    return ProgArchivesScraper(local_data_root=TEST_DATA_ROOT)

# --- Mocking local file system for tests (Alternative to placing actual files) ---
# If we don't want to rely on actual files in the main data path for tests,
# we can mock `_read_local_html_content`.

@pytest.fixture
def mock_local_scraper(monkeypatch):
    """Create a scraper with mocked file system for tests."""
    scraper = ProgArchivesScraper(local_data_root=Path("mock_data_root"))

    # Sample HTML content for mocking
    sample_album_html = """
    <html><head><title>Test Album Page</title>
    <meta property="og:title" content="Test Artist - Test Album (2023)">
    </head><body>
    <h1 class="album-title">Test Album</h1>
    <h2><a href="artist.asp?id=1">Test Artist</a></h2>
    <table>
        <tr><td>Released:</td><td>2023</td></tr>
        <tr><td>Type:</td><td>Studio Album</td></tr>
        <tr><td>Genre:</td><td>Prog Rock</td></tr>
    </table>
    <h3>Track Listing</h3>
    <p>1. Test Track 1 - 4:30<br>2. Test Track 2 - 5:45</p>
    </body></html>
    """
    
    sample_artist_html = """
    <html><head><title>Test Artist Page</title></head>
    <body>
    <h1>Test Artist</h1>
    <h2 style="margin:1px 0px;padding:0;color:#777;font-weight:normal;">Prog Rock • Utopia</h2>
    <div id="artist-biography">
        <p>Test artist biography text.</p>
    </div>
    <table class="artist-discography-table">
        <tr>
            <td class="artist-discography-td">
                <a href="album.asp?id=1"><strong>Test Album</strong></a>
                <span style="color:#777">2023</span>
                <span style="color:#C75D4F">4.20</span>
            </td>
        </tr>
    </table>
    </body></html>
    """
    
    sample_reviews_html = """
    <html><body>
    <div class="review-container">
        <div class="review-text">This is a test review.</div>
        <span class="reviewer-name">Reviewer1</span>
        <span class="review-date">May 1, 2023</span>
        <span class="review-rating">4</span>
    </div>
    </body></html>
    """

    def mock_read(file_path: Path) -> str:
        """Mock file reading function that returns predefined content based on path."""
        path_str = str(file_path)
        if "test_album" in path_str:
            return sample_album_html
        elif "test_artist" in path_str:
            return sample_artist_html
        elif "test_reviews" in path_str:
            return sample_reviews_html
        
        logger.warning(f"Mock read: File not found in mock setup - {file_path}")
        raise ValueError(f"File not found: {file_path}")

    monkeypatch.setattr(scraper, '_read_local_html_content', mock_read)
    
    # Also mock the resolve path function to return predictable values
    def mock_resolve_path(base_path: Path, relative_reference: str) -> Path:
        if 'artist.asp' in relative_reference:
            return Path("mock_data_root/artists/test_artist.html")
        elif 'album.asp' in relative_reference:
            return Path("mock_data_root/albums/test_album.html")
        elif 'album-reviews.asp' in relative_reference:
            return Path("mock_data_root/reviews/test_reviews.html")
        return base_path
        
    monkeypatch.setattr(scraper, '_resolve_relative_path', mock_resolve_path)
    
    return scraper


def test_get_album_details(mock_local_scraper):
    """Test parsing album details from local HTML file."""
    album_data = mock_local_scraper.get_album_details("test_album.html")
    
    assert album_data is not None
    assert 'error' not in album_data
    assert album_data.get('title') == "Test Album"
    assert album_data.get('artist') == "Test Artist"
    assert album_data.get('year') == 2023
    assert album_data.get('record_type') == "Studio Album"
    assert album_data.get('genre') == "Prog Rock"
    assert len(album_data.get('tracks', [])) == 2
    assert album_data.get('tracks')[0].get('title') == "Test Track 1"


def test_get_band_details(mock_local_scraper):
    """Test parsing band details from local HTML file."""
    band_data = mock_local_scraper.get_band_details("test_artist.html")
    
    assert band_data is not None
    assert 'error' not in band_data
    assert band_data.get('name') == "Test Artist"
    assert band_data.get('genre') == "Prog Rock"
    assert band_data.get('country') == "Utopia"
    assert "Test artist biography text" in band_data.get('biography', '')
    assert len(band_data.get('albums', [])) == 1
    assert band_data.get('albums')[0].get('title') == "Test Album"
    assert band_data.get('albums')[0].get('year') == 2023


def test_get_album_data(mock_local_scraper):
    """Test getting combined album data including reviews."""
    album_data = mock_local_scraper.get_album_data("test_album.html")
    
    assert album_data is not None
    assert 'error' not in album_data
    assert album_data.get('title') == "Test Album"
    assert album_data.get('artist') == "Test Artist"
    assert album_data.get('artist_page_path') == "mock_data_root/artists/test_artist.html"
    
    # If reviews are found in separate reviews page
    if 'reviews' in album_data:
        assert len(album_data.get('reviews', [])) > 0
        review = album_data.get('reviews')[0]
        assert review.get('text') == "This is a test review."
        assert review.get('reviewer') == "Reviewer1"
        assert review.get('date') == "2023-05-01"
        assert review.get('rating') == 4


def test_error_handling(mock_local_scraper, monkeypatch):
    """Test error handling for file reading errors."""
    def mock_read_error(file_path):
        raise ValueError("Test file reading error")
    
    monkeypatch.setattr(mock_local_scraper, '_read_local_html_content', mock_read_error)
    
    result = mock_local_scraper.get_album_data("non_existent.html")
    assert 'error' in result
    assert "Test file reading error" in result['error']