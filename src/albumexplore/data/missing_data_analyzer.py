from typing import Dict, List, Set, Tuple
import pandas as pd
import logging
from pathlib import Path
from .parsers.csv_parser import CSVParser
from collections import defaultdict

logger = logging.getLogger(__name__)

class MissingDataAnalyzer:
	"""Analyzes patterns of missing data in album dataset."""
	
	def __init__(self, df: pd.DataFrame):
		self.df = df
		self.missing_patterns = defaultdict(list)
		self.file_specific_issues = defaultdict(dict)
		self.priority_fields = {
			'Album': {'priority': 1, 'severity': 'critical'},
			'Genre / Subgenres': {'priority': 2, 'severity': 'high'},
			'Release Date': {'priority': 3, 'severity': 'high'},
			'Vocal Style': {'priority': 4, 'severity': 'medium'},
			'Country / State': {'priority': 5, 'severity': 'medium'},
			'Length': {'priority': 6, 'severity': 'low'},
			'Artist': {'priority': 1, 'severity': 'critical'}
		}
		self.streaming_fields = {
			'Bandcamp', 'Spotify', 'Google Play', 'YouTube', 'Amazon', 'Apple Music'
		}
		
	def analyze(self) -> Dict[str, Dict]:
		"""Run comprehensive missing data analysis."""
		results = {
			'missing_counts': self._analyze_missing_counts(),
			'missing_patterns': self._analyze_missing_patterns(),
			'completeness_score': self._calculate_completeness_score(),
			'recommendations': self._generate_recommendations()
		}
		return results
	
	def _analyze_missing_counts(self) -> Dict[str, Dict[str, int]]:
		"""Analyze count and percentage of missing values per column with priority."""
		total_rows = len(self.df)
		missing_info = {}
		
		# Analyze priority fields first
		for field, config in sorted(self.priority_fields.items(), key=lambda x: x[1]['priority']):
			if field in self.df.columns:
				missing_count = self.df[field].isna().sum()
				empty_string_count = (self.df[field] == '').sum() if self.df[field].dtype == object else 0
				total_missing = missing_count + empty_string_count
				
				missing_info[field] = {
					'missing_count': int(total_missing),
					'missing_percentage': round((total_missing / total_rows) * 100, 2),
					'null_count': int(missing_count),
					'empty_string_count': int(empty_string_count),
					'priority': config['priority'],
					'severity': config['severity']
				}
		
		# Analyze streaming fields separately
		for field in self.streaming_fields:
			if field in self.df.columns:
				missing_count = self.df[field].isna().sum()
				empty_string_count = (self.df[field] == '').sum() if self.df[field].dtype == object else 0
				total_missing = missing_count + empty_string_count
				
				missing_info[field] = {
					'missing_count': int(total_missing),
					'missing_percentage': round((total_missing / total_rows) * 100, 2),
					'null_count': int(missing_count),
					'empty_string_count': int(empty_string_count),
					'priority': 7,  # Lower priority for streaming fields
					'severity': 'low'
				}
		
		return missing_info
	
	def _analyze_missing_patterns(self) -> Dict[str, List[Dict]]:
		"""Analyze patterns in missing data."""
		patterns = {
			'common_combinations': self._find_missing_combinations(),
			'sequential_missing': self._find_sequential_missing(),
			'partial_data': self._find_partial_data()
		}
		return patterns
	
	def _find_missing_combinations(self) -> List[Dict]:
		"""Find common combinations of missing fields."""
		missing_mask = self.df.isna() | (self.df == '')
		pattern_counts = defaultdict(int)
		
		for _, row in missing_mask.iterrows():
			missing_cols = tuple(sorted(row[row].index))
			if missing_cols:
				pattern_counts[missing_cols] += 1
		
		return [
			{'columns': list(cols), 'count': count}
			for cols, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
			if count > 1  # Only include patterns that occur multiple times
		]
	
	def _find_sequential_missing(self) -> List[Dict]:
		"""Find sequences of missing data that might indicate systematic issues."""
		sequences = []
		for column in self.df.columns:
			missing_mask = self.df[column].isna() | (self.df[column] == '')
			if missing_mask.any():
				# Find runs of missing values
				runs = self._find_runs(missing_mask)
				if runs:
					sequences.append({
						'column': column,
						'sequences': [{'start': start, 'length': length} 
									for start, length in runs if length > 2]
					})
		return sequences
	
	def _find_runs(self, mask: pd.Series) -> List[Tuple[int, int]]:
		"""Helper function to find runs of True values in a boolean mask."""
		runs = []
		start = None
		length = 0
		
		for i, value in enumerate(mask):
			if value:
				if start is None:
					start = i
				length += 1
			elif start is not None:
				if length > 2:  # Only record runs longer than 2
					runs.append((start, length))
				start = None
				length = 0
		
		if start is not None and length > 2:
			runs.append((start, length))
		
		return runs
	
	def _find_partial_data(self) -> List[Dict]:
		"""Find patterns of partially filled data."""
		partial_patterns = []
		
		# Check for partial dates
		if 'Release Date' in self.df.columns:
			partial_dates = self.df[
				self.df['Release Date'].str.contains(r'^[0-9]{4}$', na=False)
			]
			if not partial_dates.empty:
				partial_patterns.append({
					'type': 'year_only_dates',
					'count': len(partial_dates),
					'example_indices': partial_dates.index[:5].tolist()
				})
		
		# Check for partial location data
		if 'Country / State' in self.df.columns:
			missing_state = self.df[
				~self.df['Country / State'].str.contains(',', na=False)
			]
			if not missing_state.empty:
				partial_patterns.append({
					'type': 'country_only_locations',
					'count': len(missing_state),
					'example_indices': missing_state.index[:5].tolist()
				})
		
		return partial_patterns
	
	def _calculate_completeness_score(self) -> Dict[str, float]:
		"""Calculate completeness scores for the dataset."""
		scores = {}
		required_cols = {'Artist', 'Album', 'Release Date', 'Length'}
		
		# Overall completeness
		total_cells = self.df.size
		filled_cells = total_cells - self.df.isna().sum().sum()
		scores['overall'] = round((filled_cells / total_cells) * 100, 2)
		
		# Required fields completeness
		for col in required_cols:
			if col in self.df.columns:
				valid_count = self.df[col].notna().sum()
				scores[f'{col}_completeness'] = round((valid_count / len(self.df)) * 100, 2)
		
		return scores
	
	def _generate_recommendations(self) -> List[Dict[str, str]]:
		"""Generate prioritized recommendations."""
		recommendations = []
		missing_counts = self._analyze_missing_counts()
		
		# Handle priority fields first
		for field, stats in missing_counts.items():
			if field in self.priority_fields:
				if stats['missing_percentage'] > 0:
					recommendations.append({
						'field': field,
						'priority': stats['priority'],
						'severity': stats['severity'],
						'message': f"Priority {stats['priority']}: Fix missing {field} data ({stats['missing_percentage']}%)"
					})
		
		# Add streaming recommendations last
		streaming_issues = [
			(field, stats) for field, stats in missing_counts.items()
			if field in self.streaming_fields and stats['missing_percentage'] > 50
		]
		if streaming_issues:
			recommendations.append({
				'field': 'Streaming Links',
				'priority': 7,
				'severity': 'low',
				'message': "Optional: Missing streaming links are expected for obscure albums"
			})
		
		return sorted(recommendations, key=lambda x: x['priority'])

def analyze_missing_data(csv_dir: Path) -> Dict:
	"""Analyze missing data in CSV files."""
	try:
		parser = CSVParser(csv_dir)
		df = parser.parse()
		
		analyzer = MissingDataAnalyzer(df)
		results = analyzer.analyze()
		
		return results
		
	except Exception as e:
		logger.error(f"Error analyzing missing data: {str(e)}", exc_info=True)
		return {}