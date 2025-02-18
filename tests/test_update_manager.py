import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database import Base, models
from albumexplore.database.update_manager import UpdateManager

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
def update_manager(session):
	return UpdateManager(session)

@pytest.fixture
def sample_album(session):
	album = models.Album(
		id="test_album",
		artist="Test Artist",
		title="Test Album",
		release_year=2023,
		raw_tags=json.dumps(["rock", "metal"], ensure_ascii=False),
		platforms=json.dumps({"spotify": "test_url"}, ensure_ascii=False)
	)
	session.add(album)
	session.commit()
	return album

@pytest.fixture
def sample_tag(session):
	tag = models.Tag(
		id="test_tag",
		name="rock",
		category="genre",
		aliases=json.dumps(["rocks", "rocky"], ensure_ascii=False),
		frequency=1
	)
	session.add(tag)
	session.commit()
	return tag

def test_update_album(update_manager, sample_album):
	updates = {
		"artist": "Updated Artist",
		"title": "Updated Album"
	}
	updated_album = update_manager.update_album(sample_album.id, updates)
	
	assert updated_album.artist == "Updated Artist"
	assert updated_album.title == "Updated Album"
	
	history = update_manager.get_update_history("album", sample_album.id)
	assert len(history) == 1
	assert json.loads(history[0].changes)["artist"]["old"] == "Test Artist"
	assert json.loads(history[0].changes)["artist"]["new"] == "Updated Artist"

def test_update_tag(update_manager, sample_tag):
	updates = {
		"name": "updated_rock",
		"aliases": ["rocks", "rocky", "rock_music"]
	}
	updated_tag = update_manager.update_tag(sample_tag.id, updates)
	
	assert updated_tag.name == "updated_rock"
	assert json.loads(updated_tag.aliases) == ["rocks", "rocky", "rock_music"]
	
	history = update_manager.get_update_history("tag", sample_tag.id)
	assert len(history) == 1
	assert json.loads(history[0].changes)["name"]["old"] == "rock"
	assert json.loads(history[0].changes)["name"]["new"] == "updated_rock"

def test_revert_update(update_manager, sample_album):
	# Make an update
	updates = {"artist": "Updated Artist"}
	updated_album = update_manager.update_album(sample_album.id, updates)
	assert updated_album.artist == "Updated Artist"
	
	# Get history and revert
	history = update_manager.get_update_history("album", sample_album.id)
	assert update_manager.revert_update(history[0].id)
	
	# Verify revert
	reverted_album = update_manager.db.query(models.Album).filter(
		models.Album.id == sample_album.id
	).first()
	assert reverted_album.artist == "Test Artist"