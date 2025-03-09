"""Tests for single instance tag handling."""
import pytest
import pandas as pd
import logging
from pathlib import Path

from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer
from albumexplore.tags.analysis.tag_similarity import TagSimilarity
from albumexplore.tags.analysis.single_instance_handler import SingleInstanceHandler
from .utils import create_test_data, setup_test_config

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def setup():
    """Set up test environment."""
    logger.debug("Setting up test environment")
    setup_test_config()
    yield
    logger.debug("Test environment cleanup complete")

@pytest.fixture
def sample_data():
    """Create sample tag data for testing."""
    tags_list = [
        ['prog-metal', 'technical metal'],
        ['prog-metal', 'experimental'],
        ['technical prog-metal', 'prog-metal'],
        ['experimental prog', 'unique variant'],
        ['single instance tag', 'prog-metal']
    ]
    logger.debug(f"Creating sample data with tags: {tags_list}")
    return create_test_data(tags_list)

@pytest.fixture
def handler(sample_data):
    """Create SingleInstanceHandler with initialized components."""
    logger.debug("Initializing test components")
    normalizer = TagNormalizer(test_mode=True)
    analyzer = TagAnalyzer(sample_data)
    similarity = TagSimilarity(analyzer)
    handler = SingleInstanceHandler(analyzer, normalizer, similarity)
    logger.debug("Test components initialized")
    return handler

def test_identify_single_instance_tags(handler):
    """Test identification of single-instance tags."""
    logger.debug("Testing single instance tag identification")
    singles = handler.identify_single_instance_tags()
    logger.debug(f"Identified single instance tags: {singles}")
    
    assert isinstance(singles, dict), "Should return a dictionary"
    assert 'unique variant' in singles, "Should identify 'unique variant' as single instance"
    assert 'single instance tag' in singles, "Should identify 'single instance tag' as single instance"
    assert 'prog-metal' not in singles, "Should not include multiple-instance tags"
    assert singles['unique variant'] == 1, "Single instance count should be 1"

def test_suggest_normalization(handler):
    """Test normalization suggestions."""
    logger.debug("Testing normalization suggestions")
    # Test suggestion for a single-instance tag
    suggestions = handler.suggest_normalization('unique variant')
    logger.debug(f"Suggestions for 'unique variant': {suggestions}")
    
    assert isinstance(suggestions, list), "Should return a list of suggestions"
    assert len(suggestions) > 0, "Should provide at least one suggestion"
    
    # Check for specific test mapping from config
    first_suggestion = suggestions[0]
    logger.debug(f"First suggestion: {first_suggestion}")
    assert first_suggestion[0] == 'experimental', "Should use test config mapping"
    assert first_suggestion[1] == 1.0, "Should have confidence 1.0 for exact match"
    
    # Verify suggestion structure
    assert len(first_suggestion) == 3, "Each suggestion should be a triple"
    assert isinstance(first_suggestion[0], str), "First element should be suggestion string"
    assert isinstance(first_suggestion[1], float), "Second element should be confidence float"
    assert isinstance(first_suggestion[2], str), "Third element should be reason string"

def test_pattern_based_suggestions(handler):
    """Test pattern-based suggestion generation."""
    logger.debug("Testing pattern-based suggestions")
    test_tag = 'experimental doom metal'
    suggestions = handler._get_pattern_based_suggestions(test_tag)
    logger.debug(f"Pattern suggestions for '{test_tag}': {suggestions}")
    
    assert isinstance(suggestions, list), "Should return a list"
    assert len(suggestions) > 0, "Should find pattern-based suggestions"
    
    for suggestion, confidence, reason in suggestions:
        assert isinstance(suggestion, str), "Suggestion should be string"
        assert confidence == 0.7, "Pattern confidence should be 0.7"
        assert isinstance(reason, str), "Should provide reason"
        assert "pattern" in reason.lower(), "Reason should mention pattern"
        logger.debug(f"Valid pattern suggestion: {suggestion} ({confidence}): {reason}")

def test_consolidation_suggestions(handler):
    """Test batch consolidation suggestions."""
    logger.debug("Testing consolidation suggestions")
    suggestions = handler.get_consolidation_suggestions()
    logger.debug(f"Consolidation suggestions: {suggestions}")
    
    assert isinstance(suggestions, dict), "Should return a dictionary"
    assert len(suggestions) > 0, "Should find suggestions"
    
    # Verify structure for each single-instance tag
    for tag, tag_suggestions in suggestions.items():
        logger.debug(f"Checking suggestions for tag '{tag}': {tag_suggestions}")
        assert isinstance(tag_suggestions, list), f"Suggestions for {tag} should be a list"
        assert len(tag_suggestions) > 0, f"Should have suggestions for {tag}"
        for suggestion in tag_suggestions:
            assert len(suggestion) == 3, "Each suggestion should be a triple"

def test_apply_suggestion(handler):
    """Test applying a single suggestion."""
    tag = 'unique variant'
    suggestion = 'experimental'
    logger.debug(f"Testing suggestion application: {tag} -> {suggestion}")
    
    # Record initial state
    initial_count = handler.analyzer.tag_counts[tag]
    logger.debug(f"Initial count for '{tag}': {initial_count}")
    assert initial_count == 1, "Should start with count of 1"
    
    # Apply suggestion
    handler.apply_suggestion(tag, suggestion)
    logger.debug(f"Applied suggestion. New tag counts: {handler.analyzer.tag_counts}")
    
    # Verify changes
    assert tag not in handler.analyzer.tag_counts, "Original tag should be removed"
    assert suggestion in handler.analyzer.tag_counts, "New tag should be added"
    assert handler.analyzer.tag_counts[suggestion] >= initial_count, "Count should be updated"

def test_apply_suggestions_batch(handler):
    """Test batch application of suggestions."""
    test_suggestions = {
        'unique variant': [('experimental', 0.9, 'test reason')],
        'single instance tag': [('prog-metal', 0.85, 'test reason')]
    }
    logger.debug(f"Testing batch suggestion application: {test_suggestions}")
    
    # Apply batch suggestions
    applied = handler.apply_suggestions_batch(test_suggestions)
    logger.debug(f"Applied suggestions: {applied}")
    assert len(applied) == 2, "Should apply both suggestions"
    
    # Verify results
    for tag, suggestion, confidence in applied:
        logger.debug(f"Verifying result: {tag} -> {suggestion} ({confidence})")
        assert confidence >= 0.8, "Only high confidence suggestions should be applied"
        assert tag not in handler.analyzer.tag_counts, f"Original tag {tag} should be removed"
        assert suggestion in handler.analyzer.tag_counts, f"New tag {suggestion} should be added"

def test_low_confidence_suggestions(handler):
    """Test handling of low confidence suggestions."""
    test_suggestions = {
        'unique variant': [('experimental', 0.5, 'low confidence')],
        'single instance tag': [('prog-metal', 0.3, 'very low confidence')]
    }
    logger.debug(f"Testing low confidence suggestions: {test_suggestions}")
    
    applied = handler.apply_suggestions_batch(test_suggestions)
    logger.debug(f"Applied low confidence suggestions: {applied}")
    assert len(applied) == 0, "Should not apply low confidence suggestions"