import pytest
from albumexplore.database import get_session, models
from albumexplore.database.tag_validation import TagValidator, TagValidationError

@pytest.fixture
def session():
    return get_session()

@pytest.fixture
def validator(session):
    return TagValidator(session)

@pytest.fixture
def categories(session):
    metal = models.TagCategory(id="metal", name="Metal")
    rock = models.TagCategory(id="rock", name="Rock")
    session.add_all([metal, rock])
    session.commit()
    return {"metal": metal, "rock": rock}

@pytest.fixture
def sample_tags(session, categories):
    tags = [
        models.Tag(
            id="1",
            name="death metal",
            normalized_name="death metal",
            category_id="metal",
            is_canonical=1
        ),
        models.Tag(
            id="2", 
            name="prog metal",
            normalized_name="progressive metal",
            category_id="metal",
            is_canonical=1
        ),
        models.Tag(
            id="3",
            name="art rock",
            normalized_name="art rock",
            category_id="rock",
            is_canonical=1
        ),
        models.Tag(
            id="4",
            name="progressive metal",
            normalized_name="progressive metal",
            category_id="metal",
            is_canonical=0
        )
    ]
    session.add_all(tags)
    session.commit()
    return tags

def test_validate_merge_basic(validator, sample_tags):
    """Test basic merge validation."""
    source = sample_tags[1]  # prog metal
    target = sample_tags[0]  # death metal
    
    # Should be valid with warning about existing variants
    warnings = validator.validate_merge(source, target)
    assert len(warnings) == 0

def test_validate_merge_non_canonical(validator, sample_tags):
    """Test merge validation with non-canonical tags."""
    source = sample_tags[1]  # prog metal
    target = sample_tags[3]  # non-canonical progressive metal
    
    with pytest.raises(TagValidationError) as exc:
        validator.validate_merge(source, target)
    assert "not a canonical tag" in str(exc.value)

def test_validate_merge_different_categories(validator, sample_tags):
    """Test merge validation with different categories."""
    source = sample_tags[1]  # prog metal
    target = sample_tags[2]  # art rock
    
    warnings = validator.validate_merge(source, target)
    assert len(warnings) == 1
    assert "different categories" in warnings[0]

def test_validate_merge_hierarchy_conflict(validator, sample_tags, session):
    """Test merge validation with hierarchy conflicts."""
    # Create circular hierarchy
    tag1, tag2 = sample_tags[0], sample_tags[1]
    tag1.parent_tags.append(tag2)
    session.commit()
    
    with pytest.raises(TagValidationError) as exc:
        validator.validate_merge(tag1, tag2)
    assert "circular hierarchy" in str(exc.value)

def test_validate_category_change(validator, sample_tags, categories):
    """Test category change validation."""
    tag = sample_tags[0]  # death metal
    
    # Valid change
    warnings = validator.validate_category_change(tag, "rock")
    assert len(warnings) == 0
    
    # Invalid category
    with pytest.raises(TagValidationError) as exc:
        validator.validate_category_change(tag, "invalid")
    assert "does not exist" in str(exc.value)

def test_validate_new_tag(validator, categories):
    """Test new tag validation."""
    # Valid tag
    assert validator.validate_new_tag("new metal tag", "metal")
    
    # Invalid characters
    assert not validator.validate_new_tag("invalid$tag!")
    
    # Empty name
    assert not validator.validate_new_tag("")
    
    # Invalid category
    assert not validator.validate_new_tag("valid name", "invalid_category")

def test_hierarchy_conflict_detection(validator, sample_tags, session):
    """Test detection of hierarchy conflicts."""
    tag1, tag2, tag3 = sample_tags[0:3]
    
    # Create hierarchy: tag1 -> tag2 -> tag3
    tag2.parent_tags.append(tag1)
    tag3.parent_tags.append(tag2)
    session.commit()
    
    # Should detect potential circular reference
    assert validator._has_hierarchy_conflict(tag3, tag1)
    
    # No conflict in non-circular hierarchy
    assert not validator._has_hierarchy_conflict(tag1, tag3)