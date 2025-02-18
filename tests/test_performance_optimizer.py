import unittest
from src.albumexplore.visualization.performance_optimizer import PerformanceOptimizer, PerformanceMetrics
import time

class TestPerformanceOptimizer(unittest.TestCase):
	def setUp(self):
		self.optimizer = PerformanceOptimizer(target_fps=30.0)
		self.test_metrics = PerformanceMetrics(
			frame_time=0.0,
			render_time=10.0,
			layout_time=5.0,
			clustering_time=3.0,
			node_count=500,
			edge_count=1000,
			visible_node_count=200,
			visible_edge_count=400,
			memory_usage=100.0
		)

	def test_frame_timing(self):
		"""Test frame timing functionality."""
		start_time = self.optimizer.start_frame()
		time.sleep(0.016)  # Simulate 16ms frame time
		# Set frame time in test_metrics before calling end_frame
		self.test_metrics.frame_time = (time.perf_counter() - start_time) * 1000
		self.optimizer.end_frame(start_time, self.test_metrics)
		self.assertIsNotNone(self.optimizer.current_metrics)
		self.assertGreater(self.optimizer.current_metrics.frame_time, 15)

	def test_optimization_suggestions(self):
		"""Test optimization suggestions generation."""
		# Simulate poor performance
		self.test_metrics.node_count = 2000
		self.test_metrics.edge_count = 3000
		# Set frame time directly
		self.test_metrics.frame_time = 100.0  # 100ms frame time
		self.optimizer.end_frame(self.optimizer.start_frame(), self.test_metrics)
		suggestions = self.optimizer.get_optimization_suggestions()
		self.assertGreater(len(suggestions), 0)
		self.assertTrue(any("LOD" in s for s in suggestions))

	def test_performance_stats(self):
		"""Test performance statistics calculation."""
		# Add some test metrics
		for _ in range(5):
			start_time = self.optimizer.start_frame()
			self.test_metrics.frame_time = 16.0  # Simulate consistent 60 FPS
			self.optimizer.end_frame(start_time, self.test_metrics)
		
		stats = self.optimizer.get_performance_stats()
		
		# Verify stats are calculated
		self.assertIn('avg_fps', stats)
		self.assertIn('avg_frame_time', stats)
		self.assertIn('avg_render_time', stats)

	def test_detail_reduction(self):
		"""Test detail reduction decision."""
		# Test with good performance
		self.test_metrics.frame_time = 16.0  # 60 FPS
		self.optimizer.end_frame(self.optimizer.start_frame(), self.test_metrics)
		self.assertFalse(self.optimizer.should_reduce_detail())
		
		# Test with poor performance
		self.test_metrics.frame_time = 100.0  # 10 FPS
		self.optimizer.end_frame(self.optimizer.start_frame(), self.test_metrics)
		self.assertTrue(self.optimizer.should_reduce_detail())

	def test_batch_size_optimization(self):
		"""Test batch size optimization."""
		# Test batch size reduction under load
		self.test_metrics.frame_time = 100.0
		self.optimizer.end_frame(self.optimizer.start_frame(), self.test_metrics)
		new_size = self.optimizer.get_optimal_batch_size(100)
		self.assertLess(new_size, 100)
		
		# Test batch size increase under good performance
		self.test_metrics.frame_time = 16.0
		self.optimizer.end_frame(self.optimizer.start_frame(), self.test_metrics)
		new_size = self.optimizer.get_optimal_batch_size(50)
		self.assertGreater(new_size, 50)

if __name__ == '__main__':
	unittest.main()