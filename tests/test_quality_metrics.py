import pytest
import pandas as pd
import networkx as nx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database import Base, models
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer
from albumexplore.tags.management.quality_metrics import QualityMetrics
from albumexplore.tags.management.review_queue import ReviewQueue

@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def categories(session):
    # Create tag categories
    genre = models.TagCategory(id="genre", name="Genre")
    style = models.TagCategory(id="style", name="Style")
    modifier = models.TagCategory(id="modifier", name="Modifier")
    session.add_all([genre, style, modifier])
    session.commit()
    return {"genre": genre, "style": style, "modifier": modifier}

@pytest.fixture
def test_data(categories):
    """Create sample tag data for testing."""
    return pd.DataFrame({
        'tags': [
            ['metal', 'prog-metal', 'progressive'],  # Test consistent metal tags
            ['black-metal', 'blackened', 'atmospheric'],  # Test modifier variations
            ['death-metal', 'technical', 'brutal'],  # Test with style modifiers
            ['prog', 'progressive', 'experimental']  # Test variant consistency
        ],
        'categories': [
            ['genre', 'genre', 'modifier'],
            ['genre', 'modifier', 'modifier'],
            ['genre', 'modifier', 'modifier'],
            ['style', 'style', 'modifier']
        ]
    })

@pytest.fixture
def analyzer(test_data):
    """Create TagAnalyzer instance."""
    analyzer = TagAnalyzer(test_data)
    analyzer.calculate_relationships()
    
    # Build graph connections with categories
    for tags, cats in zip(test_data['tags'], test_data['categories']):
        for i, (tag1, cat1) in enumerate(zip(tags, cats)):
            for tag2, cat2 in zip(tags[i+1:], cats[i+1:]):
                if not analyzer.graph.has_edge(tag1, tag2):
                    analyzer.graph.add_edge(
                        tag1, tag2,
                        weight=1.0,
                        categories=(cat1, cat2)
                    )
    return analyzer

@pytest.fixture
def metrics(analyzer):
    """Create QualityMetrics instance."""
    review_queue = ReviewQueue()
    return QualityMetrics(analyzer, review_queue)

def test_consistency_score(metrics, analyzer):
    """Test tag consistency scoring."""
    score = metrics.calculate_consistency_score("prog")
    assert 0 <= score <= 1.0
    
    # Variant with high co-occurrence should have good score
    prog_score = metrics.calculate_consistency_score("progressive")
    assert prog_score > 0.7

def test_ambiguity_index(metrics, analyzer):
    """Test tag ambiguity detection."""
    # Test modifier tag used in different contexts
    atmospheric_index = metrics.calculate_ambiguity_index("atmospheric")
    assert atmospheric_index > 0.5
    
    # Test more specific tag
    death_metal_index = metrics.calculate_ambiguity_index("death-metal")
    assert death_metal_index < 0.3

def test_relationship_strength(metrics, analyzer):
    """Test relationship strength calculations."""
    # Test strongly related tags
    strength = metrics.calculate_relationship_strength("prog", "progressive")
    assert strength > 0.8
    
    # Test weakly related tags
    weak_strength = metrics.calculate_relationship_strength("prog", "brutal")
    assert weak_strength < 0.3

def test_get_low_quality_tags(metrics):
    """Test identification of problematic tags."""
    low_quality = metrics.get_low_quality_tags()
    
    # Should identify some inconsistent tags
    assert len(low_quality) > 0
    
    # Each tag should have quality issues identified
    for tag_info in low_quality:
        assert "tag" in tag_info
        assert "issues" in tag_info
        assert len(tag_info["issues"]) > 0
