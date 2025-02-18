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
def sample_data(session):
	# Create sample tags
	tag1 = models.Tag(id="metal", name="metal", category="genre", frequency=10)
	tag2 = models.Tag(id="prog", name="progressive", category="style", frequency=5)
	tag3 = models.Tag(id="rock", name="rock", category="genre", frequency=15)
	
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
	criteria = {
		"tags": ["metal", "prog"],
		"match_all_tags": True,
		"year_range": (2019, 2020),
		"vocal_style": "clean"
	}
	results = tag_filter.filter_by_multiple_criteria(criteria)
	assert len(results) == 1
	assert results[0].id == "album1"

def test_filter_tags_by_pattern(tag_filter, sample_data):
	results = tag_filter.filter_tags_by_pattern("prog")
	assert len(results) == 1
	assert results[0].name == "progressive"

def test_filter_by_tag_hierarchy(tag_filter, sample_data):
	results = tag_filter.filter_by_tag_hierarchy("metal")
	assert len(results) == 1
	assert results[0].id == "prog"

def test_filter_by_platform(tag_filter, sample_data):
	spotify_results = tag_filter.filter_by_platform("spotify")
	assert len(spotify_results) == 1
	assert spotify_results[0].id == "album1"
	
	bandcamp_results = tag_filter.filter_by_platform("bandcamp")
	assert len(bandcamp_results) == 1
	assert bandcamp_results[0].id == "album2"