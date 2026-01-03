"""
Targeted crawler for ProgArchives.com.
Focuses on specific high-value pages (Top Lists, Subgenres) rather than full site crawling.
"""
import logging
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional
import requests
from bs4 import BeautifulSoup

# Try to import undetected_chromedriver, fallback to standard selenium
try:
    import undetected_chromedriver as uc
    HAS_UC = True
except ImportError:
    HAS_UC = False
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class ProgArchivesCrawler:
    """
    Crawls ProgArchives.com for album data.
    Uses a browser automation approach to bypass Cloudflare protection.
    """
    
    BASE_URL = "https://www.progarchives.com"
    
    # Targeted entry points
    ENTRY_POINTS = {
        "prog_metal": "https://www.progarchives.com/subgenre.asp?style=19",
        "symphonic_prog": "https://www.progarchives.com/subgenre.asp?style=4",
        "heavy_prog": "https://www.progarchives.com/subgenre.asp?style=41",
        "top_albums": "https://www.progarchives.com/top-prog-albums.asp?salbumtypes=1",
    }
    
    def __init__(self, output_dir: str = "raw_data/progarchives", headless: bool = True):
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.driver = None
        self.seen_urls: Set[str] = set()
        
        # Create daily output directory
        date_str = datetime.now().strftime("%Y%m%d")
        self.daily_dir = self.output_dir / date_str
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
    def _init_driver(self):
        """Initialize the browser driver."""
        if self.driver:
            return

        logger.info("Initializing browser driver...")
        if HAS_UC:
            logger.info("Using undetected-chromedriver")
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')
            self.driver = uc.Chrome(options=options)
        else:
            logger.info("Using standard Selenium (undetected-chromedriver not found)")
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
    def _fetch_url(self, url: str, wait_time: int = 5) -> str:
        """Fetch a URL using the browser driver."""
        self._init_driver()
        logger.info(f"Fetching {url}...")
        self.driver.get(url)
        
        # Wait for Cloudflare or page load
        time.sleep(wait_time)
        
        # Check if we are stuck on Cloudflare
        title = self.driver.title
        if "Just a moment" in title:
            logger.warning("Cloudflare challenge detected. Waiting longer...")
            time.sleep(20)
            
        return self.driver.page_source

    def crawl_genre(self, genre_key: str, max_pages: int = 1, limit_albums: int = None):
        """Crawl a specific genre listing."""
        if genre_key not in self.ENTRY_POINTS:
            raise ValueError(f"Unknown genre key: {genre_key}")
            
        base_url = self.ENTRY_POINTS[genre_key]
        logger.info(f"Starting crawl for {genre_key}: {base_url}")
        
        albums_processed = 0
        
        for page in range(max_pages):
            # Construct paginated URL
            # ProgArchives uses 'min' parameter for offset (e.g., min=100)
            # Each page typically shows 100 items
            offset = page * 100
            if offset > 0:
                if '?' in base_url:
                    url = f"{base_url}&min={offset}"
                else:
                    url = f"{base_url}?min={offset}"
            else:
                url = base_url
                
            logger.info(f"Crawling page {page + 1}: {url}")
            
            try:
                html = self._fetch_url(url)
                count = self._process_listing_page(html, limit_albums - albums_processed if limit_albums else None)
                albums_processed += count
                
                if limit_albums and albums_processed >= limit_albums:
                    logger.info(f"Reached album limit of {limit_albums}")
                    break
                    
                # Be polite between listing pages
                time.sleep(random.uniform(3, 7))
                
            except Exception as e:
                logger.error(f"Failed to crawl page {page + 1}: {e}")
                break

    def _process_listing_page(self, html: str, limit: int = None) -> int:
        """
        Extract album links from a listing page and fetch them.
        Returns number of albums processed.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find album links
        # ProgArchives links usually look like "album.asp?id=XXXX"
        links = soup.find_all('a', href=True)
        album_links = []
        
        for link in links:
            href = link['href']
            if 'album.asp?id=' in href:
                full_url = href if href.startswith('http') else f"{self.BASE_URL}/{href}"
                # Deduplicate
                if full_url not in self.seen_urls:
                    album_links.append(full_url)
                    self.seen_urls.add(full_url)
                    
        logger.info(f"Found {len(album_links)} unique album links on this page.")
        
        count = 0
        for i, url in enumerate(album_links):
            if limit is not None and count >= limit:
                break
                
            try:
                self._process_album_page(url)
                count += 1
                # Be polite
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}")
        
        return count
                
    def _process_album_page(self, url: str):
        """Fetch and save an album page."""
        logger.info(f"Processing album: {url}")
        html = self._fetch_url(url, wait_time=2)
        
        # Extract ID for filename
        # url is like .../album.asp?id=12345
        try:
            album_id = url.split('id=')[1].split('&')[0]
        except IndexError:
            album_id = "unknown_" + str(hash(url))
            
        filename = f"album_{album_id}.html"
        file_path = self.daily_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        logger.info(f"Saved to {file_path}")

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
