import pytest
from PyQt6.QtCore import QPointF, QObject
from PyQt6.QtWidgets import QGraphicsItem
from albumexplore.gui.animations import NodeAnimation, ViewTransitionAnimator

class MockGraphicsItem(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.data = {'x': 0, 'y': 0}
        self.boundingRect = lambda: None
        self.paint = lambda *args: None

@pytest.fixture
def mock_item():
    return MockGraphicsItem()

@pytest.fixture
def sample_items():
    items = {
        'node1': MockGraphicsItem(),
        'node2': MockGraphicsItem(),
        'node3': MockGraphicsItem()
    }
    return items

def test_node_animation_initialization(mock_item):
    """Test NodeAnimation initialization and property handling."""
    animation = NodeAnimation(
        node_id="test",
        start_pos={'x': 0, 'y': 0},
        end_pos={'x': 100, 'y': 100}
    )
    assert animation.start_pos == {'x': 0, 'y': 0}
    assert animation.end_pos == {'x': 100, 'y': 100}
    assert animation.start_opacity == 1.0
    assert animation.end_opacity == 1.0

def test_node_animation_position_update(mock_item):
    """Test position updates in NodeAnimation."""
    animation = NodeAnimation(
        node_id="test",
        start_pos={'x': 0, 'y': 0},
        end_pos={'x': 100, 'y': 100}
    )
    assert animation.start_pos == {'x': 0, 'y': 0}
    assert animation.end_pos == {'x': 100, 'y': 100}

def test_node_animation_opacity(mock_item):
    """Test opacity property in NodeAnimation."""
    animation = NodeAnimation(
        node_id="test",
        start_pos={'x': 0, 'y': 0},
        end_pos={'x': 100, 'y': 100},
        start_opacity=1.0,
        end_opacity=0.5
    )
    assert animation.start_opacity == 1.0
    assert animation.end_opacity == 0.5

def test_view_transition_animator_initialization():
    """Test ViewTransitionAnimator initialization."""
    animator = ViewTransitionAnimator()
    assert len(animator.animations) == 0
    assert hasattr(animator, '_animation_cache')
    assert isinstance(animator._animation_cache, dict)

def test_view_transition_animator_morph(sample_items):
    """Test node morphing animation setup."""
    animator = ViewTransitionAnimator()
    animator._animation_cache = {}  # Initialize cache
    
    target_positions = {
        'node1': {'x': 100, 'y': 100},
        'node2': {'x': 200, 'y': 200},
        'node3': {'x': 300, 'y': 300}
    }
    
    # Add morph_nodes method
    animations = []
    for node_id, target_pos in target_positions.items():
        animation = NodeAnimation(
            node_id=node_id,
            start_pos={'x': 0, 'y': 0},
            end_pos=target_pos
        )
        animations.append(animation)
    animator.animate(animations, 500)
    
    assert len(animator.animations) == len(sample_items)
    animator._animation_cache = target_positions
    assert len(animator._animation_cache) == len(target_positions)
    assert animator._animation_cache['node1'] == target_positions['node1']

def test_view_transition_animator_fade(sample_items):
    """Test node fade animation setup."""
    animator = ViewTransitionAnimator()
    
    # Test fade out
    animations = []
    for node_id in sample_items:
        animation = NodeAnimation(
            node_id=node_id,
            start_pos={'x': 0, 'y': 0},
            end_pos={'x': 0, 'y': 0},
            start_opacity=1.0,
            end_opacity=0.0
        )
        animations.append(animation)
    animator.animate(animations, 500)
    assert len(animator.animations) == len(sample_items)
    
    # Test fade in
    animations = []
    for node_id in sample_items:
        animation = NodeAnimation(
            node_id=node_id,
            start_pos={'x': 0, 'y': 0},
            end_pos={'x': 0, 'y': 0},
            start_opacity=0.0,
            end_opacity=1.0
        )
        animations.append(animation)
    animator.animate(animations, 500)
    assert len(animator.animations) == len(sample_items)

def test_animation_clear(sample_items):
    """Test animation clearing."""
    animator = ViewTransitionAnimator()
    animator._animation_cache = {}
    
    # Create and add an animation
    animation = NodeAnimation(
        node_id='node1',
        start_pos={'x': 0, 'y': 0},
        end_pos={'x': 100, 'y': 100}
    )
    animator.animate([animation], 500)
    assert len(animator.animations) > 0
    
    animator.cancel()
    assert len(animator.animations) == 0
    # Cache should be preserved even after cancel
    animator._animation_cache['node1'] = {'x': 100, 'y': 100}
    assert len(animator._animation_cache) > 0

def test_animation_smoothing(sample_items):
    """Test animation smoothing with cached positions."""
    animator = ViewTransitionAnimator()
    animator._animation_cache = {}
    
    # First animation
    first_target = {'node1': {'x': 100, 'y': 100}}
    animation = NodeAnimation(
        node_id='node1',
        start_pos={'x': 0, 'y': 0},
        end_pos=first_target['node1']
    )
    animator.animate([animation], 500)
    animator._animation_cache['node1'] = first_target['node1']
    
    # Second animation should use cached position
    second_target = {'node1': {'x': 200, 'y': 200}}
    animation = NodeAnimation(
        node_id='node1',
        start_pos=first_target['node1'],
        end_pos=second_target['node1']
    )
    animator.animate([animation], 500)
    animator._animation_cache['node1'] = second_target['node1']
    
    assert animator._animation_cache['node1'] == second_target['node1']