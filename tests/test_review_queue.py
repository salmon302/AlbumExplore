import unittest
from datetime import datetime
from albumexplore.tags.management.review_queue import ReviewQueue, ChangeType, ReviewStatus, TagChange

class TestReviewQueue(unittest.TestCase):
	def setUp(self):
		self.queue = ReviewQueue()

	def test_add_change(self):
		change_id = self.queue.add_change(
			change_type=ChangeType.MERGE,
			old_value=['heavy-metal', 'heavy metal'],
			new_value='heavy-metal',
			notes='Standardizing hyphenation'
		)
		
		self.assertIsNotNone(change_id)
		self.assertEqual(len(self.queue.pending_changes), 1)
		
		change = self.queue.pending_changes[change_id]
		self.assertEqual(change.change_type, ChangeType.MERGE)
		self.assertEqual(change.status, ReviewStatus.PENDING)
		self.assertEqual(change.notes, 'Standardizing hyphenation')

	def test_approve_change(self):
		change_id = self.queue.add_change(
			change_type=ChangeType.RENAME,
			old_value='prog',
			new_value='progressive',
			notes='Using full term'
		)
		
		success = self.queue.approve_change(change_id, reviewer='test_user', notes='Approved')
		
		self.assertTrue(success)
		self.assertEqual(len(self.queue.pending_changes), 0)
		self.assertEqual(len(self.queue.change_history), 1)
		
		approved_change = self.queue.change_history[0]
		self.assertEqual(approved_change.status, ReviewStatus.APPROVED)
		self.assertEqual(approved_change.reviewer, 'test_user')

	def test_reject_change(self):
		change_id = self.queue.add_change(
			change_type=ChangeType.DELETE,
			old_value='unused-tag',
			new_value='',
			notes='Remove unused tag'
		)
		
		success = self.queue.reject_change(change_id, reviewer='test_user', notes='Keep for historical data')
		
		self.assertTrue(success)
		self.assertEqual(len(self.queue.pending_changes), 0)
		self.assertEqual(len(self.queue.change_history), 1)
		
		rejected_change = self.queue.change_history[0]
		self.assertEqual(rejected_change.status, ReviewStatus.REJECTED)
		self.assertEqual(rejected_change.notes, 'Keep for historical data')

	def test_rollback_change(self):
		# First approve a change
		change_id = self.queue.add_change(
			change_type=ChangeType.RENAME,
			old_value='black-metal',
			new_value='blackmetal',
			notes='Remove hyphen'
		)
		self.queue.approve_change(change_id, reviewer='test_user')
		
		# Then try to rollback
		success = self.queue.rollback_change(change_id)
		
		self.assertTrue(success)
		self.assertEqual(len(self.queue.pending_changes), 1)
		
		rollback_change = list(self.queue.pending_changes.values())[0]
		self.assertEqual(rollback_change.old_value, 'blackmetal')
		self.assertEqual(rollback_change.new_value, 'black-metal')

	def test_get_pending_changes(self):
		self.queue.add_change(
			change_type=ChangeType.ADD,
			old_value='',
			new_value='new-tag',
			notes='Adding new tag'
		)
		
		pending = self.queue.get_pending_changes()
		self.assertEqual(len(pending), 1)
		self.assertEqual(pending[0].change_type, ChangeType.ADD)
		self.assertEqual(pending[0].status, ReviewStatus.PENDING)

	def test_get_change_history(self):
		change_id = self.queue.add_change(
			change_type=ChangeType.MERGE,
			old_value=['tag1', 'tag2'],
			new_value='tag1',
			notes='Merging similar tags'
		)
		self.queue.approve_change(change_id, reviewer='test_user')
		
		history = self.queue.get_change_history()
		self.assertEqual(len(history), 1)
		self.assertEqual(history[0].status, ReviewStatus.APPROVED)

if __name__ == '__main__':
	unittest.main()