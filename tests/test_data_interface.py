import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database import Base, models
from albumexplore.visualization.data_interface import DataInterface

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
def data_interface(session):
	return DataInterface(session)

@pytest.fixture
def sample_data(session):
	# Create sample tags
	tag1 = models.Tag(id="metal", name="metal", category="genre")
	tag2 = models.Tag(id="prog", name="progressive", category="style")
	tag3 = models.Tag(id="rock", name="rock", category="genre")
	
	# Create sample albums
	album1 = models.Album(
		id="album1",
		artist="Artist1",
		title="Album1",
		release_year=2020,
		vocal_style="clean"
	)
	album2 = models.Album(
		id="album2",
		artist="Artist2",
		title="Album2",
		release_year=2021,
		vocal_style="harsh"
	)
	album3 = models.Album(
		id="album3",
		artist="Artist3",
		title="Album3",
		release_year=2021,
		vocal_style="clean"
	)
	
	# Set up relationships
	album1.tags.extend([tag1, tag2])
	album2.tags.extend([tag2, tag3])
	album3.tags.extend([tag1, tag3])
	
	session.add_all([tag1, tag2, tag3, album1, album2, album3])
	session.commit()
	
	return {
		"albums": [album1, album2, album3],
		"tags": [tag1, tag2, tag3]
	}

def test_get_albums_with_filters(data_interface, sample_data):
	# Test year range filter
	albums = data_interface.get_albums({"year_range": (2021, 2021)})
	assert len(albums) == 2
	assert all(a.release_year == 2021 for a in albums)
	
	# Test tag filter
	albums = data_interface.get_albums({"tags": ["metal"]})
	assert len(albums) == 2
	
	# Test vocal style filter
	albums = data_interface.get_albums({"vocal_style": "clean"})
	assert len(albums) == 2
	assert all(a.vocal_style == "clean" for a in albums)
	
	# Test combined filters
	albums = data_interface.get_albums({
		"year_range": (2020, 2021),
		"vocal_style": "clean",
		"tags": ["metal"]
	})
	assert len(albums) == 2

def test_get_tags_by_category(data_interface, sample_data):
	genre_tags = data_interface.get_tags(category="genre")
	assert len(genre_tags) == 2
	assert all(t.category == "genre" for t in genre_tags)
	
	style_tags = data_interface.get_tags(category="style")
	assert len(style_tags) == 1
	assert style_tags[0].category == "style"

def test_get_album_connections(data_interface, sample_data):
	album_ids = [a.id for a in sample_data["albums"]]
	connections = data_interface.get_album_connections(album_ids)
	
	# Should have connections between albums with shared tags
	assert len(connections) == 3
	
	# Verify connection weights
	for conn in connections:
		assert conn['weight'] > 0
		assert len(conn['shared_tags']) == conn['weight']