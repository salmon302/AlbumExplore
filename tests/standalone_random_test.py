"""Standalone test script with embedded scraper code."""
import logging
import time
import re
from pathlib import Path
import json
from datetime import datetime
import random
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Iterator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('random_discographies_test.log')
    ]
)
logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Scraper for ProgArchives.com with caching and rate limiting."""
    
    BASE_URL = "https://www.progarchives.com"
    SUBGENRES = [
        "symphonic prog",
        "prog folk",
        "heavy prog",
        "crossover prog",
        "jazz rock fusion",
        "eclectic prog",
        "canterbury scene",
        "rio/avant-prog",
        "progressive metal",
        "technical death metal",
        "post-metal",
        "space rock"
    ]

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_bands: Optional[int] = None,
        random_sample: bool = False,
        min_request_interval: float = 5.0
    ):
        """Initialize scraper with optional limits and sampling strategy."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/progarchives")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_bands = max_bands
        self.random_sample = random_sample
        self.min_request_interval = min_request_interval
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _get_cached_response(self, url: str) -> Optional[Dict]:
        """Get cached response for URL."""
        cache_file = self.cache_dir / f"{hash(url)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {url}: {e}")
        return None

    def _save_to_cache(self, url: str, data: Dict):
        """Save response to cache."""
        cache_file = self.cache_dir / f"{hash(url)}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache response for {url}: {e}")

    def _fetch_url(self, url: str, use_cache: bool = True) -> Dict:
        """Fetch URL with caching and rate limiting."""
        if use_cache:
            cached = self._get_cached_response(url)
            if cached:
                return cached

        self._wait_for_rate_limit()
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = {
                'url': url,
                'content': response.text,
                'timestamp': datetime.now().isoformat()
            }
            
            if use_cache:
                self._save_to_cache(url, data)
                
            return data
            
        except Exception as e:
            error_msg = f"Failed to fetch {url}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}

    def get_bands_all(self) -> Iterator[Dict]:
        """Get list of all bands, optionally using sampling strategy."""
        bands_found = 0
        
        for subgenre in self.SUBGENRES:
            try:
                page = 1
                while True:
                    # Convert subgenre to URL-friendly format
                    subgenre_url = subgenre.replace(" ", "+").replace("/", "%2F")
                    url = f"{self.BASE_URL}/bands.asp?style={subgenre_url}&submit=Go&page={page}"
                    response = self._fetch_url(url)
                    
                    if 'error' in response:
                        break
                        
                    soup = BeautifulSoup(response['content'], 'html.parser')
                    band_table = soup.find('table', {'style': 'border:1px solid #a0a0a0'})
                    
                    if not band_table:
                        break
                        
                    bands_on_page = []
                    for row in band_table.find_all('tr')[1:]:  # Skip header
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 3:
                                continue
                                
                            link = cells[0].find('a')
                            if not link:
                                continue
                                
                            band_url = link['href']
                            if not band_url.startswith('http'):
                                band_url = f"{self.BASE_URL}/{band_url}"
                                
                            bands_on_page.append({
                                'name': link.text.strip(),
                                'url': band_url,
                                'country': cells[1].text.strip() if len(cells) > 1 else None,
                                'subgenre': subgenre
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error parsing band row: {e}")
                            continue
                    
                    if self.random_sample:
                        # Take first 5 and random 5 if more than 10 bands
                        if len(bands_on_page) > 10:
                            selected = bands_on_page[:5]
                            selected.extend(random.sample(bands_on_page[5:], 5))
                            bands_on_page = selected
                    
                    for band in bands_on_page:
                        yield band
                        bands_found += 1
                        
                        if self.max_bands and bands_found >= self.max_bands:
                            return
                            
                    # Check for next page link
                    next_page = soup.find('a', string='>')
                    if not next_page:
                        break
                        
                    page += 1
                    
            except Exception as e:
                logger.error(f"Error getting bands for {subgenre}: {e}")
                continue

    def get_band_details(self, url: str) -> Dict:
        """Get detailed information about a band."""
        try:
            response = self._fetch_url(url)
            if 'error' in response:
                return response
            
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract band info
            details = {
                'url': url,
                'name': self._find_band_name(soup),
                'description': self._find_band_description(soup),
                'country': self._find_band_country(soup),
                'genre': self._find_band_genre(soup),
                'members': self._find_band_members(soup),
                'albums': self._find_band_albums(soup)
            }
            
            return details
            
        except Exception as e:
            error_msg = f"Error getting band details from {url}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}

    def get_album_details(self, url: str) -> Dict:
        """Get detailed information about an album."""
        try:
            response = self._fetch_url(url)
            if 'error' in response:
                return response
            
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            details = {
                'url': url,
                'title': self._find_album_title(soup),
                'artist': self._find_album_artist(soup),
                'year': self._find_album_year(soup),
                'rating': self._find_album_rating(soup),
                'genre': self._find_album_genre(soup),
                'record_type': self._find_album_type(soup),
                'description': self._find_album_description(soup),
                'lineup': self._find_album_lineup(soup),
                'tracks': self._find_album_tracks(soup),
                'reviews': self._find_album_reviews(soup)
            }
            
            return details
            
        except Exception as e:
            error_msg = f"Error getting album details from {url}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}

    def _find_band_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Find band name."""
        name_elem = soup.find('h1', class_='band_name') or \
                   soup.find('h1', class_='artist_name')
        return name_elem.text.strip() if name_elem else None

    def _find_band_description(self, soup: BeautifulSoup) -> str:
        """Find band description/biography."""
        desc_div = soup.find('div', class_='band_description') or \
                  soup.find('div', class_='artist_description')
        return desc_div.text.strip() if desc_div else ""

    def _find_band_country(self, soup: BeautifulSoup) -> Optional[str]:
        """Find band's country."""
        country_elem = soup.find('td', string=re.compile(r'Country:'))
        if country_elem:
            value = country_elem.find_next_sibling('td')
            return value.text.strip() if value else None
        return None

    def _find_band_genre(self, soup: BeautifulSoup) -> Optional[str]:
        """Find band's primary genre."""
        genre_elem = soup.find('td', string=re.compile(r'Genre:'))
        if genre_elem:
            value = genre_elem.find_next_sibling('td')
            return value.text.strip() if value else None
        return None

    def _find_band_members(self, soup: BeautifulSoup) -> List[Dict]:
        """Find band member information."""
        members = []
        member_section = soup.find('div', class_='members')
        if member_section:
            for member in member_section.find_all('div', class_='member'):
                try:
                    name = member.find('span', class_='name')
                    role = member.find('span', class_='role')
                    if name:
                        members.append({
                            'name': name.text.strip(),
                            'role': role.text.strip() if role else None
                        })
                except Exception as e:
                    logger.warning(f"Error parsing member: {e}")
        return members

    def _find_band_albums(self, soup: BeautifulSoup) -> List[Dict]:
        """Find band's albums."""
        albums = []
        discography = soup.find('div', class_='discography')
        if discography:
            for album in discography.find_all('div', class_='album'):
                try:
                    link = album.find('a')
                    if link:
                        albums.append({
                            'title': link.text.strip(),
                            'url': f"{self.BASE_URL}{link['href']}"
                        })
                except Exception as e:
                    logger.warning(f"Error parsing album: {e}")
        return albums

    def _find_album_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album title."""
        title_elem = soup.find('h1', class_='album_name')
        return title_elem.text.strip() if title_elem else None

    def _find_album_artist(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album artist."""
        artist_elem = soup.find('a', href=re.compile(r'/artist\.asp'))
        return artist_elem.text.strip() if artist_elem else None

    def _find_album_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Find album release year."""
        year_elem = soup.find('td', string=re.compile(r'Released:'))
        if year_elem:
            value = year_elem.find_next_sibling('td')
            if value:
                year_match = re.search(r'(19|20)\d{2}', value.text)
                if year_match:
                    return int(year_match.group())
        return None

    def _find_album_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Find album rating."""
        rating_elem = soup.find('span', class_='rating')
        if rating_elem:
            try:
                return float(rating_elem.text)
            except ValueError:
                pass
        return None

    def _find_album_genre(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album genre."""
        genre_elem = soup.find('td', string=re.compile(r'Genre:'))
        if genre_elem:
            value = genre_elem.find_next_sibling('td')
            return value.text.strip() if value else None
        return None

    def _find_album_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album type (Studio, Live, etc)."""
        type_elem = soup.find('td', string=re.compile(r'Type:'))
        if type_elem:
            value = type_elem.find_next_sibling('td')
            return value.text.strip() if value else None
        return None

    def _find_album_description(self, soup: BeautifulSoup) -> str:
        """Find album description."""
        desc_div = soup.find('div', class_='album_description')
        return desc_div.text.strip() if desc_div else ""

    def _find_album_lineup(self, soup: BeautifulSoup) -> List[Dict]:
        """Find album lineup information."""
        lineup = []
        lineup_section = soup.find('div', class_='album_lineup')
        if lineup_section:
            for member in lineup_section.find_all('div', class_='member'):
                try:
                    name = member.find('span', class_='name')
                    role = member.find('span', class_='role')
                    if name:
                        lineup.append({
                            'name': name.text.strip(),
                            'role': role.text.strip() if role else None
                        })
                except Exception as e:
                    logger.warning(f"Error parsing lineup member: {e}")
        return lineup

    def _find_album_tracks(self, soup: BeautifulSoup) -> List[Dict]:
        """Find album track listing."""
        tracks = []
        tracks_section = soup.find('div', class_='tracklist')
        if tracks_section:
            for track in tracks_section.find_all('div', class_='track'):
                try:
                    number = track.find('span', class_='number')
                    title = track.find('span', class_='title')
                    duration = track.find('span', class_='duration')
                    if title:
                        tracks.append({
                            'number': int(number.text) if number else None,
                            'title': title.text.strip(),
                            'duration': duration.text.strip() if duration else None
                        })
                except Exception as e:
                    logger.warning(f"Error parsing track: {e}")
        return tracks

    def _find_album_reviews(self, soup: BeautifulSoup) -> List[Dict]:
        """Find album reviews."""
        reviews = []
        reviews_section = soup.find('div', class_='reviews')
        if reviews_section:
            for review in reviews_section.find_all('div', class_='review'):
                try:
                    text = review.find('div', class_='text')
                    rating = review.find('span', class_='rating')
                    author = review.find('span', class_='author')
                    date = review.find('span', class_='date')
                    if text:
                        reviews.append({
                            'text': text.text.strip(),
                            'rating': float(rating.text) if rating else None,
                            'author': author.text.strip() if author else None,
                            'date': date.text.strip() if date else None
                        })
                except Exception as e:
                    logger.warning(f"Error parsing review: {e}")
        return reviews

def validate_album_data(album: Dict) -> List[str]:
    """Validate album data structure and content."""
    errors = []
    
    # Required fields
    required_fields = ['title', 'artist', 'url']
    for field in required_fields:
        if field not in album:
            errors.append(f"Missing required field: {field}")
            
    # Optional but expected fields
    expected_fields = ['year', 'rating', 'genre', 'record_type', 'description']
    for field in expected_fields:
        if field not in album:
            logger.warning(f"Missing expected field: {field}")
            
    # Validate tracks if present
    if 'tracks' in album:
        for i, track in enumerate(album['tracks']):
            if not isinstance(track, dict):
                errors.append(f"Invalid track format at index {i}")
                continue
            if 'title' not in track:
                errors.append(f"Track at index {i} missing title")
            if 'number' in track and not isinstance(track['number'], (int, type(None))):
                errors.append(f"Invalid track number format at index {i}")
                
    # Validate lineup if present
    if 'lineup' in album:
        for i, member in enumerate(album['lineup']):
            if not isinstance(member, dict):
                errors.append(f"Invalid lineup member format at index {i}")
                continue
            if 'name' not in member:
                errors.append(f"Lineup member at index {i} missing name")
                
    return errors

def validate_band_data(band: Dict) -> List[str]:
    """Validate band data structure and content."""
    errors = []
    
    # Required fields
    required_fields = ['name', 'url']
    for field in required_fields:
        if field not in band:
            errors.append(f"Missing required field: {field}")
            
    # Optional but expected fields
    expected_fields = ['country', 'genre', 'description']
    for field in expected_fields:
        if field not in band:
            logger.warning(f"Missing expected field: {field}")
            
    # Validate albums list
    if 'albums' in band:
        if not isinstance(band['albums'], list):
            errors.append("Albums field is not a list")
        else:
            for i, album in enumerate(band['albums']):
                album_errors = validate_album_data(album)
                if album_errors:
                    errors.extend([f"Album {i} ({album.get('title', 'Unknown')}): {err}" 
                                 for err in album_errors])
                    
    return errors

def main():
    """Run random discography tests."""
    # Configuration
    test_bands = 5  # Number of random bands to test
    error_threshold = 0.2  # Maximum acceptable error rate (20%)
    min_albums = 3  # Minimum albums a band should have
    
    # Initialize scraper
    cache_dir = Path("cache/progarchives/test_random")
    cache_dir.mkdir(parents=True, exist_ok=True)
    scraper = ProgArchivesScraper(
        cache_dir=cache_dir,
        max_bands=10,  # Get a few extra to account for filtering
        random_sample=True  # Enable random sampling
    )
    
    # Statistics tracking
    stats = {
        'total_bands': 0,
        'total_albums': 0,
        'successful_bands': 0,
        'successful_albums': 0,
        'failed_bands': 0,
        'failed_albums': 0,
        'band_errors': [],
        'album_errors': [],
        'start_time': datetime.now().isoformat()
    }
    
    try:
        # Get list of bands
        logger.info("Getting band list...")
        all_bands = list(scraper.get_bands_all())
        logger.info(f"Found {len(all_bands)} total bands")
        
        # Filter bands with minimum albums and shuffle
        filtered_bands = [band for band in all_bands]  # We'll check album count later
        random.shuffle(filtered_bands)
        
        test_data = []
        processed_urls = set()
        
        # Process random selection
        for band in filtered_bands:
            if stats['total_bands'] >= test_bands:
                break
                
            stats['total_bands'] += 1
            band_data = {'name': band['name'], 'url': band['url'], 'errors': []}
            
            try:
                logger.info(f"\nTesting band: {band['name']}")
                
                # Get band details
                details = scraper.get_band_details(band['url'])
                if 'error' in details:
                    raise Exception(f"Failed to get band details: {details['error']}")
                
                # Skip if not enough albums
                if len(details.get('albums', [])) < min_albums:
                    logger.info(f"Skipping {band['name']} - only {len(details.get('albums', []))} albums")
                    stats['total_bands'] -= 1  # Don't count in stats
                    continue
                
                # Validate band data
                band_errors = validate_band_data(details)
                if band_errors:
                    band_data['errors'].extend(band_errors)
                    stats['band_errors'].extend(band_errors)
                
                # Track albums
                albums = []
                for album in details.get('albums', []):
                    stats['total_albums'] += 1
                    
                    try:
                        if album['url'] in processed_urls:
                            logger.warning(f"Skipping duplicate album URL: {album['url']}")
                            continue
                        processed_urls.add(album['url'])
                        
                        logger.info(f"Testing album: {album.get('title', 'Unknown')}")
                        
                        # Get album details
                        album_details = scraper.get_album_details(album['url'])
                        if 'error' in album_details:
                            raise Exception(f"Failed to get album details: {album_details['error']}")
                            
                        # Validate album data
                        album_errors = validate_album_data(album_details)
                        if album_errors:
                            stats['album_errors'].extend(album_errors)
                            album_details['errors'] = album_errors
                        
                        albums.append(album_details)
                        stats['successful_albums'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing album: {str(e)}")
                        stats['failed_albums'] += 1
                        albums.append({
                            'url': album.get('url', 'unknown'),
                            'error': str(e)
                        })
                
                band_data['albums'] = albums
                band_data['albums_total'] = len(details.get('albums', []))
                band_data['albums_processed'] = len(albums)
                
                test_data.append(band_data)
                stats['successful_bands'] += 1
                
            except Exception as e:
                logger.error(f"Error processing band {band['name']}: {str(e)}")
                stats['failed_bands'] += 1
                band_data['error'] = str(e)
                test_data.append(band_data)
        
        # Calculate error rates
        band_error_rate = stats['failed_bands'] / stats['total_bands'] if stats['total_bands'] > 0 else 1
        album_error_rate = stats['failed_albums'] / stats['total_albums'] if stats['total_albums'] > 0 else 1
        
        # Save test results
        results = {
            'test_date': datetime.now().isoformat(),
            'duration': str(datetime.now() - datetime.fromisoformat(stats['start_time'])),
            'configuration': {
                'test_bands': test_bands,
                'min_albums': min_albums,
                'error_threshold': error_threshold
            },
            'statistics': {
                'bands_total': stats['total_bands'],
                'bands_successful': stats['successful_bands'],
                'bands_failed': stats['failed_bands'],
                'band_error_rate': band_error_rate,
                'albums_total': stats['total_albums'],
                'albums_successful': stats['successful_albums'],
                'albums_failed': stats['failed_albums'],
                'album_error_rate': album_error_rate
            },
            'band_errors': stats['band_errors'],
            'album_errors': stats['album_errors'],
            'test_data': test_data
        }
        
        output_file = Path(f"test_results_random_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        # Log summary
        logger.info("\nTest Summary:")
        logger.info(f"Total bands processed: {stats['total_bands']}")
        logger.info(f"Successful bands: {stats['successful_bands']}")
        logger.info(f"Failed bands: {stats['failed_bands']}")
        logger.info(f"Band error rate: {band_error_rate:.1%}")
        logger.info(f"Total albums processed: {stats['total_albums']}")
        logger.info(f"Successful albums: {stats['successful_albums']}")
        logger.info(f"Failed albums: {stats['failed_albums']}")
        logger.info(f"Album error rate: {album_error_rate:.1%}")
        logger.info(f"\nResults saved to: {output_file}")
        
        # Check error rates
        success = True
        if band_error_rate > error_threshold:
            logger.error(f"Band error rate {band_error_rate:.1%} exceeds threshold {error_threshold:.1%}")
            success = False
        if album_error_rate > error_threshold:
            logger.error(f"Album error rate {album_error_rate:.1%} exceeds threshold {error_threshold:.1%}")
            success = False
            
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())