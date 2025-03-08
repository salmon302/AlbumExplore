"""Debug utilities for visualization performance monitoring."""

import time
from typing import Dict, Any, List, Optional
from collections import deque
import statistics
from albumexplore.gui.gui_logging import performance_logger, log_performance_metric

class PerformanceDebugger:
    """Performance monitoring and debugging for visualizations."""
    
    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
        self.history: Dict[str, deque] = {}
        self.max_history_size = 60  # Keep last 60 measurements
        self.snapshot_history: List[Dict[str, Any]] = []
        self.max_snapshots = 20
        self.last_snapshot_time = 0
        self.snapshot_interval = 1.0  # seconds
    
    def start_measure(self, name: str) -> None:
        """Start measuring a metric."""
        self.start_times[name] = time.time()
    
    def end_measure(self, name: str) -> float:
        """End measuring a metric and return time in ms."""
        if name not in self.start_times:
            return 0.0
            
        elapsed = (time.time() - self.start_times[name]) * 1000
        self.metrics[name] = elapsed
        
        # Add to history
        if name not in self.history:
            self.history[name] = deque(maxlen=self.max_history_size)
        self.history[name].append(elapsed)
        
        # Log to performance monitoring
        log_performance_metric("Visualization", name, f"{elapsed:.2f}ms")
        
        return elapsed
    
    def get_metric(self, name: str) -> Optional[float]:
        """Get the last measurement for a metric."""
        return self.metrics.get(name)
    
    def get_average(self, name: str, window: int = None) -> Optional[float]:
        """Get average of a metric over history window."""
        if name not in self.history or len(self.history[name]) == 0:
            return None
            
        values = list(self.history[name])
        if window is not None and window < len(values):
            values = values[-window:]
            
        return sum(values) / len(values)
    
    def get_percentile(self, name: str, percentile: float = 95.0) -> Optional[float]:
        """Get a percentile of a metric over history."""
        if name not in self.history or len(self.history[name]) == 0:
            return None
            
        values = sorted(self.history[name])
        idx = int(len(values) * percentile / 100)
        return values[idx]
    
    def get_performance_report(self) -> str:
        """Get a formatted report of all performance metrics."""
        lines = ["Performance Report:"]
        
        for name in sorted(self.metrics.keys()):
            current = self.metrics[name]
            avg = self.get_average(name)
            p95 = self.get_percentile(name, 95)
            
            if avg is not None and p95 is not None:
                lines.append(f"{name}: {current:.2f}ms (avg: {avg:.2f}ms, p95: {p95:.2f}ms)")
            else:
                lines.append(f"{name}: {current:.2f}ms")
        
        # Add snapshot data
        if self.snapshot_history:
            lines.append("\nLast Snapshot:")
            for key, value in self.snapshot_history[-1].items():
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:.2f}")
                else:
                    lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
    
    def copy_report_to_clipboard(self) -> None:
        """Copy performance report to clipboard."""
        try:
            # Optional, only if QApplication is available
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(self.get_performance_report())
        except:
            pass  # Silently fail if clipboard access fails
    
    def take_snapshot(self, metrics: Dict[str, Any]) -> None:
        """Take a snapshot of metrics and add to history."""
        now = time.time()
        
        # Rate-limit snapshots
        if now - self.last_snapshot_time < self.snapshot_interval:
            return
            
        self.last_snapshot_time = now
        
        # Add timestamp
        snapshot = {
            'timestamp': now,
            **metrics
        }
        
        self.snapshot_history.append(snapshot)
        
        # Trim history if needed
        if len(self.snapshot_history) > self.max_snapshots:
            self.snapshot_history = self.snapshot_history[-self.max_snapshots:]