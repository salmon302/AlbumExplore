import pytest
import pandas as pd
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer

@pytest.fixture
def sample_df():
	"""Create a sample DataFrame for testing."""
	data = {
		'Artist': ['Band A', 'Band B', 'Band C'],
		'Album': ['Album 1', 'Album 2', 'Album 3'],
		'tags': [
			['progressive metal', 'death metal'],
			['black metal', 'death metal'],
			['progressive metal', 'black metal']
		]
	}
	return pd.DataFrame(data)

def test_tag_analyzer_initialization(sample_df):
	"""Test TagAnalyzer initialization."""
	analyzer = TagAnalyzer(sample_df)
	assert len(analyzer.tag_frequencies) == 3  # unique tags
	assert analyzer.graph.number_of_nodes() == 3

def test_analyze_tags(sample_df):
	"""Test tag analysis functionality."""
	analyzer = TagAnalyzer(sample_df)
	stats = analyzer.analyze_tags()
	
	assert stats['total_tags'] == 6  # total tag occurrences
	assert stats['unique_tags'] == 3  # unique tags
	assert stats['avg_tags_per_album'] == 2.0

def test_calculate_relationships(sample_df):
	"""Test tag relationship calculation."""
	analyzer = TagAnalyzer(sample_df)
	relationships = analyzer.calculate_relationships()
	
	# Check relationships exist
	assert ('black metal', 'death metal') in relationships
	assert ('black metal', 'progressive metal') in relationships
	assert ('death metal', 'progressive metal') in relationships

def test_find_similar_tags(sample_df):
	"""Test similar tags finding."""
	analyzer = TagAnalyzer(sample_df)
	analyzer.calculate_relationships()
	
	similar = analyzer.find_similar_tags('death metal')
	assert len(similar) > 0
	assert any(tag for tag, _ in similar if tag == 'black metal')

def test_get_tag_clusters(sample_df):
	"""Test tag clustering."""
	analyzer = TagAnalyzer(sample_df)
	analyzer.calculate_relationships()
	
	clusters = analyzer.get_tag_clusters()
	assert len(clusters) > 0
	assert all(len(cluster) >= 2 for cluster in clusters.values())