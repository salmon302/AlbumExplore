import json
from datetime import datetime
from sqlalchemy.orm import Session
from .models import UpdateHistory

def log_update(db: Session, entity_type: str, entity_id: str, 
			   change_type: str, changes: dict):
	"""Log an update to the history with transaction and error handling."""
	try:
		with db.begin():
			history = UpdateHistory(
				entity_type=entity_type,
				entity_id=entity_id,
				change_type=change_type,
				changes=json.dumps(changes)
			)
			db.add(history)
			return history
	except Exception as e:
		db.rollback()
		raise ValueError(f"Error logging update: {e}") from e


def generate_stable_id(*parts: str) -> str:
	"""Generate a stable UUID based on the provided string parts.

	This uses UUID5 with a namespaced value derived from the joined
   , lowercased parts. Use this for entity IDs that should remain
	stable across re-imports when the identifying fields (e.g.
	artist and album title) are the same.
	"""
	try:
		import uuid
	except Exception:
		raise

	normalized = "||".join([(p or "").strip().lower() for p in parts])
	return str(uuid.uuid5(uuid.NAMESPACE_URL, normalized))