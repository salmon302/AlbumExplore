"""Animation utilities for GUI transitions."""

from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
import time


@dataclass
class NodeAnimation:
    """Animation data for a node."""
    node_id: str
    start_pos: Dict[str, float]
    end_pos: Dict[str, float]
    start_opacity: float = 1.0
    end_opacity: float = 1.0
    start_size: float = 1.0
    end_size: float = 1.0


class ViewTransitionAnimator(QObject):
    """Handles smooth transitions between views."""
    
    # Signal emitted when animation progresses (0 to 1)
    progress = pyqtSignal(float)
    
    # Signal emitted when animation completes
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.animations: List[NodeAnimation] = []
        self._animation_cache: Dict[str, Dict[str, float]] = {}
        self.current_progress = 0.0
        self.duration = 300  # ms
        self.start_time = 0
        self.active = False
        self.update_callback = None
    
    def animate(self, animations: List[NodeAnimation], duration_ms: int = 300) -> None:
        """Start animations with given duration."""
        self.animations = animations
        self.duration = duration_ms
        self.current_progress = 0.0
        self.start_time = time.time() * 1000  # ms
        self.active = True
        self.timer.start(16)  # ~60 FPS
        
        # Update cache with end positions
        for anim in animations:
            self._animation_cache[anim.node_id] = anim.end_pos.copy()
    
    def _update(self) -> None:
        """Update animation state."""
        if not self.active:
            return
        
        current_time = time.time() * 1000
        elapsed = current_time - self.start_time
        progress = min(1.0, elapsed / self.duration)
        
        # Apply easing function
        eased_progress = self._ease_out_cubic(progress)
        self.current_progress = progress
        
        # Emit progress signal
        self.progress.emit(progress)
        
        # Call update callback if provided
        if self.update_callback:
            current_values = self._calculate_current_values(eased_progress)
            self.update_callback(current_values)
        
        # Check for completion
        if progress >= 1.0:
            self.active = False
            self.timer.stop()
            self.finished.emit()
    
    def _calculate_current_values(self, progress: float) -> Dict[str, Dict[str, Any]]:
        """Calculate current interpolated values for all animations."""
        result = {}
        
        for anim in self.animations:
            # Interpolate position
            x = anim.start_pos.get('x', 0) + (anim.end_pos.get('x', 0) - anim.start_pos.get('x', 0)) * progress
            y = anim.start_pos.get('y', 0) + (anim.end_pos.get('y', 0) - anim.start_pos.get('y', 0)) * progress
            
            # Interpolate opacity
            opacity = anim.start_opacity + (anim.end_opacity - anim.start_opacity) * progress
            
            # Interpolate size
            size = anim.start_size + (anim.end_size - anim.start_size) * progress
            
            result[anim.node_id] = {
                'x': x,
                'y': y,
                'opacity': opacity,
                'size': size
            }
        
        return result
    
    def cancel(self) -> None:
        """Cancel ongoing animation."""
        if self.active:
            self.active = False
            self.timer.stop()
    
    def clear(self) -> None:
        """Clear all animations but preserve cache."""
        self.cancel()
        self.animations.clear()
    
    def set_update_callback(self, callback: Callable[[Dict[str, Dict[str, Any]]], None]) -> None:
        """Set callback to update nodes during animation."""
        self.update_callback = callback
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out function."""
        return 1 - (1 - t) ** 3