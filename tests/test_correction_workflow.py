import unittest
from unittest.mock import Mock, patch
import pandas as pd
from albumexplore.tags.management.correction_workflow import (
	CorrectionWorkflow, CorrectionConfidence, CorrectionSuggestion
)
from albumexplore.tags.management.review_queue import ReviewQueue, ChangeType
from albumexplore.tags.analysis.tag_similarity import TagSimilarity
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer

class TestCorrectionWorkflow(unittest.TestCase):
	def setUp(self):
		# Create test data
		test_data = pd.DataFrame({
			'tags': [
				['metal', 'heavy-metal', 'heavy metal'],
				['black-metal', 'blackmetal', 'atmospheric'],
				['death-metal', 'deathmetal', 'technical'],
				['prog', 'progressive', 'prog-metal']
			]
		})
		
		# Initialize components
		self.analyzer = TagAnalyzer(test_data)
		self.review_queue = ReviewQueue()
		self.tag_similarity = TagSimilarity(self.analyzer)
		self.workflow = CorrectionWorkflow(self.review_queue, self.tag_similarity)

	def test_suggest_corrections(self):
		suggestions = self.workflow.suggest_corrections('heavy metal')
		
		self.assertIsInstance(suggestions, list)
		if suggestions:  # We might get suggestions based on normalization
			suggestion = suggestions[0]
			self.assertIsInstance(suggestion, CorrectionSuggestion)
			self.assertEqual(suggestion.original_tag, 'heavy metal')
			self.assertIsInstance(suggestion.confidence, CorrectionConfidence)

	def test_apply_correction(self):
		change_id = self.workflow.apply_correction(
			original_tag='prog',
			corrected_tag='progressive',
			reviewer='test_user',
			notes='Using full term'
		)
		
		self.assertIsNotNone(change_id)
		self.assertIn(change_id, self.review_queue.pending_changes)
		
		change = self.review_queue.pending_changes[change_id]
		self.assertEqual(change.change_type, ChangeType.RENAME)
		self.assertEqual(change.old_value, 'prog')
		self.assertEqual(change.new_value, 'progressive')

	def test_get_correction_history(self):
		# Apply a correction first
		self.workflow.apply_correction(
			original_tag='blackmetal',
			corrected_tag='black-metal',
			reviewer='test_user'
		)
		
		history = self.workflow.get_correction_history('blackmetal')
		self.assertIsInstance(history, list)
		if history:
			self.assertEqual(len(history), 1)
			self.assertEqual(history[0].old_value, 'blackmetal')
			self.assertEqual(history[0].new_value, 'black-metal')

	def test_validate_correction(self):
		# Test valid correction (prog -> progressive)
		issues = self.workflow.validate_correction(
			original_tag='prog',
			corrected_tag='progressive'
		)
		
		self.assertIsInstance(issues, list)
		self.assertEqual(len(issues), 0)  # Should be valid correction
		
		# Test invalid correction (completely unrelated)
		issues = self.workflow.validate_correction(
			original_tag='heavy metal',
			corrected_tag='jazz fusion'
		)
		self.assertTrue(len(issues) > 0)  # Should have semantic meaning issue
		
		# Test equivalent correction
		issues = self.workflow.validate_correction(
			original_tag='heavy metal',
			corrected_tag='heavy-metal'
		)
		self.assertTrue(len(issues) > 0)  # Should flag as equivalent after normalization

	def test_confidence_levels(self):
		self.assertEqual(
			self.workflow._get_confidence_level(0.9),
			CorrectionConfidence.HIGH
		)
		self.assertEqual(
			self.workflow._get_confidence_level(0.6),
			CorrectionConfidence.MEDIUM
		)
		self.assertEqual(
			self.workflow._get_confidence_level(0.3),
			CorrectionConfidence.LOW
		)

if __name__ == '__main__':
	unittest.main()