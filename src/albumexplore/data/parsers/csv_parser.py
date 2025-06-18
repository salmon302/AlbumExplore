"""CSV parsing module."""
from pathlib import Path
from typing import Union, List, Tuple
import pandas as pd
import logging
from datetime import datetime
from ..cleaners.data_cleaner import DataCleaner

logger = logging.getLogger("albumexplore.database")

class CSVParser:
    """Parser for album CSV/TSV files."""
    
    def __init__(self, path: Union[str, Path]):
        """Initialize parser with file or directory path."""
        self.file_path = Path(path)  # Use file_path consistently
        self._data = None
        self._delimiter = None  # Will be set during parsing
        self.data_cleaner = DataCleaner()
        self.column_names = [
            'Artist', 'Album', 'Release Date', 'Length',
            'Genre / Subgenres', 'Vocal Style', 'Country / State',
            'Bandcamp', 'Spotify', 'YouTube', 'Amazon', 'Apple Music'
        ]

    @property
    def path(self) -> Path:
        """Backward compatibility property for path."""
        return self.file_path

    def parse(self) -> pd.DataFrame:
        """Parse CSV/TSV file(s) and return a cleaned DataFrame."""
        logger.info(f"Parsing data from: {self.file_path}")
        
        try:
            if self.file_path.is_dir():
                return self.parse_multiple_csv(self.file_path)
            else:
                return self.parse_single_csv(self.file_path)
            
        except Exception as e:
            logger.error(f"Error parsing data: {str(e)}")
            return pd.DataFrame(columns=self.column_names)

    def _parse_tags(self, tag_str: str) -> list:
        """Parse a tag string into a list of individual tags."""
        if pd.isna(tag_str):
            return ['untagged']
        
        # Split by both commas and pipes
        tags = []
        for part in tag_str.split('|'):
            tags.extend(t.strip().lower() for t in part.split(',') if t.strip())
        
        return tags if tags else ['untagged']

    def _detect_header_row(self, file_path: Path, delimiter: str, encoding: str) -> int:
        """Detect which row contains the actual headers by looking for data patterns."""
        try:
            # Read first 20 rows to analyze (these files have headers around line 12)
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            
            # Look for the row containing "Artist,Album,Release Date" pattern
            for i, line in enumerate(lines[:25]):  # Check first 25 lines
                line_lower = line.lower().strip()
                # Look for the standard header pattern for Reddit CSV files
                if ('artist' in line_lower and 
                    'album' in line_lower and 
                    ('release date' in line_lower or 'date' in line_lower) and
                    'genre' in line_lower):
                    logger.debug(f"Found header row at line {i} in {file_path.name}")
                    return i
            
            # If no clear headers found, use default based on Reddit CSV structure
            logger.warning(f"Could not find header row in {file_path.name}, using default row 12")
            return 12  # Reddit CSV files typically have headers at row 12-13
            
        except Exception as e:
            logger.warning(f"Error detecting header row in {file_path.name}: {e}")
            return 12  # Default to row 12

    def _assign_standard_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign standard column names based on position and content analysis."""
        if df.empty:
            return df
            
        # Expected column order based on the CSV structure we observed
        standard_mapping = {
            0: 'Artist',
            1: 'Album', 
            2: 'Release Date',
            3: 'Length',
            4: 'Genre / Subgenres',
            5: 'Vocal Style',
            6: 'Country / State',
            7: 'Bandcamp',
            8: 'Spotify',
            9: 'YouTube',
            10: 'Amazon',
            11: 'Apple Music'
        }
        
        # Create new column names
        new_columns = []
        for i, col in enumerate(df.columns):
            if i in standard_mapping:
                new_columns.append(standard_mapping[i])
            else:
                new_columns.append(f'Extra_Column_{i}')
        
        df.columns = new_columns
        return df

    def parse_single_csv(self, file_path: Path) -> pd.DataFrame:
        """Parse a single CSV/TSV file and return a cleaned DataFrame."""
        logger.debug(f"Parsing file: {file_path}")
        try:
            # Try to determine delimiter from extension
            delimiter = '\t' if file_path.suffix.lower() == '.tsv' else ','
            
            # Try reading with different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    # First, try to detect if there are proper headers
                    header_row = self._detect_header_row(file_path, delimiter, encoding)
                    
                    # Read the CSV starting from the header row
                    df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, 
                                   skiprows=header_row, header=0)
                    
                    # If we still don't have proper column names, assign standard ones
                    if df.columns[0] != 'Artist' or len(df.columns) < 5:
                        logger.debug(f"Assigning standard column names for {file_path.name}")
                        df = self._assign_standard_columns(df)
                    
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                logger.error(f"Could not read file with any supported encoding: {file_path}")
                return pd.DataFrame(columns=self.column_names)

            # Drop empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Clean and standardize column names
            df.columns = df.columns.str.strip()
            
            # Convert genres to tags list
            if 'Genre / Subgenres' in df.columns:
                df['tags'] = df['Genre / Subgenres'].apply(self._parse_tags)
                
            # Standardize date column name
            if 'Release Date' in df.columns:
                df = df.rename(columns={'Release Date': 'release_date'})
            
            # Clean and standardize the data
            df = self.data_cleaner.clean_dataframe(df)
            
            logger.debug(f"Successfully parsed {len(df)} rows from {file_path}")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            return pd.DataFrame(columns=self.column_names)

    def parse_multiple_csv(self, directory: Path) -> pd.DataFrame:
        """Parse multiple CSV files from a directory."""
        logger.info(f"Looking for CSV files in: {directory}")
        all_dfs = []
        
        try:
            # Ensure we're using Path objects
            directory = Path(directory)
            
            # Look for CSV files recursively
            csv_files = sorted(directory.glob('*.csv'))
            
            if not csv_files:
                logger.warning("No CSV files found")
                return pd.DataFrame(columns=self.column_names)
            
            # Parse each file
            for file_path in csv_files:
                logger.debug(f"Processing file: {file_path}")
                df = self.parse_single_csv(file_path)
                if not df.empty:
                    df['_source_file'] = file_path.name
                    all_dfs.append(df)
            
            if not all_dfs:
                logger.warning("No valid data found in any CSV files")
                return pd.DataFrame(columns=self.column_names)
            
            # Combine all dataframes and deduplicate
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['Artist', 'Album'], keep='first')
            
            logger.info(f"Successfully parsed {len(combined_df)} total rows from {len(all_dfs)} files")
            return combined_df
            
        except Exception as e:
            logger.error(f"Error parsing CSV files: {str(e)}")
            return pd.DataFrame(columns=self.column_names)

    @property
    def data(self) -> pd.DataFrame:
        """Return the parsed data, parsing if not already done."""
        if self._data is None:
            self._data = self.parse()
        return self._data

