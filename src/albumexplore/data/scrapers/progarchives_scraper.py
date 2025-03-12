"""Scraper for ProgArchives.com with ethical rate limiting."""
import logging
import time
import random
from typing import Dict, List, Optional, Generator
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Ethical scraper for ProgArchives.com with rate limiting."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize scraper with optional cache directory."""
        self.base_url = "https://www.progarchives.com"
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            
        # Rate limiting settings - be very considerate
        self.min_delay = 3.0  # Minimum seconds between requests
        self.max_delay = 5.0  # Maximum seconds between requests
        self.last_request_time = 0
        self.max_retries = 3
        self.retry_delay = 5
        
        # Valid record types
        self.valid_record_types = {'Studio', 'EP', 'Single', 'Fan Club', 'Promo'}
        
        # Session with headers that mimic a real browser
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

    def _wait_for_rate_limit(self):
        """Ensure ethical rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_delay:
            wait_time = random.uniform(
                self.min_delay - elapsed,
                self.max_delay - elapsed
            )
            time.sleep(wait_time)
        
        self.last_request_time = time.time()

    def get_page(self, url: str, cache_key: Optional[str] = None) -> str:
        """Get page content with rate limiting and caching."""
        if cache_key and self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.html"
            if cache_file.exists():
                logger.debug(f"Using cached content for {url}")
                return cache_file.read_text(encoding='utf-8')
        
        retries = 0
        while retries < self.max_retries:
            try:
                self._wait_for_rate_limit()
                logger.debug(f"Fetching {url}")
                response = self.session.get(url)
                response.raise_for_status()
                
                if cache_key and self.cache_dir:
                    cache_file = self.cache_dir / f"{cache_key}.html"
                    cache_file.write_text(response.text, encoding='utf-8')
                    
                return response.text
                
            except requests.RequestException as e:
                retries += 1
                logger.warning(f"Request failed (attempt {retries}/{self.max_retries}): {str(e)}")
                if retries < self.max_retries:
                    time.sleep(self.retry_delay * retries)
                else:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                    raise

    def get_all_bands(self) -> Generator[Dict, None, None]:
        """Get list of all bands from the prog metal listing."""
        # Start with the prog metal bands list
        url = f"{self.base_url}/subgenre/19/Progressive-Metal"
        logger.info(f"Fetching bands from {url}")
        
        content = self.get_page(url, cache_key="prog_metal_main")
        soup = BeautifulSoup(content, 'html.parser')
        
        seen_bands = set()
        
        # Find the grid container that holds band listings
        grid = soup.find('div', {'class': 'grid-container'})
        if grid:
            # Process bands in groups of 3 (band, style, country)
            items = grid.find_all('div', {'class': 'grid-item'})
            
            # Skip header row
            headers = items[:3]
            items = items[3:]
            
            # Process in groups of 3
            for i in range(0, len(items), 3):
                try:
                    if i + 2 >= len(items):
                        break
                        
                    band_cell = items[i]
                    style_cell = items[i + 1]
                    country_cell = items[i + 2]
                    
                    # Get band link
                    band_link = band_cell.find('a')
                    if not band_link:
                        continue
                        
                    band_url = band_link['href']
                    if not band_url.startswith('http'):
                        band_url = self.base_url + '/' + band_url
                    
                    if band_url in seen_bands:
                        continue
                        
                    band_name = band_link.text.strip()
                    if not band_name:
                        continue
                        
                    # Get genre and country
                    genre = style_cell.text.strip()
                    country = country_cell.text.strip()
                    
                    logger.info(f"Found band: {band_name}")
                    
                    band = {
                        'name': band_name,
                        'url': band_url,
                        'genre': genre,
                        'country': country
                    }
                    
                    seen_bands.add(band_url)
                    yield band
                    
                except Exception as e:
                    logger.error(f"Error parsing band entry: {str(e)}")
                    continue
        else:
            logger.warning("Could not find grid container for band listings")

    def get_band_details(self, band_url: str) -> Dict:
        """Get detailed information about a band."""
        logger.info(f"Getting details for band at {band_url}")
        content = self.get_page(band_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            details = {'description': '', 'formed_info': '', 'albums': []}
            
            # Get band info from meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc:
                desc_content = meta_desc.get('content', '')
                if desc_content:
                    details['description'] = desc_content
                    # Try to extract country
                    country_match = re.search(r'from ([^\.]+)', desc_content)
                    if country_match:
                        details['country'] = country_match.group(1).strip()
            
            # Find the main content area
            main_content = soup.find('div', {'id': 'main'})
            if main_content:
                # Look for discography sections
                album_cells = main_content.find_all('td', {'align': 'center'})
                
                current_section = 'Studio'  # Default section
                
                # Look for section headers to determine record type
                for element in main_content.find_all(['h3', 'td']):
                    text = element.get_text(strip=True).lower()
                    
                    # Check if this is a section header
                    if element.name == 'h3':
                        if 'studio' in text:
                            current_section = 'Studio'
                        elif any(x in text for x in ['ep', 'single']):
                            current_section = 'EP'
                        elif 'fan club' in text:
                            current_section = 'Fan Club'
                        elif 'promo' in text:
                            current_section = 'Promo'
                        continue
                    
                    # Only process centered cells which typically contain album entries
                    if element.get('align') != 'center':
                        continue
                        
                    try:
                        # Get album link
                        album_link = element.find('a', href=re.compile(r'album\.asp\?id=\d+'))
                        if not album_link:
                            continue
                            
                        # Get year from the gray text
                        year_span = element.find('span', {'style': 'color:#777'})
                        if not year_span:
                            continue
                            
                        year_match = re.search(r'\b(19|20)\d{2}\b', year_span.text)
                        if not year_match:
                            continue
                            
                        year = int(year_match.group())
                        
                        # Get rating - typically in red text
                        rating = None
                        rating_span = element.find('span', {'style': re.compile(r'color:#C75D4F')})
                        if rating_span:
                            try:
                                rating = float(rating_span.text.strip())
                            except (ValueError, TypeError):
                                pass
                        
                        album_url = album_link['href']
                        if not album_url.startswith('http'):
                            album_url = self.base_url + '/' + album_url
                        
                        album = {
                            'title': album_link.text.strip(),
                            'url': album_url,
                            'record_type': current_section,
                            'year': year,
                            'rating': rating
                        }
                        
                        logger.info(f"Found album: {album['title']} ({album['year']}) - {current_section}")
                        details['albums'].append(album)
                        
                    except Exception as e:
                        logger.error(f"Error parsing album entry: {str(e)}")
                        continue
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing band page {band_url}: {str(e)}")
            return {'error': str(e)}

    def get_album_details(self, album_url: str) -> Dict:
        """Get detailed information about an album."""
        logger.info(f"Getting details for album at {album_url}")
        content = self.get_page(album_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            details = {'description': '', 'lineup': []}
            
            # Get album info from meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc:
                details['description'] = meta_desc.get('content', '')
            
            # Find the main content area
            main_content = soup.find('div', {'id': 'main'})
            if main_content:
                # Look for lineup section which comes after "LINE-UP" text
                lineup_heading = None
                for element in main_content.find_all(['h3', 'div', 'td']):
                    if 'LINE-UP' in element.get_text().upper():
                        lineup_heading = element
                        break
                
                if lineup_heading:
                    current_role = None
                    # Look at elements after the lineup heading
                    for element in lineup_heading.find_next_siblings():
                        text = element.get_text(strip=True)
                        if not text:
                            continue
                            
                        if text.endswith(':'):
                            current_role = text[:-1].strip()
                        elif current_role:
                            details['lineup'].append({
                                'role': current_role,
                                'name': text.strip()
                            })
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing album page {album_url}: {str(e)}")
            return {'error': str(e)}