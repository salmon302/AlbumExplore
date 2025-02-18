from typing import List, Dict, Optional, Set
import pandas as pd
from collections import Counter
import pycountry
from datetime import datetime

class DataValidator:
	"""Validates and checks data quality for album dataset."""
	
	REQUIRED_COLUMNS = {
		'Artist', 'Album', 'Release Date', 'Length',
		'Genre / Subgenres', 'Vocal Style', 'Country / State'
	}
	
	VALID_LENGTHS = {'LP', 'EP', 'Single', 'Demo', 'Split', 'Compilation'}
	VALID_LP_FORMATS = {f"{i}xLP" for i in range(1, 25)}  # Handle up to 24xLP formats
	
	def __init__(self, df: pd.DataFrame):
		self.df = df
		self.validation_errors = []
		self.validation_warnings = []
		self._tag_frequency = None

	def validate(self) -> bool:
		"""Run all validation checks and return True if data is valid."""
		self._check_required_columns()
		self._check_data_types()
		self._check_date_validity()
		self._check_tag_format()
		self._check_tag_frequency()
		self._check_location_format()
		self._check_length_values()
		
		return len(self.validation_errors) == 0

	def _check_required_columns(self):
		"""Verify all required columns are present."""
		missing_cols = self.REQUIRED_COLUMNS - set(self.df.columns)
		if missing_cols:
			self.validation_errors.append(
				f"Missing required columns: {', '.join(missing_cols)}"
			)

	def _check_data_types(self):
		"""Verify data types of key columns."""
		if 'release_date' in self.df.columns:
			invalid_dates = self.df['release_date'].isna().sum()
			if invalid_dates > 0:
				self.validation_errors.append(
					f"Found {invalid_dates} invalid release dates"
				)
		
		string_columns = ['Artist', 'Album', 'Vocal Style']
		for col in string_columns:
			if col in self.df.columns:
				empty_values = self.df[col].isna().sum()
				if empty_values > 0:
					self.validation_errors.append(
						f"Found {empty_values} empty values in {col}"
					)

	def _check_date_validity(self):
		"""Check if release dates are within expected range and format."""
		if 'release_date' in self.df.columns:
			current_year = datetime.now().year
			
			# Count invalid dates (NaT values)
			invalid_dates = self.df['release_date'].isna().sum()
			if invalid_dates > 0:
				self.validation_errors.append("invalid release dates")
			
			# Check future dates - changed to error instead of warning
			future_dates = self.df[
				self.df['release_date'].notna() &
				(self.df['release_date'].dt.year > current_year)
			]
			if len(future_dates) > 0:
				self.validation_errors.append("dates outside expected year")
			
			# Check very old dates
			very_old_dates = self.df[
				self.df['release_date'].notna() &
				(self.df['release_date'].dt.year < 1900)
			]
			if len(very_old_dates) > 0:
				self.validation_errors.append("dates outside expected year")


	def _check_tag_format(self):
		"""Verify tag format and content."""
		if 'tags' not in self.df.columns:
			self.validation_errors.append("Tags column not found")
			return
			
		try:
			empty_tags = self.df[self.df['tags'].apply(lambda x: not isinstance(x, list) or len(x) == 0)]
			if len(empty_tags) > 0:
				self.validation_warnings.append(
					f"Found {len(empty_tags)} entries with no tags, using 'untagged'"
				)
			
			untagged = self.df[self.df['tags'].apply(lambda x: x == ['untagged'])]
			if len(untagged) > 0:
				self.validation_warnings.append(
					f"Found {len(untagged)} entries marked as 'untagged'"
				)
		except Exception as e:
			self.validation_errors.append(f"Error checking tag format: {str(e)}")

	def _check_tag_frequency(self):
		"""Analyze tag frequency to identify potential outliers."""
		if 'tags' not in self.df.columns:
			return
			
		try:
			# Initialize tag counter
			tag_counts = Counter()
			
			# Process tags
			for tags in self.df['tags']:
				if isinstance(tags, list) and tags != ['untagged']:
					tag_counts.update(tags)
			
			# Only consider a tag as single-use if it appears once
			single_use_tags = {
				tag for tag, count in tag_counts.items()
				if count == 1 and tag != 'untagged'
			}
			
			if single_use_tags:
				self.validation_warnings.append("single-use tags")
			
			self._tag_frequency = tag_counts
		except Exception as e:
			self.validation_errors.append(f"Error checking tag frequency: {str(e)}")



	def _check_location_format(self):
		"""Validate country/location format and values."""
		if 'Country / State' in self.df.columns:
			invalid_locations = []
			for loc in self.df['Country / State'].dropna():
				country = loc.split(',')[-1].strip()
				if not any(
					country.upper() == c.alpha_2 or
					country.upper() == c.alpha_3 or
					country.title() == c.name
					for c in pycountry.countries
				):
					invalid_locations.append(loc)
			
			if invalid_locations:
				self.validation_warnings.append(
					f"Found potentially invalid locations: {', '.join(invalid_locations)}"
				)

	def _check_length_values(self):
		"""Validate album length values."""
		if 'Length' in self.df.columns:
			# Combine standard formats with LP formats
			valid_formats = self.VALID_LENGTHS | self.VALID_LP_FORMATS
			
			# Find invalid lengths excluding empty strings
			invalid_lengths = self.df[
				~self.df['Length'].isin(valid_formats) & 
				(self.df['Length'].str.len() > 0)
			]['Length'].unique()
			
			if len(invalid_lengths) > 0:
				self.validation_warnings.append(
					f"Found invalid length values: {', '.join(str(l) for l in invalid_lengths)}"
				)

	@property
	def errors(self) -> List[str]:
		"""Return list of validation errors."""
		return self.validation_errors

	@property
	def warnings(self) -> List[str]:
		"""Return list of validation warnings."""
		return self.validation_warnings

	@property
	def tag_frequency(self) -> Dict[str, int]:
		"""Return tag frequency dictionary."""
		if self._tag_frequency is None:
			self._check_tag_frequency()
		return dict(self._tag_frequency)