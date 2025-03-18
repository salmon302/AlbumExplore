"""Test data generator for the database."""
import uuid
from typing import List, Tuple
from sqlalchemy.orm import Session
from .models import Tag, Album, TagRelation

class DataGenerator:
    """Generates test data for the database."""
    
    def __init__(self, session: Session):
        self.session = session
        self._used_tag_names = set()
        
    def _generate_unique_tag_name(self, base_name: str) -> str:
        """Generate a unique tag name by adding a suffix if needed."""
        if base_name not in self._used_tag_names:
            self._used_tag_names.add(base_name)
            return base_name
            
        counter = 1
        while f"{base_name} {counter}" in self._used_tag_names:
            counter += 1
        new_name = f"{base_name} {counter}"
        self._used_tag_names.add(new_name)
        return new_name

    def generate_tags(self, count: int) -> List[Tag]:
        """Generate a specified number of test tags."""
        tag_bases = ['progressive rock', 'progressive metal', 'post rock', 'avant-garde',
                    'experimental', 'psychedelic', 'jazz fusion', 'technical']
        modifiers = ['', 'fusion', 'metal', 'rock', 'jazz', 'experimental']
        
        tags = []
        for _ in range(count):
            base = tag_bases[len(tags) % len(tag_bases)]
            modifier = modifiers[len(tags) % len(modifiers)]
            name = f"{base} {modifier}".strip()
            name = self._generate_unique_tag_name(name)
            
            tag = Tag(
                id=str(uuid.uuid4()),
                name=name,
                normalized_name=None,
                category_id=None,
                frequency=0,
                is_canonical=1
            )
            self.session.add(tag)
            tags.append(tag)
            
        self.session.commit()
        return tags

    def generate_albums(self, count: int, tags: List[Tag]) -> List[Album]:
        """Generate a specified number of test albums."""
        albums = []
        for i in range(count):
            album = Album(
                id=str(uuid.uuid4()),
                artist=f"Artist {i+1}",
                title=f"Album {i+1}",
                release_date=None,
                release_year=2023,
                length="40:00",
                vocal_style="Mixed",
                country="Various",
                genre="Progressive"
            )
            # Add 2-3 random tags to each album
            album_tags = tags[i:i+3] if i < len(tags) else tags[:3]
            album.tags.extend(album_tags)
            
            self.session.add(album)
            albums.append(album)
            
        self.session.commit()
        return albums
        
    def generate_relationships(self, tags: List[Tag]) -> List[TagRelation]:
        """Generate test relationships between tags."""
        relationships = []
        for i in range(len(tags) - 1):
            relation = TagRelation(
                tag1_id=tags[i].id,
                tag2_id=tags[i + 1].id,
                relationship_type='related',
                strength=0.5
            )
            self.session.add(relation)
            relationships.append(relation)
            
        self.session.commit()
        return relationships