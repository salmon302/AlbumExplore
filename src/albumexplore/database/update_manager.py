import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .models import Album, Tag, UpdateHistory
from .db_utils import log_update

class UpdateManager:
	def __init__(self, db: Session):
		self.db = db

	def track_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Track changes between old and new data"""
		changes = {}
		for key in new_data:
			if key in old_data and old_data[key] != new_data[key]:
				changes[key] = {
					"old": old_data[key],
					"new": new_data[key]
				}
		return changes

	def update_album(self, album_id: str, updates: Dict[str, Any]) -> Optional[Album]:
		album = self.db.query(Album).filter(Album.id == album_id).first()
		if not album:
			return None

		old_data = {
			"artist": album.pa_artist_name_on_album,
			"title": album.title,
			"release_date": album.release_date,
			"release_year": album.release_year,
			"length": album.length,
			"vocal_style": album.vocal_style,
			"country": album.country,
			"raw_tags": json.loads(album.raw_tags) if album.raw_tags else [],
			"platforms": json.loads(album.platforms) if album.platforms else {}
		}

		for key, value in updates.items():
			if hasattr(album, key):
				if key in ["raw_tags", "platforms"]:
					setattr(album, key, json.dumps(value))
				else:
					setattr(album, key, value)

		changes = self.track_changes(old_data, updates)
		if changes:
			log_update(self.db, "album", album_id, "update", changes)
			self.db.commit()
			self.db.refresh(album)

		return album

	def update_tag(self, tag_id: str, updates: Dict[str, Any]) -> Optional[Tag]:
		tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
		if not tag:
			return None

		old_data = {
			"name": tag.name,
			"category": tag.category,
			"aliases": json.loads(tag.aliases) if tag.aliases else [],
			"frequency": tag.frequency
		}

		for key, value in updates.items():
			if hasattr(tag, key):
				if key == "aliases":
					setattr(tag, key, json.dumps(value))
				else:
					setattr(tag, key, value)

		changes = self.track_changes(old_data, updates)
		if changes:
			log_update(self.db, "tag", tag_id, "update", changes)
			self.db.commit()
			self.db.refresh(tag)

		return tag

	def get_update_history(self, entity_type: str, entity_id: str) -> List[UpdateHistory]:
		return self.db.query(UpdateHistory).filter(
			UpdateHistory.entity_type == entity_type,
			UpdateHistory.entity_id == entity_id
		).order_by(UpdateHistory.timestamp.desc()).all()

	def revert_update(self, history_id: int) -> bool:
		history = self.db.query(UpdateHistory).filter(
			UpdateHistory.id == history_id
		).first()
		
		if not history:
			return False

		changes = json.loads(history.changes)
		old_values = {k: v["old"] for k, v in changes.items()}

		if history.entity_type == "album":
			self.update_album(history.entity_id, old_values)
		elif history.entity_type == "tag":
			self.update_tag(history.entity_id, old_values)

		return True

	def log_update(self, entity_type: str, entity_id: str, change_type: str, changes: dict) -> UpdateHistory:
		"""Log an update to the history table."""
		return log_update(self.db, entity_type, entity_id, change_type, changes)