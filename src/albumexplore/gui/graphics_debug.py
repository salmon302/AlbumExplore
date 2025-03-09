"""Graphics debugging tools."""
import time
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject
from albumexplore.gui.gui_logging import graphics_logger, performance_logger

class GraphicsDebugMonitor:
    """Monitors graphics performance and issues."""
    
    def __init__(self):
        self.frame_times: Dict[int, float] = {}
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.paint_counts: Dict[str, int] = {}
        self.update_counts: Dict[str, int] = {}
        
    def log_paint_event(self, widget: QObject, event_type: str):
        """Log paint event."""
        current_time = time.time()
        if widget.objectName() not in self.paint_counts:
            self.paint_counts[widget.objectName()] = 0
        self.paint_counts[widget.objectName()] += 1
        
        # Calculate frame time
        frame_time = (current_time - self.last_frame_time) * 1000  # Convert to ms
        self.frame_times[self.frame_count] = frame_time
        self.frame_count += 1
        self.last_frame_time = current_time
        
        # Log timing
        graphics_logger.debug(
            f"Paint event in {widget.objectName()}, type: {event_type}, "
            f"frame time: {frame_time:.2f}ms"
        )
        
        # Performance warning if frame time is high
        if frame_time > 16.67:  # More than 60fps
            performance_logger.warning(
                f"High frame time ({frame_time:.2f}ms) in {widget.objectName()}"
            )
    
    def log_view_update(self, widget: QObject, num_nodes: int, num_edges: int):
        """Log view update."""
        if widget.objectName() not in self.update_counts:
            self.update_counts[widget.objectName()] = 0
        self.update_counts[widget.objectName()] += 1
        
        graphics_logger.debug(
            f"View update in {widget.objectName()}, "
            f"nodes: {num_nodes}, edges: {num_edges}"
        )
        
        # Performance warning if update size is large
        if num_nodes + num_edges > 1000:
            performance_logger.warning(
                f"Large update in {widget.objectName()} "
                f"({num_nodes} nodes, {num_edges} edges)"
            )
    
    def get_performance_report(self) -> str:
        """Generate performance report."""
        if not self.frame_times:
            return "No frame data collected"
        
        avg_frame_time = sum(self.frame_times.values()) / len(self.frame_times)
        max_frame_time = max(self.frame_times.values())
        
        report = ["Performance Report"]
        report.append("==================")
        report.append(f"Average frame time: {avg_frame_time:.2f}ms")
        report.append(f"Maximum frame time: {max_frame_time:.2f}ms")
        report.append(f"Total frames: {self.frame_count}")
        report.append("\nPaint counts by widget:")
        for widget, count in self.paint_counts.items():
            report.append(f"  {widget}: {count}")
        report.append("\nUpdate counts by widget:")
        for widget, count in self.update_counts.items():
            report.append(f"  {widget}: {count}")
        
        return "\n".join(report)

def init_graphics_debugging(app: QObject) -> Optional[GraphicsDebugMonitor]:
    """Initialize graphics debugging."""
    try:
        monitor = GraphicsDebugMonitor()
        graphics_logger.info("Graphics debugging initialized")
        return monitor
    except Exception as e:
        graphics_logger.error(f"Error initializing graphics debugging: {e}")
        return None