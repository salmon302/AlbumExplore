import pytest
from albumexplore.tags.grouping import TagGroups

@pytest.fixture
def tag_groups():
	"""Create a TagGroups instance for testing."""
	return TagGroups()

@pytest.fixture
def sample_tags():
	"""Create a sample set of tags for testing."""
	return [
		'metal',
		'progressive metal',
		'technical death metal',
		'atmospheric black metal',
		'folk metal',
		'medieval folk metal',
		'experimental',
		'post-metal',
		'nordic black metal',
		'symphonic'
	]

def test_categorize_tag(tag_groups):
	"""Test tag categorization."""
	assert tag_groups.categorize_tag('metal') == 'primary'
	assert tag_groups.categorize_tag('progressive metal') == 'subgenres'
	assert tag_groups.categorize_tag('atmospheric') == 'modifiers'
	assert tag_groups.categorize_tag('post-metal') == 'fusion'
	assert tag_groups.categorize_tag('nordic black metal') == 'regional'
	assert tag_groups.categorize_tag('unknown') == 'other'

def test_group_tags(tag_groups, sample_tags):
	"""Test grouping multiple tags."""
	categories = tag_groups.group_tags(sample_tags)
	
	assert 'metal' in categories['primary']
	assert 'progressive metal' in categories['subgenres']
	assert 'experimental' in categories['modifiers']
	assert 'post-metal' in categories['fusion']
	assert 'nordic black metal' in categories['regional']

def test_get_related_subgenres(tag_groups, sample_tags):
	"""Test retrieving related subgenres."""
	tag_groups.group_tags(sample_tags)
	subgenres = tag_groups.get_related_subgenres('metal')
	
	assert 'progressive metal' in subgenres
	assert 'technical death metal' in subgenres
	assert 'folk metal' in subgenres

def test_get_style_combinations(tag_groups, sample_tags):
	"""Test retrieving style combinations."""
	tag_groups.group_tags(sample_tags)
	combinations = tag_groups.get_style_combinations('metal')
	
	assert any('atmospheric' in combo for combo in combinations)
	assert any('technical' in combo for combo in combinations)
	assert any('symphonic' in combo for combo in combinations)

def test_get_category_hierarchy(tag_groups, sample_tags):
	"""Test retrieving category hierarchy."""
	tag_groups.group_tags(sample_tags)
	hierarchy = tag_groups.get_category_hierarchy()
	
	assert 'metal' in hierarchy
	metal_hierarchy = hierarchy['metal']
	assert 'subgenres' in metal_hierarchy
	assert 'modifiers' in metal_hierarchy
	assert 'fusion' in metal_hierarchy
	
	assert any('progressive metal' in subgenre for subgenre in metal_hierarchy['subgenres'])
	assert any('atmospheric' in modifier for modifier in metal_hierarchy['modifiers'])
	assert any('post-metal' in fusion for fusion in metal_hierarchy['fusion'])