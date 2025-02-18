import unittest
from albumexplore.visualization.view_integration import (
	ViewIntegrationManager, ViewTransition, TransitionType
)
from albumexplore.visualization.state import ViewType, ViewState
from albumexplore.visualization.models import VisualNode, VisualEdge
from typing import Set

class TestViewIntegration(unittest.TestCase):
	def setUp(self):
		self.integration_manager = ViewIntegrationManager()
		self.test_nodes = [
			VisualNode(
				id="node1",
				label="Test Node 1",
				size=1.0,
				color="#000",
				shape="circle",
				data={"x": 100, "y": 100}
			),
			VisualNode(
				id="node2",
				label="Test Node 2",
				size=1.0,
				color="#000",
				shape="circle",
				data={"x": 200, "y": 200}
			)
		]
		self.test_edges = [
			VisualEdge(
				source="node1",
				target="node2",
				weight=1.0,
				thickness=1.0,
				color="#000",
				data={}
			)
		]
		self.test_state = ViewState(ViewType.TABLE)

	def test_default_transitions(self):
		"""Test default transition configurations."""
		# Test table to network transition
		transition = self.integration_manager.get_transition_config(
			ViewType.TABLE, ViewType.NETWORK
		)
		self.assertEqual(transition.transition_type, TransitionType.MORPH)
		self.assertEqual(transition.duration_ms, 500)
		
		# Test network to chord transition
		transition = self.integration_manager.get_transition_config(
			ViewType.NETWORK, ViewType.CHORD
		)
		self.assertEqual(transition.transition_type, TransitionType.FADE)
		self.assertEqual(transition.duration_ms, 300)

	def test_prepare_transition(self):
		"""Test transition preparation."""
		transition_data = self.integration_manager.prepare_transition(
			self.test_nodes,
			self.test_edges,
			self.test_state,
			ViewType.NETWORK
		)
		
		self.assertIn('transition', transition_data)
		self.assertIn('preserved_positions', transition_data)
		self.assertEqual(len(transition_data['preserved_positions']), 2)
		
		# Check preserved positions for morphing
		pos = transition_data['preserved_positions']['node1']
		self.assertEqual(pos['x'], 100)
		self.assertEqual(pos['y'], 100)

	def test_sync_selection(self):
		"""Test selection synchronization."""
		sync_called = {'value': False}
		test_ids = {'node1', 'node2'}
		
		def sync_handler(ids: Set[str]):
			self.assertEqual(ids, test_ids)
			sync_called['value'] = True
		
		# Register sync handler for network view
		self.integration_manager.register_sync_handler(ViewType.NETWORK, sync_handler)
		
		# Sync selection from table view
		self.integration_manager.sync_selection(test_ids, ViewType.TABLE)
		
		self.assertTrue(sync_called['value'])
		self.assertEqual(self.integration_manager.shared_selections, test_ids)

	def test_shared_state(self):
		"""Test shared state management."""
		# Set some selections
		test_ids = {'node1', 'node2'}
		self.integration_manager.sync_selection(test_ids, ViewType.TABLE)
		
		state = self.integration_manager.get_shared_state()
		self.assertIn('selections', state)
		self.assertIn('active_transitions', state)
		
		# Check selections
		self.assertEqual(set(state['selections']), test_ids)
		
		# Check transitions
		self.assertTrue(len(state['active_transitions']) > 0)
		transition = state['active_transitions'][0]
		self.assertIn('source', transition)
		self.assertIn('target', transition)
		self.assertIn('type', transition)

if __name__ == '__main__':
	unittest.main()