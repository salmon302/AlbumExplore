"""Database initialization and test data loading."""

from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models

logger = logging.getLogger(__name__)

def load_test_data(db: Session):
    """Load test data into the database."""
    try:
        # Create some test tags first
        metal_tag = models.Tag(id="metal", name="metal", category="genre")
        prog_tag = models.Tag(id="prog", name="progressive", category="style")
        rock_tag = models.Tag(id="rock", name="rock", category="genre")
        db.add_all([metal_tag, prog_tag, rock_tag])
        db.flush()  # Ensure tags are created before referencing
        
        # Create some test albums
        albums = [
            models.Album(
                id="album1",
                artist="Dream Theater",
                title="Images and Words",
                release_year=1992,
                length="LP",
                vocal_style="clean",
                country="USA",
                tags=[metal_tag, prog_tag]
            ),
            models.Album(
                id="album2",
                artist="Tool",
                title="Lateralus",
                release_year=2001,
                length="LP",
                vocal_style="mixed",
                country="USA",
                tags=[metal_tag, prog_tag]
            ),
            models.Album(
                id="album3",
                artist="Pink Floyd",
                title="Dark Side of the Moon",
                release_year=1973,
                length="LP",
                vocal_style="clean",
                country="UK",
                tags=[prog_tag, rock_tag]
            ),
            models.Album(
                id="album4",
                artist="Opeth",
                title="Blackwater Park",
                release_year=2001,
                length="LP",
                vocal_style="mixed",
                country="Sweden",
                tags=[metal_tag, prog_tag]
            ),
            models.Album(
                id="album5",
                artist="Rush",
                title="Moving Pictures",
                release_year=1981,
                length="LP",
                vocal_style="clean",
                country="Canada",
                tags=[prog_tag, rock_tag]
            )
        ]
        
        db.add_all(albums)
        db.commit()
        logger.info(f"Successfully loaded {len(albums)} test albums")
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error loading test data: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error loading test data: {str(e)}")
        raise