"""Album Explorer application."""
from .database import init_db, get_session
from .tags import TagNormalizer, TagRelationships
from .gui.app import main

def run():
    """Run the application."""
    return main()

if __name__ == "__main__":
    run()