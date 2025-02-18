from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid
from dataclasses import dataclass

class ChangeType(Enum):
	MERGE = "merge"
	SPLIT = "split"
	RENAME = "rename"
	DELETE = "delete"
	ADD = "add"

class ReviewStatus(Enum):
	PENDING = "pending"
	APPROVED = "approved"
	REJECTED = "rejected"
	ROLLBACK = "rollback"

@dataclass
class TagChange:
	id: str
	change_type: ChangeType
	old_value: Union[str, List[str]]
	new_value: Union[str, List[str]]
	timestamp: datetime
	automated_flags: List[str]
	status: ReviewStatus
	reviewer: Optional[str]
	notes: Optional[str]

class ReviewQueue:
	def __init__(self):
		self.pending_changes: Dict[str, TagChange] = {}
		self.change_history: List[TagChange] = []
		self.automated_checks = [
			self._check_frequency_threshold,
			self._check_relationship_impact,
			self._check_naming_convention
		]

	def add_change(self, change_type: ChangeType, old_value: Union[str, List[str]], 
				  new_value: Union[str, List[str]], notes: Optional[str] = None) -> str:
		"""Add a new change to the review queue."""
		change_id = str(uuid.uuid4())
		flags = self._run_automated_checks(old_value, new_value, change_type)
		
		change = TagChange(
			id=change_id,
			change_type=change_type,
			old_value=old_value,
			new_value=new_value,
			timestamp=datetime.now(),
			automated_flags=flags,
			status=ReviewStatus.PENDING,
			reviewer=None,
			notes=notes
		)
		
		self.pending_changes[change_id] = change
		return change_id

	def approve_change(self, change_id: str, reviewer: str, notes: Optional[str] = None) -> bool:
		"""Approve a pending change."""
		if change_id not in self.pending_changes:
			return False
			
		change = self.pending_changes[change_id]
		change.status = ReviewStatus.APPROVED
		change.reviewer = reviewer
		if notes:
			change.notes = notes
			
		self.change_history.append(change)
		del self.pending_changes[change_id]
		return True

	def reject_change(self, change_id: str, reviewer: str, notes: Optional[str] = None) -> bool:
		"""Reject a pending change."""
		if change_id not in self.pending_changes:
			return False
			
		change = self.pending_changes[change_id]
		change.status = ReviewStatus.REJECTED
		change.reviewer = reviewer
		if notes:
			change.notes = notes
			
		self.change_history.append(change)
		del self.pending_changes[change_id]
		return True

	def rollback_change(self, change_id: str) -> bool:
		"""Rollback an approved change."""
		for change in self.change_history:
			if change.id == change_id and change.status == ReviewStatus.APPROVED:
				rollback_id = self.add_change(
					change_type=change.change_type,
					old_value=change.new_value,
					new_value=change.old_value,
					notes=f"Rollback of change {change_id}"
				)
				return True
		return False

	def get_pending_changes(self) -> List[TagChange]:
		"""Get all pending changes."""
		return list(self.pending_changes.values())

	def get_change_history(self) -> List[TagChange]:
		"""Get the history of all processed changes."""
		return self.change_history

	def _run_automated_checks(self, old_value: Union[str, List[str]], 
							new_value: Union[str, List[str]], 
							change_type: ChangeType) -> List[str]:
		"""Run all automated checks on a proposed change."""
		flags = []
		for check in self.automated_checks:
			result = check(old_value, new_value, change_type)
			if result:
				flags.append(result)
		return flags

	def _check_frequency_threshold(self, old_value: Union[str, List[str]], 
								 new_value: Union[str, List[str]], 
								 change_type: ChangeType) -> Optional[str]:
		"""Check if the change affects frequently used tags."""
		# Implementation will be added later
		return None

	def _check_relationship_impact(self, old_value: Union[str, List[str]], 
								 new_value: Union[str, List[str]], 
								 change_type: ChangeType) -> Optional[str]:
		"""Check if the change significantly impacts tag relationships."""
		# Implementation will be added later
		return None

	def _check_naming_convention(self, old_value: Union[str, List[str]], 
							   new_value: Union[str, List[str]], 
							   change_type: ChangeType) -> Optional[str]:
		"""Check if the new value follows naming conventions."""
		# Implementation will be added later
		return None