"""Base scraper module with rate limiting and caching."""
import logging
import time
from pathlib import Path
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for web scrapers with caching and rate limiting."""
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        min_request_interval: float = 5.0,
    ):
        """Initialize scraper with caching and rate limiting.
        
        Args:
            cache_dir: Directory to store cached responses
            min_request_interval: Minimum time in seconds between requests
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.min_request_interval = min_request_interval
        self._last_request_time = 0
        
    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL."""
        safe_name = "".join(c if c.isalnum() else "_" for c in url)
        return self.cache_dir / f"{safe_name}.json"
    
    def _load_cache(self, url: str) -> Optional[Dict]:
        """Load cached response for URL."""
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                logger.debug(f"Cache hit for {url}")
                return cached
            except Exception as e:
                logger.warning(f"Failed to load cache for {url}: {e}")
        return None
    
    def _save_cache(self, url: str, data: Dict[str, Any]) -> None:
        """Save response to cache."""
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Cached response for {url}")
        except Exception as e:
            logger.warning(f"Failed to cache response for {url}: {e}")
    
    def fetch_url(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Fetch URL with caching and rate limiting."""
        if use_cache:
            cached = self._load_cache(url)
            if cached:
                return cached
                
        self._wait_for_rate_limit()
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        self._last_request_time = time.time()
        
        data = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'content': response.text,
            'headers': dict(response.headers)
        }
        
        if use_cache:
            self._save_cache(url, data)
            
        return data