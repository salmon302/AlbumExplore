import unittest
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from albumexplore.visualization.views.enhanced_network_view import EnhancedNetworkView
from albumexplore.visualization.models import VisualNode, VisualEdge

class TestEnhancedNetworkView(unittest.TestCase):
	def setUp(self):
		self.app = QApplication([])
		self.view = EnhancedNetworkView()
		
		# Initialize test data
		self.test_nodes = [
			VisualNode(id=f"node_{i}", label=f"Node {i}", size=10,
					  color="#000000", shape="circle", 
					  data={'x': i*10, 'y': i*10})
			for i in range(5)
		]
		self.test_edges = [
			VisualEdge(source=f"node_{i}", target=f"node_{i+1}", 
					  weight=1.0, color="#000000")
			for i in range(4)
		]
		
	def tearDown(self):
		# Clean up test data
		self.test_nodes = []
		self.test_edges = []
		
		# Clean up view and application
		self.view.deleteLater()
		self.app.quit()

	def test_update_data(self):
		"""Test data update with clustering."""
		self.view.update_data(self.test_nodes, self.test_edges)
		self.assertEqual(len(self.view.nodes), len(self.test_nodes))
		self.assertEqual(len(self.view.edges), len(self.test_edges))

	def test_performance_debugging(self):
		"""Test performance debugging features."""
		nodes = [
			VisualNode(id='1', label='Node 1', data={'x': 0, 'y': 0}),
			VisualNode(id='2', label='Node 2', data={'x': 100, 'y': 100})
		]
		edges = [VisualEdge(source='1', target='2', weight=1.0)]
		
		self.view.update_data(nodes, edges)
		self.view.show()
		QTest.qWait(100)
		
		report = self.view.performance_debugger.get_performance_report()
		self.assertIn("Performance Report", report)
		self.assertIn("Node Count: 2", report)
		self.assertIn("Edge Count: 1", report)

	def test_copy_functionality(self):
		"""Test copy functionality for selected nodes."""
		test_node = VisualNode(id='test1', label='Test Node', 
							  data={'x': 0, 'y': 0, 'custom': 'value'})
		self.view.update_data([test_node], [])
		
		self.view.selected_ids.add('test1')
		QTest.keyClick(self.view, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
		
		clipboard = QApplication.clipboard()
		content = clipboard.text()
		self.assertIn('test1', content)
		self.assertIn('Test Node', content)
		self.assertIn('value', content)

	def test_performance_metrics_collection(self):
		"""Test that performance metrics are properly collected."""
		self.view.update_data(self.test_nodes, self.test_edges)
		self.view.show()
		
		self.view.viewport_scale = 2.0
		self.view.update()
		QTest.qWait(100)
		
		metrics = self.view.performance_debugger.snapshots[-1]
		self.assertGreater(metrics.frame_time, 0)
		self.assertGreater(metrics.render_time, 0)
		self.assertEqual(metrics.node_count, len(self.test_nodes))
		self.assertEqual(metrics.edge_count, len(self.test_edges))
		
	def test_copy_selected_nodes(self):
		"""Test copying multiple selected nodes."""
		self.view.update_data(self.test_nodes, self.test_edges)
		self.view.selected_ids = {'node_0', 'node_1'}
		
		QTest.keyClick(self.view, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
		
		clipboard = QApplication.clipboard()
		content = clipboard.text()
		data = json.loads(content)
		
		self.assertEqual(len(data), 2)
		self.assertEqual(data[0]['id'], 'node_0')
		self.assertEqual(data[1]['id'], 'node_1')

if __name__ == '__main__':
	unittest.main()
