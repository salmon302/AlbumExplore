"""ProgArchives.com scraper with ethical rate limiting."""
import logging
import re
import time
from typing import Dict, List, Iterator, Optional, Any
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ProgArchivesScraper(BaseScraper):
    """Scraper for ProgArchives.com that follows ethical guidelines."""
    
    BASE_URL = "https://www.progarchives.com"
    ALPHA_URL = f"{BASE_URL}/bands-alpha.asp"
    ARTIST_URL = f"{BASE_URL}/artist.asp"
    ALBUM_URL = f"{BASE_URL}/album.asp"
    ALBUM_REVIEWS_URL = f"{BASE_URL}/album-reviews.asp"
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_bands: Optional[int] = None,
        random_sample: bool = False
    ):
        """Initialize scraper with optional limits and sampling strategy."""
        super().__init__(
            cache_dir=cache_dir / "progarchives" if cache_dir else Path("cache/progarchives"),
            min_request_interval=5.0  # Ethical rate limiting
        )
        self.max_bands = max_bands
        self.random_sample = random_sample
        self._retry_count = 3  # Number of retries for failed requests

    def get_bands_all(self, use_cache: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Get all bands from ProgArchives alphabetically.
        
        Args:
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Iterator of band dictionaries with name, URL, and metadata
        """
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        band_count = 0
        
        for letter in letters:
            try:
                for band in self._get_bands_for_letter(letter, use_cache=use_cache):
                    yield band
                    band_count += 1
                    
                    if self.max_bands and band_count >= self.max_bands:
                        logger.info(f"Reached maximum band count limit ({self.max_bands})")
                        return
                        
            except Exception as e:
                logger.error(f"Error getting bands for letter {letter}: {e}")
    
    def _get_bands_for_letter(self, letter: str, use_cache: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Get all bands starting with a specific letter.
        
        Args:
            letter: The letter to get bands for
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Iterator of band dictionaries with name, URL, and metadata
        """
        url = f"{self.ALPHA_URL}?letter={letter}"
        
        try:
            # Fetch the page
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                logger.warning(f"No content received from {url}")
                return
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Find the grid container that contains the band listings
            grid_container = soup.select_one('div.grid-container')
            if not grid_container:
                logger.warning(f"Could not find grid container on {url}")
                return
                
            # Extract artist links
            artist_links = grid_container.select('a[href*="artist.asp"]')
            
            if not artist_links:
                logger.warning(f"No artist links found on {url}")
                return
                
            logger.info(f"Found {len(artist_links)} bands starting with letter '{letter}'")
            
            # Process each band entry
            for i, link in enumerate(artist_links):
                try:
                    band_url = link['href']
                    if not band_url.startswith('http'):
                        band_url = f"{self.BASE_URL}/{band_url.lstrip('/')}"
                        
                    # Get band ID from URL
                    band_id_match = re.search(r'id=(\d+)', band_url)
                    band_id = band_id_match.group(1) if band_id_match else None
                    
                    # Find genre and country information
                    # In the grid-container, each row has 3 cells:
                    # Artist | Genre | Country
                    parent = link.parent  # This is the artist cell
                    row_items = list(parent.parent.children)
                    
                    genre = None
                    country = None
                    
                    # Look for genre and country in sibling cells
                    if len(row_items) >= 3:
                        genre_cell = row_items[1]
                        country_cell = row_items[2]
                        
                        genre = self._extract_text(genre_cell)
                        country = self._extract_text(country_cell)
                    
                    band = {
                        'name': self._extract_text(link),
                        'url': band_url,
                        'id': band_id,
                    }
                    
                    if genre:
                        band['genre'] = genre
                    
                    if country:
                        band['country'] = country
                        
                    yield band
                    
                except Exception as e:
                    logger.warning(f"Error processing band {i} on letter {letter} page: {e}")
            
        except Exception as e:
            logger.error(f"Error getting bands for letter {letter}: {e}")
    
    def get_band_details(self, url_or_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about a band/artist.
        
        Args:
            url_or_id: Either a full URL or just the artist ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Dictionary with band details including name, genre, country, discography, etc.
        """
        try:
            # Convert URL to ID if needed
            artist_id = self._extract_id(url_or_id)
            if not artist_id:
                raise ValueError(f"Invalid artist URL or ID: {url_or_id}")
                
            # Use string concatenation to prevent URL encoding
            url = url_or_id if not url_or_id.isdigit() else f"{self.ARTIST_URL}?id={artist_id}"
            
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract artist information
            artist_info = self._parse_artist_info(soup, url)
            if not artist_info:
                raise ValueError(f"Could not find band info section for {url}")
                
            # Add metadata
            artist_info['url'] = url
            artist_info['id'] = artist_id
            artist_info['scraped_at'] = datetime.now().isoformat()
            
            # Get albums
            artist_info['albums'] = list(self._find_band_albums(soup))
            
            return artist_info
            
        except Exception as e:
            logger.error(f"Error getting band details from {url_or_id}: {e}")
            return {'error': str(e)}
    
    def get_album_data(self, url_or_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about an album.
        
        Args:
            url_or_id: Either a full URL or just the album ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Dictionary with album details including title, artist, tracks, etc.
        """
        try:
            # Convert URL to ID if needed
            album_id = self._extract_id(url_or_id)
            if not album_id:
                raise ValueError(f"Invalid album URL or ID: {url_or_id}")
                
            # Use string concatenation to prevent URL encoding
            url = f"{self.ALBUM_URL}?id={album_id}"
            
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract album details
            album_info = self._parse_album_info(soup)
            if not album_info:
                raise ValueError(f"Could not parse album data from {url}")
                
            # Add metadata
            album_info['url'] = url
            album_info['id'] = album_id
            album_info['scraped_at'] = datetime.now().isoformat()
            
            # Get review summary/stats
            album_info['reviews'] = self._get_review_stats(soup)
            
            # Get tracklist
            album_info['tracks'] = self._extract_tracklist(soup)
            
            return album_info
            
        except Exception as e:
            logger.error(f"Error getting album data from {url_or_id}: {e}")
            return {'error': str(e)}
            
    def get_album_reviews(self, url_or_id: str, use_cache: bool = True, max_reviews: Optional[int] = None) -> Dict[str, Any]:
        """
        Get reviews for a specific album.
        
        Args:
            url_or_id: Either a full URL or just the album ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            max_reviews: Maximum number of reviews to fetch (None for all)
            
        Returns:
            Dictionary with album reviews and review metadata
        """
        try:
            # Convert URL to ID if needed
            album_id = self._extract_id(url_or_id)
            if not album_id:
                raise ValueError(f"Invalid album URL or ID: {url_or_id}")
                
            # Use string concatenation to prevent URL encoding
            url = f"{self.ALBUM_REVIEWS_URL}?id={album_id}"
            
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract basic album info
            album_info = {
                'id': album_id,
                'url': url,
                'title': self._extract_album_title_from_reviews(soup),
                'artist': self._extract_artist_from_reviews(soup),
                'reviews': list(self._extract_reviews(soup, max_reviews)),
                'scraped_at': datetime.now().isoformat()
            }
            
            return album_info
            
        except Exception as e:
            logger.error(f"Error getting album reviews from {url_or_id}: {e}")
            return {'error': str(e)}
    
    def _extract_id(self, url_or_id: str) -> Optional[str]:
        """Extract ID from URL or return ID if already an ID string."""
        if url_or_id.isdigit():
            return url_or_id
            
        # Try to extract ID from URL - use raw string pattern
        match = re.search(r'id=(\d+)', url_or_id)
        if match:
            return match.group(1)
            
        return None
        
    def _parse_artist_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract artist information from artist page HTML."""
        artist_info = {}
        
        try:
            # Extract artist name from h1 element
            h1_element = soup.find('h1')
            if h1_element:
                artist_info['name'] = self._extract_text(h1_element)
            
            # Try multiple possible locations for genre information
            genre = None
            genre_elements = soup.select('.genresubtitle, .genre, .genre-title, .artist-genre, h2')
            for element in genre_elements:
                # Skip h2 elements that contain links (usually not genre)
                if element.name == 'h2' and element.find('a'):
                    continue
                text = self._extract_text(element)
                if text and not any(skip in text.lower() for skip in ['albums', 'reviews', 'artist']):
                    genre = text
                    break
            
            # If still no genre, try finding it in the band info grid
            if not genre:
                band_table = soup.find('table', {'style': 'border:1px solid #a0a0a0'})
                if band_table:
                    for row in band_table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            header = self._extract_text(cells[0]).lower()
                            if 'genre' in header:
                                genre = self._extract_text(cells[1])
                                break
            
            if genre:
                artist_info['genre'] = genre
                
            # Extract country information
            country_elem = soup.select_one('.countrysubtitle, .country, .artist-country')
            if country_elem:
                artist_info['country'] = self._extract_text(country_elem)
            
            # Extract biography/description
            bio_element = soup.select_one('.artistdescription')
            if bio_element:
                artist_info['bio'] = self._extract_text(bio_element)
                
            # Extract member/lineup information
            members = self._find_band_members(soup)
            if members:
                artist_info['members'] = members
                
            # Check for required fields
            if 'name' not in artist_info:
                logger.warning(f"Could not find artist name for {url}")
                return {}
                
            return artist_info
            
        except Exception as e:
            logger.error(f"Error parsing artist info for {url}: {e}")
            return {}

    def _find_band_albums(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract albums from an artist page.
        
        Args:
            soup: BeautifulSoup object of the artist page
            
        Returns:
            List of album dictionaries
        """
        albums = []
        try:
            # Method 1: Look for the standard artist-discography structure
            discography_cells = soup.select('td.artist-discography-td')
            if discography_cells:
                for cell in discography_cells:
                    try:
                        # Find the main album link - exclude buymusic/review links
                        links = cell.find_all('a', href=re.compile(r'album\.asp\?id=\d+'))
                        main_link = None
                        for link in links:
                            if not any(skip in link.get_text().lower() for skip in ['buy', 'review']):
                                main_link = link
                                break
                                
                        if not main_link:
                            continue
                            
                        # Get album URL
                        album_url = main_link['href']
                        if not album_url.startswith('http'):
                            album_url = f"{self.BASE_URL}/{album_url.lstrip('/')}"
                            
                        # Get album title - it should be in a strong tag
                        title_elem = cell.find('strong')
                        if not title_elem:
                            title_elem = main_link  # Fallback to link text if no strong tag
                            
                        title = self._extract_text(title_elem)
                        if not title:
                            continue
                            
                        album_info = {
                            'title': title,
                            'url': album_url,
                            'year': None  # Initialize year field
                        }
                        
                        # Get album ID from URL
                        id_match = re.search(r'id=(\d+)', album_url)
                        if id_match:
                            album_info['id'] = id_match.group(1)
                            
                        # Try various ways to find the year
                        cell_text = self._extract_text(cell)
                        if cell_text:
                            # First try year in parentheses format (2023)
                            year_match = re.search(r'\((\d{4})\)', cell_text)
                            if year_match:
                                album_info['year'] = int(year_match.group(1))
                            else:
                                # Try "released in YYYY" format
                                year_match = re.search(r'released\s+in\s+(\d{4})', cell_text.lower())
                                if year_match:
                                    album_info['year'] = int(year_match.group(1))
                                else:
                                    # Try finding any 4-digit year
                                    year_match = re.search(r'\b(19|20)\d{2}\b', cell_text)
                                    if year_match:
                                        album_info['year'] = int(year_match.group(0))
                            
                            # Look for album type
                            type_match = re.search(r'\b(Studio Album|Live Album|Live|EP|Single|Demo|Compilation)\b', 
                                                 cell_text, re.IGNORECASE)
                            if type_match:
                                album_info['type'] = self._normalize_album_type(type_match.group(1))
                            else:
                                album_info['type'] = 'Studio Album'  # Default type
                                
                        # If we still don't have a year, try getting it from nearby elements
                        if not album_info['year']:
                            # Look for elements with class containing 'year'
                            year_elem = cell.find(class_=re.compile(r'year|date|release'))
                            if year_elem:
                                year_text = self._extract_text(year_elem)
                                if year_text:
                                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                                    if year_match:
                                        album_info['year'] = int(year_match.group(0))
                                        
                            # Look for table cells containing year
                            if not album_info['year'] and cell.parent:
                                row = cell.parent
                                for td in row.find_all('td'):
                                    td_text = self._extract_text(td)
                                    if td_text and re.match(r'^(19|20)\d{2}$', td_text.strip()):
                                        album_info['year'] = int(td_text.strip())
                                        break
                                        
                        # If we still don't have a year, try to infer from album ID
                        # Newer IDs tend to be from newer albums, so use this as last resort
                        if not album_info['year'] and 'id' in album_info:
                            album_id = int(album_info['id'])
                            if album_id < 1000:  # Very old entries, likely from the 70s
                                album_info['year'] = 1970
                            elif album_id < 5000:  # Old entries, likely from the 80s/90s
                                album_info['year'] = 1990
                            else:  # Newer entries
                                album_info['year'] = 2000
                                
                        albums.append(album_info)
                        
                    except Exception as e:
                        logger.warning(f"Error processing album cell: {e}")
                        
            # Method 2: Try finding albums in the discography section
            if not albums:  # Only try this if Method 1 found nothing
                discography_div = soup.find('div', class_='discography')
                if discography_div:
                    album_items = discography_div.find_all(['div', 'tr'], class_=['album', 'album-item'])
                    for item in album_items:
                        try:
                            # Find main album link
                            link = item.find('a', href=re.compile(r'album\.asp\?id=\d+'))
                            if not link or any(skip in link.get_text().lower() for skip in ['buy', 'review']):
                                continue
                                
                            album_url = link['href']
                            if not album_url.startswith('http'):
                                album_url = f"{self.BASE_URL}/{album_url.lstrip('/')}"
                                
                            title = self._extract_text(link)
                            if not title:
                                continue
                                
                            album_info = {
                                'title': title,
                                'url': album_url,
                                'year': None  # Initialize year field
                            }
                            
                            # Get album ID
                            id_match = re.search(r'id=(\d+)', album_url)
                            if id_match:
                                album_info['id'] = id_match.group(1)
                                
                            # Get year and type
                            item_text = self._extract_text(item)
                            if item_text:
                                # Try various year formats
                                year_found = False
                                for pattern in [
                                    r'\((\d{4})\)',  # (2023)
                                    r'released\s+in\s+(\d{4})',  # released in 2023
                                    r'\b(19|20)\d{2}\b'  # any 4-digit year
                                ]:
                                    year_match = re.search(pattern, item_text.lower())
                                    if year_match:
                                        album_info['year'] = int(year_match.group(1))
                                        year_found = True
                                        break
                                        
                                if not year_found:
                                    # Try to find a year in any table cells
                                    for cell in item.find_all('td'):
                                        cell_text = self._extract_text(cell)
                                        if cell_text and re.match(r'^(19|20)\d{2}$', cell_text.strip()):
                                            album_info['year'] = int(cell_text.strip())
                                            break
                                            
                                # Look for album type
                                type_match = re.search(r'\b(Studio Album|Live Album|Live|EP|Single|Demo|Compilation)\b',
                                                     item_text, re.IGNORECASE)
                                if type_match:
                                    album_info['type'] = self._normalize_album_type(type_match.group(1))
                                else:
                                    album_info['type'] = 'Studio Album'
                                    
                            # If we still don't have a year, infer from album ID
                            if not album_info['year'] and 'id' in album_info:
                                album_id = int(album_info['id'])
                                if album_id < 1000:
                                    album_info['year'] = 1970
                                elif album_id < 5000:
                                    album_info['year'] = 1990
                                else:
                                    album_info['year'] = 2000
                                    
                            albums.append(album_info)
                            
                        except Exception as e:
                            logger.warning(f"Error processing album item: {e}")
                            
            # Method 3: Try finding albums in a table structure
            if not albums:  # Only try this if previous methods found nothing
                for table in soup.find_all('table', class_=['discography', 'albums', 'artist-albums']):
                    for row in table.find_all('tr'):
                        try:
                            # Skip header rows
                            if row.find('th'):
                                continue
                                
                            # Find main album link
                            link = row.find('a', href=re.compile(r'album\.asp\?id=\d+'))
                            if not link or any(skip in link.get_text().lower() for skip in ['buy', 'review']):
                                continue
                                
                            album_url = link['href']
                            if not album_url.startswith('http'):
                                album_url = f"{self.BASE_URL}/{album_url.lstrip('/')}"
                                
                            title = self._extract_text(link)
                            if not title:
                                continue
                                
                            album_info = {
                                'title': title,
                                'url': album_url,
                                'year': None  # Initialize year field
                            }
                            
                            # Get album ID
                            id_match = re.search(r'id=(\d+)', album_url)
                            if id_match:
                                album_info['id'] = id_match.group(1)
                                
                            # Look for year and type in row cells
                            cells = row.find_all('td')
                            for cell in cells:
                                cell_text = self._extract_text(cell)
                                if cell_text:
                                    if not album_info['year']:
                                        # Try various year formats
                                        for pattern in [
                                            r'\((\d{4})\)',
                                            r'released\s+in\s+(\d{4})',
                                            r'\b(19|20)\d{2}\b'
                                        ]:
                                            year_match = re.search(pattern, cell_text.lower())
                                            if year_match:
                                                album_info['year'] = int(year_match.group(1))
                                                break
                                                
                                    if 'type' not in album_info:
                                        type_match = re.search(r'\b(Studio Album|Live Album|Live|EP|Single|Demo|Compilation)\b',
                                                             cell_text, re.IGNORECASE)
                                        if type_match:
                                            album_info['type'] = self._normalize_album_type(type_match.group(1))
                                            
                            if not album_info['year'] and 'id' in album_info:
                                # Infer year from album ID as last resort
                                album_id = int(album_info['id'])
                                if album_id < 1000:
                                    album_info['year'] = 1970
                                elif album_id < 5000:
                                    album_info['year'] = 1990
                                else:
                                    album_info['year'] = 2000
                                    
                            if 'type' not in album_info:
                                album_info['type'] = 'Studio Album'
                                
                            albums.append(album_info)
                            
                        except Exception as e:
                            logger.warning(f"Error processing table row: {e}")
                            
            if not albums:
                logger.warning("No album entries found using any known structure")
                
        except Exception as e:
            logger.error(f"Error finding band albums: {e}")
            
        return albums
    
    def _normalize_album_type(self, album_type: str) -> str:
        """Normalize album type to standard values."""
        if not album_type:
            return 'Studio Album'  # Default type
            
        album_type = album_type.lower().strip()
        
        # Map various possible type strings to standard values
        type_mapping = {
            'studio': 'Studio Album',
            'studio album': 'Studio Album',
            'lp': 'Studio Album',
            'album': 'Studio Album',
            'ep': 'Single/EP',
            'single': 'Single/EP',
            'single/ep': 'Single/EP',
            'demo': 'Single/EP',
            'live': 'Live',
            'live album': 'Live',
            'compilation': 'Compilation',
            'compilation album': 'Compilation',
            'best of': 'Compilation',
            'collection': 'Compilation'
        }
        
        # Try direct mapping first
        if album_type in type_mapping:
            return type_mapping[album_type]
            
        # Try partial matching
        for key, value in type_mapping.items():
            if key in album_type:
                return value
                
        return 'Studio Album'  # Default if no match found

    def _parse_album_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract album information from album page HTML."""
        album_info = {}
        
        try:
            # First check if this looks like an album page at all
            # Look for key elements that indicate an album page
            album_indicators = [
                soup.select_one('#imgCover'),  # Album cover image
                soup.find('strong', string=re.compile(r'Songs\s*/\s*Tracks\s*Listing')),  # Track listing header
                soup.find('strong', string=re.compile(r'Line.?up\s*/\s*Musicians')),  # Lineup header
                soup.find('div', class_='discographyStar')  # Ratings section
            ]
            
            # If none of these indicators are present, this probably isn't an album page
            if not any(album_indicators):
                raise ValueError("Page does not appear to be an album page - missing key elements")
            
            # Find album title - look in multiple places
            title_candidates = [
                soup.find('h1'),  # Main page title
                soup.select_one('meta[property="og:title"]'),  # OpenGraph title
                soup.find('title')  # HTML title tag
            ]
            
            for candidate in title_candidates:
                if candidate:
                    if isinstance(candidate, Tag) and candidate.get('content'):
                        title_text = candidate['content']
                    else:
                        title_text = self._extract_text(candidate)
                        
                    if title_text:
                        # Clean up the title
                        title_text = re.sub(r'\s*reviews$', '', title_text, flags=re.I)
                        title_parts = re.split(r'\s*[-–]\s*|\s*\(', title_text)
                        if len(title_parts) >= 2:
                            album_info['artist'] = title_parts[0].strip()
                            album_info['title'] = title_parts[1].strip()
                            break
                        else:
                            album_info['title'] = title_text
            
            # Get artist information if not already found
            if 'artist' not in album_info:
                artist_link = soup.select_one('h2 a[href*="artist.asp"]')
                if artist_link:
                    album_info['artist'] = self._extract_text(artist_link)
                    artist_url = artist_link['href']
                    if not artist_url.startswith('http'):
                        artist_url = f"{self.BASE_URL}/{artist_url.lstrip('/')}"
                    album_info['artist_url'] = artist_url
                    
                    artist_id_match = re.search(r'id=(\d+)', artist_url)
                    if artist_id_match:
                        album_info['artist_id'] = artist_id_match.group(1)
            
            # Look for release information
            release_info = None
            for strong_tag in soup.find_all('strong'):
                text = self._extract_text(strong_tag)
                if text and ('released' in text.lower() or 'album' in text.lower()):
                    release_info = text
                    break
                    
            if release_info:
                # Try to extract year and album type
                year_match = re.search(r'\b(19|20)\d{2}\b', release_info)
                if year_match:
                    try:
                        album_info['year'] = int(year_match.group(0))
                    except ValueError:
                        pass
                        
                type_match = re.search(r'(Studio|Live|EP|Single|Demo|Compilation)(?:\s+Album)?',
                                     release_info, re.IGNORECASE)
                if type_match:
                    album_info['type'] = self._normalize_album_type(type_match.group(0))
            
            # Get tracklist
            tracklist = None
            for strong_tag in soup.find_all('strong'):
                if 'Songs / Tracks Listing' in self._extract_text(strong_tag):
                    tracklist = strong_tag.find_next('p')
                    break
                    
            if tracklist:
                tracks = []
                track_text = self._extract_text(tracklist)
                if track_text:
                    # Split by newlines or numbers with periods
                    track_lines = [line.strip() for line in re.split(r'\n|(?<=\d)\.\s+', track_text) if line.strip()]
                    
                    for i, line in enumerate(track_lines, 1):
                        if not line.startswith('Total Time'):
                            track_info = {'number': i}
                            
                            # Look for duration in parentheses at end
                            duration_match = re.search(r'\((\d+:\d+)\)$', line)
                            if duration_match:
                                track_info['duration'] = duration_match.group(1)
                                line = line[:duration_match.start()].strip()
                                
                            track_info['title'] = line
                            tracks.append(track_info)
                            
                album_info['tracks'] = tracks
            
            # Get lineup/musicians
            lineup = None
            for strong_tag in soup.find_all('strong'):
                if 'Line-up / Musicians' in self._extract_text(strong_tag):
                    lineup = strong_tag.find_next('p')
                    break
                    
            if lineup:
                members = []
                lineup_text = self._extract_text(lineup)
                if lineup_text:
                    # Split by line breaks or dashes
                    member_lines = [line.strip() for line in re.split(r'\n|-', lineup_text) if line.strip()]
                    
                    for line in member_lines:
                        # Try to separate name from instruments
                        parts = [p.strip() for p in re.split(r'\s*/\s*|\s+\|\s+|\s*:\s*', line, maxsplit=1)]
                        if len(parts) >= 2:
                            members.append({
                                'name': parts[0],
                                'role': parts[1]
                            })
                        else:
                            members.append({
                                'name': parts[0],
                                'role': None
                            })
                            
                album_info['members'] = members
            
            # Get album cover URL
            cover_img = soup.select_one('#imgCover')
            if cover_img and cover_img.get('src'):
                img_url = cover_img['src']
                if not img_url.startswith('http'):
                    img_url = f"{self.BASE_URL}/{img_url.lstrip('/')}"
                album_info['cover_image'] = img_url
                
            # Consider the page valid if we have at least:
            # 1. A title, OR
            # 2. An artist name, OR
            # 3. Any tracks or members
            if (album_info.get('title') or 
                album_info.get('artist') or 
                album_info.get('tracks') or 
                album_info.get('members')):
                return album_info
                
            raise ValueError("Page does not appear to be an album page - no album data found")
            
        except Exception as e:
            logger.error(f"Error parsing album info: {e}")
            return {'error': str(e)}
    
    def _get_review_stats(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract review statistics from album page."""
        stats = {
            'avg_rating': None,
            'num_ratings': 0,
            'num_reviews': 0
        }
        
        try:
            # Look for average rating span
            avg_rating_span = soup.select_one('span[id^="avgRatings_"]')
            if avg_rating_span and avg_rating_span.get_text():
                try:
                    stats['avg_rating'] = float(avg_rating_span.get_text())
                except (ValueError, TypeError):
                    pass
                    
            # Look for number of ratings span
            num_ratings_span = soup.select_one('span[id^="nbRatings_"]')
            if num_ratings_span and num_ratings_span.get_text():
                try:
                    stats['num_ratings'] = int(num_ratings_span.get_text())
                except (ValueError, TypeError):
                    pass
                    
            # Look for number of reviews info
            review_stats = soup.select_one('.ratings_count') or soup.select_one('a[href="#reviews"]')
            if review_stats:
                text = self._extract_text(review_stats)
                if text:
                    reviews_match = re.search(r'(\d+)\s+reviews', text)
                    if reviews_match:
                        try:
                            stats['num_reviews'] = int(reviews_match.group(1))
                        except (ValueError, TypeError):
                            pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error extracting review stats: {e}")
            return stats
    
    def _extract_tracklist(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract album tracklist."""
        tracks = []
        
        try:
            # Look for the tracklist paragraph after "Songs / Tracks Listing" heading
            tracklist_p = None
            for strong_tag in soup.find_all('strong'):
                if 'Songs / Tracks Listing' in self._extract_text(strong_tag):
                    tracklist_p = strong_tag.find_next('p')
                    break
                    
            if not tracklist_p:
                return tracks
                
            # Get text content
            tracklist_text = self._extract_text(tracklist_p)
            if not tracklist_text:
                return tracks
                
            # Split into lines by <br> tags or by numbered tracks
            # For the HTML version, we need to split by <br> tags
            track_lines = []
            for line in tracklist_p.get_text(separator='||').split('||'):
                line = line.strip()
                if line:
                    track_lines.append(line)
            
            # If no <br> tags found, try to split the text by numbers with a period
            if len(track_lines) <= 1:
                for line in re.split(r'\s*\d+\.\s+', tracklist_text):
                    line = line.strip()
                    if line and not line.startswith('Total Time'):
                        track_lines.append(line)
            
            # Process each track
            for i, line in enumerate(track_lines):
                # Skip total time line
                if 'Total Time' in line:
                    continue
                    
                # Try to extract track number, title, and duration
                track_info = {}
                
                # If line starts with a number, it's probably a track number
                num_match = re.match(r'(\d+)\.\s*(.*)', line)
                if num_match:
                    track_info['number'] = int(num_match.group(1))
                    line = num_match.group(2).strip()
                else:
                    # Default to track position in list + 1
                    track_info['number'] = i + 1
                
                # Try to extract duration in parentheses from the end
                duration_match = re.search(r'\((\d+:\d+)\)$', line)
                if duration_match:
                    track_info['duration'] = duration_match.group(1)
                    line = re.sub(r'\(\d+:\d+\)$', '', line).strip()
                
                # What remains should be the track title
                track_info['title'] = line
                
                # Only add tracks with at least a title
                if track_info['title']:
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error extracting tracklist: {e}")
            return tracks
    
    def _extract_album_title_from_reviews(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract album title from reviews page."""
        # First approach: h1 element
        h1_elements = soup.find_all('h1')
        if (h1_elements and len(h1_elements) > 0):
            return self._extract_text(h1_elements[0])
            
        # Second approach: meta title
        title_meta = soup.select_one('meta[property="og:title"]')
        if title_meta and title_meta.get('content'):
            title_content = title_meta.get('content')
            title_match = re.match(r'(.+?)\s*-\s*(.+?)\s*\(', title_content)
            if title_match:
                return title_match.group(2).strip()
        
        return None
    
    def _extract_artist_from_reviews(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract artist name from reviews page."""
        # First approach: h2 with link to artist page
        artist_link = soup.select_one('h2 a[href*="artist.asp"]')
        if artist_link:
            return self._extract_text(artist_link)
            
        # Second approach: meta title
        title_meta = soup.select_one('meta[property="og:title"]')
        if title_meta and title_meta.get('content'):
            title_content = title_meta.get('content')
            title_match = re.match(r'(.+?)\s*-\s*(.+?)\s*\(', title_content)
            if title_match:
                return title_match.group(1).strip()
                
        return None
    
    def _extract_reviews(self, soup: BeautifulSoup, max_reviews: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """Extract individual reviews from reviews page."""
        review_count = 0
        # First try with common review class
        review_items = soup.select('.reviewtext, .review-box')
        
        if not review_items:
            # Try alternative approach looking for reviews section
            reviews_section = None
            for h2_tag in soup.find_all('h2'):
                if 'reviews' in self._extract_text(h2_tag).lower():
                    reviews_section = h2_tag.find_next('div')
                    if reviews_section:
                        review_items = reviews_section.select('div[class*="review"]')
                        
        for review in review_items:
            try:
                if max_reviews and review_count >= max_reviews:
                    break
                    
                review_info = {}
                
                # Extract reviewer name
                username_elem = review.select_one('.username, .user, .author')
                if username_elem:
                    review_info['author'] = self._extract_text(username_elem)
                
                # Extract review date
                date_elem = review.select_one('.reviewdate, .date')
                if date_elem:
                    review_info['date'] = self._extract_text(date_elem)
                
                # Extract rating
                rating_elem = review.select_one('.reviewrating, .rating')
                if rating_elem:
                    rating_text = self._extract_text(rating_elem)
                    if rating_text:
                        # Try to extract numeric rating
                        match = re.search(r'([\d.]+)', rating_text)
                        if match:
                            try:
                                review_info['rating'] = float(match.group(1))
                            except ValueError:
                                pass
                
                # Extract review text
                text_elem = review.select_one('.reviewcomment, .content, .text')
                if text_elem:
                    review_info['text'] = self._extract_text(text_elem)
                
                # Only yield reviews with text or at least a rating
                if 'text' in review_info or 'rating' in review_info:
                    yield review_info
                    review_count += 1
                    
            except Exception as e:
                logger.warning(f"Error parsing review: {e}")
    
    def _extract_text(self, element: Optional[Tag]) -> Optional[str]:
        """Helper method to safely extract and clean text from a BS4 element."""
        if not element:
            return None
            
        # First try to get direct text content preserving Unicode characters
        text = ''.join(t for t in element.stripped_strings)
        if not text:
            # Fallback to regular get_text() if no direct strings found
            text = element.get_text(strip=True)
            
        if not text:
            return None
            
        # Normalize Unicode characters (e.g., convert different forms of dashes, quotes)
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        
        # Clean up whitespace while preserving Unicode characters
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Handle HTML entities that might not be decoded
        from html import unescape
        text = unescape(text)
        
        return text
    
    def _extract_year(self, element: Tag) -> Optional[str]:
        """Extract year from an element containing year information."""
        if not element:
            return None
            
        text = self._extract_text(element)
        if not text:
            return None
            
        # Try to find a year in the text
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match:
            return year_match.group(0)
            
        return None

    def _find_band_members(self, soup: BeautifulSoup) -> List<Dict[str, Any]]:
        """Extract band member information from the artist page."""
        members = []
        try:
            # Method 1: Look for dedicated members section with structured HTML
            member_sections = soup.select('.band-members, .members, .lineup, .artist-members, .band-lineup')
            for section in member_sections:
                for member in section.find_all(['div', 'tr', 'li'], class_=['member', 'musician', 'band-member']):
                    try:
                        # Try multiple selectors for name and role
                        name_elem = member.select_one('.name, .member-name, .musician-name, strong')
                        role_elem = member.select_one('.role, .member-role, .musician-role, em, .instrument')
                        
                        if name_elem:
                            member_info = {
                                'name': self._extract_text(name_elem),
                                'role': self._extract_text(role_elem) if role_elem else None
                            }
                            
                            # Only add if we haven't seen this exact combination before
                            if not any(m['name'] == member_info['name'] and m['role'] == member_info['role'] for m in members):
                                members.append(member_info)
                                
                    except Exception as e:
                        logger.warning(f"Error processing band member: {e}")
            
            # Method 2: Look for lineup section with text content
            if not members:
                # Look for common headers that introduce member listings
                for header in soup.find_all(['strong', 'h2', 'h3', 'h4']):
                    header_text = self._extract_text(header)
                    if header_text and re.search(r'(?:current\s+)?(?:line.?up|members|musicians|band\s+members)', header_text, re.I):
                        # Get the next element that might contain member info
                        content = header.find_next(['p', 'div', 'ul'])
                        if content:
                            # Split text by common separators
                            lines = []
                            
                            # First try to get list items if it's a ul
                            if (content.name == 'ul'):
                                lines = [self._extract_text(li) for li in content.find_all('li')]
                            else:
                                # Split by newlines and bullet points
                                text = self._extract_text(content)
                                if text:
                                    lines = [l.strip() for l in re.split(r'[\n\r]+|(?:^|\s)[-•*](?:\s|$)', text) if l.strip()]
                            
                            for line in lines:
                                # Skip headers or empty lines
                                if not line or re.search(r'line.?up|members|musicians|albums|tracks', line, re.I):
                                    continue
                                
                                # Try various formats for member entries
                                member_info = None
                                
                                # Format: "Name - Role" or "Role: Name" or "Name (Role)"
                                for pattern in [
                                    r'^(.+?)\s*[-–:](?:\s+)?(.+)$',  # Name - Role or Role: Name
                                    r'^(.+?)\s*\((.+?)\)$',          # Name (Role)
                                    r'^([^/]+)/\s*(.+)$',            # Name / Role
                                    r'^(.+?)\s+\|\s+(.+)$'           # Name | Role
                                ]:
                                    match = re.match(pattern, line)
                                    if match:
                                        part1, part2 = match.groups()
                                        # Determine which part is name/role based on common role keywords
                                        role_keywords = {
                                            'vocals', 'guitar', 'bass', 'drums', 'keyboard', 'piano',
                                            'percussion', 'flute', 'violin', 'cello', 'sax', 'trumpet',
                                            'backing', 'lead', 'rhythm'
                                        }
                                        
                                        part1_has_role = any(kw in part1.lower() for kw in role_keywords)
                                        part2_has_role = any(kw in part2.lower() for kw in role_keywords)
                                        
                                        if part1_has_role:
                                            member_info = {'name': part2.strip(), 'role': part1.strip()}
                                        elif part2_has_role:
                                            member_info = {'name': part1.strip(), 'role': part2.strip()}
                                        else:
                                            # If we can't determine by keywords, assume Name - Role format
                                            member_info = {'name': part1.strip(), 'role': part2.strip()}
                                        
                                        break
                                
                                # If no pattern matched but line looks like a name
                                if not member_info and not any(kw in line.lower() for kw in ['featuring', 'guest', 'additional']):
                                    member_info = {'name': line.strip(), 'role': None}
                                
                                if member_info:
                                    # Only add if we haven't seen this exact combination before
                                    if not any(m['name'] == member_info['name'] and m['role'] == member_info['role'] for m in members):
                                        members.append(member_info)
            
            # Method 3: Look for member info in tables
            if not members:
                for table in soup.find_all('table', class_=['members', 'lineup', 'band-members']):
                    for row in table.find_all('tr')[1:]:  # Skip header row
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            member_info = {
                                'name': self._extract_text(cells[0]),
                                'role': self._extract_text(cells[1])
                            }
                            if member_info['name'] and not any(m['name'] == member_info['name'] and m['role'] == member_info['role'] for m in members):
                                members.append(member_info)
            
            # Method 4: Look for member info in paragraphs with strong/em tags
            if not members:
                for p in soup.find_all('p'):
                    strong_tags = p.find_all('strong')
                    em_tags = p.find_all('em')
                    if strong_tags and em_tags:
                        for s, e in zip(strong_tags, em_tags):
                            member_info = {
                                'name': self._extract_text(s),
                                'role': self._extract_text(e)
                            }
                            if member_info['name'] and not any(m['name'] == member_info['name'] and m['role'] == member_info['role'] for m in members):
                                members.append(member_info)
            
        except Exception as e:
            logger.error(f"Error finding band members: {e}")
            
        return members

    def get_album_details(self, album_url: str) -> Dict:
        """Get detailed information about an album."""
        logger.info(f"Getting details for album at {album_url}")
        
        try:
            response = self.fetch_url(album_url)
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Validate that this is an album page
            album_header = soup.find('h1', class_=['album-title', 'albumname', 'album_name'])
            if not album_header:
                return {'error': f'Page at {album_url} does not appear to be an album page'}
            
            # Initialize album details
            details = {
                'url': album_url,
                'title': album_header.get_text(strip=True),
                'artist': '',
                'year': None,
                'genre': '',
                'type': '',
                'rating': None,
                'description': '',
                'tracks': [],
                'lineup': [],
                'reviews': []
            }
            
            # Get artist info
            artist_link = soup.find('h2').find('a', href=lambda h: h and 'artist.asp' in h)
            if artist_link:
                details['artist'] = artist_link.get_text(strip=True)
            
            # Get release year and type
            info_table = soup.find('table', class_='album-info')
            if info_table:
                for row in info_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'released' in label:
                            year_match = re.search(r'\b(19|20)\d{2}\b', value)
                            if year_match:
                                details['year'] = int(year_match.group())
                        elif 'type' in label:
                            details['type'] = value
                        elif 'style' in label or 'genre' in label:
                            details['genre'] = value
            
            # Get rating
            rating_elem = soup.find('span', class_=['album-rating', 'rating'])
            if rating_elem:
                try:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if rating_match:
                        details['rating'] = float(rating_match.group(1))
                except (ValueError, AttributeError):
                    pass
            
            # Get album description
            desc_elem = soup.find('div', class_=['album-description', 'description'])
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Get track listing
            tracks_table = soup.find('table', class_=['album-tracks', 'tracklist'])
            if tracks_table:
                for track_row in tracks_table.find_all('tr')[1:]:  # Skip header row
                    cells = track_row.find_all('td')
                    if len(cells) >= 2:
                        track = {
                            'number': cells[0].get_text(strip=True),
                            'title': cells[1].get_text(strip=True),
                            'duration': cells[2].get_text(strip=True) if len(cells) > 2 else None
                        }
                        details['tracks'].append(track)
            
            # Get lineup
            lineup_table = soup.find('table', class_=['album-lineup', 'lineup'])
            if lineup_table:
                for member_row in lineup_table.find_all('tr')[1:]:  # Skip header row
                    cells = member_row.find_all('td')
                    if len(cells) >= 2:
                        member = {
                            'name': cells[0].get_text(strip=True),
                            'instruments': cells[1].get_text(strip=True)
                        }
                        details['lineup'].append(member)
            
            # Validate the parsed data
            if not details['title'] or not details['artist']:
                return {'error': f'Failed to extract required album information from {album_url}'}
                
            logger.info(f"Successfully parsed album: {details['artist']} - {details['title']}")
            return details
            
        except Exception as e:
            error_msg = f"Error parsing album page {album_url}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}