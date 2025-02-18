import pytest
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.info_display import InfoDisplay

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
				"artist": "Artist1",
				"title": "Album1",
				"year": 2020,
				"genre": "metal",
				"tags": ["metal", "prog"],
				"length": "LP"
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
				"artist": "Artist2",
				"title": "Album2",
				"year": 2021,
				"genre": "rock",
				"tags": ["rock"],
				"length": "EP"
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
			data={
				"type": "connection",
				"shared_tags": ["rock"]
			}
		)
	]

@pytest.fixture
def info_display():
	return InfoDisplay()

def test_node_details(info_display, sample_nodes):
	details = info_display.get_node_details(sample_nodes[0])
	assert details["id"] == "album1"
	assert details["artist"] == "Artist1"
	assert details["title"] == "Album1"
	assert details["year"] == 2020
	assert details["genre"] == "metal"
	assert set(details["tags"]) == {"metal", "prog"}
	assert details["length"] == "LP"
	assert details["connections"] == 2.0

def test_edge_details(info_display, sample_edges):
	details = info_display.get_edge_details(sample_edges[0])
	assert details["source"] == "album1"
	assert details["target"] == "album2"
	assert details["weight"] == 1.0
	assert details["shared_tags"] == ["rock"]
	assert details["type"] == "connection"

def test_selection_summary(info_display, sample_nodes, sample_edges):
	summary = info_display.get_selection_summary(sample_nodes, sample_edges)
	assert summary["node_count"] == 2
	assert summary["edge_count"] == 1
	assert set(summary["genres"]) == {"metal", "rock"}
	assert set(summary["years"]) == {2020, 2021}
	assert summary["total_connections"] == 1.0
	assert summary["average_connection_strength"] == 1.0

def test_view_statistics(info_display, sample_nodes, sample_edges):
	stats = info_display.get_view_statistics(sample_nodes, sample_edges)
	assert stats["total_nodes"] == 2
	assert stats["total_edges"] == 1
	assert stats["genre_distribution"] == {"metal": 1, "rock": 1}
	assert stats["year_distribution"] == {2020: 1, 2021: 1}
	assert stats["tag_distribution"] == {"metal": 1, "prog": 1, "rock": 1}
	assert stats["average_connections"] == 1.0
	assert stats["density"] == 1.0  # One edge out of one possible edge