"""Graphics debugging utilities for GUI visualization."""

from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, Qt
import time
from albumexplore.gui.gui_logging import graphics_logger, log_graphics_event


class GraphicsDebugMonitor(QObject):
    """Monitors and logs graphics performance and issues."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_monitoring = False
        self.last_event_time = time.time()
        self.event_count = 0
        self.error_count = 0
        self.frame_times: List[float] = []
        self.background_issues: List[Dict[str, Any]] = []
        self.buffer_issues: List[Dict[str, Any]] = []

    def start_monitoring(self) -> None:
        """Start graphics monitoring."""
        self.is_monitoring = True
        self.last_event_time = time.time()
        graphics_logger.info("Graphics monitoring started")

    def stop_monitoring(self) -> None:
        """Stop graphics monitoring."""
        self.is_monitoring = False
        graphics_logger.info("Graphics monitoring stopped")

    def log_paint_event(self, widget: Any, event_type: str) -> None:
        """Log a paint event with timing and background state."""
        if not self.is_monitoring:
            return
            
        current_time = time.time()
        delta = (current_time - self.last_event_time) * 1000  # ms
        self.last_event_time = current_time
        
        widget_name = widget.__class__.__name__
        self.event_count += 1
        
        # Check background attributes
        background_state = {
            "translucent": widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground),
            "no_system_bg": widget.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground),
            "opaque_paint": widget.testAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent),
            "auto_fill": widget.autoFillBackground()
        }
        
        if any(background_state.values()):  # If any background attributes are True
            self.background_issues.append({
                "widget": widget_name,
                "time": current_time,
                "state": background_state
            })
            
        if delta > 33:  # More than 30 FPS
            graphics_logger.debug(
                f"{event_type}: {widget_name} took {delta:.2f}ms "
                f"({1000/max(1, delta):.1f} FPS) - BG state: {background_state}"
            )

    def log_buffer_state(self, widget: Any, is_valid: bool) -> None:
        """Log buffer state and background composition."""
        if not self.is_monitoring:
            return
            
        widget_name = widget.__class__.__name__
        state = "valid" if is_valid else "invalid/null"
        
        if not is_valid:
            self.error_count += 1
            self.buffer_issues.append({
                "widget": widget_name,
                "time": time.time(),
                "error": "Invalid buffer"
            })
            
        graphics_logger.debug(f"Buffer state for {widget_name}: {state}")

    def log_view_update(self, widget: Any, visible_items: int, total_items: int) -> None:
        """Log view update with item counts and background state."""
        if not self.is_monitoring:
            return
            
        widget_name = widget.__class__.__name__
        current_time = time.time()
        delta = (current_time - self.last_event_time) * 1000
        
        graphics_logger.debug(
            f"View update: {widget_name} showing {visible_items}/{total_items} "
            f"items, took {delta:.2f}ms"
        )
        
        # Report if background issues accumulating
        if len(self.background_issues) > 10:
            graphics_logger.warning(
                f"{widget_name} has accumulated {len(self.background_issues)} "
                "background-related issues"
            )
            self.background_issues = []  # Reset counter

    def __del__(self) -> None:
        """Clean up on deletion."""
        if self.is_monitoring:
            self.stop_monitoring()


def init_graphics_debugging(widget: Any) -> GraphicsDebugMonitor:
    """Initialize graphics debugging for a widget."""
    monitor = GraphicsDebugMonitor(widget)
    monitor.start_monitoring()
    return monitor