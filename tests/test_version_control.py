import unittest
from datetime import datetime
from albumexplore.tags.management.version_control import VersionControl, TagVersion

class TestVersionControl(unittest.TestCase):
	def setUp(self):
		self.vc = VersionControl()

	def test_add_tag_version(self):
		version = self.vc.add_tag_version('heavy-metal', notes='Initial version')
		self.assertIsInstance(version, TagVersion)
		self.assertEqual(version.version, 1)
		self.assertEqual(version.tag, 'heavy-metal')
		self.assertEqual(len(self.vc.tag_versions['heavy-metal']), 1)

	def test_get_tag_versions(self):
		self.vc.add_tag_version('black-metal')
		self.vc.add_tag_version('black-metal', notes='Updated definition')
		versions = self.vc.get_tag_versions('black-metal')
		self.assertEqual(len(versions), 2)
		self.assertEqual(versions[0].version, 1)
		self.assertEqual(versions[1].version, 2)

	def test_get_latest_tag_version(self):
		self.vc.add_tag_version('death-metal')
		self.vc.add_tag_version('death-metal', notes='Minor correction')
		latest = self.vc.get_latest_tag_version('death-metal')
		self.assertEqual(latest.version, 2)
		self.assertEqual(latest.notes, 'Minor correction')

	def test_get_next_version(self):
		self.vc.add_tag_version('prog')
		self.vc.add_tag_version('prog')
		next_version = self.vc._get_next_version('prog')
		self.assertEqual(next_version, 3)

		# Test with no existing versions
		next_version = self.vc._get_next_version('new-tag')
		self.assertEqual(next_version, 1)

if __name__ == '__main__':
	unittest.main()