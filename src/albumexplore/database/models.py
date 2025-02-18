from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from . import Base

# Association table for album-tag relationships
album_tags = Table(
	'album_tags',
	Base.metadata,
	Column('album_id', String, ForeignKey('albums.id')),
	Column('tag_id', String, ForeignKey('tags.id'))
)

# Association table for tag hierarchy
tag_hierarchy = Table(
	'tag_hierarchy',
	Base.metadata,
	Column('parent_id', String, ForeignKey('tags.id')),
	Column('child_id', String, ForeignKey('tags.id'))
)

class Album(Base):
	__tablename__ = "albums"

	id = Column(String, primary_key=True)
	artist = Column(String, nullable=False)
	title = Column(String, nullable=False)
	release_date = Column(DateTime)
	release_year = Column(Integer)
	length = Column(String)
	vocal_style = Column(String)
	country = Column(String)
	genre = Column(String)
	x = Column(Float, nullable=True)  # Spatial coordinate for chunking
	y = Column(Float, nullable=True)  # Spatial coordinate for chunking
	last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
	tags = relationship("Tag", secondary=album_tags, back_populates="albums")
	raw_tags = Column(String)  # Stored as JSON string
	platforms = Column(String)  # Stored as JSON string

class Tag(Base):
	__tablename__ = "tags"

	id = Column(String, primary_key=True)
	name = Column(String, nullable=False, unique=True)
	category = Column(String)
	aliases = Column(String)  # Stored as JSON string
	frequency = Column(Integer, default=0)
	
	# Add parent-child relationships
	parent_tags = relationship(
		"Tag",
		secondary=tag_hierarchy,
		primaryjoin=(tag_hierarchy.c.child_id == id),
		secondaryjoin=(tag_hierarchy.c.parent_id == id),
		backref="child_tags"
	)
	albums = relationship("Album", secondary=album_tags, back_populates="tags")

class TagRelation(Base):
	__tablename__ = "tag_relationships"

	id = Column(Integer, primary_key=True)
	tag1_id = Column(String, ForeignKey('tags.id'))
	tag2_id = Column(String, ForeignKey('tags.id'))
	relationship_type = Column(String, nullable=False)
	strength = Column(Float)

class UpdateHistory(Base):
	__tablename__ = "update_history"

	id = Column(Integer, primary_key=True)
	timestamp = Column(DateTime, default=datetime.utcnow)
	entity_type = Column(String, nullable=False)  # 'album' or 'tag'
	entity_id = Column(String, nullable=False)
	change_type = Column(String, nullable=False)  # 'create', 'update', 'delete'
	changes = Column(String)  # JSON string of changes