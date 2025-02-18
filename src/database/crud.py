import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .models import Album, Tag, TagRelation
from .db_utils import log_update
from .update_manager import UpdateManager

def create_album(db: Session, album_data: dict):
    """Create a new album record with transaction and error handling."""
    try:
        with db.begin():
            album = Album(**album_data)
            db.add(album)
            UpdateManager(db).log_update('album', album.id, 'create', album_data)
            return album
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Error creating album: {e}") from e
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error creating album: {e}") from e

def create_tag(db: Session, tag_data: dict):
    """Create a new tag record with transaction and error handling."""
    try:
        with db.begin():
            tag = Tag(**tag_data)
            db.add(tag)
            UpdateManager(db).log_update('tag', tag.id, 'create', tag_data)
            return tag
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Error creating tag: {e}") from e
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error creating tag: {e}") from e

def create_tag_relation(db: Session, relation_data: dict):
    """Create a new tag relationship with transaction and error handling."""
    try:
        with db.begin():
            relation = TagRelation(**relation_data)
            db.add(relation)
            return relation
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Error creating tag relation: {e}") from e
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error creating tag relation: {e}") from e

def log_update(db: Session, entity_type: str, entity_id: str, 
               change_type: str, changes: dict):
    """Log an update to the history with transaction and error handling."""
    try:
        with db.begin():
            history = log_update(db,
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

def get_album(db: Session, album_id: str):
    """Get album by ID with error handling."""
    try:
        return db.query(Album).filter(Album.id == album_id).first()
    except Exception as e:
        raise ValueError(f"Error getting album: {e}") from e

def get_tag(db: Session, tag_id: str):
    """Get tag by ID with error handling."""
    try:
        return db.query(Tag).filter(Tag.id == tag_id).first()
    except Exception as e:
        raise ValueError(f"Error getting tag: {e}") from e

def get_tag_by_name(db: Session, name: str):
    """Get tag by name with error handling."""
    try:
        return db.query(Tag).filter(Tag.name == name).first()
    except Exception as e:
        raise ValueError(f"Error getting tag by name: {e}") from e

def get_tag_relations(db: Session, tag_id: str):
    """Get all relations for a tag with error handling."""
    try:
        return db.query(TagRelation).filter(
            (TagRelation.tag1_id == tag_id) | 
            (TagRelation.tag2_id == tag_id)
        ).all()
    except Exception as e:
        raise ValueError(f"Error getting tag relations: {e}") from e

def update_album(db: Session, album_id: str, updates: Dict[str, Any]) -> Optional[Album]:
    """Update album with change tracking and error handling."""
    try:
        with db.begin():
            return UpdateManager(db).update_album(album_id, updates)
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error updating album: {e}") from e

def update_tag(db: Session, tag_id: str, updates: Dict[str, Any]) -> Optional[Tag]:
    """Update tag with change tracking and error handling."""
    try:
        with db.begin():
            return UpdateManager(db).update_tag(tag_id, updates)
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error updating tag: {e}") from e

def delete_album(db: Session, album_id: str) -> None:
    """Delete album with error handling."""
    try:
        with db.begin():
            album = db.query(Album).filter(Album.id == album_id).first()
            if album:
                db.delete(album)
                UpdateManager(db).log_update('album', album_id, 'delete', {})
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error deleting album: {e}") from e

def delete_tag(db: Session, tag_id: str) -> None:
    """Delete tag with error handling."""
    try:
        with db.begin():
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                db.delete(tag)
                UpdateManager(db).log_update('tag', tag_id, 'delete', {})
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error deleting tag: {e}") from e

def add_parent_tag(db: Session, child_id: str, parent_id: str) -> bool:
    """Add a parent-child relationship between tags."""
    try:
        child_tag = get_tag(db, child_id)
        parent_tag = get_tag(db, parent_id)
        if child_tag and parent_tag:
            child_tag.parent_tags.append(parent_tag)
            UpdateManager(db).log_update('tag', child_id, 'update', {'added_parent': parent_id})
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error adding parent tag: {e}") from e

def remove_parent_tag(db: Session, child_id: str, parent_id: str) -> bool:
    """Remove a parent-child relationship between tags."""
    try:
        child_tag = get_tag(db, child_id)
        parent_tag = get_tag(db, parent_id)
        if child_tag and parent_tag and parent_tag in child_tag.parent_tags:
            child_tag.parent_tags.remove(parent_tag)
            UpdateManager(db).log_update('tag', child_id, 'update', {'removed_parent': parent_id})
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error removing parent tag: {e}") from e

def get_inherited_tags(db: Session, tag_id: str, depth: int = -1) -> List[Tag]:
    """Get all inherited tags up to specified depth (-1 for unlimited)."""
    try:
        tag = get_tag(db, tag_id)
        if not tag:
            return []
        
        inherited = set()
        to_process = [(tag, 0)]
        
        while to_process:
            current_tag, current_depth = to_process.pop(0)
            if depth != -1 and current_depth >= depth:
                continue
                
            for parent in current_tag.parent_tags:
                if parent.id not in inherited:
                    inherited.add(parent.id)
                    to_process.append((parent, current_depth + 1))
        
        return [get_tag(db, tag_id) for tag_id in inherited]
    except Exception as e:
        raise ValueError(f"Error getting inherited tags: {e}") from e

def get_tag_children(db: Session, tag_id: str, depth: int = -1) -> List[Tag]:
    """Get all child tags up to specified depth (-1 for unlimited)."""
    try:
        tag = get_tag(db, tag_id)
        if not tag:
            return []
        
        children = set()
        to_process = [(tag, 0)]
        
        while to_process:
            current_tag, current_depth = to_process.pop(0)
            if depth != -1 and current_depth >= depth:
                continue
                
            for child in current_tag.child_tags:
                if child.id not in children:
                    children.add(child.id)
                    to_process.append((child, current_depth + 1))
        
        return [get_tag(db, tag_id) for tag_id in children]
    except Exception as e:
        raise ValueError(f"Error getting tag children: {e}") from e
