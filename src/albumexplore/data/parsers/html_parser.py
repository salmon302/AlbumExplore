from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ProgArchivesParser:
    """Parser for ProgArchives HTML files."""
    
    def __init__(self, directory_path: Path):
        """Initialize parser with directory containing HTML files."""
        self.directory_path = Path(directory_path)
        self._data = None
        
    def parse_album(self, html_content: str) -> Dict:
        """Parse a single album HTML file."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize album data dictionary
        album_data = {
            'title': None,
            'artist': None,
            'genre': None,
            'record_type': None,
            'year': None,
            'rating': None
        }
        
        try:
            # Extract basic information (implement specific selectors based on HTML structure)
            # These selectors will need to be adjusted based on actual HTML structure
            album_data['title'] = self._extract_text(soup.find('h1', class_='album-title'))
            album_data['artist'] = self._extract_text(soup.find('div', class_='artist-name'))
            album_data['genre'] = self._extract_text(soup.find('div', class_='genre'))
            
            # Extract record type and year
            record_info = self._extract_text(soup.find('div', class_='album-info'))
            if record_info:
                # Parse record type and year from the info text
                # This will need to be adjusted based on actual format
                pass
            
            # Extract rating
            rating_elem = soup.find('div', class_='rating')
            if rating_elem:
                album_data['rating'] = self._parse_rating(rating_elem.text)
                
        except Exception as e:
            logger.error(f"Error parsing album: {e}")
        
        return album_data
    
    def parse_directory(self) -> pd.DataFrame:
        """Parse all HTML files in the directory."""
        all_albums = []
        
        for html_file in self.directory_path.glob('*.html'):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                album_data = self.parse_album(content)
                all_albums.append(album_data)
            except Exception as e:
                logger.error(f"Error processing file {html_file}: {e}")
        
        return pd.DataFrame(all_albums)
    
    @property
    def data(self) -> pd.DataFrame:
        """Return the parsed data, parsing if not already done."""
        if self._data is None:
            self._data = self.parse_directory()
        return self._data
    
    def _extract_text(self, element) -> Optional[str]:
        """Safely extract text from a BeautifulSoup element."""
        if element:
            return element.text.strip()
        return None
    
    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating text into a float."""
        try:
            # Remove any non-numeric characters except decimal point
            rating = ''.join(c for c in rating_text if c.isdigit() or c == '.')
            return float(rating)
        except (ValueError, TypeError):
            return None