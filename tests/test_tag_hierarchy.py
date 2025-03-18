import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database import Base, models
from albumexplore.tags.relationships import TagRelationships
from albumexplore.database.crud import (
    add_parent_tag,
    remove_parent_tag,
    get_inherited_tags,
    get_tag_children
)

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
    session.add_all([genre, style])
    session.commit()
    return {"genre": genre, "style": style}

@pytest.fixture
def create_tag(session):
    """Helper fixture to create a tag."""
    def _create_tag(tag_data):
        tag = models.Tag(
            id=tag_data['id'],
            name=tag_data['name'],
            category_id=tag_data.get('category_id', 'genre')  # Default to genre category
        )
        session.add(tag)
        session.commit()
        return tag
    return _create_tag

def test_add_parent_tag(session, create_tag):
    # Create test tags
    parent = create_tag({'id': 'metal', 'name': 'Metal'})
    child = create_tag({'id': 'prog-metal', 'name': 'Progressive Metal'})
    
    # Test adding parent relationship
    result = add_parent_tag(session, child.id, parent.id)
    assert result is True
    
    # Verify relationship
    child_tag = session.query(models.Tag).filter(models.Tag.id == 'prog-metal').first()
    assert len(child_tag.parent_tags) == 1
    assert child_tag.parent_tags[0].id == 'metal'

def test_remove_parent_tag(session, create_tag):
    # Create and link tags
    parent = create_tag({'id': 'metal', 'name': 'Metal'})
    child = create_tag({'id': 'prog-metal', 'name': 'Progressive Metal'})
    add_parent_tag(session, child.id, parent.id)
    
    # Test removing relationship
    result = remove_parent_tag(session, child.id, parent.id)
    assert result is True
    
    # Verify relationship removed
    child_tag = session.query(models.Tag).filter(models.Tag.id == 'prog-metal').first()
    assert len(child_tag.parent_tags) == 0

def test_get_inherited_tags(session, create_tag):
    # Create tag hierarchy
    root = create_tag({'id': 'metal', 'name': 'Metal'})
    mid = create_tag({'id': 'prog-metal', 'name': 'Progressive Metal'})
    leaf = create_tag({'id': 'tech-prog-metal', 'name': 'Technical Progressive Metal'})
    
    add_parent_tag(session, mid.id, root.id)
    add_parent_tag(session, leaf.id, mid.id)
    
    # Test inheritance
    inherited = get_inherited_tags(session, leaf.id)
    assert len(inherited) == 2
    inherited_ids = {tag.id for tag in inherited}
    assert inherited_ids == {'metal', 'prog-metal'}

def test_get_tag_children(session, create_tag):
    # Create tag hierarchy
    root = create_tag({'id': 'metal', 'name': 'Metal'})
    child1 = create_tag({'id': 'prog-metal', 'name': 'Progressive Metal'})
    child2 = create_tag({'id': 'death-metal', 'name': 'Death Metal'})
    
    add_parent_tag(session, child1.id, root.id)
    add_parent_tag(session, child2.id, root.id)
    
    # Test getting children
    children = get_tag_children(session, root.id)
    assert len(children) == 2
    children_ids = {tag.id for tag in children}
    assert children_ids == {'prog-metal', 'death-metal'}