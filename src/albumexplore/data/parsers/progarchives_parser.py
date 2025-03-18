"""Parser for ProgArchives HTML files."""
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import logging
import re
from typing import Dict, List, Optional, Tuple
from albumexplore.data.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class ProgArchivesParser(BaseParser):
    """Parser for ProgArchives HTML files."""
    
    VALID_RECORD_TYPES = {'Studio', 'Singles/EPs/Fan Club/Promo'}
    ENCODINGS_TO_TRY = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
    
    def __init__(self, directory_path: Path):
        """Initialize parser with directory containing HTML files."""
        super().__init__()
        self.directory_path = Path(directory_path)
        self._data = None

    def parse_album_row(self, row) -> Dict:
        """Parse a single album row from the subgenre page."""
        album_data = {
            'title': None,
            'artist': None,
            'genre': None,
            'record_type': None,
            'year': None,
            'rating': None,
            'subgenre': None
        }
        
        try:
            # Title and Artist are in the third column
            title_artist_cell = row.find_all('td')[2]
            title_link = title_artist_cell.find('a', href=re.compile(r'album\.asp'))
            artist_link = title_artist_cell.find('a', href=re.compile(r'artist\.asp'))
            
            if title_link:
                album_data['title'] = title_link.text.strip()
            if artist_link:
                album_data['artist'] = artist_link.text.strip()
            
            # Genre, Record Type, and Year are in the fourth column
            info_cell = row.find_all('td')[3]
            if info_cell:
                info_text = info_cell.get_text(strip=True)
                genre_match = re.match(r'([^,]+)', info_text)
                if genre_match:
                    album_data['genre'] = genre_match.group(1).strip()
                
                # Extract record type and year
                record_type, year = self._parse_record_info(info_text)
                album_data['record_type'] = record_type
                album_data['year'] = year
            
            # Rating is in the fifth column
            rating_cell = row.find_all('td')[4]
            if rating_cell:
                rating_span = rating_cell.find('span', style=re.compile(r'color:#C75D4F'))
                if rating_span:
                    album_data['rating'] = self._parse_rating(rating_span.text)
                    
        except Exception as e:
            logger.error(f"Error parsing album row: {e}")
        
        return album_data

    def parse_file(self, html_path: Path) -> List[Dict]:
        """Parse a single HTML file containing a subgenre's album list."""
        albums = []
        content = None
        
        # Try different encodings
        for encoding in self.ENCODINGS_TO_TRY:
            try:
                with open(html_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            logger.error(f"Failed to read {html_path} with any encoding")
            return albums
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # Get subgenre from filename
            subgenre = html_path.stem.replace('_', ' ')
            
            # Find the table containing album rows
            table = soup.find('table', style=re.compile(r'border:1px solid #a0a0a0'))
            if table:
                # Skip header row, process each album row
                for row in table.find_all('tr')[1:]:  # Skip header row
                    album_data = self.parse_album_row(row)
                    if album_data['record_type'] in self.VALID_RECORD_TYPES:
                        album_data['subgenre'] = subgenre
                        albums.append(album_data)
            
        except Exception as e:
            logger.error(f"Error processing file {html_path}: {e}")
        
        return albums

    def parse(self) -> pd.DataFrame:
        """Parse all HTML files in the directory."""
        all_albums = []
        
        for html_file in self.directory_path.glob('*.html'):
            if html_file.name == 'ProgSubgenres':  # Skip directory
                continue
            
            logger.info(f"Processing {html_file.name}")
            albums = self.parse_file(html_file)
            all_albums.extend(albums)
        
        df = pd.DataFrame(all_albums)
        return self._post_process_dataframe(df)

    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating text into a float."""
        try:
            # Remove any non-numeric characters except decimal point
            rating = ''.join(c for c in rating_text if c.isdigit() or c == '.')
            return float(rating)
        except (ValueError, TypeError):
            return None

    def _parse_record_info(self, info_text: str) -> Tuple[Optional[str], Optional[int]]:
        """Parse record type and year from album info text."""
        record_type = None
        year = None
        
        try:
            # Extract year
            year_match = re.search(r'\b(19|20)\d{2}\b', info_text)
            if year_match:
                year = int(year_match.group())
            
            # Extract record type with improved matching
            lower_info = info_text.lower()
            
            # Match Singles/EPs/Fan Club/Promo first
            if any(x in lower_info for x in ['single', 'ep', 'e.p.', 'promo', 'fan club', 'promotional']):
                record_type = 'Singles/EPs/Fan Club/Promo'
            # Then match Studio albums
            elif any(x in lower_info for x in ['studio', 'full-length', 'lp', 'album']):
                record_type = 'Studio'
                
        except Exception as e:
            logger.error(f"Error parsing record info '{info_text}': {e}")
            
        return record_type, year

    def _post_process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate the parsed data."""
        if len(df) == 0:
            return df
            
        # Remove rows with missing required fields
        required_fields = ['title', 'artist', 'genre', 'record_type', 'year']
        df = df.dropna(subset=required_fields)
        
        # Convert year to integer
        df['year'] = pd.to_numeric(df['year'], downcast='integer')
        
        # Sort by subgenre, year and artist
        df = df.sort_values(['subgenre', 'year', 'artist'])
        
        logger.info(f"Processed {len(df)} albums across {df['subgenre'].nunique()} subgenres")
        return df