"""Tests for tag analysis functionality."""
import pytest
import pandas as pd
from typing import List

from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer

@pytest.fixture
def sample_df():
    """Create sample DataFrame for testing."""
    data = {
        'Artist': ['Band A', 'Band B', 'Band C'],
        'Title': ['Album 1', 'Album 2', 'Album 3'],
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
    # We now use tag_counts instead of tag_frequencies
    assert len(analyzer.tag_counts) == 3  # unique tags
    assert analyzer.tag_counts['death metal'] == 2  # appears twice
    assert analyzer.tag_counts['progressive metal'] == 2
    assert analyzer.tag_counts['black metal'] == 2

def test_analyze_tags(sample_df):
    """Test tag analysis functionality."""
    analyzer = TagAnalyzer(sample_df)
    assert len(analyzer.relationship_graph.nodes()) == 3
    assert len(analyzer.relationship_graph.edges()) > 0
    
    # Check co-occurrence counts
    death_metal_co = analyzer.get_co_occurrences('death metal')
    assert death_metal_co['black metal'] == 1
    assert death_metal_co['progressive metal'] == 1

def test_tag_relationships(sample_df):
    """Test tag relationship analysis."""
    analyzer = TagAnalyzer(sample_df)
    
    # Test co-occurrences
    co_occurs = analyzer.get_co_occurrences('progressive metal')
    assert co_occurs['death metal'] == 1
    assert co_occurs['black metal'] == 1
    
    # Test graph edges
    assert analyzer.relationship_graph.has_edge('progressive metal', 'death metal')
    assert analyzer.relationship_graph.has_edge('black metal', 'death metal')
    assert analyzer.relationship_graph.has_edge('progressive metal', 'black metal')

def test_find_similar_tags(sample_df):
    """Test similar tags finding."""
    analyzer = TagAnalyzer(sample_df)
    
    similar = analyzer.find_similar_tags('progressive metal')
    assert len(similar) > 0
    
    # Both black metal and death metal should be similar to progressive metal
    similar_tags = [tag for tag, _ in similar]
    assert 'black metal' in similar_tags
    assert 'death metal' in similar_tags
    
    # All similarity scores should be valid
    assert all(0 <= score <= 1.0 for _, score in similar)

def test_get_tag_clusters(sample_df):
    """Test tag clustering."""
    analyzer = TagAnalyzer(sample_df)
    clusters = analyzer.get_tag_clusters()
    
    assert len(clusters) > 0
    assert isinstance(clusters[0], set)
    
    # All tags should be in one cluster since they're all connected
    assert len(clusters) == 1
    assert len(clusters[0]) == 3

def test_common_patterns(sample_df):
    """Test pattern detection."""
    # Add some data with clear patterns
    data = {
        'Artist': ['Band D', 'Band E', 'Band F'],
        'Title': ['Album 4', 'Album 5', 'Album 6'],
        'tags': [
            ['progressive metal', 'progressive rock'],
            ['technical death metal', 'technical metal'],
            ['atmospheric black metal', 'atmospheric death metal']
        ]
    }
    df = pd.concat([sample_df, pd.DataFrame(data)], ignore_index=True)
    analyzer = TagAnalyzer(df)
    
    patterns = analyzer.get_common_patterns()
    # 'progressive', 'technical', 'atmospheric' should be detected as prefixes
    # 'metal' should be detected as a suffix
    assert 'progressive' in patterns
    assert 'metal' in patterns
    assert len(patterns['metal']) >= 2  # Should have multiple variants