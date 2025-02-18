from typing import List, Dict, Optional, Set
import pandas as pd
from collections import Counter
import pycountry
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataValidator:
	"""Validates and checks data quality for album dataset."""
	
	PRIORITY_FIELDS = {
		'Album': {'priority': 1, 'severity': 'critical'},
		'Genre / Subgenres': {'priority': 2, 'severity': 'high'},
		'Release Date': {'priority': 3, 'severity': 'high'},
		'Vocal Style': {'priority': 4, 'severity': 'medium'},
		'Country / State': {'priority': 5, 'severity': 'medium'},
		'Length': {'priority': 6, 'severity': 'low'},
		'Artist': {'priority': 1, 'severity': 'critical'},  # Artist is critical but usually complete
	}
	
	STREAMING_FIELDS = {
		'Bandcamp', 'Spotify', 'Google Play', 'YouTube', 'Amazon', 'Apple Music'
	}
	
	REQUIRED_COLUMNS = {
		'Artist', 'Album', 'Release Date', 'Length',
		'Genre / Subgenres', 'Vocal Style', 'Country / State'
	}
	
	VALID_LENGTHS = {'LP', 'EP', 'Single', 'Demo', 'Split', 'Compilation'}
	VALID_LP_FORMATS = {f"{i}xLP" for i in range(1, 25)}  # Handle up to 24xLP formats
	
	def __init__(self, df: pd.DataFrame):
		self.df = df.copy()
		self._tag_frequency = None
		self.validation_errors = []
		self.validation_warnings = []
		self.current_year = datetime.now().year

	def validate(self) -> bool:
		"""Run all validation checks and return True if data is valid."""
		self.validation_errors = []
		self.validation_warnings = []
		
		# Handle missing data first
		self._handle_missing_data()
		
		# Continue with other validations
		self._check_required_columns()
		self._check_date_validity()
		if 'tags' in self.df.columns:
			self._check_tag_format()
			self._check_tag_frequency()
		self._check_location_format()
		self._check_length_values()
		
		# Only count dictionary-type errors with critical or high severity
		critical_errors = [
			e for e in self.validation_errors 
			if isinstance(e, dict) and 
			e.get('severity') in ['critical', 'high']
		]
		
		return len(critical_errors) == 0


	def _check_required_columns(self):
		"""Verify all required columns are present."""
		missing_cols = self.REQUIRED_COLUMNS - set(self.df.columns)
		if missing_cols:
			self.validation_errors.append({
				'field': 'columns',
				'severity': 'critical',
				'message': f"Missing required columns: {', '.join(missing_cols)}",
				'count': len(missing_cols)
			})

	def _check_data_types(self):
		"""Verify data types of key columns with priority-based validation."""
		# Check date columns first
		date_columns = ['release_date', 'Release Date']
		for date_col in date_columns:
			if date_col in self.df.columns:
				try:
					pd.to_datetime(self.df[date_col])
				except (ValueError, TypeError):
					self.validation_errors.append({
						'field': date_col,
						'severity': 'high',
						'message': "invalid release dates"
					})
				
				invalid_dates = self.df[date_col].isna().sum()
				if invalid_dates > 0:
					self.validation_errors.append({
						'field': date_col,
						'severity': 'high',
						'count': invalid_dates,
						'message': "invalid release dates"
					})
		
		# Check priority fields
		for field, config in sorted(self.PRIORITY_FIELDS.items(), key=lambda x: x[1]['priority']):
			if field in self.df.columns:
				empty_mask = (
					self.df[field].isna() | 
					(self.df[field].astype(str).str.strip() == '')
				)
				missing_count = empty_mask.sum()
				if missing_count > 0:
					severity = config['severity']
					self.validation_errors.append({
						'field': field,
						'severity': severity,
						'count': missing_count,
						'message': f"Missing {field} data ({missing_count} entries)"
					})

	def _check_date_validity(self):
		"""Check if release dates are within expected range and format."""
		current_year = datetime.now().year
		max_future_year = current_year + 5
		
		if 'Release Date' in self.df.columns:
			try:
				dates = pd.to_datetime(self.df['Release Date'])
				future_dates = dates[dates.dt.year > max_future_year]
				if not future_dates.empty:
					self.validation_errors.append({
						'field': 'Release Date',
						'severity': 'high',
						'message': "dates outside expected year",
						'count': len(future_dates)
					})
			except (ValueError, TypeError):
				self.validation_errors.append({
					'field': 'Release Date',
					'severity': 'high',
					'message': "Invalid release date format detected",
					'count': 1
				})




	def _check_tag_format(self):

		"""Verify tag format and content."""
		if 'tags' not in self.df.columns:
			self.validation_errors.append("Tags column not found")
			return
			
		try:
			empty_tags = self.df[self.df['tags'].apply(lambda x: not isinstance(x, list) or len(x) == 0)]
			if len(empty_tags) > 0:
				self.validation_warnings.append("entries with no tags")
			
			untagged = self.df[self.df['tags'].apply(lambda x: x == ['untagged'])]
			if len(untagged) > 0:
				self.validation_warnings.append("entries marked as 'untagged'")
				
			# Check for invalid tag formats
			invalid_tags = self.df[self.df['tags'].apply(lambda x: x is None or not isinstance(x, list))]
			if len(invalid_tags) > 0:
				msg = "Error checking tag format: Invalid tag format detected"
				logger.warning(msg)
				self.validation_errors.append(msg)
				
		except Exception as e:
			msg = f"Error checking tag format: {str(e)}"
			logger.warning(msg)
			self.validation_errors.append(msg)

	def _check_tag_frequency(self):
		"""Analyze tag frequency and format to identify potential issues."""
		if 'tags' not in self.df.columns:
			return
			
		try:
			# Process all tags and count their frequency
			tag_counts = Counter()
			single_word_tags = set()
			
			for tags in self.df['tags']:
				if isinstance(tags, list) and tags != ['untagged']:
					# Split any remaining combined tags (e.g., "prog metal | unique-tag")
					processed_tags = []
					for tag in tags:
						if '|' in tag:
							processed_tags.extend(t.strip().lower() for t in tag.split('|'))
						else:
							processed_tags.append(tag.lower())
					
					# Update frequency counts
					tag_counts.update(processed_tags)
					
					# Check for single-word tags
					for tag in processed_tags:
						if len(tag.split()) == 1 and tag != 'untagged':
							single_word_tags.add(tag)
			
			# Common genre terms to exclude from warnings
			common_terms = {
				'metal', 'rock', 'jazz', 'blues', 'progressive', 'death', 'black',
				'doom', 'thrash', 'folk', 'ambient', 'electronic', 'industrial',
				'punk', 'grunge', 'classical', 'experimental', 'alternative',
				'hardcore', 'indie', 'pop', 'post', 'psychedelic', 'symphonic',
				'technical', 'traditional', 'avant-garde', 'fusion', 'instrumental'
			}
			
			# Check for single-use tags
			single_use_tags = {
				tag for tag, count in tag_counts.items()
				if count == 1 and 
				tag != 'untagged' and
				not any(term in tag.lower().replace('-', ' ').split() for term in common_terms)
			}
			
			if single_use_tags:
				self.validation_warnings.append("single-use tags")
				
			# Add warning for single-word tags that aren't in common terms
			uncommon_single_word = single_word_tags - common_terms
			if uncommon_single_word:
				self.validation_warnings.append("single-word tags")
			
			self._tag_frequency = tag_counts
		except Exception as e:
			self.validation_errors.append(f"Error checking tag frequency: {str(e)}")







	def _check_location_format(self):
		"""Validate country/location format and values."""
		if 'Country / State' in self.df.columns:
			invalid_locations = []
			for loc in self.df['Country / State'].dropna():
				# Split on comma and check the last part (country)
				parts = [p.strip() for p in loc.split(',')]
				country = parts[-1]
				
				# Common country codes and names
				valid = (
					country == 'UK' or  # Special case for UK
					country == 'US' or  # Special case for US
					any(
						country.upper() == c.alpha_2 or
						country.upper() == c.alpha_3 or
						country.title() == c.name
						for c in pycountry.countries
					)
				)
				
				if not valid:
					invalid_locations.append(loc)
			
			if invalid_locations:
				self.validation_warnings.append("potentially invalid locations")

	def _check_length_values(self):
		"""Validate album length values."""
		if 'Length' in self.df.columns:
			valid_formats = self.VALID_LENGTHS | self.VALID_LP_FORMATS
			invalid_lengths = self.df[
				~self.df['Length'].isin(valid_formats) & 
				(self.df['Length'].str.len() > 0)
			]['Length'].unique()
			
			if len(invalid_lengths) > 0:
				self.validation_errors.append("invalid length values")

	def _analyze_missing_counts(self) -> Dict[str, Dict[str, float]]:
		"""Analyze missing data counts and percentages."""
		missing_counts = {}
		total_rows = len(self.df)
		
		for field in set(list(self.PRIORITY_FIELDS.keys()) + list(self.STREAMING_FIELDS)):
			if field in self.df.columns:
				empty_mask = (
					self.df[field].isna() | 
					(self.df[field].astype(str).str.strip() == '')
				)
				missing = empty_mask.sum()
				missing_counts[field] = {
					'missing_count': missing,
					'missing_percentage': round((missing / total_rows) * 100, 2)
				}
		
		return missing_counts

	def _generate_recommendations(self) -> List[Dict[str, str]]:
		"""Generate recommendations based on priority fields."""
		recommendations = []
		missing_counts = self._analyze_missing_counts()
		
		# Handle priority fields first
		for field, config in sorted(self.PRIORITY_FIELDS.items(), key=lambda x: x[1]['priority']):
			if field in missing_counts and missing_counts[field]['missing_percentage'] > 0:
				recommendations.append({
					'field': field,
					'severity': config['severity'],
					'priority': config['priority'],
					'suggestion': f"Priority {config['priority']}: {missing_counts[field]['missing_percentage']}% missing in {field}. Requires immediate attention."
				})
		
		# Handle streaming fields separately with lower priority
		for field in self.STREAMING_FIELDS:
			if field in missing_counts and missing_counts[field]['missing_percentage'] > 50:
				recommendations.append({
					'field': field,
					'severity': 'low',
					'priority': 7,
					'suggestion': f"Optional: Missing {field} links ({missing_counts[field]['missing_percentage']}%). Not critical for core functionality."
				})
		
		return sorted(recommendations, key=lambda x: (x['priority'], -float(x['suggestion'].split('%')[0])))

	@property
	def errors(self) -> List[Dict[str, str]]:
		"""Return list of validation errors with severity levels."""
		return self.validation_errors

	@property
	def warnings(self) -> List[Dict[str, str]]:
		"""Return list of validation warnings with severity levels."""
		return self.validation_warnings

	@property
	def tag_frequency(self) -> Dict[str, int]:
		"""Return tag frequency dictionary."""
		if self._tag_frequency is None:
			self._check_tag_frequency()
		return dict(self._tag_frequency)

	def _is_future_release(self, row: pd.Series) -> bool:
		"""Check if an entry is for a future release."""
		if 'Release Date' in row:
			try:
				date = pd.to_datetime(row['Release Date'])
				return date.year > self.current_year
			except:
				# If date parsing fails, check filename year
				return row.get('_file_year', self.current_year) > self.current_year
		return False

	def _handle_missing_data(self) -> None:
		"""Handle missing data based on whether it's a future or past release."""
		for idx, row in self.df.iterrows():
			is_future = self._is_future_release(row)
			
			# Check if required columns exist before accessing
			if 'Album' in self.df.columns:
				if pd.isna(row['Album']) or str(row['Album']).strip() == '':
					if is_future:
						self.df.at[idx, 'Album'] = 'TBA'
					else:
						self.validation_errors.append({
							'field': 'Album',
							'severity': 'critical',
							'message': f"Missing album title for past release by {row.get('Artist', 'Unknown')}"
						})
			
			if 'Release Date' in self.df.columns:
				if pd.isna(row['Release Date']) or str(row['Release Date']).strip() == '':
					if is_future:
						self.df.at[idx, 'Release Date'] = f"{row.get('_file_year', self.current_year)}-TBA"
					else:
						self.validation_errors.append({
							'field': 'Release Date',
							'severity': 'high',
							'message': f"Missing release date for {row.get('Album', 'Unknown')} by {row.get('Artist', 'Unknown')}"
						})
			
			if 'Genre / Subgenres' in self.df.columns:
				if pd.isna(row['Genre / Subgenres']) or str(row['Genre / Subgenres']).strip() == '':
					if not is_future:
						self.validation_errors.append({
							'field': 'Genre / Subgenres',
							'severity': 'high',
							'message': f"Missing genre for {row.get('Album', 'Unknown')} by {row.get('Artist', 'Unknown')}"
						})
			
			if 'Vocal Style' in self.df.columns:
				if pd.isna(row['Vocal Style']) or str(row['Vocal Style']).strip() == '':
					if 'Genre / Subgenres' in row and not pd.isna(row['Genre / Subgenres']):
						vocal_style = self._infer_vocal_style(row['Genre / Subgenres'])
						if vocal_style:
							self.df.at[idx, 'Vocal Style'] = vocal_style
							self.validation_warnings.append({
								'field': 'Vocal Style',
								'severity': 'low',
								'message': f"Inferred vocal style '{vocal_style}' for {row.get('Album', 'Unknown')}"
							})

	def _infer_vocal_style(self, genre: str) -> Optional[str]:
		"""Infer vocal style from genre information."""
		genre = genre.lower()
		
		# Common genre-vocal style mappings
		if any(x in genre for x in ['death metal', 'black metal', 'deathcore']):
			return 'Harsh'
		elif any(x in genre for x in ['prog-rock', 'symphonic', 'power metal']):
			return 'Clean'
		elif any(x in genre for x in ['prog-metal', 'metalcore']):
			return 'Mixed'
		elif 'instrumental' in genre:
			return 'Instrumental'
		
		return None

	@property
	def recommendations(self) -> List[Dict[str, str]]:
		"""Return prioritized recommendations for data improvement."""
		return self._generate_recommendations()