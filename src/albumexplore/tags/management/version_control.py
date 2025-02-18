from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class TagVersion:
	id: str
	tag: str
	version: int
	timestamp: datetime
	notes: Optional[str]

class VersionControl:
	def __init__(self):
		self.tag_versions: Dict[str, List[TagVersion]] = {}

	def add_tag_version(self, tag: str, notes: Optional[str] = None) -> TagVersion:
		"""Add a new version of a tag."""
		version_id = str(uuid.uuid4())
		version_number = self._get_next_version(tag)
		
		new_version = TagVersion(
			id=version_id,
			tag=tag,
			version=version_number,
			timestamp=datetime.now(),
			notes=notes
		)
		
		if tag not in self.tag_versions:
			self.tag_versions[tag] = []
		self.tag_versions[tag].append(new_version)
		return new_version

	def get_tag_versions(self, tag: str) -> List[TagVersion]:
		"""Get all versions of a tag."""
		return self.tag_versions.get(tag, [])

	def get_latest_tag_version(self, tag: str) -> Optional[TagVersion]:
		"""Get the latest version of a tag."""
		versions = self.get_tag_versions(tag)
		return versions[-1] if versions else None

	def _get_next_version(self, tag: str) -> int:
		"""Get the next version number for a tag."""
		versions = self.get_tag_versions(tag)
		return versions[-1].version + 1 if versions else 1