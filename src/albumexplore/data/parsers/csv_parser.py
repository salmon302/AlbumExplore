from pathlib import Path
from typing import Union
import pandas as pd
import logging
from datetime import datetime
from albumexplore.data.cleaners.data_cleaner import DataCleaner

class CSVParser:
	def __init__(self, path: Union[str, Path]):
		self.path = Path(path)
		self.file_path = self.path  # Add this line to match test expectations
		self._data = None
		self._delimiter = "\t" if str(path).endswith(".tsv") else ","
		self.data_cleaner = DataCleaner()
		self.column_names = [
			'Artist', 'Album', 'Release Date', 'Length',
			'Genre / Subgenres', 'Vocal Style', 'Country / State',
			'Bandcamp', 'Spotify', 'Google Play', 'YouTube', 'Amazon'
		]

	def parse(self) -> pd.DataFrame:
		logging.info("Starting CSV parsing...")
		if self.path.is_dir():
			return self.parse_multiple_csv(self.path)
		else:
			return self.parse_single_csv(self.path)

	def parse_single_csv(self, file_path: Path) -> pd.DataFrame:
		try:
			logging.info(f"Parsing single CSV file: {file_path}")
			# Extract year from filename
			filename = file_path.name
			year_match = None
			# Try to find year in format " - YYYY"
			parts = filename.split(' - ')
			if len(parts) > 1:
				for part in parts[1:]:  # Look in parts after the first " - "
					# Extract first 4 digits if they form a valid year
					year_str = ''.join(filter(str.isdigit, part))[:4]
					if year_str and len(year_str) == 4 and 1900 <= int(year_str) <= datetime.now().year + 1:
						year_match = year_str
						break
			
			file_year = year_match if year_match else None
			logging.debug(f"Extracted year from filename: {file_year}")

			
			with open(file_path, 'r', encoding='utf-8') as f:
				content = f.readlines()
			
			header_row = -1
			for i, line in enumerate(content):
				if all(col in line for col in ['Artist', 'Album', 'Release Date', 'Length', 'Genre / Subgenres']):
					header_row = i
					break
			
			if header_row == -1:
				logging.error(f"Required columns not found in {file_path}")
				return pd.DataFrame(columns=self.column_names)
			
			temp_content = content[header_row:]
			temp_file = file_path.parent / f"temp_{file_path.name}"
			with open(temp_file, 'w', encoding='utf-8') as f:
				f.writelines(temp_content)
			
			try:
				df = pd.read_csv(
					temp_file,
					encoding='utf-8',
					sep=self._delimiter,
					engine='python',
					on_bad_lines='skip',
					dtype=str
				)
				
				df.columns = df.columns.str.strip()
				df = df.dropna(subset=['Artist'], how='all')
				df = df[df['Artist'].str.strip() != '']
				
				df['_file_year'] = file_year
				
				if 'Release Date' in df.columns:
					logging.info("Preprocessing 'Release Date' column...")
					df['Release Date'] = df.apply(
						lambda row: self._preprocess_date(row['Release Date'], row['_file_year']), 
						axis=1
					)
				
				df = df.drop('_file_year', axis=1)
				
				for col in df.columns:
					df[col] = df[col].apply(lambda x: str(x).rstrip('.0') if pd.notna(x) else '')
				
				df = self.data_cleaner.clean_dataframe(df)
				
				return df
				
			finally:
				if temp_file.exists():
					temp_file.unlink()
		
		except Exception as e:
			logging.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
			return pd.DataFrame(columns=self.column_names)

	def parse_multiple_csv(self, directory: Path) -> pd.DataFrame:
		logging.info(f"Parsing multiple CSV files from directory: {directory}")
		all_files = list(directory.glob("*.csv")) + list(directory.glob("*.tsv"))
		dfs = []
		
		for file_path in all_files:
			try:
				df = self.parse_single_csv(file_path)
				if not df.empty:
					dfs.append(df)
			except Exception as e:
				logging.error(f"Error parsing file {file_path}: {e}", exc_info=True)
		
		if dfs:
			logging.info(f"Concatenating {len(dfs)} dataframes...")
			combined_df = pd.concat(dfs, ignore_index=True)
			self._data = combined_df
			logging.info(f"Successfully parsed {len(combined_df)} rows of data")
			return combined_df
		else:
			logging.warning("No data found in the specified directory.")
			self._data = pd.DataFrame(columns=self.column_names)
			return self._data

	def _preprocess_date(self, date_str: str, file_year: str = None) -> str:
		"""Preprocess date string to standard format."""
		if pd.isna(date_str) or not str(date_str).strip():
			return f"{file_year}-01-01" if file_year else None
			
		date_str = str(date_str).strip()
		
		# Handle month names
		month_map = {
			'january': '01', 'february': '02', 'march': '03', 'april': '04',
			'may': '05', 'june': '06', 'july': '07', 'august': '08',
			'september': '09', 'october': '10', 'november': '11', 'december': '12'
		}
		
		# Convert "Month Day" format to "YYYY-MM-DD"
		parts = date_str.lower().split()
		if len(parts) >= 2 and parts[0] in month_map:
			month = month_map[parts[0]]
			day = ''.join(filter(str.isdigit, parts[1])) or '01'
			
			# Check if year is in the date string
			year = None
			if len(parts) >= 3:
				year_str = ''.join(filter(str.isdigit, parts[2]))
				if year_str and len(year_str) == 4:
					year = year_str
			
			# If no year in date string, use file year
			if not year:
				year = file_year if file_year else '2025'
				
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
		
		# Use file year for text-only dates
		if file_year and not any(char.isdigit() for char in date_str):
			return f"{file_year}-01-01"
		
		# Try to extract year from the date string
		year = ''.join(filter(str.isdigit, date_str))
		if year and len(year) == 4:
			return f"{year}-01-01"
		
		# Default to file year if available, otherwise 2025
		return f"{file_year}-01-01" if file_year else "2025-01-01"

	@property
	def data(self) -> pd.DataFrame:
		if self._data is None:
			self.parse()
		return self._data

