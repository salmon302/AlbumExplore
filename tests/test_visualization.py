import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from albumexplore.database import Base, models
from albumexplore.visualization.base import NetworkGraph, TableView, VisualNode, VisualEdge
from albumexplore.visualization.layout import ForceDirectedLayout, Point


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
def sample_data(session):
	# Create sample tags
	tag1 = models.Tag(id="metal", name="metal", category="genre")
	tag2 = models.Tag(id="prog", name="progressive", category="style")
	
	# Create sample albums
	album1 = models.Album(
		id="album1",
		artist="Artist1",
		title="Album1",
		release_year=2020,
		length="LP"
	)
	album2 = models.Album(
		id="album2",
		artist="Artist2",
		title="Album2",
		release_year=2021,
		length="EP"
	)
	
	# Set up relationships
	album1.tags.append(tag1)
	album2.tags.extend([tag1, tag2])
	
	session.add_all([tag1, tag2, album1, album2])
	session.commit()
	
	return {"albums": [album1, album2], "tags": [tag1, tag2]}

def test_network_graph_processing(sample_data):
	graph = NetworkGraph()
	graph.process_data(sample_data["albums"], sample_data["tags"])
	
	# Check nodes
	assert len(graph.nodes) == 2
	assert any(node.shape == "circle" for node in graph.nodes)  # LP
	assert any(node.shape == "square" for node in graph.nodes)  # EP
	
	# Check edges (should have one edge due to shared tag)
	assert len(graph.edges) == 1
	edge = graph.edges[0]
	assert edge.weight == 1  # One shared tag
	assert {"album1", "album2"} == {edge.source, edge.target}

def test_force_directed_layout(sample_data):
	graph = NetworkGraph()
	graph.process_data(sample_data["albums"], sample_data["tags"])
	
	# Test layout initialization
	assert not graph.is_layout_initialized
	graph.update_layout()
	assert graph.is_layout_initialized
	
	# Check if positions were created
	assert len(graph.layout.positions) == len(graph.nodes)
	for node in graph.nodes:
		pos = graph.layout.positions[node.id]
		assert isinstance(pos, Point)
		assert 0 <= pos.x <= graph.width
		assert 0 <= pos.y <= graph.height

def test_table_view_processing(sample_data):
	table = TableView()
	table.process_data(sample_data["albums"], sample_data["tags"])
	
	# Check rows
	assert len(table.nodes) == 2
	for node in table.nodes:
		assert node.shape == "row"
		assert "artist" in node.data
		assert "title" in node.data
		assert "year" in node.data
		assert "tags" in node.data