"""Database models."""
from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Float, DateTime
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

# Association tables
album_tags = Table(
    'album_tags',
    Base.metadata,
    Column('album_id', Integer, ForeignKey('albums.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Album(Base):
    """Album model."""
    __tablename__ = 'albums'
    
    id = Column(String, primary_key=True)
    artist = Column(String, nullable=False)
    title = Column(String, nullable=False)
    release_date = Column(DateTime)
    release_year = Column(Integer)
    length = Column(String)
    vocal_style = Column(String)
    country = Column(String)
    genre = Column(String)
    x = Column(Float)
    y = Column(Float)
    last_updated = Column(DateTime)
    raw_tags = Column(String)
    platforms = Column(String)
    
    # Relationships
    tags = relationship("Tag", secondary=album_tags, back_populates="albums")

    def __repr__(self):
        return f"<Album {self.artist} - {self.title}>"

# Association table for tag hierarchy
tag_hierarchy = Table(
    'tag_hierarchy',
    Base.metadata,
    Column('parent_id', String, ForeignKey('tags.id')),
    Column('child_id', String, ForeignKey('tags.id'))
)

class TagCategory(Base):
    __tablename__ = "tag_categories"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    
    # Relationship to tags
    tags = relationship("Tag", back_populates="category")
    
    def __repr__(self):
        return f"<TagCategory {self.name}>"

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    normalized_name = Column(String, nullable=True, index=True)
    category_id = Column(String, ForeignKey('tag_categories.id'))
    frequency = Column(Integer, default=0)
    is_canonical = Column(Integer, default=1)
    
    # Relationships
    category = relationship("TagCategory", back_populates="tags")
    parent_tags = relationship(
        "Tag",
        secondary=tag_hierarchy,
        primaryjoin=(tag_hierarchy.c.child_id == id),
        secondaryjoin=(tag_hierarchy.c.parent_id == id),
        backref="child_tags"
    )
    albums = relationship("Album", secondary=album_tags, back_populates="tags")
    variants = relationship("TagVariant", back_populates="canonical_tag")

    def __repr__(self):
        return f"<Tag {self.name}>"

class TagVariant(Base):
    __tablename__ = "tag_variants"
    
    id = Column(Integer, primary_key=True)
    variant = Column(String, nullable=False, index=True)
    canonical_tag_id = Column(String, ForeignKey('tags.id'), nullable=False)
    
    # Relationship to canonical tag
    canonical_tag = relationship("Tag", back_populates="variants")
    
    def __repr__(self):
        return f"<TagVariant {self.variant} -> {self.canonical_tag.name}>"

class TagRelation(Base):
    __tablename__ = "tag_relationships"

    id = Column(Integer, primary_key=True)
    tag1_id = Column(String, ForeignKey('tags.id'))
    tag2_id = Column(String, ForeignKey('tags.id'))
    relationship_type = Column(String, nullable=False)
    strength = Column(Float)

    def __repr__(self):
        return f"<TagRelation {self.tag1_id} -> {self.tag2_id}>"

class UpdateHistory(Base):
    __tablename__ = "update_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    entity_type = Column(String, nullable=False)  # 'album' or 'tag'
    entity_id = Column(String, nullable=False)
    change_type = Column(String, nullable=False)  # 'create', 'update', 'delete'
    changes = Column(String)  # JSON string of changes