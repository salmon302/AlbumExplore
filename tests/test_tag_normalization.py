import pytest
from albumexplore.visualization.data_interface import TagNormalizer
from albumexplore.database import models, get_session
from albumexplore.database.tag_manager import TagManager

@pytest.fixture
def normalizer():
    return TagNormalizer()

@pytest.fixture
def session():
    return get_session()

@pytest.fixture
def tag_manager(session):
    return TagManager(session)

def test_basic_normalization(normalizer):
    """Test basic tag normalization cases."""
    assert normalizer.normalize("prog-metal") == "progressive metal"
    assert normalizer.normalize("Prog-Metal") == "progressive metal"
    assert normalizer.normalize("Progressive Metal") == "progressive metal"
    assert normalizer.normalize("ProgressiveMetal") == "progressive metal"

def test_variant_handling(normalizer):
    """Test handling of tag variants."""
    # Test different separators
    assert normalizer.normalize("math-rock") == "math rock"
    assert normalizer.normalize("math_rock") == "math rock"
    assert normalizer.normalize("mathrock") == "math rock"
    
    # Test case insensitivity
    assert normalizer.normalize("Math-Rock") == "math rock"
    assert normalizer.normalize("MATH ROCK") == "math rock"
    
    # Test prefix standardization
    assert normalizer.normalize("progressive rock") == "prog-rock"
    assert normalizer.normalize("technical death") == "tech-death"
    assert normalizer.normalize("experimental metal") == "exp-metal"

def test_category_inference(normalizer):
    """Test category inference from tag names."""
    assert normalizer.get_category("black metal") == "metal"
    assert normalizer.get_category("art rock") == "rock"
    assert normalizer.get_category("jazz fusion") == "fusion"
    assert normalizer.get_category("noise") == "experimental"
    assert normalizer.get_category("unknown style") == "other"

def test_tag_merging(tag_manager, session):
    """Test merging of similar tags."""
    # Create test tags
    tag1 = models.Tag(id="1", name="prog-metal", normalized_name="progressive metal")
    tag2 = models.Tag(id="2", name="progressive metal", normalized_name="progressive metal")
    session.add_all([tag1, tag2])
    session.commit()
    
    # Test merge
    tag_manager._merge_tags(tag1, tag2)
    session.refresh(tag1)
    session.refresh(tag2)
    
    assert tag1.is_canonical == 0
    assert tag2.is_canonical == 1
    assert tag1.normalized_name == tag2.normalized_name

def test_tag_categorization(tag_manager, session):
    """Test automatic tag categorization."""
    # Create test category
    metal_cat = models.TagCategory(id="metal", name="Metal")
    session.add(metal_cat)
    
    # Create test tags with relationships
    tag1 = models.Tag(id="1", name="death metal", category_id="metal")
    tag2 = models.Tag(id="2", name="melodic death")  # No category
    rel = models.TagRelation(
        tag1_id="1",
        tag2_id="2",
        relationship_type="related",
        strength=0.8
    )
    session.add_all([tag1, tag2, rel])
    session.commit()
    
    # Test category suggestion
    suggested = tag_manager.suggest_category(tag2)
    assert suggested == "metal"  # Should suggest metal based on relationship

def test_config_loading(normalizer):
    """Test loading of configuration from file."""
    normalizer.reload_config()
    
    # Test that basic substitutions are loaded
    assert "prog-?(?:metal|rock)" in normalizer._substitutions
    assert "progressive" in normalizer._prefix_standardization
    assert "metal" in normalizer._category_mapping

def test_cache_behavior(normalizer):
    """Test caching behavior of normalizer."""
    # Initial normalization
    result1 = normalizer.normalize("prog-metal")
    
    # Should use cache
    result2 = normalizer.normalize("prog-metal")
    
    assert result1 == result2
    assert "prog-metal" in normalizer._variant_cache
    
    # Clear cache
    normalizer.clear_cache()
    assert len(normalizer._variant_cache) == 0