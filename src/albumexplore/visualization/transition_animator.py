"""Animation system for smooth transitions between visualization states."""

from typing import Dict, Any, Optional, List, Callable
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
import time
import math
from .models import VisualNode, VisualEdge
from .state import ViewType
from albumexplore.gui.animations import ViewTransitionAnimator, NodeAnimation

class TransitionAnimator(QObject):
    """Handles smooth transitions between visualization states."""
    
    # Signal emitted when animation progresses (progress from 0.0 to 1.0)
    progress = pyqtSignal(float)
    
    # Signal emitted when animation completes
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_animation)
        
        self.start_time = 0
        self.duration = 300  # ms
        self.easing_function = self._ease_out_cubic
        self.active = False
        self.update_callback = None
        self.completion_callback = None
        
        # Animation state
        self.start_values = {}
        self.end_values = {}
        self.current_values = {}
    
    def animate_transition(self, nodes: Dict[str, Any], 
                          target_positions: Dict[str, Dict[str, float]], 
                          transition_type: str, 
                          duration_ms: int = 300) -> None:
        """Start animating nodes to target positions."""
        if self.active:
            self.cancel_animations()
            
        self.start_time = time.time()
        self.duration = duration_ms / 1000  # Convert to seconds
        self.active = True
        
        # Save initial positions
        self.start_values = {}
        for node_id, node in nodes.items():
            if node_id in target_positions:
                # Get current position
                self.start_values[node_id] = {
                    'x': node.pos.get('x', 0),
                    'y': node.pos.get('y', 0)
                }
        
        # Save target positions
        self.end_values = target_positions
        
        # Start the timer
        self.timer.start(16)  # ~60 FPS
    
    def _update_animation(self) -> None:
        """Update animation on timer tick."""
        if not self.active:
            return
            
        current_time = time.time()
        elapsed = current_time - self.start_time
        progress = min(1.0, elapsed / self.duration)
        
        # Apply easing
        eased_progress = self.easing_function(progress)
        
        # Update current values
        self.current_values = {}
        for node_id, start in self.start_values.items():
            if node_id not in self.end_values:
                continue
                
            end = self.end_values[node_id]
            
            # Interpolate position
            self.current_values[node_id] = {
                'x': start['x'] + (end['x'] - start['x']) * eased_progress,
                'y': start['y'] + (end['y'] - start['y']) * eased_progress
            }
        
        # Notify progress
        self.progress.emit(progress)
        
        # Call update callback if provided
        if self.update_callback:
            self.update_callback(self.current_values)
        
        # Check if animation is complete
        if progress >= 1.0:
            self.active = False
            self.timer.stop()
            self.finished.emit()
            
            if self.completion_callback:
                self.completion_callback()
    
    def cancel_animations(self) -> None:
        """Cancel all running animations."""
        if self.active:
            self.active = False
            self.timer.stop()
    
    def get_current_values(self) -> Dict[str, Dict[str, float]]:
        """Get current interpolated values."""
        return self.current_values
    
    def set_update_callback(self, callback: Callable[[Dict[str, Dict[str, float]]], None]) -> None:
        """Set callback function to update nodes during animation."""
        self.update_callback = callback
    
    def set_completion_callback(self, callback: Callable[[], None]) -> None:
        """Set callback function called when animation completes."""
        self.completion_callback = callback
    
    def set_easing_function(self, easing_name: str) -> None:
        """Set the easing function by name."""
        easing_functions = {
            'linear': self._ease_linear,
            'ease_in': self._ease_in_quad,
            'ease_out': self._ease_out_cubic,
            'ease_in_out': self._ease_in_out_quad,
            'bounce': self._ease_out_bounce,
            'elastic': self._ease_out_elastic
        }
        
        self.easing_function = easing_functions.get(easing_name, self._ease_out_cubic)
    
    # Easing functions
    def _ease_linear(self, t: float) -> float:
        return t
    
    def _ease_in_quad(self, t: float) -> float:
        return t * t
    
    def _ease_out_cubic(self, t: float) -> float:
        return 1 - (1 - t) ** 3
    
    def _ease_in_out_quad(self, t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return 1 - (-2 * t + 2) ** 2 / 2
    
    def _ease_out_bounce(self, t: float) -> float:
        n1 = 7.5625
        d1 = 2.75
        
        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375
    
    def _ease_out_elastic(self, t: float) -> float:
        if t == 0 or t == 1:
            return t
            
        c4 = (2 * math.pi) / 3
        return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1