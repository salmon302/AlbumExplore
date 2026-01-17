import logging
import time
import re
import csv
from typing import List, Dict, Optional, Generator
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
import os
import random
import json
from requests.utils import cookiejar_from_dict

# Try to import cloudscraper for anti-bot bypass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

logger = logging.getLogger(__name__)

@dataclass
class ArtistReference:
    """Basic artist info extracted from the alpha index."""
    id: int
    name: str
    url: str
    country: str = ""
    genre: str = ""

class ProgArchivesCollector:
    """
    Collector for ProgArchives data.
    Implements the 'Artist-First' strategy:
    1. Collect all artists from alphabetical index.
    2. Collect discography from each artist page.
    """
    
    BASE_URL = "https://www.progarchives.com"
    
    # Updated headers to mimic modern browser
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.progarchives.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    def __init__(self, raw_data_dir: str = "raw_data/progarchives", delay: float = 1.0, 
                 use_browser: bool = False, browser_headful: bool = False, browser_wait: float = 8.0):
        self.raw_data_dir = Path(raw_data_dir)
        self.artists_dir = self.raw_data_dir / "artists"
        self.lists_dir = self.raw_data_dir / "lists"
        self.index_file = self.raw_data_dir / "artists_master_index.csv"
        self.delay = delay
        self.use_browser = use_browser or (os.environ.get('PROGARCHIVES_USE_BROWSER', '').lower() in ('1', 'true', 'yes'))
        self.browser_headful = browser_headful
        self.browser_wait = browser_wait
        
        self.artists_dir.mkdir(parents=True, exist_ok=True)
        self.lists_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_session()
        # Try to load persisted browser cookies so we don't trigger captchas repeatedly
        try:
            self._load_browser_cookies()
        except Exception:
            pass

    def _init_session(self):
        """Initialize HTTP session with cloudscraper (if avail) or robust requests."""
        # Optional proxy support via env var PROGARCHIVES_PROXY (format: http://user:pass@host:port)
        proxy = os.environ.get('PROGARCHIVES_PROXY')

        # Small list of alternate UAs for rotation on retries
        self._ua_candidates = [
            self.HEADERS['User-Agent'],
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15',
        ]

        if HAS_CLOUDSCRAPER:
            logger.info("Initializing collector with CloudScraper (anti-bot bypass detected)")
            try:
                # Let cloudscraper pick defaults which might be more up to date
                self.session = cloudscraper.create_scraper()
                # Helper for specific headers we definitely want
                self.session.headers.update({
                    'Referer': 'https://www.progarchives.com/',
                    'Accept-Language': 'en-US,en;q=0.9',
                })
                if proxy:
                    logger.info(f"Using proxy from PROGARCHIVES_PROXY: {proxy}")
                    self.session.proxies.update({'http': proxy, 'https': proxy})
            except Exception as e:
                logger.warning(f"Failed to init cloudscraper: {e}. Falling back to standard requests.")
                self.session = requests.Session()
                self.session.headers.update(self.HEADERS)
                if proxy:
                    self.session.proxies.update({'http': proxy, 'https': proxy})
        else:
            logger.info("Initializing collector with standard Requests (CloudScraper not found)")
            self.session = requests.Session()
            self.session.headers.update(self.HEADERS)
            if proxy:
                self.session.proxies.update({'http': proxy, 'https': proxy})
        
        # Configure robust retries
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

        # Path to persist browser cookies for reuse across runs
        self._cookies_file = self.raw_data_dir / "browser_cookies.json"
        
    def _get(self, url: str) -> Optional[str]:
        """Fetch URL with rate limiting."""
        # Basic delay + small jitter
        time.sleep(self.delay + random.random() * 0.5)

        max_attempts = 3
        backoff = 2
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Fetching (attempt {attempt}): {url}")
                response = self.session.get(url, timeout=30)

                # Handle 403 specifically with diagnostics and UA rotation
                if response.status_code == 403:
                    logger.error(f"403 Forbidden for {url} - Possible firewall/IP block.")
                    # Log headers for debugging
                    try:
                        logger.debug(f"Response headers: {dict(response.headers)}")
                        logger.debug(f"Response snippet: {response.text[:500]!r}")
                    except Exception:
                        pass

                    # Rotate UA and retry if attempts remain
                    if attempt < max_attempts:
                        new_ua = random.choice(self._ua_candidates)
                        logger.info(f"Rotating User-Agent to: {new_ua} and backing off {backoff} seconds")
                        try:
                            self.session.headers['User-Agent'] = new_ua
                        except Exception:
                            logger.debug("Could not set User-Agent on session")
                        time.sleep(backoff + random.random())
                        backoff *= 2
                        continue
                    else:
                        # Final failure
                            # Optionally attempt browser fallback when enabled
                            if self.use_browser:
                                logger.info('Attempting Selenium browser fallback due to persistent 403')
                                rendered = self._fetch_with_browser(url, headful=self.browser_headful, wait=self.browser_wait)
                                return rendered
                            return None

                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"RequestException for {url} on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    logger.info(f"Backing off {backoff} seconds before retry")
                    time.sleep(backoff + random.random())
                    backoff *= 2
                    # rotate UA before retry
                    try:
                        self.session.headers['User-Agent'] = random.choice(self._ua_candidates)
                    except Exception:
                        pass
                    continue
                else:
                    logger.error(f"Failed to fetch {url} after {max_attempts} attempts: {e}")
                    return None

    def _save_browser_cookies(self, cookies: list):
        try:
            # cookies: list of dicts from selenium.get_cookies()
            d = {c['name']: c.get('value', '') for c in cookies}
            with open(self._cookies_file, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            # Update requests session cookie jar
            self.session.cookies.update(d)
        except Exception as e:
            logger.debug(f"Could not save browser cookies: {e}")

    def _load_browser_cookies(self):
        if self._cookies_file.exists():
            try:
                with open(self._cookies_file, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    self.session.cookies.update(d)
                    logger.info(f"Loaded {len(d)} cookies from {self._cookies_file}")
            except Exception as e:
                logger.debug(f"Failed to load cookies: {e}")

    def _fetch_with_browser(self, url: str, headful: bool = False, wait: float = 8.0) -> Optional[str]:
        """Use Selenium (or undetected-chromedriver) to render the page and return HTML.
        Persists cookies to avoid repeated captchas.
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        try:
            import undetected_chromedriver as uc
            use_uc = True
        except Exception:
            uc = None
            use_uc = False

        opts = Options()
        if not headful:
            opts.add_argument('--headless=new')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-extensions')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_argument('--window-size=1920,1080')
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)

        proxy = os.environ.get('PROGARCHIVES_PROXY')
        if proxy:
            opts.add_argument(f'--proxy-server={proxy}')

        driver = None
        try:
            if use_uc:
                logger.info('Starting undetected_chromedriver for browser fallback')
                driver = uc.Chrome(options=opts)
            else:
                logger.info('Starting standard Selenium Chrome for browser fallback')
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=opts)
                try:
                    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    })
                except Exception:
                    pass

            driver.get(url)
            # Wait briefly for Cloudflare challenge to complete
            time.sleep(wait)
            page = driver.page_source

            # Persist cookies
            try:
                cookies = driver.get_cookies()
                self._save_browser_cookies(cookies)
            except Exception:
                logger.debug('Could not retrieve/save cookies from browser')

            return page
        except Exception as e:
            logger.error(f"Browser fetch failed: {e}")
            return None
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass

    def fetch_all_artists(self, cache_index: bool = True) -> Generator[ArtistReference, None, None]:
        """
        Step 1: Iterate through 'bands-alpha.asp?letter=X' to find all artists.
        Yields ArtistReference objects and optionally saves them to a master CSV.
        """
        letters = list('abcdefghijklmnopqrstuvwxyz') + ['0']
        all_artists = []
        
        # Load from cache if requested and exists
        if cache_index and self.index_file.exists():
            logger.info(f"Loading artists from existing index: {self.index_file}")
            with open(self.index_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    artist = ArtistReference(
                        id=int(row['id']),
                        name=row['name'],
                        url=row['url'],
                        country=row.get('country', ''),
                        genre=row.get('genre', '')
                    )
                    # When reading from cache, just yield, don't accumulate for saving again
                    yield artist
            return

        # Otherwise, scrape freshly
        for letter in letters:
            url = f"{self.BASE_URL}/bands-alpha.asp?letter={letter}"
            html = self._get(url)
            
            if not html:
                continue
                
            with open(self.lists_dir / f"alpha_{letter}.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=re.compile(r'artist\.asp\?id=\d+'))
            
            logger.info(f"Found {len(links)} artists for letter '{letter}'")
            
            for link in links:
                try:
                    href = link['href']
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}/{href}"
                    
                    match = re.search(r'id=(\d+)', href)
                    if not match:
                        continue
                        
                    artist = ArtistReference(
                        id=int(match.group(1)),
                        name=link.get_text(strip=True),
                        url=full_url
                    )
                    all_artists.append(artist)
                    yield artist
                    
                except Exception as e:
                    logger.warning(f"Error parsing artist link {link}: {e}")

        # Save collected index if we did a fresh scrape
        if all_artists:
            self._save_index(all_artists)

    def _save_index(self, artists: List[ArtistReference]):
        """Save artist references to CSV index."""
        logger.info(f"Saving {len(artists)} artists to master index...")
        with open(self.index_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'name', 'url', 'country', 'genre']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for artist in artists:
                writer.writerow(asdict(artist))

    def fetch_artist_page(self, artist: ArtistReference) -> bool:
        """
        Step 2: Fetch specific artist page and save it.
        Returns True if successful (or skipped).
        """
        filename = f"artist_{artist.id}.html"
        file_path = self.artists_dir / filename
        
        if file_path.exists():
            logger.debug(f"Skipping existing: {artist.name}")
            return True
            
        html = self._get(artist.url)
        if html:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info(f"Saved {artist.name} to {filename}")
            return True
        return False
