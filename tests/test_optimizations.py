import unittest
from albumexplore.visualization.optimizations import ViewOptimizer, DetailLevel, Viewport
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewType

class TestViewOptimizer(unittest.TestCase):
	def setUp(self):
		self.optimizer = ViewOptimizer()
		self.viewport = Viewport(x=0, y=0, width=100, height=100, zoom=1.0)
		
		# Test data
		self.test_node = VisualNode(
			id="test1",
			label="Test Node",
			size=10,
			color="#000000",
			shape="circle",
			data={"x": 50, "y": 50}
		)
		
		self.test_edge = VisualEdge(
			source="test1",
			target="test2",
			weight=1.0,
			thickness=2.0,
			color="#000000",
			data={"source_x": 0, "source_y": 0, "target_x": 100, "target_y": 100}
		)

	def test_detail_level_with_density(self):
		# Test with different node densities
		sparse_nodes = [self.test_node]  # Low density
		dense_nodes = [self.test_node.copy() for _ in range(100)]  # High density
		
		# High zoom, low density should be HIGH detail
		detail = self.optimizer.get_detail_level(2.0, len(sparse_nodes), self.viewport)
		self.assertEqual(detail, DetailLevel.HIGH)
		
		# High zoom, high density should reduce detail
		detail = self.optimizer.get_detail_level(2.0, len(dense_nodes), self.viewport)
		self.assertEqual(detail, DetailLevel.MEDIUM)
		
		# Low zoom, high density should be LOW detail
		detail = self.optimizer.get_detail_level(0.5, len(dense_nodes), self.viewport)
		self.assertEqual(detail, DetailLevel.LOW)

	def test_force_directed_edge_bundling(self):
		# Create parallel edges
		edges = []
		for i in range(5):
			edge = VisualEdge(
				source=f"source{i}",
				target=f"target{i}",
				weight=1.0,
				thickness=1.0,
				color="#000000",
				data={
					"source_x": 0,
					"source_y": i,
					"target_x": 100,
					"target_y": i + 1
				}
			)
			edges.append(edge)
		
		# Test force-directed bundling
		bundled = self.optimizer._bundle_force_directed(edges)
		self.assertLess(len(bundled), len(edges))
		
		# Check bundle properties
		for edge in bundled:
			self.assertIn("bundle_size", edge.data)
			if edge.data["bundle_size"] > 1:
				self.assertGreater(edge.thickness, 1.0)

	def test_edge_filtering(self):
		# Create edges with different weights
		edges = [
			VisualEdge("s1", "t1", weight=1.0, thickness=1.0, color="#000", data={}),
			VisualEdge("s2", "t2", weight=2.0, thickness=1.0, color="#000", data={}),
			VisualEdge("s3", "t3", weight=3.0, thickness=1.0, color="#000", data={})
		]
		
		# Test filtering at different detail levels
		filtered_high = self.optimizer._filter_edge_crossings(edges, DetailLevel.HIGH)
		self.assertEqual(len(filtered_high), len(edges))
		
		filtered_low = self.optimizer._filter_edge_crossings(edges, DetailLevel.LOW)
		self.assertLess(len(filtered_low), len(edges))
		
		# Check that highest weight edges are kept
		self.assertEqual(filtered_low[0].weight, 3.0)

	def test_viewport_area_calculation(self):
		viewport = Viewport(x=0, y=0, width=100, height=100, zoom=2.0)
		area = viewport.get_visible_area()
		self.assertEqual(area, 2500.0)  # 100*100 / (2.0*2.0)

	def test_node_optimization(self):
		# Test node in viewport
		nodes = self.optimizer.optimize_nodes([self.test_node], self.viewport)
		self.assertEqual(len(nodes), 1)
		
		# Test node outside viewport
		outside_node = VisualNode(
			id="test2",
			label="Outside Node",
			size=10,
			color="#000000",
			shape="circle",
			data={"x": 200, "y": 200}
		)
		nodes = self.optimizer.optimize_nodes([outside_node], self.viewport)
		self.assertEqual(len(nodes), 0)

	def test_edge_optimization(self):
		# Test edge optimization for different view types
		edges = self.optimizer.optimize_edges(
			[self.test_edge], 
			self.viewport,
			ViewType.NETWORK
		)
		self.assertEqual(len(edges), 1)
		
		# Test edge bundling
		edges = self.optimizer.bundle_edges(
			[self.test_edge, self.test_edge], 
			ViewType.CHORD,
			DetailLevel.HIGH  # Add the missing detail_level parameter
		)
		self.assertEqual(len(edges), 1)
		self.assertGreater(edges[0].weight, self.test_edge.weight)

	def test_viewport_checks(self):
		# Test node viewport check
		self.assertTrue(
			self.optimizer._is_in_viewport(self.test_node, self.viewport)
		)
		
		# Test edge viewport check
		self.assertTrue(
			self.optimizer._is_edge_in_viewport(self.test_edge, self.viewport)
		)

if __name__ == '__main__':
	unittest.main()
