"""Tests for ProgArchives data importer."""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from albumexplore.data.importers.progarchives_importer import ProgArchivesImporter
from albumexplore.data.models.album import Album
from albumexplore.data.models.artist import Artist
from albumexplore.data.models.track import Track
from albumexplore.data.models.review import Review
from albumexplore.data.models.tag import Tag

@pytest.fixture
def sample_album_data():
    return {
        'title': 'Test Album',
        'artist': 'Test Artist',
        'year': 2023,
        'description': 'Test description',
        'url': 'https://www.progarchives.com/album.asp?id=123',
        'record_type': 'Studio',
        'rating': 4.5,
        'subgenre': 'Symphonic-Prog',
        'tracks': [
            {
                'number': 1,
                'title': 'Test Track',
                'duration': '5:00'
            }
        ],
        'reviews': [
            {
                'text': 'Great album!',
                'rating': 4.5,
                'author': 'Reviewer',
                'date': '2023-01-01'
            }
        ],
        'scraped_at': datetime.now().isoformat()
    }

@pytest.fixture
def sample_band_data():
    return {
        'name': 'Test Band',
        'country': 'Norway',
        'description': 'Test band bio',
        'url': 'https://www.progarchives.com/artist.asp?id=456',
        'albums': [
            {
                'title': 'Album 1',
                'url': 'https://www.progarchives.com/album.asp?id=1'
            },
            {
                'title': 'Album 2',
                'url': 'https://www.progarchives.com/album.asp?id=2'
            }
        ],
        'scraped_at': datetime.now().isoformat()
    }

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    
    # Create all tables
    from albumexplore.data.models.base import Base
    Base.metadata.create_all(engine)
    
    return Session()

@pytest.fixture
def importer(db_session):
    """Create importer with mocked scraper."""
    return ProgArchivesImporter(db_session)

def test_import_new_album(importer, sample_album_data, db_session):
    """Test importing a new album."""
    with patch.object(importer.scraper, 'get_album_details', return_value=sample_album_data):
        album = importer.import_album('test_url')
        
        assert album is not None
        assert album.title == sample_album_data['title']
        assert album.artist_name == sample_album_data['artist']
        assert len(album.tracks) == 1
        assert len(album.reviews) == 1
        assert len(album.tags) == 1
        assert album.progarchives_id == 123

def test_update_existing_album(importer, sample_album_data, db_session):
    """Test updating an existing album."""
    # Create existing album
    existing = Album(
        title=sample_album_data['title'],
        artist_name=sample_album_data['artist'],
        description='Old description'
    )
    db_session.add(existing)
    db_session.commit()
    
    # Update with new data
    with patch.object(importer.scraper, 'get_album_details', return_value=sample_album_data):
        album = importer.import_album('test_url')
        
        assert album is existing  # Should return same object
        assert album.description == sample_album_data['description']
        assert len(album.reviews) == 1
        assert len(album.tags) == 1

def test_import_band_with_albums(importer, sample_band_data, db_session):
    """Test importing a band with their albums."""
    with patch.object(importer.scraper, 'get_band_details', return_value=sample_band_data):
        with patch.object(importer.scraper, 'get_album_details', return_value=sample_album_data):
            artist = importer.import_band('test_url')
            
            assert artist is not None
            assert artist.name == sample_band_data['name']
            assert artist.country == sample_band_data['country']
            assert len(artist.albums) > 0

def test_deduplication(importer, sample_album_data, db_session):
    """Test that albums are properly deduplicated."""
    with patch.object(importer.scraper, 'get_album_details', return_value=sample_album_data):
        # Import same album twice
        album1 = importer.import_album('test_url')
        album2 = importer.import_album('test_url')
        
        assert album1 is album2  # Should return same object
        # Check database has only one record
        count = db_session.query(Album).count()
        assert count == 1

def test_tag_creation(importer, sample_album_data, db_session):
    """Test that genre tags are properly created and linked."""
    with patch.object(importer.scraper, 'get_album_details', return_value=sample_album_data):
        album = importer.import_album('test_url')
        
        # Check tag was created
        tag = db_session.query(Tag).first()
        assert tag is not None
        assert tag.name == f"progarchives:{sample_album_data['subgenre'].lower()}"
        assert tag.category == 'genre'
        assert tag.source == 'progarchives'
        
        # Check tag was linked to album
        assert tag in album.tags

def test_error_handling(importer, db_session):
    """Test handling of scraping errors."""
    error_data = {'error': 'Failed to fetch data'}
    with patch.object(importer.scraper, 'get_album_details', return_value=error_data):
        album = importer.import_album('test_url')
        assert album is None  # Should return None on error
        
        # Database should be clean
        count = db_session.query(Album).count()
        assert count == 0

def test_date_parsing(importer):
    """Test parsing of different date formats."""
    assert importer._parse_date('2023-01-01') is not None
    assert importer._parse_date('01/01/2023') is not None
    assert importer._parse_date('invalid') is None
    assert importer._parse_date(None) is None