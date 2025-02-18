import pytest
from pathlib import Path
import pandas as pd
from albumexplore.data.parsers import CSVParser
from albumexplore.data.validators.data_validator import DataValidator
from albumexplore.data.cleaners.data_cleaner import DataCleaner

@pytest.fixture
def sample_csv_path(tmp_path):
	"""Create a sample CSV file for testing."""
	csv_content = '''2025 Progressive Metal Albums,,Releases:,609,
,,LPs:,521,,,,,,,,
,,EPs:,89,,,,,,,,
,,Debuts:,102,,,,,,,,
,,Reissue/Special:,7,,,,,,,,
Artist,Album,Release Date,Length,Genre / Subgenres,Vocal Style,Country / State,Bandcamp,Spotify,YouTube,Amazon,Apple Music
Test Band,Test Album,2025-01-01,LP,Progressive Metal | unique-tag,Clean,US,BC,S,,,
Another Band,Second Album,2025-01-02,EP,"Black metal, Death metal",Harsh,"London, UK",BC,S,,,'''
	
	csv_file = tmp_path / "test_albums.csv"
	csv_file.write_text(csv_content)
	return csv_file

def test_csv_parser_initialization(sample_csv_path):
	"""Test CSV parser initialization."""
	parser = CSVParser(sample_csv_path)
	assert parser.file_path == sample_csv_path
	assert parser._data is None

def test_csv_parsing(sample_csv_path):
	"""Test basic CSV parsing functionality."""
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	assert isinstance(df, pd.DataFrame)
	assert len(df) == 2  # Two album entries
	assert 'tags' in df.columns
	assert 'release_date' in df.columns
	
	# Check for untagged entries
	assert df['tags'].apply(lambda x: x == ['untagged']).any() == False

def test_tag_cleaning(sample_csv_path):
	"""Test tag cleaning and normalization."""
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	# Check first row tags
	assert isinstance(df['tags'].iloc[0], list)
	assert 'progressive metal' in df['tags'].iloc[0]
	assert 'unique-tag' in df['tags'].iloc[0]
	
	# Check second row tags
	assert len(df['tags'].iloc[1]) == 2
	assert 'black metal' in df['tags'].iloc[1]
	assert 'death metal' in df['tags'].iloc[1]

def test_date_parsing(sample_csv_path):
	"""Test date parsing and validation."""
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	assert pd.notna(df['release_date'].iloc[0])
	assert df['release_date'].iloc[0].year == 2025
	assert df['release_date'].iloc[0].month == 1
	assert df['release_date'].iloc[0].day == 1

def test_date_parsing_with_file_year(tmp_path):
	"""Test date parsing with year from filename."""
	# Create a sample CSV file with 2018 in the name
	csv_content = '''Artist,Album,Release Date,Length,Genre / Subgenres,Vocal Style,Country / State,Bandcamp,Spotify,YouTube,Amazon,Apple Music
Test Band,Test Album,January 26,LP,Progressive Metal,Clean,US,BC,S,,,
Another Band,Second Album,March 15 2019,EP,Black metal,Harsh,UK,BC,S,,,'''
	
	# Use the same filename format as the actual CSV files
	csv_file = tmp_path / "_r_ProgMetal _ Yearly Albums - 2018.csv"
	csv_file.write_text(csv_content)
	
	parser = CSVParser(csv_file)
	df = parser.parse()
	
	# Check that January 26 gets the year from filename
	assert pd.notna(df['release_date'].iloc[0])
	assert df['release_date'].iloc[0].year == 2018
	assert df['release_date'].iloc[0].month == 1
	assert df['release_date'].iloc[0].day == 26
	
	# Check that explicit year in date is preserved
	assert df['release_date'].iloc[1].year == 2019
	assert df['release_date'].iloc[1].month == 3
	assert df['release_date'].iloc[1].day == 15

def test_data_validation(sample_csv_path):
	"""Test data validation functionality."""
	parser = CSVParser(sample_csv_path)
	df = parser.parse()
	
	# Validate data
	validator = DataValidator(df)
	validator.validate()
	assert len(validator.validation_errors) == 0
	# We expect warnings for single-use tags
	assert "single-use tags" in str(validator.validation_warnings)
