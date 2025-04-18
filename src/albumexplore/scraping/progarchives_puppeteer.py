"""Puppeteer-based scraper for ProgArchives.com with stealth mode."""
import logging
from pathlib import Path
from typing import Dict, Optional
import asyncio
import json
from pyppeteer import launch
from pyppeteer_stealth import stealth

logger = logging.getLogger(__name__)

class ProgArchivesPuppeteerScraper:
    """Scraper for ProgArchives.com using Puppeteer with stealth mode."""
    
    BASE_URL = "https://www.progarchives.com"
    DUCKDUCKGO_URL = "https://duckduckgo.com"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        min_request_interval: float = 10.0,
        headless: bool = True
    ):
        """Initialize scraper with caching and rate limiting."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/progarchives_puppeteer")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.min_request_interval = min_request_interval
        self._last_request_time = 0
        self.headless = headless
        self._browser = None
        self._page = None

    async def init(self):
        """Initialize browser and page."""
        if not self._browser:
            self._browser = await launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self._page = await self._browser.newPage()
            await stealth(self._page)

    async def close(self):
        """Close browser and page."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None

    def _get_cache_path(self, url_or_query: str) -> Path:
        """Get cache file path for URL or search query."""
        safe_name = "".join(c if c.isalnum() else "_" for c in url_or_query)
        return self.cache_dir / f"{safe_name}.json"

    def _get_cached_response(self, url_or_query: str) -> Optional[Dict]:
        """Get cached response for URL or search query."""
        cache_file = self._get_cache_path(url_or_query)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {url_or_query}: {e}")
        return None

    def _save_to_cache(self, url_or_query: str, data: Dict):
        """Save response to cache."""
        cache_file = self._get_cache_path(url_or_query)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache response for {url_or_query}: {e}")

    async def get_album_info(self, album_name: str, use_cache: bool = True) -> Dict:
        """Get information about an album using DuckDuckGo search."""
        if use_cache:
            cached = self._get_cached_response(album_name)
            if cached:
                return cached

        await self.init()
        
        try:
            # Navigate to DuckDuckGo
            await self._page.goto(self.DUCKDUCKGO_URL)
            
            # Type search query and submit
            search_query = f"{album_name} site:progarchives.com"
            await self._page.type('input[name="q"]', search_query)
            await self._page.keyboard.press('Enter')
            await self._page.waitForSelector('.results')
            
            # Get first result that links to progarchives.com
            results = await self._page.querySelectorAll('.result__a')
            prog_archives_link = None
            
            for result in results:
                href = await self._page.evaluate('el => el.href', result)
                if 'progarchives.com' in href:
                    prog_archives_link = href
                    break
            
            if not prog_archives_link:
                return {'error': 'No ProgArchives.com result found'}
            
            # Navigate to album page
            await self._page.goto(prog_archives_link)
            await self._page.waitForSelector('.album_description')
            
            # Extract album info
            album_info = await self._page.evaluate('''() => {
                const info = {};
                
                // Get album name and artist
                const titleEl = document.querySelector('h1.album-title');
                if (titleEl) {
                    info.albumName = titleEl.textContent.trim();
                }
                
                const artistEl = document.querySelector('.artist-name');
                if (artistEl) {
                    info.artistName = artistEl.textContent.trim();
                }
                
                // Get rating info
                const ratingEl = document.querySelector('.rating');
                if (ratingEl) {
                    info.avgRating = ratingEl.textContent.trim();
                }
                
                const ratingsCountEl = document.querySelector('.ratings-count');
                if (ratingsCountEl) {
                    info.ratings = parseInt(ratingsCountEl.textContent.trim());
                }
                
                // Get rating distribution
                const distributionEls = document.querySelectorAll('.rating-distribution .percentage');
                info.distribution = Array.from(distributionEls).map(el => el.textContent.trim());
                
                return info;
            }''')
            
            if use_cache:
                self._save_to_cache(album_name, album_info)
            
            return album_info
            
        except Exception as e:
            logger.error(f"Error getting album info for {album_name}: {e}")
            return {'error': str(e)}