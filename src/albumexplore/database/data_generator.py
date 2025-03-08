"""Generate test data for development and testing."""

from typing import List
from sqlalchemy.orm import Session
import random
from .models import Tag, Album, TagRelation
import uuid
from datetime import datetime, timedelta

class DataGenerator:
    """Generates test data for the application."""
    
    def __init__(self, session: Session):
        self.session = session
        
    def generate_tags(self, count: int) -> List[Tag]:
        """Generate a specified number of test tags."""
        genres = ['metal', 'rock', 'jazz', 'fusion', 'experimental']
        modifiers = ['progressive', 'psychedelic', 'avant-garde', 'post', 'neo']
        
        tags = []
        for _ in range(count):
            tag = Tag(
                id=str(uuid.uuid4()),
                name=f"{random.choice(modifiers)} {random.choice(genres)}",
                is_canonical=1
            )
            self.session.add(tag)
            tags.append(tag)
            
        self.session.commit()
        return tags
        
    def generate_albums(self, count: int, available_tags: List[Tag]) -> List[Album]:
        """Generate test albums with random tags."""
        artists = ['Dream Theater', 'Tool', 'Opeth', 'Porcupine Tree', 'Rush']
        albums = []
        
        start_date = datetime(2000, 1, 1)
        
        for i in range(count):
            album = Album(
                id=str(uuid.uuid4()),
                artist=random.choice(artists),
                title=f"Test Album {i + 1}",
                release_date=start_date + timedelta(days=random.randint(0, 7300)),
                length=f"{random.randint(30, 75)}:{random.randint(0, 59):02d}",
                x=random.uniform(-100, 100),
                y=random.uniform(-100, 100)
            )
            
            # Add random tags
            num_tags = random.randint(2, 5)
            album.tags = random.sample(available_tags, num_tags)
            
            self.session.add(album)
            albums.append(album)
            
        self.session.commit()
        return albums
        
    def generate_tag_relationships(self, tags: List[Tag]) -> List[TagRelation]:
        """Generate relationships between tags."""
        relationships = []
        
        # Create relationships between random pairs of tags
        num_relationships = len(tags) * 2
        for _ in range(num_relationships):
            tag1, tag2 = random.sample(tags, 2)
            
            rel = TagRelation(
                tag1_id=tag1.id,
                tag2_id=tag2.id,
                relationship_type='related',
                strength=random.uniform(0.1, 1.0)
            )
            
            self.session.add(rel)
            relationships.append(rel)
            
        self.session.commit()
        return relationships