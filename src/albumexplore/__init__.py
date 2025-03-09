"""Album exploration and analysis system."""
from pathlib import Path
import sys
import logging

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to Python path if not already there
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__version__ = '0.1.0'

from .database import init_db, get_session
from .tags import TagNormalizer, TagRelationships
from .gui.app import main

def run():
    """Run the application."""
    return main()

if __name__ == "__main__":
    run()