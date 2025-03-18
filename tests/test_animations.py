"""Tests for animation system."""
from unittest.mock import Mock, patch
import pytest
from PyQt6.QtCore import QTimer
from albumexplore.gui.animations import NodeAnimation, ViewTransitionAnimator
from albumexplore.visualization.models import Point

@pytest.fixture
def mock_timer():
    """Mock QTimer."""
    with patch('albumexplore.gui.animations.QTimer') as mock:
        instance = Mock()
        mock.return_value = instance
        yield instance

@pytest.fixture
def mock_view():
    """Mock view widget."""
    view = Mock()
    view.width.return_value = 800
    view.height.return_value = 600
    return view

def test_node_animation_initialization():
    """Test node animation initialization."""
    anim = NodeAnimation()
    assert anim.duration == 300  # Default duration
    assert not anim.is_active
    assert anim.current_time == 0

def test_view_transition_animator_initialization(mock_timer, mock_view):
    """Test transition animator initialization."""
    animator = ViewTransitionAnimator(mock_view)
    assert animator.duration == 300
    assert not animator.is_active
    assert animator.view == mock_view

def test_view_transition_animator_morph(mock_timer, mock_view):
    """Test morph transition."""
    animator = ViewTransitionAnimator(mock_view)
    start_pos = Point(x=0, y=0)
    end_pos = Point(x=100, y=100)
    
    animator.morph(start_pos, end_pos)
    assert animator.is_active
    assert animator._start_pos == start_pos
    assert animator._end_pos == end_pos
    mock_timer.start.assert_called_once()

def test_view_transition_animator_fade(mock_timer, mock_view):
    """Test fade transition."""
    animator = ViewTransitionAnimator(mock_view)
    animator.fade_out()
    assert animator.is_active
    assert animator._opacity == 1.0
    mock_timer.start.assert_called_once()

def test_animation_clear(mock_timer, mock_view):
    """Test clearing animations."""
    animator = ViewTransitionAnimator(mock_view)
    animator.morph(Point(0, 0), Point(100, 100))
    
    animator.clear()
    assert not animator.is_active
    mock_timer.stop.assert_called_once()
    assert animator.current_time == 0

def test_animation_smoothing(mock_timer, mock_view):
    """Test animation smoothing function."""
    animator = ViewTransitionAnimator(mock_view)
    # Test easing curve at different points
    assert animator._smooth(0.0) == 0.0
    assert animator._smooth(1.0) == 1.0
    assert 0.0 < animator._smooth(0.5) < 1.0  # Middle point should be smoothed