"""Tests for tag similarity analysis."""
import pytest
import pandas as pd
from typing import List, Set

from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer
from albumexplore.tags.analysis.tag_similarity import TagSimilarity
from .utils import create_test_data

@pytest.fixture
def sample_data():
    """Create sample tag data for testing."""
    tags_list = [
        ['prog-metal', 'technical metal', 'experimental'],
        ['prog-metal', 'avant-garde metal', 'experimental'],
        ['technical death metal', 'prog-metal'],
        ['experimental prog', 'progressive rock'],
        ['technical metal', 'prog-metal'],
        ['atmospheric black metal', 'cosmic black metal'],
        ['experimental black metal', 'atmospheric black metal'],
        ['psychedelic rock', 'psych rock', 'space rock']
    ]
    return create_test_data(tags_list, n_albums=8)

@pytest.fixture
def similarity(sample_data):
    """Create TagSimilarity instance with sample data."""
    analyzer = TagAnalyzer(sample_data)
    return TagSimilarity(analyzer)

def test_find_similar_tags(similarity):
    """Test finding similar tags."""
    # Test co-occurrence based similarity
    similar = similarity.find_similar_tags('prog-metal')
    assert len(similar) > 0
    assert any(tag == 'technical metal' for tag, _ in similar)
    
    # Test string similarity
    similar = similarity.find_similar_tags('psych rock')
    assert any(tag == 'psychedelic rock' for tag, _ in similar)
    assert all(0 <= score <= 1.0 for _, score in similar)

def test_cooccurrence_similarity(similarity):
    """Test co-occurrence based similarity."""
    similar = similarity._get_cooccurrence_similarity('prog-metal')
    assert len(similar) > 0
    assert any(tag == 'technical metal' for tag, _ in similar)
    assert all(score > 0 for _, score in similar)

def test_string_similarity(similarity):
    """Test string similarity metrics."""
    similar = similarity._get_string_similarity('atmospheric black metal')
    assert len(similar) > 0
    assert any(tag == 'experimental black metal' for tag, _ in similar)
    assert all(0 <= score <= 1.0 for _, score in similar)

def test_pattern_similarity(similarity):
    """Test pattern-based similarity."""
    similar = similarity._get_pattern_similarity('experimental black metal')
    assert len(similar) > 0
    # Should find matches with same prefix or suffix pattern
    assert any('experimental' in tag for tag, _ in similar)
    assert any('black metal' in tag for tag, _ in similar)
    assert all(score == 0.7 for _, score in similar)

def test_similarity_threshold(similarity):
    """Test similarity threshold filtering."""
    # Get results with different thresholds
    high_threshold = similarity.find_similar_tags('prog-metal', threshold=0.8)
    low_threshold = similarity.find_similar_tags('prog-metal', threshold=0.3)
    
    # High threshold should return fewer results
    assert len(high_threshold) <= len(low_threshold)
    # High threshold results should all be in low threshold results
    high_tags = {tag for tag, _ in high_threshold}
    low_tags = {tag for tag, _ in low_threshold}
    assert high_tags.issubset(low_tags)

def test_caching(similarity):
    """Test similarity cache behavior."""
    tag = 'prog-metal'
    
    # First call should compute similarity
    first_result = similarity.find_similar_tags(tag)
    assert tag in similarity._similarity_cache
    
    # Second call should use cache
    second_result = similarity.find_similar_tags(tag)
    assert first_result == second_result
    
    # Clear cache and verify recomputation
    similarity.clear_cache()
    assert tag not in similarity._similarity_cache

def test_find_similar_tag_clusters(similarity):
    """Test finding clusters of similar tags."""
    clusters = similarity.find_similar_tag_clusters(min_similarity=0.6)
    
    # Verify cluster properties
    assert len(clusters) > 0
    assert all(isinstance(cluster, set) for cluster in clusters)
    assert all(len(cluster) > 0 for cluster in clusters)
    
    # Check specific clusters
    found_metal_cluster = False
    found_rock_cluster = False
    
    for cluster in clusters:
        if 'prog-metal' in cluster:
            found_metal_cluster = True
            assert any('technical' in tag for tag in cluster)
        elif 'psychedelic rock' in cluster:
            found_rock_cluster = True
            assert 'psych rock' in cluster
            
    assert found_metal_cluster, "Should find prog metal cluster"
    assert found_rock_cluster, "Should find psychedelic rock cluster"

def test_score_normalization(similarity):
    """Test that similarity scores are properly normalized."""
    for tag in ['prog-metal', 'experimental', 'psychedelic rock']:
        similar = similarity.find_similar_tags(tag)
        assert all(0 <= score <= 1.0 for _, score in similar), f"Invalid scores for {tag}"

def test_combined_similarity_scores(similarity):
    """Test combining similarity scores from different metrics."""
    # Create test similarity scores
    test_similarities = [
        ('tag1', 0.8),
        ('tag2', 0.6),
        ('tag1', 0.7),  # Duplicate tag with different score
        ('tag3', 0.9)
    ]
    
    combined = similarity._combine_similarity_scores([test_similarities])
    
    # Check results
    assert isinstance(combined, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in combined)
    assert len(combined) == 3  # Should have 3 unique tags
    
    # Verify max score is used for duplicates
    tag1_score = next(score for tag, score in combined if tag == 'tag1')
    assert tag1_score == 0.8  # Should use max score for tag1