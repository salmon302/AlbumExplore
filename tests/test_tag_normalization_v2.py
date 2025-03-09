"""Tests for enhanced tag normalization system."""
import pytest
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.tags.config.tag_rules_config import TagRulesConfig

@pytest.fixture
def normalizer():
    return TagNormalizer()

@pytest.fixture
def config():
    return TagRulesConfig()

def test_basic_normalization(normalizer):
    """Test basic tag normalization cases."""
    # Test prefix normalization
    assert normalizer.normalize("progressive metal") == "prog-metal"
    assert normalizer.normalize("alternative rock") == "alt-rock"
    assert normalizer.normalize("experimental jazz") == "exp-jazz"
    assert normalizer.normalize("atmospheric black metal") == "atmo-black-metal"
    
    # Test compound terms
    assert normalizer.normalize("post metal") == "post-metal"
    assert normalizer.normalize("postmetal") == "post-metal"
    assert normalizer.normalize("tech death") == "tech-death"
    assert normalizer.normalize("blackgaze") == "black-gaze"
    
    # Test misspellings
    assert normalizer.normalize("psych rock") == "psychedelic rock"
    assert normalizer.normalize("athmospheric") == "atmospheric"
    assert normalizer.normalize("avantgarde") == "avant-garde"
    
    # Test case insensitivity
    assert normalizer.normalize("PROG METAL") == "prog-metal"
    assert normalizer.normalize("Post-Metal") == "post-metal"
    
def test_category_detection(normalizer):
    """Test tag category detection."""
    # Metal categories
    assert normalizer.get_category("death metal") == "metal"
    assert normalizer.get_category("melodic black metal") == "metal"
    assert normalizer.get_category("prog-metal") == "metal"
    
    # Rock categories
    assert normalizer.get_category("psychedelic rock") == "rock"
    assert normalizer.get_category("prog-rock") == "rock"
    assert normalizer.get_category("indie rock") == "rock"
    
    # Electronic categories
    assert normalizer.get_category("darksynth") == "electronic"
    assert normalizer.get_category("synthwave") == "electronic"
    assert normalizer.get_category("industrial") == "electronic"
    
    # Other categories
    assert normalizer.get_category("world music") == "folk_world"
    assert normalizer.get_category("avant-garde") == "experimental"
    assert normalizer.get_category("jazz fusion") == "fusion"
    
def test_single_instance_handling(normalizer):
    """Test handling of single-instance tags."""
    # Register some single instance tags
    normalizer.register_single_instance_tag("ethereal doom metal")
    normalizer.register_single_instance_tag("cosmic black metal")
    
    # Test suggestions
    suggestions = normalizer.suggest_normalization_for_single_instance("ethereal doom metal")
    assert len(suggestions) > 0
    assert suggestions[0][0] == "atmospheric doom metal"  # Should be the highest confidence match
    
    # Test adding new rules
    normalizer.add_single_instance_rule("cosmic black metal", "atmospheric black metal")
    assert normalizer.normalize("cosmic black metal") == "atmospheric black metal"
    
def test_cache_behavior(normalizer):
    """Test caching behavior."""
    # First normalization should cache the result
    result1 = normalizer.normalize("prog metal")
    result2 = normalizer.normalize("prog metal")
    assert result1 == result2 == "prog-metal"
    
    # Clear cache and verify it recomputes
    normalizer.clear_cache()
    result3 = normalizer.normalize("prog metal")
    assert result3 == "prog-metal"
    
def test_merge_history(normalizer):
    """Test merge history tracking."""
    normalizer.add_variant("prog", "progressive")
    normalizer.add_variant("synth", "synthesizer")
    
    history = normalizer.get_merge_history()
    assert len(history) == 2
    assert history[0]["variant"] == "prog"
    assert history[0]["canonical"] == "progressive"
    assert "timestamp" in history[0]
    
def test_config_reloading(normalizer):
    """Test configuration reloading."""
    initial_result = normalizer.normalize("prog metal")
    normalizer.reload_config()
    reloaded_result = normalizer.normalize("prog metal")
    assert initial_result == reloaded_result
    
def test_prefix_patterns(config):
    """Test prefix pattern handling."""
    patterns = config.get_prefix_patterns("post-")
    assert "post" in patterns
    assert "post-" in patterns
    
def test_suffix_patterns(config):
    """Test suffix pattern handling."""
    patterns = config.get_suffix_patterns("core")
    assert "core" in patterns
    assert "-core" in patterns
    
def test_compound_terms(config):
    """Test compound term handling."""
    terms = config.get_compound_terms()
    assert "post-metal" in terms
    assert "black-metal" in terms
    
def test_category_info(config):
    """Test category information retrieval."""
    metal_info = config.get_category_info("metal")
    assert "core_terms" in metal_info
    assert "primary_genres" in metal_info
    assert "modifiers" in metal_info