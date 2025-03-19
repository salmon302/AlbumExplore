import pytest
from PyQt6.QtCore import QTimer
from albumexplore.gui.animations import ViewTransitionAnimator, NodeAnimation

def test_animator_creation():
    """Test ViewTransitionAnimator initialization."""
    animator = ViewTransitionAnimator()
    assert not animator.active
    assert animator.duration == 300
    assert animator.current_progress == 0.0

def test_node_animation():
    """Test NodeAnimation basic functionality."""
    start_pos = {'x': 0, 'y': 0}
    end_pos = {'x': 100, 'y': 100}
    animation = NodeAnimation(
        node_id="test_node",
        start_pos=start_pos,
        end_pos=end_pos,
        start_opacity=1.0,
        end_opacity=0.5
    )
    assert animation.node_id == "test_node"
    assert animation.start_pos == start_pos
    assert animation.end_pos == end_pos
    assert animation.start_opacity == 1.0
    assert animation.end_opacity == 0.5

def test_animation_progress():
    """Test animation progress calculation."""
    animator = ViewTransitionAnimator()
    animations = [
        NodeAnimation(
            node_id="node1",
            start_pos={'x': 0, 'y': 0},
            end_pos={'x': 100, 'y': 100}
        )
    ]
    
    # Start animation
    animator.animate(animations, duration_ms=1000)
    assert animator.active
    
    # Simulate time passing
    current_values = animator._calculate_current_values(0.5)
    assert current_values["node1"]["x"] == pytest.approx(50)
    assert current_values["node1"]["y"] == pytest.approx(50)

def test_animation_callback():
    """Test animation update callback."""
    animator = ViewTransitionAnimator()
    callback_values = None
    
    def update_callback(values):
        nonlocal callback_values
        callback_values = values
    
    animator.set_update_callback(update_callback)
    
    animations = [
        NodeAnimation(
            node_id="test",
            start_pos={'x': 0, 'y': 0},
            end_pos={'x': 100, 'y': 100}
        )
    ]
    
    animator.animate(animations)
    # Force an update
    animator._update()
    
    assert callback_values is not None
    assert "test" in callback_values

def test_animation_cancellation():
    """Test animation can be cancelled."""
    animator = ViewTransitionAnimator()
    animations = [
        NodeAnimation(
            node_id="test",
            start_pos={'x': 0, 'y': 0},
            end_pos={'x': 100, 'y': 100}
        )
    ]
    
    animator.animate(animations)
    assert animator.active
    
    animator.cancel()
    assert not animator.active