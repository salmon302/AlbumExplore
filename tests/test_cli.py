import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from albumexplore.main import search_albums, get_tag_relationships

class TestCLI(unittest.TestCase):
	def setUp(self):
		# Sample test data
		self.test_data = pd.DataFrame({
			'Artist': ['Test Artist', 'Another Artist'],
			'Album': ['Test Album', 'Another Album'],
			'Release Date': ['January 1', 'January 2'],
			'tags': [['metal', 'prog-metal'], ['black metal', 'death metal']]
		})
		
	def test_search_albums(self):
		"""Test album search functionality."""
		results = search_albums(self.test_data, 'metal')
		self.assertEqual(len(results), 2)
		
		results = search_albums(self.test_data, 'prog')
		self.assertEqual(len(results), 1)
	
	@patch('albumexplore.tags.TagNormalizer')
	@patch('albumexplore.tags.TagRelationships')
	def test_tag_relationships(self, mock_relationships, mock_normalizer):
		"""Test tag relationship functionality."""
		mock_normalizer.normalize.return_value = 'metal'
		mock_relationships.get_related_tags.return_value = [
			('prog-metal', 0.8),
			('death metal', 0.7)
		]
		
		all_tags = {'metal', 'prog-metal', 'death metal'}
		result = get_tag_relationships('metal', mock_normalizer, mock_relationships, all_tags)
		self.assertIsNotNone(result)
		
		result = get_tag_relationships('invalid', mock_normalizer, mock_relationships, all_tags)
		self.assertIsNone(result)

if __name__ == '__main__':
	unittest.main()