"""ProgArchives.com scraper with ethical rate limiting."""
import logging
from typing import Dict, List, Iterator, Optional
from pathlib import Path
from bs4 import BeautifulSoup
import random
import re
from datetime import datetime
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ProgArchivesScraper(BaseScraper):
    """Scraper for ProgArchives.com that follows ethical guidelines."""
    
    BASE_URL = "https://www.progarchives.com"
    ALPHA_URL = f"{BASE_URL}/bands-alpha.asp"
    
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

    def _get_bands_for_letter(self, letter: str) -> Iterator[Dict]:
        """Get bands starting with a specific letter."""
        try:
            url = f"{self.ALPHA_URL}?letter={letter}"
            response = self.fetch_url(url)
            
            if not response or not response.get('content'):
                logger.warning(f"No content received for letter {letter}")
                return
                
            yield from self._parse_band_table(response['content'])
            
        except Exception as e:
            logger.error(f"Error getting bands for letter {letter}: {e}")
            return

    def _get_bands_from_all(self) -> Iterator[Dict]:
        """Fallback method to get all bands from main listing."""
        try:
            response = self.fetch_url(self.ALPHA_URL)
            if not response or not response.get('content'):
                logger.warning("No content received from main listing")
                return
                
            yield from self._parse_band_table(response['content'])
            
        except Exception as e:
            logger.error(f"Error getting bands from main listing: {e}")
            return

    def get_bands_all(self) -> Iterator[Dict]:
        """Get list of bands from alphabetical listing, optionally using sampling strategy."""
        bands_found = 0
        seen_urls = set()
        try:
            all_bands = []
            letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ*')  # Include * for misc/numbers
            
            # Randomize letter order if using random sampling
            if self.random_sample:
                random.shuffle(letters)
            
            for letter in letters:
                letter_bands = list(self._get_bands_for_letter(letter))
                if letter_bands:
                    # If random sampling, shuffle bands from each letter
                    if self.random_sample:
                        random.shuffle(letter_bands)
                    all_bands.extend(letter_bands)
                    logger.info(f"Found {len(letter_bands)} bands for letter {letter}")
                    
                    # Early exit if we have enough bands
                    if self.max_bands and len(all_bands) >= self.max_bands * 2:
                        break
            
            if not all_bands:
                # Fallback to all-bands page
                all_bands = list(self._get_bands_from_all())
            
            if not all_bands:
                raise ValueError("No bands found in alphabetical listing")
            
            if self.random_sample:
                if self.max_bands:
                    # Take a diverse sample by selecting bands from different parts of the list
                    sample_size = min(self.max_bands, len(all_bands))
                    interval = len(all_bands) // sample_size
                    sampled_bands = []
                    for i in range(0, len(all_bands), interval):
                        if len(sampled_bands) < sample_size:
                            sampled_bands.append(all_bands[i])
                    all_bands = sampled_bands
                else:
                    # If no max_bands specified, shuffle the entire list
                    random.shuffle(all_bands)
            
            for band in all_bands:
                if band['url'] not in seen_urls:
                    seen_urls.add(band['url'])
                    yield band
                    bands_found += 1
                    
                    if self.max_bands and bands_found >= self.max_bands:
                        return

        except Exception as e:
            logger.error(f"Error getting bands from alphabetical listing: {e}")
            raise

    def _parse_band_table(self, content: str) -> Iterator[Dict]:
        """Parse HTML content to extract band information."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Updated selectors with fallbacks, ordered by specificity
        table_selectors = [
            'table.table-artists',
            'table.artists-list',
            'table.bands-list',
            '#artistsTable',
            '#band-list table',
            'table.list',
            'table'  # Last resort
        ]
        
        for selector in table_selectors:
            tables = soup.select(selector)
            for table in tables:
                # Verify this looks like a band table
                if not self._is_valid_band_table(table):
                    continue
                
                for row in table.find_all('tr'):
                    band_info = self._parse_band_row(row)
                    if band_info:
                        yield band_info
                
                # If we found valid bands in this table, stop looking
                return

    def _is_valid_band_table(self, table: BeautifulSoup) -> bool:
        """Verify if a table appears to be a valid band listing."""
        # Should have multiple rows
        rows = table.find_all('tr')
        if len(rows) < 2:
            return False
            
        # Should have header row with expected columns
        header = rows[0]
        header_text = header.text.lower()
        return any(term in header_text for term in ['artist', 'band', 'genre', 'style'])

    def _parse_band_row(self, row: BeautifulSoup) -> Optional[Dict]:
        """Parse a single row from the band table."""
        try:
            # Skip header rows
            if row.find('th'):
                return None
                
            cells = row.find_all('td')
            if len(cells) < 2:  # Need at least name and genre
                return None
                
            band_link = row.find('a')
            if not band_link:
                return None
                
            band_url = band_link.get('href')
            if not band_url:
                return None
                
            if not band_url.startswith('http'):
                band_url = f"{self.BASE_URL}/{band_url.lstrip('/')}"
                
            # Extract genre from appropriate column
            genre = None
            for cell in cells[1:]:
                text = cell.text.strip()
                if text and not text.isdigit() and not '/' in text:
                    genre = text
                    break
            
            return {
                'name': band_link.text.strip(),
                'url': band_url,
                'genre': genre
            }
            
        except Exception as e:
            logger.warning(f"Error parsing band row: {e}")
            return None

    def get_band_details(self, url: str) -> Dict:
        """Get detailed information about a band."""
        try:
            response = self.fetch_url(url)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")

            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Get main band info
            band_info = self._find_band_info(soup)
            if not band_info:
                raise ValueError(f"Could not find band info section for {url}")

            details = {
                'url': url,
                'name': self._extract_text(band_info.find('h1', {'class': 'band-name'})),
                'genre': self._extract_text(band_info.find('div', {'class': 'band-genre'})),
                'country': self._extract_text(band_info.find('div', {'class': 'band-country'})),
                'description': self._find_band_description(soup),
                'members': self._find_band_members(soup),
                'albums': list(self._find_band_albums(soup)),
                'scraped_at': datetime.now().isoformat()
            }

            # Clean data
            details = {k.strip(): v for k, v in details.items() if v}
            
            # Validate required fields
            required_fields = ['name', 'genre', 'country']
            missing_fields = [f for f in required_fields if not details.get(f)]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting band details from {url}: {e}")
            return {'error': str(e)}

    def _find_band_info(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Extract main band info section."""
        return soup.find('div', {'class': ['band-header', 'artist-header']})

    def _extract_text(self, element) -> Optional[str]:
        """Safely extract and clean text from an element."""
        if element:
            text = element.get_text().strip()
            return text if text else None
        return None

    def _find_band_description(self, soup: BeautifulSoup) -> str:
        """Extract band description/biography."""
        desc_div = soup.find('div', {'class': ['band-description', 'artist-bio']})
        return self._extract_text(desc_div) or ""

    def _find_band_members(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract band member information."""
        members = []
        member_section = soup.find('div', {'class': ['members', 'lineup']})
        if member_section:
            for member in member_section.find_all(['div', 'li'], {'class': ['member', 'member-item']}):
                try:
                    name = member.find(['span', 'div'], {'class': 'name'})
                    role = member.find(['span', 'div'], {'class': ['role', 'instrument']})
                    years = member.find(['span', 'div'], {'class': 'years'})
                    
                    if name:
                        member_info = {
                            'name': self._extract_text(name),
                            'role': self._extract_text(role),
                            'years': self._extract_text(years)
                        }
                        members.append({k: v for k, v in member_info.items() if v})
                except Exception as e:
                    logger.warning(f"Error parsing member: {e}")
        return members

    def _find_band_albums(self, soup: BeautifulSoup) -> Iterator[Dict]:
        """Extract album information."""
        album_section = soup.find('div', {'class': ['discography', 'albums']})
        if album_section:
            for album in album_section.find_all(['div', 'tr'], {'class': ['album', 'album-entry']}):
                try:
                    title_elem = album.find(['h3', 'td', 'div'], {'class': ['title', 'album-title']})
                    year_elem = album.find(['span', 'td', 'div'], {'class': ['year', 'album-year']})
                    type_elem = album.find(['span', 'td', 'div'], {'class': ['type', 'album-type']})
                    
                    # Extract and validate album type
                    album_type = self._extract_text(type_elem)
                    if album_type:
                        album_type = album_type.strip().title()
                        if 'Studio' in album_type:
                            album_type = 'Studio Album'
                        elif any(t in album_type for t in ['EP', 'Single']):
                            album_type = 'Single/EP'
                        elif 'Live' in album_type:
                            album_type = 'Live'
                        elif 'Compilation' in album_type:
                            album_type = 'Compilation'
                        else:
                            album_type = 'Studio Album'  # Default to studio album

                    title = self._extract_text(title_elem)
                    if title:
                        album_info = {
                            'title': title,
                            'year': self._extract_year(year_elem),
                            'type': album_type,
                            'url': self._extract_album_url(title_elem)
                        }
                        
                        # Only yield if we have the minimum required fields
                        if album_info['title'] and album_info['year'] and album_info['type']:
                            yield album_info

                except Exception as e:
                    logger.warning(f"Error parsing album: {e}")

    def _extract_year(self, element) -> Optional[str]:
        """Extract and validate year from element."""
        if element:
            text = self._extract_text(element)
            if text:
                # Extract 4-digit year using regex
                match = re.search(r'(19|20)\d{2}', text)
                if match:
                    return match.group(0)
        return None

    def _extract_album_url(self, element) -> Optional[str]:
        """Extract album URL from element."""
        if element:
            link = element.find('a')
            if link and link.get('href'):
                url = link['href']
                if not url.startswith('http'):
                    url = f"{self.BASE_URL}/{url.lstrip('/')}"
                return url
        return None