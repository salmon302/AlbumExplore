import unittest
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer

class TestTagNormalizer(unittest.TestCase):
	def setUp(self):
		self.normalizer = TagNormalizer()

	def test_case_normalization(self):
		self.assertEqual(self.normalizer.normalize("DEATH METAL"), "death metal")
		self.assertEqual(self.normalizer.normalize("Post-Metal"), "post-metal")

	def test_hyphenation(self):
		self.assertEqual(self.normalizer.normalize("post metal"), "post-metal")
		self.assertEqual(self.normalizer.normalize("post - metal"), "post-metal")

	def test_compound_terms(self):
		self.assertEqual(self.normalizer.normalize("deathcore"), "deathcore")
		self.assertEqual(self.normalizer.normalize("progmetal"), "progressive metal")
		self.assertEqual(self.normalizer.normalize("techno metal"), "technical metal")

	def test_regional_variations(self):
		self.assertEqual(self.normalizer.normalize("metal-core"), "metalcore")
		self.assertEqual(self.normalizer.normalize("death-core"), "deathcore")

	def test_special_characters(self):
		self.assertEqual(self.normalizer.normalize("death & metal"), "death metal")
		self.assertEqual(self.normalizer.normalize("post.metal"), "post-metal")  # Updated expectation

if __name__ == '__main__':
	unittest.main()