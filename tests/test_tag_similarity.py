import pytest
import pandas as pd
from albumexplore.tags.analysis import TagAnalyzer
from albumexplore.tags.analysis.tag_similarity import TagSimilarity

@pytest.fixture
def sample_df():
	"""Create a sample DataFrame for testing."""
	data = {
		'Artist': ['Band A', 'Band B', 'Band C', 'Band D'],
		'Album': ['Album 1', 'Album 2', 'Album 3', 'Album 4'],
		'tags': [
			['progressive metal', 'technical death metal'],
			['death metal', 'technical death metal'],
			['progressive metal', 'melodic death metal'],
			['death metal', 'melodic death metal']
		]
	}
	return pd.DataFrame(data)

@pytest.fixture
def tag_similarity(sample_df):
	"""Create TagSimilarity instance with sample data."""
	analyzer = TagAnalyzer(sample_df)
	analyzer.calculate_relationships()
	return TagSimilarity(analyzer)

def test_similarity_initialization(tag_similarity):
	"""Test TagSimilarity initialization."""
	assert isinstance(tag_similarity.similarity_matrix, dict)
	assert isinstance(tag_similarity.cached_similarities, dict)

def test_calculate_similarities(tag_similarity):
	"""Test similarity calculation between tags."""
	similarities = tag_similarity.calculate_similarities()
	
	# Check that similarities exist
	assert len(similarities) > 0
	
	# Check symmetry
	for (tag1, tag2), sim in similarities.items():
		assert similarities.get((tag2, tag1)) == sim
		assert 0 <= sim <= 1  # Similarity should be between 0 and 1

def test_find_similar_tags(tag_similarity):
	"""Test finding similar tags."""
	similar_tags = tag_similarity.find_similar_tags('death metal')
	
	assert len(similar_tags) > 0
	for tag, similarity in similar_tags:
		assert isinstance(similarity, float)
		assert 0 <= similarity <= 1

def test_tag_similarity_metrics(tag_similarity):
	"""Test individual similarity metrics."""
	tag1 = 'technical death metal'
	tag2 = 'melodic death metal'
	
	# Test string similarity
	string_sim = tag_similarity._calculate_tag_similarity(tag1, tag2)
	assert 0 <= string_sim <= 1
	
	# Test co-occurrence similarity
	cooc_sim = tag_similarity._calculate_cooccurrence_similarity(tag1, tag2)
	assert 0 <= cooc_sim <= 1
	
	# Test network similarity
	network_sim = tag_similarity._calculate_network_similarity(tag1, tag2)
	assert 0 <= network_sim <= 1