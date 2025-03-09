"""Tests for tag relationship management."""
import pytest
import networkx as nx
from typing import Dict, List, Set

from albumexplore.tags.normalizer import TagNormalizer
from albumexplore.tags.analysis import TagAnalyzer, TagSimilarity
from albumexplore.tags.relationships import TagRelationships
from .utils import create_test_data

@pytest.fixture
def sample_data():
    """Create sample tag data for testing."""
    tags_list = [
        ['prog-metal', 'technical metal', 'experimental'],
        ['prog-metal', 'avant-garde metal', 'experimental'],
        ['technical death metal', 'prog-metal'],
        ['progressive metal', 'prog-metal'],  # variant
        ['technical metal', 'prog-metal'],
        ['atmospheric black metal', 'cosmic black metal'],
        ['experimental black metal', 'atmospheric black metal'],
        ['psychedelic rock', 'psych rock', 'space rock'],
        ['progressive rock', 'prog rock'],  # variant
        ['metal', 'heavy metal'],  # broader term
        ['symphonic metal', 'metal'],  # narrower term
        ['technical death metal', 'death metal']  # specialization
    ]
    return create_test_data(tags_list, n_albums=12)

@pytest.fixture
def relationships(sample_data):
    """Create TagRelationships instance with sample data."""
    normalizer = TagNormalizer(test_mode=True)
    analyzer = TagAnalyzer(sample_data)
    similarity = TagSimilarity(analyzer)
    return TagRelationships(normalizer, analyzer, similarity)

def test_graph_initialization(relationships):
    """Test initial graph construction."""
    assert isinstance(relationships.relationship_graph, nx.DiGraph)
    assert len(relationships.relationship_graph.nodes()) > 0
    assert len(relationships.relationship_graph.edges()) > 0
    
    # Check node attributes
    for node in relationships.relationship_graph.nodes():
        attrs = relationships.relationship_graph.nodes[node]
        assert 'count' in attrs
        assert 'category' in attrs
        
    # Check edge attributes
    for u, v, attrs in relationships.relationship_graph.edges(data=True):
        assert 'type' in attrs
        assert attrs['type'] in ('variant', 'specialization')

def test_tag_variants(relationships):
    """Test variant tag identification."""
    variants = relationships.get_tag_variants('prog-metal')
    assert 'progressive metal' in variants
    
    variants = relationships.get_tag_variants('psychedelic rock')
    assert 'psych rock' in variants

def test_hierarchical_relationships(relationships):
    """Test hierarchical tag relationships."""
    # Test broader tags
    broader = relationships.get_broader_tags('symphonic metal')
    assert 'metal' in broader
    
    # Test narrower tags
    narrower = relationships.get_narrower_tags('metal')
    assert 'symphonic metal' in narrower
    
    # Test specialization relationships
    broader = relationships.get_broader_tags('technical death metal')
    assert 'death metal' in broader

def test_related_tags(relationships):
    """Test finding related tags."""
    related = relationships.get_related_tags('prog-metal')
    assert len(related) > 0
    
    # Check structure
    for tag, score in related:
        assert isinstance(tag, str)
        assert isinstance(score, float)
        assert 0 <= score <= 1.0
        
    # Variants should have highest similarity
    variant_score = next(score for tag, score in related 
                        if tag == 'progressive metal')
    assert variant_score == 1.0
    
    # Check hierarchical relationships
    metal_related = relationships.get_related_tags('metal')
    assert any(tag == 'symphonic metal' and score >= 0.9 
              for tag, score in metal_related)

def test_canonical_form_suggestion(relationships):
    """Test canonical form suggestions."""
    # Test variant normalization
    canonical = relationships.suggest_canonical_form('prog rock')
    assert canonical == 'progressive rock'
    
    # Test no suggestion for canonical forms
    canonical = relationships.suggest_canonical_form('prog-metal')
    assert canonical is None or canonical == 'prog-metal'

def test_tag_hierarchy(relationships):
    """Test hierarchical tag structure."""
    # Test full hierarchy
    hierarchy = relationships.get_tag_hierarchy()
    assert isinstance(hierarchy, dict)
    assert len(hierarchy) > 0
    
    # Test specific root
    metal_hierarchy = relationships.get_tag_hierarchy('metal')
    assert 'variants' in metal_hierarchy
    assert 'narrower' in metal_hierarchy
    assert any('symphonic metal' in branch 
              for branch in metal_hierarchy['narrower'].keys())

def test_tag_merging(relationships):
    """Test tag merging functionality."""
    # Record initial state
    initial_count = relationships.analyzer.tag_counts['prog-metal']
    variant_count = relationships.analyzer.tag_counts['progressive metal']
    
    # Merge tags
    relationships.merge_tags('progressive metal', 'prog-metal')
    
    # Check counts are combined
    assert relationships.analyzer.tag_counts['prog-metal'] == initial_count + variant_count
    assert 'progressive metal' not in relationships.analyzer.tag_counts
    
    # Check graph updates
    assert 'progressive metal' not in relationships.relationship_graph
    assert 'prog-metal' in relationships.relationship_graph

def test_relationship_transitivity(relationships):
    """Test transitive relationship handling."""
    # Set up chain: tech death -> death metal -> metal
    death_broader = relationships.get_broader_tags('technical death metal')
    assert 'death metal' in death_broader
    
    metal_broader = relationships.get_broader_tags('death metal')
    assert 'metal' in metal_broader
    
    # Check narrower relationships
    metal_narrower = relationships.get_narrower_tags('metal')
    assert 'death metal' in metal_narrower
    
    death_narrower = relationships.get_narrower_tags('death metal')
    assert 'technical death metal' in death_narrower

def test_cycle_prevention(relationships):
    """Test prevention of cyclic relationships."""
    # Try to create a cycle
    relationships.merge_tags('technical metal', 'metal')
    relationships.merge_tags('death metal', 'technical death metal')
    
    # Verify no cycles exist
    assert nx.is_directed_acyclic_graph(relationships.relationship_graph)

def test_multi_path_relationships(relationships):
    """Test handling of multiple relationship paths."""
    # Create multiple paths
    relationships.merge_tags('prog rock', 'progressive rock')
    relationships.merge_tags('progressive metal', 'prog-metal')
    
    # Both should resolve to same canonical form
    assert (relationships.suggest_canonical_form('prog rock') == 
            relationships.suggest_canonical_form('progressive rock'))
    assert (relationships.suggest_canonical_form('progressive metal') == 
            relationships.suggest_canonical_form('prog-metal'))