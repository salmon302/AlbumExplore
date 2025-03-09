"""Test utilities and helper functions."""
import os
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_test_data(tags_list: List[List[str]], n_albums: int = 5) -> pd.DataFrame:
    """Create a test DataFrame with specified tags."""
    if len(tags_list) < n_albums:
        # Repeat tags list if needed
        tags_list = (tags_list * ((n_albums // len(tags_list)) + 1))[:n_albums]
        
    data = {
        'id': range(1, n_albums + 1),
        'artist': [f'Artist_{i}' for i in range(1, n_albums + 1)],
        'title': [f'Album_{i}' for i in range(1, n_albums + 1)],
        'year': [2020 + (i % 5) for i in range(n_albums)],
        'tags': tags_list
    }
    
    logger.debug(f"Created test data with {n_albums} albums and tags: {tags_list}")
    return pd.DataFrame(data)

def load_test_config(name: str) -> Dict[str, Any]:
    """Load a test configuration file."""
    test_dir = Path(__file__).parent
    config_path = test_dir / 'test_data' / f'{name}.json'
    
    if not config_path.exists():
        logger.warning(f"Test config file not found: {config_path}")
        return {}
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.debug(f"Loaded test config from {config_path}")
            logger.debug(f"Config contents: {json.dumps(config, indent=2)}")
            return config
    except Exception as e:
        logger.error(f"Error loading test config: {e}")
        return {}
        
def setup_test_config():
    """Set up test configuration directory and files."""
    test_dir = Path(__file__).parent
    test_data_dir = test_dir / 'test_data'
    test_data_dir.mkdir(exist_ok=True)
    logger.debug(f"Created test data directory: {test_data_dir}")
    
    # Create basic test config if it doesn't exist
    config_path = test_data_dir / 'tag_rules_test.json'
    if not config_path.exists():
        test_config = {
            'categories': {
                'metal': {
                    'core_terms': ['metal', 'metalcore'],
                    'primary_genres': ['prog-metal', 'technical metal'],
                    'modifiers': ['progressive', 'technical', 'experimental']
                },
                'experimental': {
                    'core_terms': ['experimental', 'avant-garde'],
                    'primary_genres': ['experimental metal', 'avant-garde'],
                    'modifiers': ['progressive', 'atmospheric', 'technical']
                }
            },
            'prefix_patterns': {
                'prog-': ['prog', 'progressive'],
                'tech-': ['tech', 'technical']
            },
            'suffix_patterns': {
                'metal': ['metal'],
                'core': ['core']
            },
            'compound_terms': {
                'prog-metal': ['progressive metal', 'prog metal'],
                'tech-metal': ['technical metal', 'tech metal']
            },
            'common_misspellings': {
                'progressive': ['progresive', 'progessive'],
                'technical': ['tecnical', 'techincal']
            },
            'single_instance_mappings': {
                'unique variant': 'experimental',
                'single instance tag': 'prog-metal'
            }
        }
        
        try:
            with open(config_path, 'w') as f:
                json.dump(test_config, f, indent=2)
            logger.debug(f"Created test config file: {config_path}")
            logger.debug(f"Test config contents: {json.dumps(test_config, indent=2)}")
        except Exception as e:
            logger.error(f"Error creating test config: {e}")
            raise

def get_test_file_path(filename: str) -> Path:
    """Get the absolute path to a test file."""
    return Path(__file__).parent / 'test_data' / filename

def setup_test_config() -> None:
    """Set up test configuration."""
    # Create test config directory if it doesn't exist
    test_config_dir = Path(__file__).parent / 'test_config'
    test_config_dir.mkdir(exist_ok=True)
    
    # Create test config file
    config = {
        'database': {
            'url': 'sqlite:///:memory:'
        },
        'logging': {
            'level': 'DEBUG',
            'directory': str(test_config_dir / 'logs')
        },
        'graphics': {
            'debug': True,
            'buffer_strategy': 'double'
        }
    }
    
    config_path = test_config_dir / 'test_config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Set environment variable for test config
    os.environ['ALBUMEXPLORE_CONFIG'] = str(config_path)

def get_test_data_path() -> Path:
    """Get path to test data directory."""
    return Path(__file__).parent / 'test_data'

def create_test_db() -> None:
    """Create test database with sample data."""
    from albumexplore.database import init_db, get_session
    from albumexplore.database.models import Album, Tag
    
    # Initialize test database
    init_db('sqlite:///:memory:')
    session = get_session()
    
    # Add sample data
    albums = [
        Album(artist="Artist 1", title="Album 1", release_year=2020),
        Album(artist="Artist 2", title="Album 2", release_year=2021),
        Album(artist="Artist 3", title="Album 3", release_year=2022)
    ]
    
    tags = [
        Tag(name="Progressive Metal"),
        Tag(name="Progressive Rock"),
        Tag(name="Technical Death Metal")
    ]
    
    # Add relationships
    albums[0].tags.append(tags[0])
    albums[1].tags.append(tags[1])
    albums[2].tags.append(tags[2])
    
    session.add_all(albums)
    session.add_all(tags)
    session.commit()
    
def clear_test_data() -> None:
    """Clean up test data."""
    from albumexplore.database import get_session
    from albumexplore.database.models import Album, Tag
    
    session = get_session()
    session.query(Album).delete()
    session.query(Tag).delete()
    session.commit()