import unittest
import os
from pathlib import Path
from albumexplore.scraping.progarchives.parser import ProgArchivesParser

class TestProgArchivesParser(unittest.TestCase):
    def setUp(self):
        # Point to the directory containing the real sample file in the workspace
        self.sample_dir = Path(r'ProgArchives Data/Additional HTML Structure Examples')
        self.parser = ProgArchivesParser(local_data_root=self.sample_dir)
        self.sample_filename = 'CIRCE LINK & CHRISTIAN NESMITH Arcana reviews.html'
        self.sample_file_path = self.sample_dir / self.sample_filename

    def test_parse_real_sample_file(self):
        if not self.sample_file_path.exists():
            self.skipTest(f'Sample file not found at {self.sample_file_path}')

        result = self.parser.get_album_data(self.sample_file_path)

        self.assertNotIn('error', result, f'Parser returned error: {result.get('error')}')

        self.assertEqual(result.get('album_title'), 'ARCANA')
        self.assertEqual(result.get('artist_name'), 'Circe Link & Christian Nesmith')
        self.assertEqual(result.get('year'), 2024)
        
        tracks = result.get('tracks', [])
        self.assertTrue(len(tracks) > 0, 'No tracks extracted')
        
        self.assertEqual(result.get('album_type'), 'Studio Album')
        self.assertIn('rating_value', result)

if __name__ == '__main__':
    unittest.main()
