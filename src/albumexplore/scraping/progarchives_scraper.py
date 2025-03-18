"""ProgArchives.com scraper with ethical rate limiting and caching."""
import logging
import time
import re
from pathlib import Path
import json
from datetime import datetime
import requests
from typing import Dict, List, Optional, Iterator
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Scraper for ProgArchives.com with caching and rate limiting."""
    
    BASE_URL = "https://www.progarchives.com"
    SUBGENRES = [
        "Symphonic-Prog", "Prog-Folk", "Heavy-Prog", "Prog-Rock",
        "Jazz-Rock-Fusion", "Eclectic-Prog", "Canterbury", "RIO-Avant",
        "Prog-Metal", "Tech-Death-Metal", "Post-Metal", "Space-Rock",
        "Psychedelic-Space-Rock", "Neo-Prog", "Post-Rock", "Math-Rock",
        "Crossover-Prog", "Proto-Prog", "Art-Rock", "Krautrock",
        "Zeuhl", "Progressive-Electronic"
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
                    url = f"{self.BASE_URL}/subgenre/{subgenre}/bands/{page}"
                    response = self._fetch_url(url)
                    
                    if 'error' in response:
                        break
                        
                    soup = BeautifulSoup(response['content'], 'html.parser')
                    band_table = soup.find('table', class_='bands_list')
                    
                    if not band_table:
                        break
                        
                    bands_on_page = []
                    for row in band_table.find_all('tr')[1:]:  # Skip header
                        try:
                            cols = row.find_all('td')
                            if len(cols) < 3:
                                continue
                                
                            link = cols[0].find('a')
                            if not link:
                                continue
                                
                            bands_on_page.append({
                                'name': link.text.strip(),
                                'url': f"{self.BASE_URL}{link['href']}",
                                'country': cols[1].text.strip(),
                                'subgenre': subgenre
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error parsing band row: {e}")
                            continue
                    
                    if self.random_sample:
                        import random
                        # Take first 5 and random 5
                        if len(bands_on_page) > 10:
                            selected = bands_on_page[:5]
                            selected.extend(random.sample(bands_on_page[5:], 5))
                            bands_on_page = selected
                    
                    for band in bands_on_page:
                        yield band
                        bands_found += 1
                        
                        if self.max_bands and bands_found >= self.max_bands:
                            return
                            
                    # Check for next page
                    if not soup.find('a', string='>'):
                        break
                        
                    page += 1
                    
            except Exception as e:
                logger.error(f"Error getting bands for {subgenre}: {e}")
                continue

    def get_band_details(self, url: str, use_cache: bool = True) -> Dict:
        """Get detailed information about a band."""
        try:
            response = self._fetch_url(url, use_cache)
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
                'albums': self._find_band_albums(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            return details
            
        except Exception as e:
            error_msg = f"Error getting band details from {url}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}

    def get_album_details(self, url: str, use_cache: bool = True) -> Dict:
        """Get detailed information about an album."""
        try:
            response = self._fetch_url(url, use_cache)
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
                'reviews': self._find_album_reviews(soup),
                'scraped_at': datetime.now().isoformat()
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