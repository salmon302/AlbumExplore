"""ProgArchives.com scraper using Puppeteer to bypass bot detection."""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.page import Page
import re
import backoff  # Will add this to requirements.txt

logger = logging.getLogger(__name__)

class ProgArchivesPuppeteerScraper:
    """Scraper for ProgArchives.com using Puppeteer with stealth mode."""
    
    BASE_URL = "https://www.progarchives.com"
    SEARCH_URL = "https://www.progarchives.com/bands-alpha.asp"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        headless: bool = True,
        min_request_interval: float = 5.0
    ):
        """Initialize scraper with Puppeteer configuration."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/progarchives")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.min_request_interval = min_request_interval
        self._last_request_time = 0
        self._browser = None
        
    async def init(self):
        """Initialize browser instance."""
        if not self._browser:
            self._browser = await launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920x1080',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                ]
            )

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None

    def _get_cached_response(self, key: str) -> Optional[Dict]:
        """Get cached response for key."""
        cache_file = self.cache_dir / f"{hash(key)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {key}: {e}")
        return None

    def _save_to_cache(self, key: str, data: Dict):
        """Save response to cache."""
        cache_file = self.cache_dir / f"{hash(key)}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache response for {key}: {e}")

    @backoff.on_exception(
        backoff.expo,
        (asyncio.TimeoutError, Exception),
        max_tries=3,
        max_time=300
    )
    async def _search_progarchives(self, query: str) -> Optional[str]:
        """Search ProgArchives.com directly using their search functionality."""
        try:
            page = await self._browser.newPage()
            await page.setDefaultNavigationTimeout(60000)  # 60 seconds
            
            # Go to the bands page first
            await page.goto(self.SEARCH_URL, {'waitUntil': 'networkidle0'})
            
            # Look for search box
            search_input = await page.querySelector('input[type="text"], input[name="searchkey"]')
            if not search_input:
                raise ValueError("Could not find search input")
                
            # Type search query and submit
            await search_input.type(query)
            await search_input.press('Enter')
            await page.waitForNavigation({'waitUntil': 'networkidle0'})
            
            # Check if we found a result
            results = await page.querySelectorAll('a[href*="album.asp"], a[href*="artist.asp"]')
            if not results:
                return None
                
            # Get the URL of the first result
            url = await page.evaluate('el => el.href', results[0])
            return url
            
        except Exception as e:
            logger.error(f"Error searching ProgArchives: {e}")
            raise
            
        finally:
            if page:
                await page.close()

    async def get_album_details(self, search_query: str, use_cache: bool = True) -> Dict:
        """
        Get album details by searching for it and scraping the first result.
        
        Args:
            search_query: Album name or "Artist - Album" to search for
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary with album details
        """
        cache_key = f"album_details:{search_query}"
        if use_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                return cached

        try:
            # Search for the album
            url = await self._search_progarchives(search_query)
            if not url:
                raise ValueError(f"Could not find album: {search_query}")
            
            # Visit album page and extract details
            page = await self._browser.newPage()
            await page.setDefaultNavigationTimeout(60000)  # 60 seconds
            await page.goto(url, {'waitUntil': 'networkidle0'})
            details = await self._extract_album_details(page)
            
            if use_cache and details and 'error' not in details:
                self._save_to_cache(cache_key, details)
                
            return details

        except Exception as e:
            error = f"Error getting album details for '{search_query}': {str(e)}"
            logger.error(error)
            return {'error': error}
            
        finally:
            if page:
                await page.close()

    async def _extract_album_details(self, page: Page) -> Dict:
        """Extract album details from the loaded page."""
        try:
            # Basic validation that we're on an album page
            if not await page.querySelector('h1.album-title, h1.albumname, h1.album_name'):
                raise ValueError("Not a valid album page")

            # Extract various elements
            title = await self._get_text(page, 'h1.album-title, h1.albumname, h1.album_name')
            artist = await self._get_text(page, 'h2 a[href*="artist.asp"]')
            
            # Get year from title or release info
            year = None
            year_text = await self._get_text(page, 'td:contains("Released:") + td')
            if year_text:
                year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                if year_match:
                    year = int(year_match.group())
            
            # Get rating information
            rating = None
            rating_elem = await page.querySelector('#avgRatings_1')
            if rating_elem:
                rating_text = await page.evaluate('el => el.textContent', rating_elem)
                try:
                    rating = float(rating_text)
                except (ValueError, TypeError):
                    pass

            # Get rating distribution
            distribution = []
            dist_elem = await page.querySelector('#ratingDistribution')
            if dist_elem:
                dist_text = await page.evaluate('el => el.textContent', dist_elem)
                dist_matches = re.findall(r'\((\d+%)\)', dist_text)
                distribution = dist_matches if dist_matches else []

            # Get track listing
            tracks = []
            track_section = await page.querySelector('h3:contains("Tracks"), strong:contains("Tracks")')
            if track_section:
                track_content = await page.evaluate('el => el.nextElementSibling.textContent', track_section)
                if track_content:
                    for line in track_content.split('\n'):
                        line = line.strip()
                        if not line or 'total time' in line.lower():
                            continue
                        
                        track_match = re.match(r'^(?:(\d+)[\.)\s-]+)?(.+?)(?:\s*[-(\s]+(\d+:\d+))?$', line)
                        if track_match:
                            number = int(track_match.group(1)) if track_match.group(1) else len(tracks) + 1
                            title = track_match.group(2).strip()
                            duration = track_match.group(3)
                            
                            if title and not title.startswith(('CD', '*', '-')):
                                tracks.append({
                                    'number': number,
                                    'title': title,
                                    'duration': duration.strip() if duration else None
                                })

            # Get lineup information
            lineup = []
            lineup_section = await page.querySelector('h3:contains("Line-up"), strong:contains("Line-up")')
            if lineup_section:
                lineup_content = await page.evaluate('el => el.nextElementSibling.textContent', lineup_section)
                if lineup_content:
                    for line in lineup_content.split('\n'):
                        line = line.strip()
                        if not line or line.startswith(('-', '*', '•')):
                            continue
                            
                        # Try various formats for parsing musician entries
                        for pattern in [
                            r'^(.+?)\s*[-:]\s*(.+)$',  # Name - Role or Role: Name
                            r'^(.+?)\s*\((.+?)\)$',    # Name (Role)
                            r'^([^/]+)/\s*(.+)$'       # Name / Role
                        ]:
                            match = re.match(pattern, line)
                            if match:
                                part1, part2 = match.groups()
                                # Determine which part is name/role based on common role keywords
                                role_keywords = {
                                    'vocals', 'guitar', 'bass', 'drums', 'keyboards', 'piano',
                                    'percussion', 'flute', 'violin', 'cello', 'saxophone'
                                }
                                
                                part1_has_role = any(kw in part1.lower() for kw in role_keywords)
                                part2_has_role = any(kw in part2.lower() for kw in role_keywords)
                                
                                if part1_has_role:
                                    role, name = part1, part2
                                elif part2_has_role:
                                    name, role = part1, part2
                                else:
                                    continue
                                    
                                lineup.append({
                                    'name': name.strip(),
                                    'role': role.strip()
                                })
                                break

            # Get genre and record type
            genre = await self._get_text(page, 'td:contains("Genre:") + td')
            record_type = await self._get_text(page, 'td:contains("Type:") + td')

            details = {
                'url': page.url,
                'title': title,
                'artist': artist,
                'year': year,
                'rating': rating,
                'rating_distribution': distribution,
                'genre': genre,
                'record_type': record_type,
                'tracks': tracks,
                'lineup': lineup,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            if not details['title'] or not details['artist']:
                raise ValueError("Missing required fields (title/artist)")
                
            return details

        except Exception as e:
            error = f"Error extracting album details: {str(e)}"
            logger.error(error)
            return {'error': error}

    async def _get_text(self, page: Page, selector: str) -> Optional[str]:
        """Get text content from an element."""
        try:
            element = await page.querySelector(selector)
            if element:
                text = await page.evaluate('el => el.textContent', element)
                return text.strip()
        except Exception:
            pass
        return None

    async def get_band_details(self, search_query: str, use_cache: bool = True) -> Dict:
        """
        Get band details by searching for it and scraping the first result.
        
        Args:
            search_query: Band name to search for
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary with band details
        """
        cache_key = f"band_details:{search_query}"
        if use_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                return cached

        try:
            # Search for the band
            url = await self._search_progarchives(search_query)
            if not url:
                raise ValueError(f"Could not find band: {search_query}")
            
            # Visit band page and extract details
            page = await self._browser.newPage()
            await page.setDefaultNavigationTimeout(60000)  # 60 seconds
            await page.goto(url, {'waitUntil': 'networkidle0'})
            details = await self._extract_band_details(page)
            
            if use_cache and details and 'error' not in details:
                self._save_to_cache(cache_key, details)
                
            return details

        except Exception as e:
            error = f"Error getting band details for '{search_query}': {str(e)}"
            logger.error(error)
            return {'error': error}
            
        finally:
            if page:
                await page.close()

    async def _extract_band_details(self, page: Page) -> Dict:
        """Extract band details from the loaded page."""
        try:
            # Basic validation that we're on a band page
            if not await page.querySelector('h1.band-title, h1.artistname, h1.band_name'):
                raise ValueError("Not a valid band page")

            # Extract various elements
            name = await self._get_text(page, 'h1.band-title, h1.artistname, h1.band_name')
            
            # Get genre and country
            genre = await self._get_text(page, 'td:contains("Genre:") + td')
            country = await self._get_text(page, 'td:contains("Country:") + td')
            
            # Get biography
            bio = await self._get_text(page, '#artist-biography')
            
            # Get discography
            albums = []
            album_rows = await page.querySelectorAll('td.artist-discography-td')
            for row in album_rows:
                try:
                    title_link = await row.querySelector('a[href*="album.asp"]')
                    if title_link:
                        title = await page.evaluate('el => el.textContent', title_link)
                        url = await page.evaluate('el => el.href', title_link)
                        
                        # Try to get year and rating
                        row_text = await page.evaluate('el => el.textContent', row)
                        year_match = re.search(r'\b(19|20)\d{2}\b', row_text)
                        year = int(year_match.group()) if year_match else None
                        
                        rating_match = re.search(r'(\d+\.\d+)/5', row_text)
                        rating = float(rating_match.group(1)) if rating_match else None
                        
                        albums.append({
                            'title': title.strip(),
                            'url': url,
                            'year': year,
                            'rating': rating
                        })
                except Exception as e:
                    logger.warning(f"Error parsing album row: {e}")
                    continue

            details = {
                'url': page.url,
                'name': name,
                'genre': genre,
                'country': country,
                'biography': bio,
                'albums': albums,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            if not details['name']:
                raise ValueError("Missing required field (name)")
                
            return details

        except Exception as e:
            error = f"Error extracting band details: {str(e)}"
            logger.error(error)
            return {'error': error}