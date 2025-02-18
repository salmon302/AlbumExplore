import pytest
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.filters import FilterSystem
from albumexplore.database import Base, models

@pytest.fixture
def sample_nodes():
	return [
		VisualNode(
			id="album1",
			label="Artist1 - Album1",
			size=2.0,
			color="#808080",
			shape="circle",
			data={
				"type": "album",
				"tags": ["metal", "prog"],
				"year": 2020,
				"genre": "metal"
			}
		),
		VisualNode(
			id="album2",
			label="Artist2 - Album2",
			size=1.0,
			color="#808080",
			shape="circle",
			data={
				"type": "album",
				"tags": ["rock"],
				"year": 2021,
				"genre": "rock"
			}
		),
		VisualNode(
			id="album3",
			label="Artist3 - Album3",
			size=1.0,
			color="#808080",
			shape="circle",
			data={
				"type": "album",
				"tags": ["metal", "rock"],
				"year": 2021,
				"genre": "metal"
			}
		)
	]

@pytest.fixture
def sample_edges():
	return [
		VisualEdge(
			source="album1",
			target="album2",
			weight=1.0,
			color="#666666",
			thickness=0.5,
			data={"shared_tags": ["rock"]}
		),
		VisualEdge(
			source="album2",
			target="album3",
			weight=0.5,
			color="#666666",
			thickness=0.25,
			data={"shared_tags": ["metal"]}
		)
	]

@pytest.fixture
def filter_system():
	return FilterSystem()

def test_tag_filter(filter_system, sample_nodes):
	filter_system.add_filter('tag', 'metal')
	filtered_nodes = filter_system.filter_nodes(sample_nodes)
	assert len(filtered_nodes) == 2
	assert {node.id for node in filtered_nodes} == {"album1", "album3"}

def test_year_range_filter(filter_system, sample_nodes):
	filter_system.add_filter('year_range', (2021, 2021))
	filtered_nodes = filter_system.filter_nodes(sample_nodes)
	assert len(filtered_nodes) == 2
	assert {node.id for node in filtered_nodes} == {"album2", "album3"}

def test_genre_filter(filter_system, sample_nodes):
	filter_system.add_filter('genre', 'metal')
	filtered_nodes = filter_system.filter_nodes(sample_nodes)
	assert len(filtered_nodes) == 2
	assert {node.id for node in filtered_nodes} == {"album1", "album3"}

def test_edge_filter(filter_system, sample_nodes, sample_edges):
	# Filter nodes by genre
	filter_system.add_filter('genre', 'metal')
	filtered_nodes = filter_system.filter_nodes(sample_nodes)
	visible_nodes = {node.id for node in filtered_nodes}
	
	# Filter edges based on visible nodes
	filtered_edges = filter_system.filter_edges(sample_edges, visible_nodes)
	assert len(filtered_edges) == 0  # No edges between metal albums

def test_edge_weight_filter(filter_system, sample_nodes, sample_edges):
	filter_system.add_filter('min_weight', 0.75)
	filtered_edges = filter_system.filter_edges(sample_edges, {node.id for node in sample_nodes})
	assert len(filtered_edges) == 1
	assert filtered_edges[0].source == "album1"
	assert filtered_edges[0].target == "album2"

def test_combined_filters(filter_system, sample_nodes, sample_edges):
	# Add multiple filters
	filter_system.add_filter('tag', 'metal')
	filter_system.add_filter('year_range', (2021, 2021))
	
	# Apply filters
	filtered_nodes, filtered_edges = filter_system.apply_filters(sample_nodes, sample_edges)
	
	# Should only get album3 (metal tag and 2021)
	assert len(filtered_nodes) == 1
	assert filtered_nodes[0].id == "album3"
	
	# Should get no edges as only one node is visible
	assert len(filtered_edges) == 0

def test_remove_filter(filter_system, sample_nodes):
	filter_system.add_filter('genre', 'metal')
	assert len(filter_system.filter_nodes(sample_nodes)) == 2
	
	filter_system.remove_filter('genre')
	assert len(filter_system.filter_nodes(sample_nodes)) == 3

def test_clear_filters(filter_system, sample_nodes):
	filter_system.add_filter('genre', 'metal')
	filter_system.add_filter('year_range', (2021, 2021))
	assert len(filter_system.filter_nodes(sample_nodes)) == 1
	
	filter_system.clear_filters()
	assert len(filter_system.filter_nodes(sample_nodes)) == 3