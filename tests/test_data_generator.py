import random
from typing import List, Tuple, Dict
from albumexplore.visualization.models import VisualNode, VisualEdge
import pytest
from albumexplore.database.data_generator import DataGenerator
from albumexplore.database.models import Tag, Album, TagRelation

@pytest.fixture
def data_generator(session):
    """Create a DataGenerator instance for testing."""
    return DataGenerator(session)

def create_test_dataset(generator: DataGenerator) -> Tuple[List[Tag], List[Album], List[TagRelation]]:
    """Create a complete test dataset with tags, albums, and relationships."""
    # Generate tags first
    tags = generator.generate_tags(20)
    
    # Generate albums using those tags
    albums = generator.generate_albums(10, tags)
    
    # Generate relationships between tags
    relationships = generator.generate_tag_relationships(tags)
    
    return tags, albums, relationships

class TestDataGenerator:
    """Test data generation functionality."""
    
    def test_generate_tags(self, data_generator):
        """Test tag generation."""
        tags = data_generator.generate_tags(10)
        assert len(tags) == 10
        assert all(tag.name for tag in tags)
        
    def test_generate_albums(self, data_generator):
        """Test album generation."""
        # First generate some tags to use
        tags = data_generator.generate_tags(5)
        
        # Generate albums using those tags
        albums = data_generator.generate_albums(3, tags)
        assert len(albums) == 3
        assert all(album.title for album in albums)
        assert all(len(album.tags) > 0 for album in albums)
        
    def test_generate_relationships(self, data_generator):
        """Test relationship generation between tags."""
        tags = data_generator.generate_tags(5)
        relationships = data_generator.generate_tag_relationships(tags)
        
        assert len(relationships) > 0
        assert all(rel.tag1_id and rel.tag2_id for rel in relationships)
        assert all(0 <= rel.strength <= 1.0 for rel in relationships)
        
    def test_create_test_dataset(self, data_generator):
        """Test creating a complete test dataset."""
        tags, albums, relationships = create_test_dataset(data_generator)
        
        assert len(tags) == 20
        assert len(albums) == 10
        assert len(relationships) > 0
        
        # Verify relationships between entities
        assert all(album.tags for album in albums)
        assert all(tag.albums for tag in tags)
