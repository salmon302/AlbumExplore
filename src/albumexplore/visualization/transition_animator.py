"""Transition animator for smooth view transitions."""
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import time
from dataclasses import dataclass
from .models import VisualNode
from albumexplore.gui.gui_logging import graphics_logger

@dataclass
class TransitionState:
    """State information for a transition."""
    start_positions: Dict[str, Dict[str, float]]
    end_positions: Dict[str, Dict[str, float]]
    start_opacity: Dict[str, float]
    end_opacity: Dict[str, float]
    start_scale: Dict[str, float]
    end_scale: Dict[str, float]
    duration_ms: int = 300
    easing: str = "cubic-bezier(0.4, 0.0, 0.2, 1)"

class TransitionAnimator(QObject):
    """Handles smooth transitions between views."""
    
    # Signals
    transition_frame = pyqtSignal(dict)  # Emits current transition state
    transition_complete = pyqtSignal()   # Emits when transition completes
    
    def __init__(self):
        super().__init__()
        self.current_transition: Optional[TransitionState] = None
        self.start_time: float = 0
        self.is_active: bool = False
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_transition)
        self.update_timer.setInterval(16)  # ~60 FPS
    
    def start_transition(self, transition_state: TransitionState) -> None:
        """Start a new transition."""
        graphics_logger.debug("Starting transition animation")
        self.current_transition = transition_state
        self.start_time = time.time()
        self.is_active = True
        self.update_timer.start()
    
    def cancel_animations(self) -> None:
        """Cancel any ongoing animations."""
        if self.is_active:
            graphics_logger.debug("Cancelling transition animation")
            self.update_timer.stop()
            self.is_active = False
            self.current_transition = None
    
    def _update_transition(self) -> None:
        """Update transition state."""
        if not self.is_active or not self.current_transition:
            self.update_timer.stop()
            return
        
        current_time = time.time()
        elapsed = (current_time - self.start_time) * 1000  # Convert to ms
        progress = min(1.0, elapsed / self.current_transition.duration_ms)
        
        # Apply easing
        eased_progress = self._ease_cubic(progress)
        
        # Calculate current state
        current_state = {}
        for node_id in self.current_transition.start_positions:
            start_pos = self.current_transition.start_positions[node_id]
            end_pos = self.current_transition.end_positions[node_id]
            
            current_state[node_id] = {
                "x": start_pos["x"] + (end_pos["x"] - start_pos["x"]) * eased_progress,
                "y": start_pos["y"] + (end_pos["y"] - start_pos["y"]) * eased_progress,
                "opacity": (self.current_transition.start_opacity.get(node_id, 1.0) +
                          (self.current_transition.end_opacity.get(node_id, 1.0) -
                           self.current_transition.start_opacity.get(node_id, 1.0)) * eased_progress),
                "scale": (self.current_transition.start_scale.get(node_id, 1.0) +
                         (self.current_transition.end_scale.get(node_id, 1.0) -
                          self.current_transition.start_scale.get(node_id, 1.0)) * eased_progress)
            }
        
        # Emit current state
        self.transition_frame.emit(current_state)
        
        # Check for completion
        if progress >= 1.0:
            self.update_timer.stop()
            self.is_active = False
            self.current_transition = None
            self.transition_complete.emit()
    
    def _ease_cubic(self, t: float) -> float:
        """Cubic easing function."""
        return t * t * (3 - 2 * t)
    
    def update_transition(self, view: Any, transition_data: Dict[str, Any], progress: float) -> None:
        """Update view with current transition state."""
        if not hasattr(view, 'node_items'):
            return
        
        # Get transition parameters
        positions = transition_data.get('preserved_positions', {})
        opacity = transition_data.get('opacity', {})
        scale = transition_data.get('scale', {})
        
        # Apply current state to nodes
        for node_id, pos in positions.items():
            if node_id in view.node_items:
                item = view.node_items[node_id]
                current_x = item.pos().x()
                current_y = item.pos().y()
                target_x = float(pos.get('x', current_x))
                target_y = float(pos.get('y', current_y))
                
                # Interpolate position
                x = current_x + (target_x - current_x) * progress
                y = current_y + (target_y - current_y) * progress
                
                # Apply new position
                item.setPos(x, y)
                
                # Update opacity if specified
                if node_id in opacity:
                    start_opacity = item.opacity()
                    target_opacity = float(opacity[node_id])
                    current_opacity = start_opacity + (target_opacity - start_opacity) * progress
                    item.setOpacity(current_opacity)
                
                # Update scale if specified
                if node_id in scale:
                    start_scale = item.scale()
                    target_scale = float(scale[node_id])
                    current_scale = start_scale + (target_scale - start_scale) * progress
                    item.setScale(current_scale)