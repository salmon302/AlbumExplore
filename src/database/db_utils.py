from datetime import datetime
from sqlalchemy.orm import Session
from .models import UpdateHistory

def log_update(db: Session, entity_type: str, entity_id: str, 
			  change_type: str, changes: dict) -> UpdateHistory:
	"""Log an update to the history table."""
	try:
		history = UpdateHistory(
			entity_type=entity_type,
			entity_id=entity_id,
			change_type=change_type,
			changes=str(changes)
		)
		db.add(history)
		return history
	except Exception as e:
		db.rollback()
		raise ValueError(f"Error logging update: {e}") from e