"""Album exploration and analysis system.

This module intentionally avoids importing heavy subsystems (database, GUI)
at import time. Use the thin wrapper functions `init_db`, `get_session`, and
`run` to access those subsystems; they import the real implementations lazily
when called. This prevents side-effects during tooling, demos, and tests.
"""
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


def init_db(*args, **kwargs):
    """Lazily initialize the database.

    Delegates to `albumexplore.database.init_db` to avoid import-time DB
    initialization.
    """
    from .database import init_db as _init_db

    return _init_db(*args, **kwargs)


def get_session(*args, **kwargs):
    """Lazily get a DB session.

    Delegates to `albumexplore.database.get_session`.
    """
    from .database import get_session as _get_session

    return _get_session(*args, **kwargs)


def get_tag_normalizer_class():
    """Return the `TagNormalizer` class (imported lazily)."""
    from .tags import TagNormalizer

    return TagNormalizer


def get_tag_relationships_class():
    """Return the `TagRelationships` class (imported lazily)."""
    from .tags import TagRelationships

    return TagRelationships


def run():
    """Run the application by importing the GUI `main` lazily."""
    from .gui.app import main

    return main()


if __name__ == "__main__":
    run()