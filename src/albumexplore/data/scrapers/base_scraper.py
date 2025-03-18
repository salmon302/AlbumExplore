"""Base scraper module with rate limiting and caching."""
import logging
import time
from pathlib import Path
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BaseScraper:
    """Base scraper with rate limiting and caching."""
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        min_request_interval: float = 5.0,
        max_daily_requests: int = 1000,
        max_retries: int = 3
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.min_request_interval = min_request_interval
        self.max_daily_requests = max_daily_requests
        self.max_retries = max_retries
        
        self._last_request_time = 0
        self._daily_requests = 0
        self._daily_reset = datetime.now()
        
    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting."""
        # Reset daily counter if needed
        now = datetime.now()
        if now - self._daily_reset > timedelta(days=1):
            self._daily_requests = 0
            self._daily_reset = now
            
        # Check daily limit
        if self._daily_requests >= self.max_daily_requests:
            raise Exception("Daily request limit reached")
            
        # Wait for minimum interval
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL."""
        from hashlib import md5
        url_hash = md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"
    
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
        
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                self._last_request_time = time.time()
                self._daily_requests += 1
                
                data = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'content': response.text,
                    'headers': dict(response.headers)
                }
                
                if use_cache:
                    self._save_cache(url, data)
                    
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")