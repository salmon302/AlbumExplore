import unittest
from albumexplore.visualization.responsive import (
	ResponsiveManager, ScreenSize, Orientation, LayoutConfig
)

class TestResponsiveManager(unittest.TestCase):
	def setUp(self):
		self.manager = ResponsiveManager()

	def test_screen_size_detection(self):
		# Test small screen
		size, config = self.manager.update_screen_size(600, 800)
		self.assertEqual(size, ScreenSize.SMALL)
		self.assertEqual(self.manager.current_orientation, Orientation.PORTRAIT)

		# Test medium screen
		size, config = self.manager.update_screen_size(800, 600)
		self.assertEqual(size, ScreenSize.MEDIUM)
		self.assertEqual(self.manager.current_orientation, Orientation.LANDSCAPE)

		# Test large screen
		size, config = self.manager.update_screen_size(1200, 800)
		self.assertEqual(size, ScreenSize.LARGE)
		self.assertEqual(self.manager.current_orientation, Orientation.LANDSCAPE)

	def test_layout_adjustments(self):
		# Test table view adjustments
		self.manager.update_screen_size(600, 800)  # Small screen
		adjustments = self.manager.get_layout_adjustments("table")
		self.assertIn("columns", adjustments)
		self.assertEqual(adjustments["node_size_scale"], 0.7)
		self.assertFalse(adjustments["show_labels"])

		# Test network view adjustments
		self.manager.update_screen_size(1200, 800)  # Large screen
		adjustments = self.manager.get_layout_adjustments("network")
		self.assertEqual(adjustments["node_size_scale"], 1.0)
		self.assertTrue(adjustments["show_labels"])
		self.assertEqual(adjustments["controls_position"], "right")

	def test_optimal_dimensions(self):
		# Test small portrait screen
		self.manager.update_screen_size(600, 800)  # Set screen size first
		dimensions = self.manager.get_optimal_dimensions(600, 800)
		self.assertEqual(dimensions["width"], 600)  # Full width in portrait mode
		self.assertEqual(dimensions["height"], 800)
		self.assertEqual(dimensions["sidebar_width"], 0)  # No sidebar in portrait

		# Test large landscape screen
		self.manager.update_screen_size(1200, 800)  # Set screen size first
		dimensions = self.manager.get_optimal_dimensions(1200, 800)
		self.assertEqual(dimensions["width"], 900)  # 1200 - 300 sidebar
		self.assertEqual(dimensions["height"], 800)
		self.assertEqual(dimensions["sidebar_width"], 300)

	def test_layout_config_scaling(self):
		# Test small screen scaling
		size, config = self.manager.update_screen_size(600, 800)
		self.assertLess(config.node_size_scale, 1.0)
		self.assertLess(config.edge_thickness_scale, 1.0)

		# Test large screen scaling
		size, config = self.manager.update_screen_size(1200, 800)
		self.assertEqual(config.node_size_scale, 1.0)
		self.assertEqual(config.edge_thickness_scale, 1.0)

if __name__ == '__main__':
	unittest.main()