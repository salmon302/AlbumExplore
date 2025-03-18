import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database import Base, models
from albumexplore.tags.filters.tag_filter import TagFilter

@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def tag_filter(session):
    return TagFilter(session)

@pytest.fixture
def categories(session):
    # Create tag categories
    genre = models.TagCategory(id="genre", name="Genre")
    style = models.TagCategory(id="style", name="Style")
    session.add_all([genre, style])
    session.commit()
    return {"genre": genre, "style": style}

@pytest.fixture
def sample_data(session, categories):
    # Create sample tags with proper category_id references
    tag1 = models.Tag(id="metal", name="metal", category_id="genre", frequency=10)
    tag2 = models.Tag(id="prog", name="progressive", category_id="style", frequency=5)
    tag3 = models.Tag(id="rock", name="rock", category_id="genre", frequency=15)
    
    # Create sample albums
    album1 = models.Album(
        id="album1",
        artist="Artist1",
        title="Album1",
        release_year=2020,
        vocal_style="clean",
        country="USA",
        platforms=json.dumps({"spotify": "url1"})
    )
    album2 = models.Album(
        id="album2",
        artist="Artist2",
        title="Album2",
        release_year=2021,
        vocal_style="harsh",
        country="Sweden",
        platforms=json.dumps({"bandcamp": "url2"})
    )
    
    # Create relationships
    relation = models.TagRelation(
        tag1_id="metal",
        tag2_id="prog",
        relationship_type="parent",
        strength=0.8
    )
    
    # Add to session
    session.add_all([tag1, tag2, tag3, album1, album2, relation])
    
    # Create album-tag associations
    album1.tags.extend([tag1, tag2])
    album2.tags.extend([tag2, tag3])
    
    session.commit()
    return {"tags": [tag1, tag2, tag3], "albums": [album1, album2]}

def test_filter_by_multiple_criteria(tag_filter, sample_data):
    # Test combining filters
    result = tag_filter.filter_tags({
        "category_id": "genre",
        "min_frequency": 10
    })
    assert len(result) == 2
    assert all(t.category_id == "genre" for t in result)
    assert all(t.frequency >= 10 for t in result)

def test_filter_tags_by_pattern(tag_filter, sample_data):
    # Test pattern matching
    result = tag_filter.filter_tags({"name_pattern": "prog"})
    assert len(result) == 1
    assert result[0].name == "progressive"

def test_filter_by_tag_hierarchy(tag_filter, sample_data):
    # Test hierarchical relationships
    result = tag_filter.filter_tags({"parent_tag": "metal"})
    assert len(result) == 1
    assert result[0].name == "progressive"

def test_filter_by_platform(tag_filter, sample_data):
    # Test filtering by platform
    result = tag_filter.filter_tags({"platform": "spotify"})
    assert len(result) == 2
    assert "metal" in [t.name for t in result]
    assert "progressive" in [t.name for t in result]