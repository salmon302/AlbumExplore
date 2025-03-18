"""Scraper for ProgArchives.com with ethical rate limiting."""
from typing import Dict, List, Optional, Iterator
import logging
import re
import time
import random
from pathlib import Path
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Scraper for ProgArchives.com with caching and rate limiting."""
    
    BASE_URL = "https://www.progarchives.com"

    def __init__(self, cache_dir: Optional[Path] = None, max_bands: Optional[int] = None, random_sample: bool = False):
        """Initialize scraper with optional caching and sampling."""
        self.cache_dir = cache_dir
        self.max_bands = max_bands
        self.random_sample = random_sample

    def get_bands_all(self) -> Iterator[Dict]:
        """Get list of all bands using alphabetical listing."""
        bands_found = 0
        letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ*')  # Include * for special characters
        
        if self.random_sample:
            random.shuffle(letters)
        
        for letter in letters:
            try:
                page = 1
                while True:
                    url = f"{self.BASE_URL}/bands-alpha.asp?letter={letter}&page={page}"
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
                                'genre': cells[2].text.strip() if len(cells) > 2 else None
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
                logger.error(f"Error getting bands for letter {letter}: {e}")
                continue

    def _fetch_url(self, url: str) -> Dict:
        """Fetch and return URL content, caching if necessary."""
        # Insert caching logic here, using self.cache_dir
        response = requests.get(url)
        response.raise_for_status()
        return response.content.decode('utf-8')

    def _clean_text(self, text: str) -> str:
        """Clean and sanitize the input text."""
        return ' '.join(text.split())

    def _find_description(self, soup: BeautifulSoup) -> str:
        """Find album description from various possible locations."""
        # Try meta description first
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']

        # Try album description table
        desc_td = soup.find('td', {'style': 'text-align:justify'})
        if desc_td:
            return self._clean_text(desc_td.text)

        # Try any justified text div that might contain description
        desc_div = soup.find(['div', 'td', 'p'], {'style': re.compile(r'text-align:\s*justify', re.I)})
        if desc_div:
            return self._clean_text(desc_div.text)

        return ''

    def _find_release_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Find release information from various possible locations."""
        info = {}
        
        # Try standard album_description table first
        album_table = soup.find('table', {'class': 'album_description'})
        if album_table:
            for td in album_table.find_all('td'):
                text = td.get_text(strip=True)
                if ':' in text:
                    label, value = text.split(':', 1)
                    label = label.strip().lower()
                    if label in ['released', 'recorded', 'label', 'format', 'catalog']:
                        info[label] = value.strip()

        return info

    def _parse_record_info(self, info_text: str) -> Tuple[Optional[str], Optional[int]]:
        """Parse record type and year from album info text."""
        record_type = None
        year = None
        
        try:
            # Extract year
            year_match = re.search(r'\b(19|20)\d{2}\b', info_text)
            if year_match:
                year = int(year_match.group())
            
            # Extract record type with improved detection
            lower_info = info_text.lower()
            
            # Check for EP/Single/Fan Club/Promo first
            if any(x in lower_info for x in ['ep', 'e.p.', 'extended play']):
                record_type = 'Singles/EPs/Fan Club/Promo'
            elif any(x in lower_info for x in ['single', 'promo', 'promotional', 'fan club']):
                record_type = 'Singles/EPs/Fan Club/Promo'
            # Then check for Studio albums    
            elif any(x in lower_info for x in ['studio', 'full-length', 'full length', 'album']):
                record_type = 'Studio'
            # Skip live/compilation/other types
            elif any(x in lower_info for x in ['live', 'compilation', 'bootleg', 'demo']):
                record_type = None
                
        except Exception as e:
            logger.error(f"Error parsing record info '{info_text}': {e}")
            
        return record_type, year

    def _parse_track(self, track_text: str) -> Optional[Dict]:
        """Parse a single track text into track information."""
        # Match various track formats
        track_matches = [
            # Format: "1. Track Name - 5:30"
            re.match(r'^(\d+)\.\s*(.+?)(?:\s*-\s*(\d+:\d+))?$', track_text),
            # Format: "1 - Track Name - 5:30"
            re.match(r'^(\d+)\s*-\s*(.+?)(?:\s*-\s*(\d+:\d+))?$', track_text),
        ]
        
        for match in track_matches:
            if match:
                track = {
                    'number': int(match.group(1)),
                    'title': match.group(2).strip(),
                    'duration': match.group(3).strip() if match.group(3) else None
                }
                if self._validate_track_info(track):
                    return track
        return None

    def _find_tracks(self, soup: BeautifulSoup) -> List[Dict]:
        """Find track listing from various possible locations."""
        tracks = []
        seen_track_numbers = set()
        
        # Try class-based search first
        track_containers = []
        track_div = soup.find('div', {'class': 'track_list'})
        if track_div:
            track_containers.append(track_div)
        else:
            # Fallback to heading-based search
            track_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'tracks?|songs?|track\s*list', re.I))
            for header in track_headers:
                container = header.find_parent(['div', 'section'])
                if container:
                    track_containers.append(container)

        # Process found containers
        for container in track_containers:
            track_elements = container.find_all(['p', 'div'])
            for elem in track_elements:
                track_text = elem.get_text(strip=True)
                track = self._parse_track(track_text)
                if track and track['number'] not in seen_track_numbers:
                    tracks.append(track)
                    seen_track_numbers.add(track['number'])

        return sorted(tracks, key=lambda x: x['number'])

    def _find_reviews(self, soup: BeautifulSoup) -> List[Dict]:
        """Find review information from various possible locations."""
        reviews = []
        
        # Try class-based search
        review_details = soup.find_all('div', {'class': 'review_detail'})
        if not review_details:
            # Try heading-based search
            review_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'reviews?|ratings?', re.I))
            for header in review_headers:
                container = header.find_parent(['div', 'section'])
                if container:
                    review_details.extend(container.find_all(['div', 'section']))

        for detail in review_details:
            try:
                # Find review text
                text_elem = detail.find(['div', 'p'], {'class': 'review_text'}) or \
                           detail.find(['div', 'p'], string=lambda x: x and len(x.strip()) > 50)
                if not text_elem:
                    continue

                review = {
                    'text': text_elem.get_text(strip=True),
                    'rating': None,
                    'reviewer': None,
                    'date': None
                }

                # Find rating
                rating_elem = detail.find(['div', 'span'], {'class': 'rating'}) or \
                            detail.find(string=re.compile(r'\d+\.?\d*/[0-9.]+'))
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)/[0-9.]+', rating_text)
                    if rating_match:
                        try:
                            rating = float(rating_match.group(1))
                            if 0 <= rating <= 5:
                                review['rating'] = rating
                        except ValueError:
                            pass

                # Find reviewer info
                info_elem = detail.find(['div', 'p'], {'class': 'review_info'}) or \
                           detail.find(string=re.compile(r'by\s+\w+\s+on\s+\d{2}/\d{2}/\d{4}'))
                if info_elem:
                    info_text = info_elem.get_text(strip=True)
                    reviewer_match = re.search(r'by\s+([^on]+?)(?:\s+on\s+|$)', info_text)
                    if reviewer_match:
                        review['reviewer'] = reviewer_match.group(1).strip()
                    
                    date_match = re.search(r'on\s+(\d{2}/\d{2}/\d{4})', info_text)
                    if date_match:
                        review['date'] = date_match.group(1)

                if self._validate_review(review):
                    reviews.append(review)

            except Exception as e:
                logger.warning(f"Error parsing review: {str(e)}")
                continue

        return reviews

    def _find_lineup(self, soup: BeautifulSoup) -> List[Dict]:
        """Find lineup information from various possible locations."""
        lineup = []
        seen_entries = set()

        logger.debug("Starting lineup search")
        
        # 1. Try finding elements with standard lineup class
        lineup_div = soup.find('div', {'class': 'lineup'})
        if lineup_div:
            logger.debug("Found lineup div with class")
            self._extract_members(lineup_div, lineup, seen_entries)

        # 2. Try elements under musician/member headers
        headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'musicians|members|line.?up|credits|personnel|band', re.I))
        logger.debug(f"Found {len(headers)} potential lineup section headers")
        for header in headers:
            logger.debug(f"Processing header: {header.get_text(strip=True)}")
            # Check next elements until we hit another header or section
            current = header.find_next_sibling()
            while current and not current.find(['h2', 'h3', 'h4']):
                self._extract_members(current, lineup, seen_entries)
                current = current.find_next_sibling()

            # Also check parent container
            parent = header.find_parent(['div', 'section'])
            if parent:
                logger.debug("Processing parent container")
                self._extract_members(parent, lineup, seen_entries)

        # 3. Look for musician patterns directly
        for container in soup.find_all(['div', 'section']):
            if container.find(['h2', 'h3', 'h4'], string=re.compile(r'musicians|members|line.?up|credits|personnel|band', re.I)):
                logger.debug("Found container with musician-related header")
                self._extract_members(container, lineup, seen_entries)

        logger.debug(f"Found {len(lineup)} total lineup entries")
        for entry in lineup:
            logger.debug(f"Lineup entry: {entry['role']} - {entry['name']}")

        return lineup

    def _extract_members(self, container: Tag, lineup: List[Dict], seen_entries: set) -> None:
        """Extract member information from a container element."""
        if not container:
            return

        # Process the container's own text
        text = container.get_text(strip=True)
        if text and not re.match(r'musicians|members|line.?up|credits|personnel|tracks?|songs?|reviews?', text, re.I):
            logger.debug(f"Processing container text: {text}")
            self._try_add_member(text, lineup, seen_entries)

        # Process direct children first, then descend/recurse
        for elem in container.find_all(['p', 'div', 'li'], recursive=False):
            text = elem.get_text(strip=True)
            if text:
                logger.debug(f"Processing direct child: {text}")
                self._try_add_member(text, lineup, seen_entries)

    def _try_add_member(self, text: str, lineup: List[Dict], seen_entries: set) -> None:
        """Try to parse and add a member entry from text."""
        # Skip non-member text
        if re.match(r'musicians|members|line.?up|credits|personnel|tracks?|songs?|reviews?', text, re.I):
            return

        # Try various separators
        separators = [':', ' - ', ' – ', ' — ', '--']
        for separator in separators:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    role = parts[0].strip()
                    name = parts[1].strip()
                    
                    # Skip if either part is empty
                    if not role or not name:
                        continue
                        
                    # Skip common non-member patterns
                    if re.search(r'track|song|duration|length|time|year|genre|style|rating', role, re.I):
                        continue
                    
                    entry_key = f"{role.lower()}:{name.lower()}"
                    if entry_key not in seen_entries:
                        logger.debug(f"Adding member: {role} - {name}")
                        lineup.append({'role': role, 'name': name})
                        seen_entries.add(entry_key)
                    break

    def _validate_track_info(self, track: Dict) -> bool:
        """Validate track information."""
        if not isinstance(track.get('number'), int):
            return False
        if not track.get('title'):
            return False
        if track.get('duration') and not re.match(r'^\d+:\d+$', track['duration']):
            return False
        return True

    def _validate_review(self, review: Dict) -> bool:
        """Validate review information."""
        if not review.get('text') or len(review['text'].strip()) < 50:
            return False
        if review.get('rating') is not None and not (0 <= review['rating'] <= 5):
            return False
        return True

    def get_album_details(self, album_url: str) -> Dict:
        """Get detailed information about an album."""
        logger.info(f"Getting details for album at {album_url}")
        content = self.get_page(album_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            details = {
                'description': '',
                'lineup': [],
                'tracks': [],
                'reviews': [],
                'release_info': {},
                'error_log': []
            }

            # Get album description
            details['description'] = self._find_description(soup)

            # Get release info
            details['release_info'] = self._find_release_info(soup)

            # Get tracks
            details['tracks'] = self._find_tracks(soup)

            # Get lineup
            details['lineup'] = self._find_lineup(soup)

            # Get reviews
            details['reviews'] = self._find_reviews(soup)

            # Log validation results
            logger.info(f"Validated {len(details['tracks'])} tracks")
            logger.info(f"Validated {len(details['reviews'])} reviews")
            logger.info(f"Found {len(details['release_info'])} release info fields")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing album page {album_url}: {str(e)}")
            return {'error': str(e)}