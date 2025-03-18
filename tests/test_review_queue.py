import pytest
from datetime import datetime
from albumexplore.database import models
from albumexplore.tags.management.review_queue import ReviewQueue, ChangeType, ReviewStatus, TagChange

@pytest.fixture
def queue():
    return ReviewQueue()

@pytest.fixture
def categories(session):
    # Create tag categories
    genre = models.TagCategory(id="genre", name="Genre")
    style = models.TagCategory(id="style", name="Style")
    modifier = models.TagCategory(id="modifier", name="Modifier")
    session.add_all([genre, style, modifier])
    session.commit()
    return {"genre": genre, "style": style, "modifier": modifier}

def test_add_change(queue):
    change_id = queue.add_change(
        change_type=ChangeType.MERGE,
        old_value=['heavy-metal', 'heavy metal'],
        new_value='heavy-metal',
        notes='Standardizing hyphenation'
    )
    
    assert change_id is not None
    assert len(queue.pending_changes) == 1
    
    change = queue.pending_changes[change_id]
    assert change.change_type == ChangeType.MERGE
    assert change.status == ReviewStatus.PENDING
    assert change.notes == 'Standardizing hyphenation'

def test_approve_change(queue):
    change_id = queue.add_change(
        change_type=ChangeType.RENAME,
        old_value='prog',
        new_value='progressive',
        notes='Using full term'
    )
    
    success = queue.approve_change(change_id, reviewer='test_user', notes='Approved')
    
    assert success
    assert len(queue.pending_changes) == 0
    assert len(queue.change_history) == 1
    
    approved_change = queue.change_history[0]
    assert approved_change.status == ReviewStatus.APPROVED
    assert approved_change.reviewer == 'test_user'

def test_reject_change(queue):
    change_id = queue.add_change(
        change_type=ChangeType.DELETE,
        old_value='unused-tag',
        new_value='',
        notes='Remove unused tag'
    )
    
    success = queue.reject_change(change_id, reviewer='test_user', notes='Keep for historical data')
    
    assert success
    assert len(queue.pending_changes) == 0
    assert len(queue.change_history) == 1
    
    rejected_change = queue.change_history[0]
    assert rejected_change.status == ReviewStatus.REJECTED
    assert rejected_change.notes == 'Keep for historical data'

def test_rollback_change(queue):
    # First approve a change
    change_id = queue.add_change(
        change_type=ChangeType.RENAME,
        old_value='black-metal',
        new_value='blackmetal',
        notes='Remove hyphen'
    )
    queue.approve_change(change_id, reviewer='test_user')
    
    # Then try to rollback
    success = queue.rollback_change(change_id)
    
    assert success
    assert len(queue.pending_changes) == 1
    
    rollback_change = list(queue.pending_changes.values())[0]
    assert rollback_change.old_value == 'blackmetal'
    assert rollback_change.new_value == 'black-metal'

def test_get_pending_changes(queue):
    queue.add_change(
        change_type=ChangeType.ADD,
        old_value='',
        new_value='new-tag',
        notes='Adding new tag'
    )
    
    pending = queue.get_pending_changes()
    assert len(pending) == 1
    assert pending[0].change_type == ChangeType.ADD
    assert pending[0].status == ReviewStatus.PENDING

def test_get_change_history(queue):
    change_id = queue.add_change(
        change_type=ChangeType.MERGE,
        old_value=['tag1', 'tag2'],
        new_value='tag1',
        notes='Merging similar tags'
    )
    queue.approve_change(change_id, reviewer='test_user')
    
    history = queue.get_change_history()
    assert len(history) == 1
    assert history[0].status == ReviewStatus.APPROVED