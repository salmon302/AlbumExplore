import pytest
import pandas as pd
from datetime import datetime
from albumexplore.data.cleaners.data_cleaner import DataCleaner

@pytest.fixture
def sample_df():
	"""Create a sample DataFrame with data that needs cleaning."""
	return pd.DataFrame({
		'Artist': [' Test Band  ', 'Another Band'],
		'Album': ['Test Album ', ' Second Album'],
		'Release Date': ['January 1', 'February 15'],
		'Length': ['LP', 'EP'],
		'Genre / Subgenres': ['  Progressive Metal , Heavy Metal', 'Black Metal,Death Metal  '],
		'Vocal Style': ['Clean ', ' Harsh'],
		'Country / State': ['London, United Kingdom', 'New York, US'],
		'tags': [[], []]  # Empty tags before cleaning
	})

def test_clean_strings():
	"""Test string cleaning functionality."""
	cleaner = DataCleaner()
	df = pd.DataFrame({
		'Artist': [' Test Band  ', 'Another Band '],
		'Album': ['Test Album ', ' Second Album'],
		'Vocal Style': ['Clean ', ' Harsh']
	})
	
	cleaned_df = cleaner._clean_strings(df)
	assert cleaned_df['Artist'].iloc[0] == 'Test Band'
	assert cleaned_df['Album'].iloc[1] == 'Second Album'
	assert cleaned_df['Vocal Style'].iloc[0] == 'Clean'

def test_standardize_dates():
	"""Test date standardization."""
	cleaner = DataCleaner()
	current_year = datetime.now().year
	
	df = pd.DataFrame({
		'Release Date': [
			'January 1',                  # Month Day format
			'February 15, 2023',          # Month Day, Year format
			'March 20 2022',              # Month Day Year format
			'2021',                       # Year only format
			'early 2020',                 # Special case with year
			None,                         # None value
			'TBA',                        # Invalid format
			'April 1st, 2019'             # Month Day(st/nd/rd/th), Year format
		]
	})
	
	cleaned_df = cleaner._standardize_dates(df)
	
	# Test Month Day format (should use current year)
	assert cleaned_df['release_date'].iloc[0].year == current_year
	assert cleaned_df['release_date'].iloc[0].month == 1
	assert cleaned_df['release_date'].iloc[0].day == 1
	
	# Test Month Day, Year format
	assert cleaned_df['release_date'].iloc[1].year == 2023
	assert cleaned_df['release_date'].iloc[1].month == 2
	assert cleaned_df['release_date'].iloc[1].day == 15
	
	# Test Month Day Year format
	assert cleaned_df['release_date'].iloc[2].year == 2022
	assert cleaned_df['release_date'].iloc[2].month == 3
	assert cleaned_df['release_date'].iloc[2].day == 20
	
	# Test Year only format
	assert cleaned_df['release_date'].iloc[3].year == 2021
	assert cleaned_df['release_date'].iloc[3].month == 1
	assert cleaned_df['release_date'].iloc[3].day == 1
	
	# Test special case with year
	assert cleaned_df['release_date'].iloc[4].year == 2020
	assert cleaned_df['release_date'].iloc[4].month == 1
	assert cleaned_df['release_date'].iloc[4].day == 1
	
	# Test None value
	assert pd.isna(cleaned_df['release_date'].iloc[5])
	
	# Test invalid format
	assert pd.isna(cleaned_df['release_date'].iloc[6])
	
	# Test Month Day(st/nd/rd/th), Year format
	assert cleaned_df['release_date'].iloc[7].year == 2019
	assert cleaned_df['release_date'].iloc[7].month == 4
	assert cleaned_df['release_date'].iloc[7].day == 1

def test_standardize_locations():
	"""Test location standardization."""
	cleaner = DataCleaner()
	df = pd.DataFrame({
		'Country / State': ['London, United Kingdom', 'New York, US', 'Invalid']
	})
	
	cleaned_df = cleaner._standardize_locations(df)
	assert cleaned_df['country_code'].iloc[0] == 'GB'
	assert cleaned_df['country_code'].iloc[1] == 'US'
	assert cleaned_df['country_code'].iloc[2] == 'Invalid'  # Keep original for invalid locations

def test_clean_tags():
	"""Test tag cleaning."""
	cleaner = DataCleaner()
	df = pd.DataFrame({
		'Genre / Subgenres': ['  Progressive Metal , Heavy Metal', 'Black Metal,Death Metal  ']
	})
	
	cleaned_df = cleaner._clean_tags(df)
	assert 'progressive metal' in cleaned_df['tags'].iloc[0]
	assert 'heavy metal' in cleaned_df['tags'].iloc[0]
	assert 'black metal' in cleaned_df['tags'].iloc[1]
	assert 'death metal' in cleaned_df['tags'].iloc[1]

def test_clean_dataframe(sample_df):
	"""Test complete DataFrame cleaning."""
	cleaner = DataCleaner()
	current_year = datetime.now().year
	
	# Test with Genre / Subgenres column present
	cleaned_df = cleaner.clean_dataframe(sample_df)
	
	# Check string cleaning
	assert cleaned_df['Artist'].iloc[0] == 'Test Band'
	assert cleaned_df['Album'].iloc[1] == 'Second Album'
	
	# Check date standardization
	assert cleaned_df['release_date'].iloc[0].year == current_year
	assert cleaned_df['release_date'].iloc[0].month == 1
	
	# Check location standardization
	assert cleaned_df['country_code'].iloc[0] == 'GB'
	assert cleaned_df['country_code'].iloc[1] == 'US'
	
	# Check tag cleaning
	assert 'progressive metal' in cleaned_df['tags'].iloc[0]
	assert 'heavy metal' in cleaned_df['tags'].iloc[0]
	
	# Test with Genre / Subgenres column missing
	sample_df_no_genre = sample_df.drop(columns=['Genre / Subgenres'])
	cleaned_df_no_genre = cleaner.clean_dataframe(sample_df_no_genre)
	assert cleaned_df_no_genre['tags'].iloc[0] == ['untagged']
	
	# Test with empty Genre / Subgenres
	sample_df_empty_genre = sample_df.copy()
	sample_df_empty_genre['Genre / Subgenres'] = ''
	cleaned_df_empty_genre = cleaner.clean_dataframe(sample_df_empty_genre)
	assert cleaned_df_empty_genre['tags'].iloc[0] == ['untagged']