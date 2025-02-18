from pathlib import Path
from typing import Union
import pandas as pd
import logging
from data.cleaners.data_cleaner import DataCleaner

class CSVParser:
	def __init__(self, path: Union[str, Path]):
		self.file_path = Path(path)
		self._data = None
		self._delimiter = "\t" if str(path).endswith(".tsv") else ","
		self.data_cleaner = DataCleaner()
		self.column_names = [
			'Artist', 'Album', 'Release Date', 'Length',
			'Genre / Subgenres', 'Vocal Style', 'Country / State',
			'Bandcamp', 'Spotify', 'Google Play', 'YouTube', 'Amazon'
		]

	def parse(self) -> pd.DataFrame:
		"""Parse CSV/TSV file(s) and return a cleaned DataFrame."""
		if self.file_path.is_dir():
			return self.parse_multiple_csv(self.file_path)
		else:
			return self.parse_single_csv(self.file_path)

	def parse_single_csv(self, file_path: Path) -> pd.DataFrame:
		"""Parse a single CSV/TSV file and return a cleaned DataFrame."""
		try:
			# Read the file content first to handle special cases
			with open(file_path, 'r', encoding='utf-8') as f:
				content = f.readlines()
			
			# Find the actual header row by looking for the main column headers
			header_row = -1
			for i, line in enumerate(content):
				if all(col in line for col in ['Artist', 'Album', 'Release Date', 'Length', 'Genre / Subgenres']):
					header_row = i
					break
			
			if header_row == -1:
				logging.error(f"Required columns not found in {file_path}")
				return pd.DataFrame(columns=self.column_names)
			
			# Create a new temporary file with just the data we want
			temp_content = content[header_row:]
			temp_file = file_path.parent / f"temp_{file_path.name}"
			with open(temp_file, 'w', encoding='utf-8') as f:
				f.writelines(temp_content)
			
			try:
				# Read the temporary file with string type for all columns
				df = pd.read_csv(
					temp_file,
					encoding='utf-8',
					sep=self._delimiter,
					engine='python',
					on_bad_lines='skip',
					dtype=str  # Force all columns to be read as strings
				)
				
				# Clean column names and data
				df.columns = df.columns.str.strip()
				df = df.dropna(subset=['Artist'], how='all')
				df = df[df['Artist'].str.strip() != '']
				
				# Preprocess dates before cleaning
				if 'Release Date' in df.columns:
					df['Release Date'] = df['Release Date'].apply(self._preprocess_date)
				
				# Convert any float-like strings to proper string format
				for col in df.columns:
					df[col] = df[col].apply(lambda x: str(x).rstrip('.0') if pd.notna(x) else '')
				
				# Apply data cleaning
				df = self.data_cleaner.clean_dataframe(df)
				
				return df
				
			finally:
				# Clean up temporary file
				if temp_file.exists():
					temp_file.unlink()

			
		except Exception as e:
			logging.error(f"Error parsing file {file_path}: {str(e)}")
			return pd.DataFrame(columns=self.column_names)

	def parse_multiple_csv(self, directory: Path) -> pd.DataFrame:
		"""Parse multiple CSV files from a directory."""
		all_files = list(directory.glob("*.csv")) + list(directory.glob("*.tsv"))
		dfs = []
		
		for file_path in all_files:
			try:
				df = self.parse_single_csv(file_path)
				if not df.empty:
					dfs.append(df)
			except Exception as e:
				logging.error(f"Error parsing file {file_path}: {e}")
		
		if dfs:
			combined_df = pd.concat(dfs, ignore_index=True)
			self._data = combined_df
			return combined_df
		else:
			self._data = pd.DataFrame(columns=self.column_names)
			return self._data

	def _preprocess_date(self, date_str: str) -> str:
		"""Preprocess date strings before they reach the data cleaner."""
		if pd.isna(date_str) or not str(date_str).strip():
			return date_str
			
		date_str = str(date_str).strip()
		
		# Extract year from filename
		file_year = None
		filename = self.file_path.stem
		year_match = next((part.strip() for part in filename.split('-') if part.strip().isdigit() and len(part.strip()) == 4), None)
		if year_match:
			file_year = year_match
		
		# Handle month names
		month_map = {
			'january': '01', 'february': '02', 'march': '03', 'april': '04',
			'may': '05', 'june': '06', 'july': '07', 'august': '08',
			'september': '09', 'october': '10', 'november': '11', 'december': '12'
		}
		
		# Convert "Month Day" format to "YYYY-MM-DD"
		parts = date_str.lower().split()
		if len(parts) == 2 and parts[0] in month_map:
			month = month_map[parts[0]]
			day = ''.join(filter(str.isdigit, parts[1])) or '01'
			year = file_year or '2025'  # Use file year or default to 2025
			return f"{year}-{month}-{day}"
		
		# Handle seasons
		season_map = {
			'spring': '03', 'summer': '06',
			'fall': '09', 'autumn': '09', 'winter': '12'
		}
		
		for season, month in season_map.items():
			if season in date_str.lower():
				year = file_year or ''.join(filter(str.isdigit, date_str)) or '2025'
				return f"{year}-{month}-01"
		
		# Handle year-only format
		if date_str.isdigit() and len(date_str) == 4:
			return f"{date_str}-01-01"
		
		return date_str

	@property
	def data(self) -> pd.DataFrame:
		"""Return the parsed data, parsing if not already done."""
		if self._data is None:
			self.parse()
		return self._data
