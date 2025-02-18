import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.database.models import Base, Tag
from albumexplore.database.crud import (
	create_tag, add_parent_tag, remove_parent_tag,
	get_inherited_tags, get_tag_children
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

def test_add_parent_tag(session):
	# Create test tags
	parent = create_tag(session, {'id': 'metal', 'name': 'Metal'})
	child = create_tag(session, {'id': 'prog-metal', 'name': 'Progressive Metal'})
	
	# Test adding parent relationship
	result = add_parent_tag(session, child.id, parent.id)
	assert result is True
	
	# Verify relationship
	child_tag = session.query(Tag).filter(Tag.id == 'prog-metal').first()
	assert len(child_tag.parent_tags) == 1
	assert child_tag.parent_tags[0].id == 'metal'

def test_remove_parent_tag(session):
	# Create and link tags
	parent = create_tag(session, {'id': 'metal', 'name': 'Metal'})
	child = create_tag(session, {'id': 'prog-metal', 'name': 'Progressive Metal'})
	add_parent_tag(session, child.id, parent.id)
	
	# Test removing relationship
	result = remove_parent_tag(session, child.id, parent.id)
	assert result is True
	
	# Verify relationship removed
	child_tag = session.query(Tag).filter(Tag.id == 'prog-metal').first()
	assert len(child_tag.parent_tags) == 0

def test_get_inherited_tags(session):
	# Create tag hierarchy
	root = create_tag(session, {'id': 'metal', 'name': 'Metal'})
	mid = create_tag(session, {'id': 'prog-metal', 'name': 'Progressive Metal'})
	leaf = create_tag(session, {'id': 'tech-prog-metal', 'name': 'Technical Progressive Metal'})
	
	add_parent_tag(session, mid.id, root.id)
	add_parent_tag(session, leaf.id, mid.id)
	
	# Test inheritance
	inherited = get_inherited_tags(session, leaf.id)
	assert len(inherited) == 2
	inherited_ids = {tag.id for tag in inherited}
	assert inherited_ids == {'metal', 'prog-metal'}

def test_get_tag_children(session):
	# Create tag hierarchy
	root = create_tag(session, {'id': 'metal', 'name': 'Metal'})
	child1 = create_tag(session, {'id': 'prog-metal', 'name': 'Progressive Metal'})
	child2 = create_tag(session, {'id': 'death-metal', 'name': 'Death Metal'})
	
	add_parent_tag(session, child1.id, root.id)
	add_parent_tag(session, child2.id, root.id)
	
	# Test getting children
	children = get_tag_children(session, root.id)
	assert len(children) == 2
	children_ids = {tag.id for tag in children}
	assert children_ids == {'prog-metal', 'death-metal'}