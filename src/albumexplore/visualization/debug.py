from dataclasses import dataclass
from typing import Dict, List, Optional
import time
from collections import deque
import json
from pathlib import Path
import logging
from PyQt6.QtWidgets import QApplication

@dataclass
class PerformanceSnapshot:
	timestamp: float
	frame_time: float
	render_time: float
	layout_time: float
	node_count: int
	edge_count: int
	memory_usage: float
	viewport_scale: float
	fps: float

class PerformanceDebugger:
	def __init__(self, log_path: Optional[str] = None):
		self.snapshots = deque(maxlen=300)  # 5 seconds at 60 FPS
		self.start_times: Dict[str, float] = {}
		self.log_path = log_path or str(Path.home() / "albumexplore_perf.log")
		self._setup_logging()
		
	def _setup_logging(self):
		self.logger = logging.getLogger("PerformanceDebugger")
		self.logger.setLevel(logging.DEBUG)
		handler = logging.FileHandler(self.log_path)
		handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
		self.logger.addHandler(handler)
		
	def start_measure(self, name: str):
		self.start_times[name] = time.perf_counter()
		
	def end_measure(self, name: str) -> float:
		if name in self.start_times:
			duration = (time.perf_counter() - self.start_times[name]) * 1000
			del self.start_times[name]
			return duration
		return 0.0
		
	def take_snapshot(self, metrics: Dict[str, float]):
		snapshot = PerformanceSnapshot(
			timestamp=time.time(),
			frame_time=metrics.get('frame_time', 0),
			render_time=metrics.get('render_time', 0),
			layout_time=metrics.get('layout_time', 0),
			node_count=int(metrics.get('node_count', 0)),
			edge_count=int(metrics.get('edge_count', 0)),
			memory_usage=metrics.get('memory_usage', 0),
			viewport_scale=metrics.get('viewport_scale', 1.0),
			fps=1000.0 / metrics.get('frame_time', 16.7) if metrics.get('frame_time', 0) > 0 else 60.0
		)
		self.snapshots.append(snapshot)
		self._log_snapshot(snapshot)
		
	def _log_snapshot(self, snapshot: PerformanceSnapshot):
		self.logger.debug(json.dumps({
			'timestamp': snapshot.timestamp,
			'fps': snapshot.fps,
			'frame_time': snapshot.frame_time,
			'render_time': snapshot.render_time,
			'layout_time': snapshot.layout_time,
			'node_count': snapshot.node_count,
			'edge_count': snapshot.edge_count,
			'memory_usage': snapshot.memory_usage,
			'viewport_scale': snapshot.viewport_scale
		}))
		
	def get_performance_report(self) -> str:
		if not self.snapshots:
			return "No performance data available"
			
		recent = list(self.snapshots)[-60:]  # Last second at 60 FPS
		avg_fps = sum(s.fps for s in recent) / len(recent)
		avg_frame_time = sum(s.frame_time for s in recent) / len(recent)
		
		return f"""Performance Report
===================
Average FPS: {avg_fps:.1f}
Frame Time: {avg_frame_time:.1f}ms
Node Count: {recent[-1].node_count}
Edge Count: {recent[-1].edge_count}
Memory Usage: {recent[-1].memory_usage/1024/1024:.1f}MB
Viewport Scale: {recent[-1].viewport_scale:.2f}x
"""

	def copy_report_to_clipboard(self) -> None:
		"""Copy current performance report to clipboard."""
		try:
			report = self.get_performance_report()
			if report:
				clipboard = QApplication.clipboard()
				clipboard.setText(report)
		except Exception as e:
			print(f"Error copying performance report: {str(e)}")