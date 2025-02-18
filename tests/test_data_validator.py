import unittest
import pandas as pd
from datetime import datetime
from albumexplore.data.validators.data_validator import DataValidator


class TestDataValidator(unittest.TestCase):
	def test_check_required_columns(self):
		validator = DataValidator(pd.DataFrame({'Artist': ['A'], 'Album': ['B']}))
		validator.validate()
		self.assertIn("Missing required columns", str(validator.errors))

	def test_check_data_types(self):
		df = pd.DataFrame({
			'release_date': [None, 'invalid', datetime(2025, 1, 1)],
			'Artist': ['', 'Artist', 'Test'],
			'Album': ['Album', '', 'Test']
		})
		validator = DataValidator(df)
		validator.validate()
		errors_str = str(validator.errors)
		# Check for missing required columns error
		self.assertIn("Missing required columns", errors_str)
		# Check for missing album title error
		self.assertIn("Missing album title", errors_str)

	def test_check_date_validity(self):
		current_year = datetime.now().year
		max_future_year = current_year + 5
		
		# Test date within allowed range
		df = pd.DataFrame({
			'Artist': ['Test'],
			'Album': ['Test'],
			'Release Date': [f'{current_year + 1}-01-01'],  # Next year should be valid
			'Length': ['LP'],
			'Genre / Subgenres': ['Test'],
			'Vocal Style': ['Clean'],
			'Country / State': ['US']
		})
		df['release_date'] = pd.to_datetime(df['Release Date'])
		validator = DataValidator(df)
		validator.validate()
		self.assertNotIn("dates outside expected year", str(validator.errors))
		
		# Test date too far in the future
		df = pd.DataFrame({
			'Artist': ['Test'],
			'Album': ['Test'],
			'Release Date': [f'{current_year + 10}-01-01'],  # 10 years in future should fail
			'Length': ['LP'],
			'Genre / Subgenres': ['Test'],
			'Vocal Style': ['Clean'],
			'Country / State': ['US']
		})
		df['release_date'] = pd.to_datetime(df['Release Date'])
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("dates outside expected year", str(validator.errors))

	def test_check_tag_format(self):
		df = pd.DataFrame({
			'Artist': ['Test'] * 3,
			'Album': ['Test'] * 3,
			'Release Date': ['2024-01-01'] * 3,
			'Length': ['LP'] * 3,
			'Genre / Subgenres': ['Test'] * 3,
			'Vocal Style': ['Clean'] * 3,
			'Country / State': ['US'] * 3,
			'tags': [[], ['tag'], None]
		})
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("entries with no tags", str(validator.warnings))

	def test_check_tag_frequency(self):
		# Test with no single-use tags
		df = pd.DataFrame({
			'Artist': ['Test'] * 3,
			'Album': ['Test'] * 3,
			'Release Date': ['2024-01-01'] * 3,
			'Length': ['LP'] * 3,
			'Genre / Subgenres': ['Test'] * 3,
			'Vocal Style': ['Clean'] * 3,
			'Country / State': ['US'] * 3,
			'tags': [['tag1'], ['tag2'], ['tag1', 'tag2']]  # Each tag used multiple times
		})
		validator = DataValidator(df)
		validator.validate()
		self.assertNotIn("single-use tags", str(validator.warnings))
		
		# Test with single-use tags
		df_single = pd.DataFrame({
			'Artist': ['Test'] * 2,
			'Album': ['Test'] * 2,
			'Release Date': ['2024-01-01'] * 2,
			'Length': ['LP'] * 2,
			'Genre / Subgenres': ['Test'] * 2,
			'Vocal Style': ['Clean'] * 2,
			'Country / State': ['US'] * 2,
			'tags': [['tag1'], ['tag2']]  # Each tag used only once
		})
		validator_single = DataValidator(df_single)
		validator_single.validate()
		self.assertIn("single-use tags", str(validator_single.warnings))

	def test_check_location_format(self):
		df = pd.DataFrame({'Country / State': ['US', 'invalid', None]})
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("potentially invalid locations", str(validator.warnings))

	def test_check_length_values(self):
		df = pd.DataFrame({
			'Artist': ['Test'],
			'Album': ['Test'],
			'Release Date': ['2024-01-01'],
			'Length': ['invalid'],
			'Genre / Subgenres': ['Test'],
			'Vocal Style': ['Clean'],
			'Country / State': ['US']
		})
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("invalid length values", str(validator.errors))

	def test_untagged_handling(self):
		df = pd.DataFrame({
			'Artist': ['Test'],
			'Album': ['Test'],
			'Release Date': ['2024-01-01'],
			'Length': ['LP'],
			'Genre / Subgenres': ['Test'],
			'Vocal Style': ['Clean'],
			'Country / State': ['US'],
			'tags': [['untagged']]
		})
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("entries marked as 'untagged'", str(validator.warnings))

	def test_error_logging(self):
		with self.assertLogs(level='WARNING') as log:
			df = pd.DataFrame({
				'Artist': ['Test'],
				'Album': ['Test'],
				'Release Date': ['2024-01-01'],
				'Length': ['LP'],
				'Genre / Subgenres': ['Test'],
				'Vocal Style': ['Clean'],
				'Country / State': ['US'],
				'tags': [None]
			})
			validator = DataValidator(df)
			validator.validate()
			self.assertTrue(any("Error checking tag format" in msg for msg in log.output))

	def test_valid_data_validation(self):
		"""Test validation with valid data."""
		current_year = datetime.now().year
		df = pd.DataFrame({
			'Artist': ['Test Band', 'Another Band'],
			'Album': ['Test Album', 'Second Album'],
			'Release Date': [f'{current_year}-01-15', f'{current_year}-01-20'],
			'Length': ['LP', 'EP'],
			'Genre / Subgenres': ['Progressive Metal, Heavy Metal', 'Black Metal, Death Metal'],
			'Vocal Style': ['Clean', 'Harsh'],
			'Country / State': ['US', 'GB'],
			'tags': [
				['progressive metal', 'heavy metal'],
				['black metal', 'death metal']
			]
		})
		validator = DataValidator(df)
		self.assertTrue(validator.validate())
		self.assertEqual(len(validator.errors), 0)
		self.assertEqual(len(validator.warnings), 0)

	def test_single_word_tags(self):
		"""Test single-word tag detection."""
		df = pd.DataFrame({
			'Artist': ['Test Band'],
			'Album': ['Test Album'],
			'Release Date': ['2024-01-01'],
			'Length': ['LP'],
			'Genre / Subgenres': ['prog'],
			'Vocal Style': ['Clean'],
			'Country / State': ['US'],
			'tags': [['prog']]
		})
		validator = DataValidator(df)
		validator.validate()
		self.assertIn("single-word tags", str(validator.warnings))

