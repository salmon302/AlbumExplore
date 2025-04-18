"""ProgArchives.com scraper with ethical rate limiting and caching."""
import logging
import time
import re
import random
from pathlib import Path
import json
from datetime import datetime
import requests
from typing import Dict, List, Optional, Iterator
from bs4 import BeautifulSoup, NavigableString
import string
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Scraper for ProgArchives.com with caching and rate limiting."""
    
    BASE_URL = "https://www.progarchives.com"
    ALPHA_URL = f"{BASE_URL}/bands-alpha.asp"
    ARTIST_URL = f"{BASE_URL}/artist.asp"
    ALBUM_URL = f"{BASE_URL}/album.asp"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_bands: Optional[int] = None,
        random_sample: bool = False,
        min_request_interval: float = 10.0,
        max_retries: int = 3
    ):
        """Initialize scraper with optional limits and sampling strategy."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/progarchives")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_bands = max_bands
        self.random_sample = random_sample
        self.min_request_interval = min_request_interval
        self.max_retries = max_retries
        self._last_request_time = 0
        self.timeout = 30
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

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
        """Fetch URL with caching, rate limiting and retries."""
        if use_cache:
            cached = self._get_cached_response(url)
            if cached:
                return cached

        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                self._wait_for_rate_limit()
                
                # Follow redirects but keep track of final URL
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                
                # Check if we were redirected
                if response.url != url:
                    logger.warning(f"URL redirected from {url} to {response.url}")
                    
                # Check if we got an error page
                if "Error Message" in response.text or "404 Not Found" in response.text:
                    raise ValueError(f"Page returned error content: {url}")
                
                result = {
                    'content': response.text,
                    'status': response.status_code,
                    'final_url': response.url
                }
                
                if use_cache:
                    self._save_to_cache(url, result)
                return result
                
            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries < self.max_retries:
                    sleep_time = self.min_request_interval * (2 ** retries)  # Exponential backoff
                    logger.warning(f"Retry {retries}/{self.max_retries} for {url} after {sleep_time}s. Error: {last_error}")
                    time.sleep(sleep_time)

        error = f"Error fetching {url} after {self.max_retries} retries: {last_error}"
        logger.error(error)
        return {'error': error}

    def get_bands_all(self) -> Iterator[Dict]:
        """Get list of all bands using alphabetical listings."""
        bands_found = 0
        letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
        logger.info("Starting band collection...")
        
        if self.random_sample:
            random.shuffle(letters)
        
        for letter in letters:
            try:
                page = 1
                while True:
                    url = f"{self.ALPHA_URL}?letter={letter}"
                    if page > 1:
                        url += f"&page={page}"
                    
                    logger.info(f"Fetching {url}")
                    response = self._fetch_url(url)
                    
                    if 'error' in response:
                        logger.error(f"Error fetching {url}: {response['error']}")
                        break
                        
                    soup = BeautifulSoup(response['content'], 'html.parser')
                    grid_items = soup.find_all('div', class_='grid-item')
                    
                    if not grid_items:
                        logger.debug(f"No more bands found for letter {letter}")
                        break

                    # Process grid items in groups of 3 (name, genre, country)
                    bands_on_page = []
                    for i in range(0, len(grid_items), 3):
                        try:
                            if i + 2 >= len(grid_items):
                                break
                                
                            name_div = grid_items[i]
                            genre_div = grid_items[i + 1]
                            country_div = grid_items[i + 2]
                            
                            link = name_div.find('a')
                            if not link:
                                continue
                                
                            band_url = link['href']
                            if not band_url.startswith('http'):
                                band_url = f"{self.BASE_URL}/{band_url.lstrip('/')}"
                                
                            bands_on_page.append({
                                'name': link.text.strip(),
                                'url': band_url,
                                'genre': genre_div.text.strip(),
                                'country': country_div.text.strip()
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error parsing band entry: {e}")
                            continue
                    
                    logger.info(f"Found {len(bands_on_page)} bands on page {page} for letter {letter}")
                    
                    if self.random_sample:
                        if len(bands_on_page) > 10:
                            # Take first 5 and random 5 from rest for a good mix
                            selected = bands_on_page[:5]
                            selected.extend(random.sample(bands_on_page[5:], 5))
                            bands_on_page = selected
                    
                    for band in bands_on_page:
                        yield band
                        bands_found += 1
                        
                        if self.max_bands and bands_found >= self.max_bands:
                            logger.info(f"Reached max bands limit ({self.max_bands})")
                            return
                    
                    # Check for next page
                    next_page = soup.find('a', string='>')
                    if not next_page:
                        break
                        
                    page += 1
                    time.sleep(self.min_request_interval)  # Rate limiting between pages
                    
            except Exception as e:
                logger.error(f"Error getting bands for letter {letter}: {e}")
                continue
                
        logger.info(f"Band collection complete. Found {bands_found} total bands")

    def get_band_details(self, url: str, use_cache: bool = True) -> Dict:
        """Get detailed information about a band."""
        try:
            response = self._fetch_url(url, use_cache)
            if 'error' in response:
                return response
            
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract band name
            name = soup.find('h1')
            if not name:
                name = soup.find('h2')
                
            # Extract genre and country
            h2_info = soup.find('h2', style="margin:1px 0px;padding:0;color:#777;font-weight:normal;")
            genre = country = None
            if h2_info:
                info_parts = h2_info.text.split('•')
                if len(info_parts) >= 2:
                    genre = info_parts[0].strip()
                    country = info_parts[1].strip()
            
            # Find biography
            bio_div = soup.find('div', id='artist-biography')
            bio = ""
            if bio_div:
                bio_paras = bio_div.find_all('p')
                bio = "\n".join(p.text.strip() for p in bio_paras if p.text.strip())
                
            # Find albums
            discography = []
            
            # Each album type (studio, live, etc) is in its own table
            discography_tables = soup.find_all('table', class_='artist-discography-table')
            logger.debug(f"Found {len(discography_tables)} discography tables")
            
            for table in discography_tables:
                logger.debug(f"Processing discography table")
                
                # Find all album cells - each album is in its own td with class artist-discography-td
                album_cells = table.find_all('td', class_='artist-discography-td')
                
                for cell in album_cells:
                    try:
                        # Find the album link
                        album_link = cell.find('a')
                        if not album_link:
                            continue
                            
                        # Get URL
                        album_url = album_link.get('href')
                        if album_url and not album_url.startswith('http'):
                            album_url = f"{self.BASE_URL}/{album_url.lstrip('/')}"
                        
                        # Find title - it's in the strong tag
                        title = None
                        title_elem = cell.find('strong')
                        if title_elem:
                            title = title_elem.text.strip()
                        
                        if not title:
                            continue
                        
                        # Get year - find span with color:#777
                        year = None
                        year_span = cell.find('span', style=lambda x: x and 'color:#777' in x)
                        if year_span:
                            try:
                                year = int(year_span.text.strip())
                            except (ValueError, TypeError):
                                pass
                        
                        # Get rating if available
                        rating = None
                        rating_span = cell.find('span', style=lambda x: x and 'color:#C75D4F' in x)
                        if rating_span:
                            try:
                                rating = float(rating_span.text.strip())
                            except (ValueError, TypeError):
                                pass
                        
                        album = {
                            'title': title,
                            'url': album_url,
                            'year': year,
                            'rating': rating
                        }
                        discography.append(album)
                        logger.debug(f"Added album: {title} ({year}) - rating: {rating}")
                        
                    except Exception as e:
                        logger.warning(f"Error parsing album cell: {e}")
                        continue
            
            logger.debug(f"Found total of {len(discography)} albums")
            
            details = {
                'url': url,
                'name': name.text.strip() if name else None,
                'genre': genre,
                'country': country, 
                'biography': bio,
                'albums': discography,
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
            # Ensure URL has correct format
            if url.isdigit():
                url = f"{self.ALBUM_URL}?id={url}"
            elif not url.startswith('http'):
                url = urljoin(self.BASE_URL, url.lstrip('/'))
                
            response = self._fetch_url(url, use_cache)
            if 'error' in response:
                return response
                
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # First validate we're on an album page
            if not soup.select_one('h1.album-title, h1.albumname, h1.album_name'):
                error = f"Page at {response.get('final_url', url)} does not appear to be an album page"
                logger.error(error)
                return {'error': error}
            
            # Find tracklist section
            track_content = None
            for heading in soup.find_all(['strong', 'h3']):
                if re.search(r'tracks?\s*(?:list(?:ing)?)?', heading.get_text(), re.I):
                    track_content = heading.find_next('p')
                    break
                    
            # Find lineup section
            lineup_content = None
            for heading in soup.find_all(['strong', 'h3']):
                if re.search(r'line.?up|musicians', heading.get_text(), re.I):
                    lineup_content = heading.find_next('p')
                    break
            
            details = {
                'url': response.get('final_url', url),
                'title': self._find_album_title(soup),
                'artist': self._find_album_artist(soup),
                'year': self._find_album_year(soup),
                'rating': self._find_album_rating(soup),
                'genre': self._find_album_genre(soup),
                'record_type': self._find_album_type(soup),
                'tracks': self._extract_tracks(track_content),
                'lineup': self._extract_lineup(lineup_content),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            if not details['title'] or not details['artist']:
                error = f"Missing required fields for {url} - title: {details['title']}, artist: {details['artist']}"
                logger.error(error)
                return {'error': error}
                
            return details
            
        except Exception as e:
            error = f"Error getting album details from {url}: {str(e)}"
            logger.error(error)
            return {'error': error}

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
        # Try main heading first
        title_h1 = soup.select_one('h1.album-title, h1.albumname, h1.album_name')
        if (title_h1):
            return title_h1.get_text(strip=True)
            
        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            content = meta_title.get('content', '')
            # Format is usually "Artist - Album (Year)"
            match = re.match(r'.+?\s*-\s*(.+?)\s*\(', content)
            if match:
                return match.group(1).strip()
        
        return None

    def _find_album_artist(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album artist."""
        # Try artist link in header
        artist_link = soup.select_one('h2 a[href*="artist.asp"], .artistname a')
        if artist_link:
            return artist_link.get_text(strip=True)
            
        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            content = meta_title.get('content', '')
            match = re.match(r'(.+?)\s*-\s*.+?\s*\(', content)
            if match:
                return match.group(1).strip()
                
        return None

    def _find_album_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Find album release year."""
        # Try release info section
        release_row = soup.find('td', string=re.compile(r'Released:', re.I))
        if release_row:
            value = release_row.find_next_sibling('td')
            if value:
                year_match = re.search(r'\b(19|20)\d{2}\b', value.get_text())
                if year_match:
                    return int(year_match.group())
                    
        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            content = meta_title.get('content', '')
            year_match = re.search(r'\((\d{4})\)', content)
            if year_match:
                return int(year_match.group(1))
                
        return None

    def _find_album_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Find album rating."""
        # Try rating span
        rating_span = soup.select_one('span.rating, span.album-rating')
        if rating_span:
            try:
                return float(rating_span.get_text(strip=True))
            except (ValueError, TypeError):
                pass
                
        # Try rating in text
        rating_text = soup.find(string=re.compile(r'Rating:\s*(\d+\.?\d*)/5'))
        if rating_text:
            try:
                rating_match = re.search(r'(\d+\.?\d*)/5', rating_text)
                if rating_match:
                    return float(rating_match.group(1))
            except (ValueError, TypeError):
                pass
                
        return None

    def _find_album_genre(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album genre."""
        # Try genre row
        genre_row = soup.find('td', string=re.compile(r'Genre:', re.I))
        if genre_row:
            value = genre_row.find_next_sibling('td')
            if value:
                return value.get_text(strip=True)
                
        # Try genre heading
        genre_h2 = soup.find('h2', class_='genre')
        if genre_h2:
            return genre_h2.get_text(strip=True)
            
        return None

    def _find_album_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album type (Studio, Live, etc)."""
        type_row = soup.find('td', string=re.compile(r'Type:', re.I))
        if type_row:
            value = type_row.find_next_sibling('td')
            if value:
                album_type = value.get_text(strip=True)
                # Normalize album types
                type_map = {
                    'studio': 'Studio Album',
                    'live': 'Live Album',
                    'compilation': 'Compilation',
                    'ep': 'EP',
                    'single': 'Single'
                }
                lower_type = album_type.lower()
                for key, normalized in type_map.items():
                    if key in lower_type:
                        return normalized
                return album_type
        return None

    def _extract_tracks(self, track_content: BeautifulSoup) -> List[Dict]:
        """Extract track information from track listing section."""
        tracks = []
        seen_tracks = set()  # Avoid duplicates
        
        if not track_content:
            return tracks

        # Get text content, preserving line breaks
        content = []
        for elem in track_content.contents:
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                if text:
                    content.append(text)
            elif elem.name == 'br':
                content.append('\n')
            else:
                text = elem.get_text().strip()
                if text:
                    content.append(text)
                    
        # Join and split by line breaks
        track_lines = ''.join(content).split('\n')
        
        # Process each line
        track_number = 1
        for line in track_lines:
            line = line.strip()
            if not line or 'total time' in line.lower():
                continue
                
            # Try to parse track info
            track_match = re.match(r'^(?:(\d+)[\.)\s-]+)?(.+?)(?:\s*[-(\s]+(\d+:\d+))?$', line)
            if track_match:
                number = int(track_match.group(1)) if track_match.group(1) else track_number
                title = track_match.group(2).strip()
                duration = track_match.group(3)
                
                # Skip if we've seen this track before
                track_key = f"{number}-{title}"
                if track_key in seen_tracks:
                    continue
                    
                if title and not title.startswith(('CD', '*', '-')):  # Skip CD markers and notes
                    tracks.append({
                        'number': number,
                        'title': title,
                        'duration': duration.strip() if duration else None
                    })
                    seen_tracks.add(track_key)
                    track_number = number + 1
                    
        return tracks

    def _extract_lineup(self, lineup_content: BeautifulSoup) -> List[Dict]:
        """Extract lineup information from musicians section."""
        lineup = []
        seen_members = set()
        
        if not lineup_content:
            return lineup
            
        # Split content by line breaks and process each line
        for line in lineup_content.get_text().split('\n'):
            line = line.strip()
            if not line or line.startswith(('-', '*', '•')):
                continue
                
            # Try multiple formats for parsing musician entries
            member_match = None
            for pattern in [
                r'^(.+?)\s*[-:]\s*(.+)$',  # Name - Role or Role: Name
                r'^(.+?)\s*\((.+?)\)$',    # Name (Role)
                r'^([^/]+)/\s*(.+)$'       # Name / Role
            ]:
                match = re.match(pattern, line)
                if match:
                    member_match = match
                    break
                    
            if member_match:
                part1, part2 = member_match.groups()
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
                    
                # Clean up and normalize
                name = self._clean_text(name)
                role = self._clean_text(role)
                
                if name and role and name not in seen_members:
                    lineup.append({
                        'name': name,
                        'role': role
                    })
                    seen_members.add(name)
                    
        return lineup

    def get_album_details(self, url: str, use_cache: bool = True) -> Dict:
        """Get detailed information about an album."""
        try:
            # Ensure URL has correct format
            if url.isdigit():
                url = f"{self.ALBUM_URL}?id={url}"
            elif not url.startswith('http'):
                url = urljoin(self.BASE_URL, url.lstrip('/'))
                
            response = self._fetch_url(url, use_cache)
            if 'error' in response:
                return response
                
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # First validate we're on an album page
            if not soup.select_one('h1.album-title, h1.albumname, h1.album_name'):
                error = f"Page at {response.get('final_url', url)} does not appear to be an album page"
                logger.error(error)
                return {'error': error}
            
            # Find tracklist section
            track_content = None
            for heading in soup.find_all(['strong', 'h3']):
                if re.search(r'tracks?\s*(?:list(?:ing)?)?', heading.get_text(), re.I):
                    track_content = heading.find_next('p')
                    break
                    
            # Find lineup section
            lineup_content = None
            for heading in soup.find_all(['strong', 'h3']):
                if re.search(r'line.?up|musicians', heading.get_text(), re.I):
                    lineup_content = heading.find_next('p')
                    break
            
            details = {
                'url': response.get('final_url', url),
                'title': self._find_album_title(soup),
                'artist': self._find_album_artist(soup),
                'year': self._find_album_year(soup),
                'rating': self._find_album_rating(soup),
                'genre': self._find_album_genre(soup),
                'record_type': self._find_album_type(soup),
                'tracks': self._extract_tracks(track_content),
                'lineup': self._extract_lineup(lineup_content),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            if not details['title'] or not details['artist']:
                error = f"Missing required fields for {url} - title: {details['title']}, artist: {details['artist']}"
                logger.error(error)
                return {'error': error}
                
            return details
            
        except Exception as e:
            error = f"Error getting album details from {url}: {str(e)}"
            logger.error(error)
            return {'error': error}

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean text content by removing extra whitespace and HTML."""
        if not text:
            return ""
        # Remove HTML tags and normalize whitespace
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _find_album_description(self, soup: BeautifulSoup) -> str:
        """Find album description."""
        desc_div = soup.find('div', class_='album_description')
        return desc_div.text.strip() if desc_div else ""

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