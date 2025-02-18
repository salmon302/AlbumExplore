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
		
		# Apply cleaning steps
		df = self._clean_strings(df)
		
		# Handle tags
		if 'Genre / Subgenres' not in df.columns or df['Genre / Subgenres'].isna().all():
			df['tags'] = [['untagged']] * len(df)
		else:
			df = self._clean_tags(df)
		
		df = self._standardize_dates(df)
		df = self._standardize_locations(df)
		
		return df

		
	def _standardize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Standardize dates in the DataFrame."""
		if 'Release Date' in df.columns:
			df['release_date'] = df['Release Date'].apply(self._parse_date)
		return df
	
	def _standardize_locations(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Standardize location data in the DataFrame."""
		if 'Country / State' in df.columns:
			df['country_code'] = df['Country / State'].apply(self._get_country_code)
		return df
	
	def _clean_tags(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Clean and standardize tags in the DataFrame."""
		if 'Genre / Subgenres' in df.columns:
			df['tags'] = df['Genre / Subgenres'].apply(self._process_tags)
		return df

	def _process_tags(self, genre_str: str) -> List[str]:
		"""Process genre string into list of tags."""
		if pd.isna(genre_str) or not str(genre_str).strip():
			return ['untagged']
		
		# Split by comma and handle nested genres
		tags = []
		for genre in str(genre_str).split(','):
			# Clean the tag
			tag = genre.strip().lower()
			if tag and tag != 'nan':
				# Split nested genres (e.g., "prog-metal/rock" -> ["prog-metal", "prog-rock"])
				if '/' in tag:
					subtags = [t.strip() for t in tag.split('/')]
					tags.extend(subtags)
				else:
					tags.append(tag)
		
		# Remove duplicates while preserving order
		return list(dict.fromkeys(tags)) if tags else ['untagged']
	
	def _clean_strings(self, df: pd.DataFrame) -> pd.DataFrame:
		"""Clean string columns by removing extra whitespace and standardizing case."""
		string_columns = ['Artist', 'Album', 'Vocal Style']
		for col in string_columns:
			if col in df.columns:
				df[col] = df[col].str.strip()
		return df
	
	def _parse_date(self, date_str: str) -> pd.Timestamp:
		"""Parse date string to timestamp."""
		if pd.isna(date_str) or not str(date_str).strip():
			return None
		
		date_str = str(date_str).strip()
		
		# Handle "Month Day" format
		parts = date_str.split()
		if len(parts) == 2:  # Format: "Month Day"
			month_map = {
				'january': 1, 'february': 2, 'march': 3,
				'april': 4, 'may': 5, 'june': 6,
				'july': 7, 'august': 8, 'september': 9,
				'october': 10, 'november': 11, 'december': 12
			}
			
			month = parts[0].lower()
			day = ''.join(filter(str.isdigit, parts[1]))
			
			if month in month_map and day.isdigit():
				return pd.Timestamp(2025, month_map[month], int(day))
		
		try:
			return pd.to_datetime(date_str)
		except:
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
