import pytest
from albumexplore.tags import TagNormalizer, TagRelationships

def test_tag_normalizer_initialization():
	"""Test tag normalizer initialization."""
	normalizer = TagNormalizer()
	assert len(normalizer.known_tags) > 0
	assert isinstance(normalizer.tag_aliases, dict)

def test_basic_normalization():
	"""Test basic tag normalization."""
	normalizer = TagNormalizer()
	
	# Test common misspellings
	assert normalizer.normalize('prog') == 'progressive'
	assert normalizer.normalize('prog metal') == 'progressive metal'
	
	# Test case normalization
	assert normalizer.normalize('DEATH METAL') == 'death metal'
	assert normalizer.normalize('Black Metal') == 'black metal'

def test_tag_alias_management():
	"""Test tag alias functionality."""
	normalizer = TagNormalizer()
	
	normalizer.add_alias('melodeath', 'melodic death metal')
	assert normalizer.normalize('melodeath') == 'melodic death metal'

def test_tag_relationships_initialization():
	"""Test tag relationships initialization."""
	relationships = TagRelationships()
	assert len(relationships.hierarchies) > 0
	assert relationships.graph.number_of_nodes() > 0

def test_hierarchy_navigation():
	"""Test tag hierarchy navigation."""
	relationships = TagRelationships()
	
	# Test parent-child relationships
	parents = relationships.get_parent_tags('melodic death metal')
	assert 'death metal' in parents
	assert 'metal' in parents
	
	children = relationships.get_child_tags('death metal')
	assert 'melodic death metal' in children
	assert 'technical death metal' in children

def test_tag_similarity():
	"""Test tag similarity calculations."""
	relationships = TagRelationships()
	
	# Test exact match
	assert relationships.calculate_similarity('death metal', 'death metal') == 1.0
	
	# Test related tags
	similarity = relationships.calculate_similarity('melodic death metal', 'death metal')
	assert 0 < similarity < 1
	
	# Test unrelated tags
	assert relationships.calculate_similarity('death metal', 'folk metal') < 0.5

def test_related_tags():
	"""Test related tags retrieval."""
	relationships = TagRelationships()
	
	related = relationships.get_related_tags('black metal')
	assert len(related) > 0
	assert any(tag for tag, weight in related if 'atmospheric' in tag)

def test_integrated_tag_system():
	"""Test integration between normalizer and relationships."""
	normalizer = TagNormalizer()
	relationships = TagRelationships()
	
	# Test normalization followed by relationship lookup
	raw_tag = 'prog metal'
	normalized = normalizer.normalize(raw_tag)
	assert normalized == 'progressive metal'
	
	# Check relationships of normalized tag
	parents = relationships.get_parent_tags(normalized)
	assert 'metal' in parents