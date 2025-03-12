"""Graphics debugging utilities."""
from typing import Dict, Any, Optional
from datetime import datetime
from albumexplore.gui.gui_logging import graphics_logger

def init_graphics_debugging(view) -> Dict[str, Any]:
    """Initialize graphics debugging for a view."""
    return {
        'frame_count': 0,
        'frame_times': [],
        'last_fps_update': 0,
        'debug_info': {}
    }

class GraphicsDebugMonitor:
    """Monitor and log graphics-related debug information."""
    
    def __init__(self):
        self.stats = {
            'view_updates': 0,
            'last_update_time': None,
            'node_counts': [],
            'edge_counts': []
        }
    
    def log_view_update(self, view, node_count: int, edge_count: int):
        """Log information about a view update."""
        self.stats['view_updates'] += 1
        self.stats['last_update_time'] = datetime.now()
        self.stats['node_counts'].append(node_count)
        self.stats['edge_counts'].append(edge_count)
        
        graphics_logger.debug(
            f"View update {self.stats['view_updates']}: "
            f"{node_count} nodes, {edge_count} edges"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current debug statistics."""
        return self.stats.copy()