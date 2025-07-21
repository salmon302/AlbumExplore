"""Database models."""
from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

"""Database models."""
from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

# Association tables
album_tags = Table(
    'album_tags',
    Base.metadata,
    Column('album_id', String, ForeignKey('albums.id')),
    Column('tag_id', String, ForeignKey('tags.id'))
)

album_atomic_tags = Table(
    'album_atomic_tags',
    Base.metadata,
    Column('album_id', String, ForeignKey('albums.id')),
    Column('atomic_tag_id', String, ForeignKey('atomic_tags.id')),
    Column('source_tag_id', String, ForeignKey('tags.id'), nullable=True),
    Column('confidence', Float, nullable=False, default=1.0),
    Column('created_at', DateTime, nullable=False, default=datetime.utcnow)
)

tag_hierarchy = Table(
    'tag_hierarchy',
    Base.metadata,
    Column('parent_id', String, ForeignKey('tags.id')),
    Column('child_id', String, ForeignKey('tags.id')),
    extend_existing=True
)

class Album(Base):
    """Album model."""
    __tablename__ = 'albums'
    
    id = Column(String, primary_key=True)
    # artist = Column(String, nullable=False) # Comment out or remove old artist string field
    title = Column(String, nullable=False)
    type = Column(String, nullable=True)  # Added type field for Studio/Live/EP etc.
    cover_image_url = Column(String, nullable=True) # Added cover_image_url field
    pa_album_id = Column(String, nullable=True, index=True) # Added ProgArchives specific album ID
    pa_artist_name_on_album = Column(String, nullable=True) # Added ProgArchives specific artist name from album page
    pa_rating_value = Column(Float, nullable=True)  # ProgArchives rating value
    pa_rating_count = Column(Integer, nullable=True)  # ProgArchives rating count
    pa_review_count = Column(Integer, nullable=True)  # ProgArchives review count
    source_html_file = Column(String, nullable=True) # Source HTML file for the album data
    release_date = Column(DateTime)
    release_year = Column(Integer)
    length = Column(String)
    vocal_style = Column(String)
    country = Column(String)
    genre = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    x = Column(Float)
    y = Column(Float)
    last_updated = Column(DateTime)
    raw_tags = Column(String)
    platforms = Column(String)
    
    # New fields for ProgArchives integration
    artist_id = Column(String, ForeignKey('artists.id')) # New FK to Artist table
    pa_lineup_text = Column(Text) # For storing raw lineup details from ProgArchives

    # Relationships
    artist_obj = relationship("Artist", back_populates="albums") # Renamed to avoid confusion with old 'artist' column
    tags = relationship("Tag", secondary=album_tags, back_populates="albums")
    atomic_tags = relationship("AtomicTag", secondary=album_atomic_tags, back_populates="albums")
    tracks = relationship("Track", order_by="Track.track_number_raw", back_populates="album")
    reviews = relationship("Review", back_populates="album")

    def __repr__(self):
        artist_name = getattr(self, 'pa_artist_name_on_album', 'Unknown Artist')
        return f"<Album {artist_name} - {self.title}>"

class TagCategory(Base):
    __tablename__ = "tag_categories"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    
    # Relationships to tags and atomic tags
    tags = relationship("Tag", back_populates="category")
    atomic_tags = relationship("AtomicTag", back_populates="category")
    
    def __repr__(self):
        return f"<TagCategory {self.name}>"

class Tag(Base):
    __tablename__ = "tags"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    normalized_name = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(String, ForeignKey('tag_categories.id'))
    frequency = Column(Integer, default=0)
    is_canonical = Column(Integer, default=1)
    
    # Atomic tag support columns
    is_atomic = Column(Boolean, default=False)
    is_composite = Column(Boolean, default=False)
    atomic_components = Column(Text, nullable=True)  # JSON list of atomic tag IDs
    decomposition_confidence = Column(Float, nullable=True)
    last_atomic_update = Column(DateTime, nullable=True)
    
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
    decompositions = relationship("TagDecomposition", back_populates="composite_tag")

    def __repr__(self):
        return f"<Tag {self.name}>"

class AtomicTag(Base):
    """Atomic tag model - represents fundamental, indivisible tag concepts."""
    __tablename__ = "atomic_tags"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category_id = Column(String, ForeignKey('tag_categories.id'))
    is_core = Column(Boolean, default=False)  # Core vs derived atomic tag
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("TagCategory", back_populates="atomic_tags")
    decompositions = relationship("TagDecomposition", back_populates="atomic_tag")
    albums = relationship("Album", secondary=album_atomic_tags, back_populates="atomic_tags")
    
    def __repr__(self):
        return f"<AtomicTag {self.name}>"


class TagDecomposition(Base):
    """Tracks decomposition rules and history for composite tags."""
    __tablename__ = "tag_decompositions"
    
    id = Column(Integer, primary_key=True)
    composite_tag_id = Column(String, ForeignKey('tags.id'), nullable=False)
    atomic_tag_id = Column(String, ForeignKey('atomic_tags.id'), nullable=False)
    rule_source = Column(String, nullable=True)  # "manual", "automatic", "inferred"
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    composite_tag = relationship("Tag", back_populates="decompositions")
    atomic_tag = relationship("AtomicTag", back_populates="decompositions")
    
    def __repr__(self):
        return f"<TagDecomposition {self.composite_tag_id} -> {self.atomic_tag_id}>"


class TagVariant(Base):
    __tablename__ = "tag_variants"
    
    id = Column(Integer, primary_key=True)
    variant = Column(String, nullable=False, index=True)
    canonical_tag_id = Column(String, ForeignKey('tags.id'), nullable=False)
    
    # Relationship to canonical tag
    canonical_tag = relationship("Tag", back_populates="variants")
    
    def __repr__(self):
        return f"<TagVariant {self.variant} -> {self.canonical_tag.name}>"

class Artist(Base):
    __tablename__ = "artists"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    # Add other artist-specific fields here, e.g.:
    # country = Column(String)
    # formation_year = Column(Integer)

    # Relationship to albums (if one artist can have multiple albums)
    albums = relationship("Album", back_populates="artist_obj") # Updated to match renamed relationship

    def __repr__(self):
        return f"<Artist {self.name}>"

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

class Track(Base):
    __tablename__ = "tracks"

    id = Column(String, primary_key=True)
    album_id = Column(String, ForeignKey('albums.id'), nullable=False)
    title = Column(String, nullable=False)
    track_number_raw = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_subtrack = Column(Boolean, nullable=True)

    # Relationship to Album
    album = relationship("Album", back_populates="tracks")

    def __repr__(self):
        return f"<Track {self.track_number_raw}. {self.title}>"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)
    album_id = Column(String, ForeignKey('albums.id'), nullable=False)
    reviewer_name = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    review_text = Column(Text, nullable=True)
    review_date = Column(DateTime, nullable=True)
    source_html_file = Column(String, nullable=True)
    pa_review_id = Column(String, nullable=True, index=True)

    # Relationship to Album
    album = relationship("Album", back_populates="reviews")

    def __repr__(self):
        return f"<Review for {self.album_id} by {self.reviewer_name} - {self.rating}>"