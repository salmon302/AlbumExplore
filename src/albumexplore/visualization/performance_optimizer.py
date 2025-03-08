"""Performance optimization for visualization rendering."""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import time
from collections import deque
import statistics
from albumexplore.gui.gui_logging import performance_logger, log_performance_metric


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    frame_time: float = 0.0  # in milliseconds
    render_time: float = 0.0  # in milliseconds
    node_count: int = 0
    edge_count: int = 0 
    visible_node_count: int = 0
    visible_edge_count: int = 0
    lod_level: int = 0
    memory_usage: int = 0  # in bytes
    viewport_scale: float = 1.0
    
    # History tracking
    history: List[Dict[str, float]] = field(default_factory=list)
    max_history_size: int = 10
    
    def update(self, metrics: Dict[str, Any]) -> None:
        """Update metrics from a dictionary."""
        for key, value in metrics.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Add to history
        self.history.append({**metrics})
        
        # Trim history if needed
        if len(self.history) > self.max_history_size:
            self.history = self.history[-self.max_history_size:]
    
    def get_average(self, metric_name: str) -> float:
        """Get average value of a metric over history."""
        values = [h.get(metric_name, 0) for h in self.history if metric_name in h]
        if not values:
            return 0
        return sum(values) / len(values)
    
    def is_stable(self) -> bool:
        """Check if performance metrics are stable."""
        if len(self.history) < 3:
            return False
            
        frame_times = [h.get('frame_time', 0) for h in self.history if 'frame_time' in h]
        if not frame_times:
            return False
            
        avg = sum(frame_times) / len(frame_times)
        variance = sum((t - avg) ** 2 for t in frame_times) / len(frame_times)
        
        # Consider stable if standard deviation is less than 20% of average
        return (variance ** 0.5) / avg < 0.2


class PerformanceOptimizer:
    """Dynamically optimizes visualization performance."""
    
    def __init__(self):
        self.target_fps = 30  # Target frames per second
        self.target_frame_time = 1000 / self.target_fps  # Target ms per frame
        self.current_quality = 1.0  # Quality multiplier (1.0 = full)
        self.min_quality = 0.3
        self.adaptation_speed = 0.1  # How quickly to adapt quality (0.0-1.0)
        
        # Optimization strategies
        self.enable_lod = True
        self.enable_clustering = True
        self.enable_edge_filtering = True
        self.enable_node_filtering = True
        
        # Thresholds for various optimizations
        self.node_threshold = 300  # When to start reducing visible nodes
        self.edge_threshold = 1000  # When to start reducing visible edges
        
        # State tracking
        self.consecutive_slow_frames = 0
        self.consecutive_fast_frames = 0
    
    def optimize(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Analyze performance metrics and suggest optimizations."""
        frame_time = metrics.frame_time
        
        # If we're below target FPS, reduce quality
        if frame_time > self.target_frame_time:
            self.consecutive_slow_frames += 1
            self.consecutive_fast_frames = 0
            
            # Only reduce quality after several consecutive slow frames
            if self.consecutive_slow_frames >= 3:
                self._reduce_quality(metrics)
                self.consecutive_slow_frames = 0
        
        # If we're well above target FPS, increase quality gradually
        elif frame_time < self.target_frame_time * 0.7:
            self.consecutive_fast_frames += 1
            self.consecutive_slow_frames = 0
            
            # Only increase quality after many consecutive fast frames
            if self.consecutive_fast_frames >= 10:
                self._increase_quality()
                self.consecutive_fast_frames = 0
        
        # At target FPS, reset counters
        else:
            self.consecutive_slow_frames = 0
            self.consecutive_fast_frames = 0
        
        # Return current optimization settings
        return {
            'quality': self.current_quality,
            'lod_enabled': self.enable_lod,
            'clustering_enabled': self.enable_clustering,
            'edge_filtering': self.enable_edge_filtering,
            'node_filtering': self.enable_node_filtering,
            'frame_time': frame_time,
            'target_frame_time': self.target_frame_time
        }
    
    def _reduce_quality(self, metrics: PerformanceMetrics) -> None:
        """Reduce quality to improve performance."""
        # First, reduce overall quality
        self.current_quality = max(
            self.min_quality,
            self.current_quality * (1.0 - self.adaptation_speed)
        )
        
        # Adjust strategies based on metrics
        if metrics.node_count > self.node_threshold and not self.enable_node_filtering:
            # Too many nodes, enable node filtering
            self.enable_node_filtering = True
            
        if metrics.edge_count > self.edge_threshold and not self.enable_edge_filtering:
            # Too many edges, enable edge filtering
            self.enable_edge_filtering = True
            
        if metrics.frame_time > self.target_frame_time * 2:
            # Very slow frames, enable all optimizations
            self.enable_lod = True
            self.enable_clustering = True
    
    def _increase_quality(self) -> None:
        """Gradually increase quality if performance permits."""
        # Increase overall quality gradually
        self.current_quality = min(
            1.0,
            self.current_quality * (1.0 + self.adaptation_speed * 0.5)
        )
        
        # If quality is very high, consider disabling some optimizations
        if self.current_quality > 0.9:
            if self.enable_edge_filtering:
                # Try disabling edge filtering first
                self.enable_edge_filtering = False
            elif self.enable_node_filtering:
                # Then try disabling node filtering
                self.enable_node_filtering = False
    
    def get_quality_settings(self) -> Dict[str, Any]:
        """Get current quality settings for rendering."""
        return {
            'node_detail_level': max(1, int(3 * self.current_quality)),
            'show_labels': self.current_quality > 0.6,
            'edge_opacity': min(1.0, self.current_quality * 1.2),
            'edge_detail': max(1, int(3 * self.current_quality)),
            'antialiasing': self.current_quality > 0.8,
            'animation_enabled': self.current_quality > 0.4,
            'texture_quality': max(1, int(3 * self.current_quality)),
            'show_effects': self.current_quality > 0.7
        }
