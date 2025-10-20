from typing import Dict, Any, List
import pandas as pd
import pycountry
import logging
from datetime import datetime

class DataCleaner:
	"""Handles data cleaning and standardization for album data."""
	
	def __init__(self):
		self.country_codes = {
			country.name.lower(): country.alpha_2
			for country in pycountry.countries
		}
	
	def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Clean and standardize all data in the DataFrame."""
		df = df.copy()
		
		# Initialize error/warning lists
		self.errors = []
		self.warnings = []
		
		# Check for required columns first
		required_columns = {
			'Artist', 'Album', 'Release Date', 'Length',
			'Genre / Subgenres', 'Vocal Style', 'Country / State'
		}
		missing_columns = required_columns - set(df.columns)
		
		# Clean strings first
		df = self._clean_strings(df)
		
		# Clean and normalize data
		df = self._standardize_dates(df)
		df = self._standardize_locations(df)
		df = self._standardize_vocal_styles(df)
		
		# Handle tags - ensure this happens after checking for missing columns
		if 'Genre / Subgenres' not in df.columns:
			df['tags'] = [['untagged'] for _ in range(len(df))]
		else:
			df = self._clean_tags(df)
		
		# Validate data
		if missing_columns:
			self.errors.append(f"Missing required columns: {', '.join(missing_columns)}")
		
		# Check for invalid length values
		if 'Length' in df.columns:
			valid_lengths = {'LP', 'EP', 'Single'}
			invalid_lengths = df[~df['Length'].isin(valid_lengths)]['Length'].unique()
			if len(invalid_lengths) > 0:
				self.errors.append("invalid length values")
		
		# Check for dates outside expected range
		if 'release_date' in df.columns:
			try:
				current_year = datetime.now().year
				# Only check if the column actually contains datetime objects
				if df['release_date'].dtype.name.startswith('datetime'):
					future_dates = df[df['release_date'].notna() & (df['release_date'].dt.year > current_year + 1)]
					if not future_dates.empty:
						self.errors.append("dates outside expected year")
			except (AttributeError, TypeError):
				# Column exists but doesn't contain datetime data, skip validation
				pass
		
		# Check for single-word tags
		if 'tags' in df.columns:
			single_word_tags = set()
			for tags in df['tags']:
				if isinstance(tags, list):
					single_word_tags.update(tag for tag in tags if len(tag.split()) == 1)
			if single_word_tags:
				self.warnings.append("single-word tags")
		
		return df

	def _process_tags(self, genre_str: str) -> List[str]:
		"""Process genre string into list of tags."""
		if pd.isna(genre_str) or not str(genre_str).strip():
			return ['untagged']
		
		tags = []
		# Split by comma first
		for genre_group in str(genre_str).split(','):
			genre_group = genre_group.strip()
			# Handle pipe-separated tags
			if '|' in genre_group:
				pipe_tags = [t.strip().lower() for t in genre_group.split('|')]
				tags.extend(t for t in pipe_tags if t and t != 'nan')
			else:
				# Handle non-pipe tags
				tag = genre_group.strip().lower()
				if tag and tag != 'nan':
					if '/' in tag:
						subtags = [t.strip() for t in tag.split('/')]
						tags.extend(subtags)
					else:
						tags.append(tag)
		
		return tags if tags else ['untagged']

	
	def _clean_strings(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Clean string columns by removing extra whitespace and standardizing case."""
		string_columns = ['Artist', 'Album', 'Vocal Style']
		for col in string_columns:
			if col in df.columns:
				df[col] = df[col].str.strip()
		return df

	def _standardize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Standardize dates in the DataFrame."""
		if 'Release Date' in df.columns:
			df['release_date'] = df['Release Date'].apply(self._parse_date)
		return df

	def _standardize_locations(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Standardize locations in the DataFrame."""
		if 'Country / State' in df.columns:
			df['country_code'] = df['Country / State'].apply(self._get_country_code)
		return df

	def _standardize_vocal_styles(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Standardize vocal styles in the DataFrame."""
		if 'Vocal Style' in df.columns:
			df['vocal_style_normalized'] = df['Vocal Style'].apply(self._normalize_vocal_style)
		return df

	def _clean_tags(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Clean tags in the DataFrame."""
		# Always initialize tags column with untagged for all rows
		if 'Genre / Subgenres' not in df.columns or df['Genre / Subgenres'].isna().all() or df['Genre / Subgenres'].str.strip().eq('').all():
			df['tags'] = [['untagged'] for _ in range(len(df))]
			return df
		
		try:
			df['tags'] = df['Genre / Subgenres'].apply(self._process_tags)
		except Exception as e:
			logging.error(f"Error processing tags: {str(e)}")
			df['tags'] = [['untagged'] for _ in range(len(df))]
		
		return df

	
	def _parse_date(self, date_str: str) -> pd.Timestamp:
		"""Parse date string to timestamp."""
		if pd.isna(date_str) or not str(date_str).strip() or str(date_str).strip().upper() in ['TBA', 'TBD', 'N/A']:
			return None
			
		date_str = str(date_str).strip()
		
		# Handle special cases
		special_cases = {
			'early': '-01-01',
			'mid': '-06-01',
			'late': '-12-01'
		}
		
		for prefix, suffix in special_cases.items():
			if prefix in date_str.lower():
				year = ''.join(filter(str.isdigit, date_str))
				if year and len(year) == 4:
					try:
						return pd.to_datetime(f"{year}{suffix}")
					except ValueError:
						pass
		
		try:
			# Try parsing with pandas' flexible parser first
			parsed_date = pd.to_datetime(date_str, errors='coerce')
			if pd.notna(parsed_date):
				# Validate year range
				if 1900 <= parsed_date.year <= datetime.now().year + 1:
					return parsed_date
			
			# Handle "Month Day Year" or "Month Day" format
			parts = date_str.split()
			month_map = {
				'mat': 'mar',  # Common typo
				'january': 'jan', 'february': 'feb', 'march': 'mar',
				'april': 'apr', 'may': 'may', 'june': 'jun',
				'july': 'jul', 'august': 'aug', 'september': 'sep',
				'october': 'oct', 'november': 'nov', 'december': 'dec'
			}
			
			if len(parts) >= 2:
				month = parts[0].lower()
				day = ''.join(filter(str.isdigit, parts[1]))
				
				# Handle month typos
				if month in month_map:
					month = month_map[month]
				
				# Check if year is provided
				year = None
				if len(parts) >= 3:
					year_str = ''.join(filter(str.isdigit, parts[2]))
					if year_str and len(year_str) == 4:
						year = int(year_str)
				
				if not year:
					# Only use current year if no year was provided
					year = datetime.now().year
				
				try:
					date_str = f"{year} {month} {day}"
					return pd.to_datetime(date_str, format='%Y %b %d')
				except ValueError:
					pass
			
			# Handle year-only format
			if date_str.isdigit() and len(date_str) == 4:
				year = int(date_str)
				if 1900 <= year <= datetime.now().year + 1:
					return pd.to_datetime(f"{year}-01-01")
			
			return None
			
		except Exception as e:
			logging.error(f"Unexpected error parsing date '{date_str}': {str(e)}")
			return None
	
	def _get_country_code(self, location: str) -> str:
		"""Get standardized country code from location string."""
		if pd.isna(location):
			return location
		
		# Split for entries like "London, UK" or "New York, US"
		parts = location.split(',')
		if len(parts) > 1:
			country = parts[-1].strip().lower()
		else:
			country = location.strip().lower()
		
		# Handle common variations
		country_mapping = {
			'us': 'US',
			'usa': 'US',
			'united states': 'US',
			'uk': 'GB',
			'united kingdom': 'GB',
			'great britain': 'GB'
		}
		
		if country in country_mapping:
			return country_mapping[country]
		
		# Try to find country code from pycountry
		return self.country_codes.get(country, location)

	def _normalize_vocal_style(self, vocal_style: str) -> str:
		"""Normalize vocal style values."""
		if pd.isna(vocal_style) or not str(vocal_style).strip():
			return ''
		
		vocal_style = str(vocal_style).strip().lower()
		
		# Map common vocal style variations to standardized values
		vocal_style_mapping = {
			'clean': 'clean',
			'harsh': 'harsh', 
			'mixed': 'mixed',
			'instrumental': 'instrumental',
			'screaming': 'harsh',
			'growling': 'harsh',
			'death': 'harsh',
			'black': 'harsh',
			'melodic': 'clean',
			'sung': 'clean',
			'singing': 'clean',
			'vocals': 'clean',  # Default vocals to clean
			'screamed': 'harsh',
			'growled': 'harsh'
		}
		
		return vocal_style_mapping.get(vocal_style, vocal_style)
