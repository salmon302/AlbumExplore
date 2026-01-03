"""Last.fm API integration module."""
import os
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    
    # Look for .env in project root
    env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars

from .client import LastFmClient
from .fetcher import LastFmFetcher

__all__ = ['LastFmClient', 'LastFmFetcher']
