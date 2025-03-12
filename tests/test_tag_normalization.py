import pytest
from albumexplore.tags.normalizer import TagNormalizer

def test_tag_normalization():
    """Test basic tag normalization functionality."""
    normalizer = TagNormalizer()

    # Test basic normalization
    assert normalizer.normalize("Post-Metal") == "post-metal"
    assert normalizer.normalize("PROG METAL") == "prog metal"
    assert normalizer.normalize("Progressive  Metal") == "progressive metal"

    # Test special character handling
    assert normalizer.normalize("avant-garde/experimental") == "avant-garde experimental"
    assert normalizer.normalize("folk/pagan metal") == "folk pagan metal"

    # Test whitespace handling
    assert normalizer.normalize("  tech death  ") == "tech death"
    assert normalizer.normalize("melodic\tblack") == "melodic black"