import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
from albumexplore.data.parsers import CSVParser
from albumexplore.data.cleaners import DataCleaner
from albumexplore.data.validators.data_validator import DataValidator
from albumexplore.tags.normalizer import TagNormalizer
from albumexplore.tags.relationships import TagRelationships
from albumexplore.tags.analysis import TagAnalyzer

@pytest.fixture
def sample_csv_path(tmp_path):
	"""Create a sample CSV file for testing."""
	csv_content = '''2025 Progressive Metal Albums,,Releases:,609,
,,LPs:,521,,,,,,,,
,,EPs:,89,,,,,,,,
Artist,Album,Release Date,Length,Genre / Subgenres,Vocal Style,Country / State,Bandcamp,Spotify,YouTube,Amazon,Apple Music
Test Band,Test Album,January 15,LP,"Progressive Metal, Heavy Metal, Unique Genre",Clean,United Kingdom,BC,S,,,
Another Band,Second Album,February 1,EP,"Black Metal, Death Metal",Harsh,United States,BC,S,,,
Third Band,Third Album,March 15,LP,"Progressive Metal, Technical Death Metal",Mixed,Germany,BC,S,,,'''
	
	csv_file = tmp_path / "test_albums.csv"
	csv_file.write_text(csv_content)
	return csv_file

def test_data_processing_pipeline(sample_csv_path):
	"""Test complete data processing pipeline."""
	# Parse CSV
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	# Validate data
	validator = DataValidator(df)
	validator.validate()
	assert len(validator.validation_errors) == 0
	assert len(validator.validation_warnings) > 0  # We expect warnings for single-use tags

	
	# Clean data
	cleaner = DataCleaner()
	cleaned_df = cleaner.clean_dataframe(df)
	
	# Verify cleaning results
	assert cleaned_df['country_code'].iloc[0] == 'GB'
	assert cleaned_df['country_code'].iloc[1] == 'US'
	assert cleaned_df['country_code'].iloc[2] == 'DE'
	assert cleaned_df['release_date'].iloc[0].year == 2025

def test_tag_system_integration(sample_csv_path):
	"""Test tag system components integration."""
	# Process data
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	cleaner = DataCleaner()
	df = cleaner.clean_dataframe(df)
	
	# Initialize tag components
	normalizer = TagNormalizer()
	relationships = TagRelationships()
	analyzer = TagAnalyzer(df)
	
	# Test tag normalization
	assert normalizer.normalize('progressive metal') == 'progressive metal'
	assert normalizer.normalize('prog') == 'progressive'
	
	# Test tag relationships
	related_tags = relationships.get_related_tags('progressive metal')
	assert len(related_tags) > 0
	assert any('metal' in tag for tag, weight in related_tags)
	
	# Test tag analysis
	stats = analyzer.analyze_tags()
	assert stats['unique_tags'] > 0
	assert stats['avg_tags_per_album'] > 0

def test_end_to_end_workflow(sample_csv_path):
	"""Test complete workflow from data import to tag analysis."""
	# 1. Data Processing
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	validator = DataValidator(df)
	is_valid = validator.validate()
	if not is_valid:
		print("Validation errors:", validator.errors)
		print("Validation warnings:", validator.warnings)
	assert is_valid
	
	cleaner = DataCleaner()
	df = cleaner.clean_dataframe(df)
	
	# 2. Tag Processing
	normalizer = TagNormalizer()
	relationships = TagRelationships()
	analyzer = TagAnalyzer(df)
	
	# 3. Analysis
	stats = analyzer.analyze_tags()
	relationships = analyzer.calculate_relationships()
	clusters = analyzer.get_tag_clusters()
	
	# Verify results
	assert stats['total_tags'] > 0
	assert len(relationships) > 0
	assert len(clusters) > 0
	
	# 4. Verify tag normalization
	normalized_tags = set()
	for tags in df['tags']:
		normalized_tags.update(normalizer.normalize_list(tags))
	
	assert 'progressive metal' in normalized_tags
	assert 'death metal' in normalized_tags