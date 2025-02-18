from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import time
from collections import deque
import statistics

@dataclass
class PerformanceMetrics:
	frame_time: float
	render_time: float
	layout_time: float
	clustering_time: float
	node_count: int
	edge_count: int
	visible_node_count: int
	visible_edge_count: int
	memory_usage: float
	viewport_scale: float = 1.0
	antialiasing_enabled: bool = True
	edge_bundling_enabled: bool = False

class PerformanceOptimizer:
	def __init__(self, target_fps: float = 30.0):
		self.target_fps = target_fps
		self.target_frame_time = 1000.0 / target_fps
		self.metrics_history = deque(maxlen=120)  # 2 seconds at 60 FPS
		self.current_metrics: Optional[PerformanceMetrics] = None
		
		# Performance thresholds (ms)
		self.critical_frame_time = 33.3   # 30 FPS
		self.warning_frame_time = 16.7    # 60 FPS
		
		# Optimization state
		self.optimization_level = 0
		self.last_optimization_time = time.time()
		self.optimization_cooldown = 1.0  # seconds
		
	def start_frame(self) -> float:
		"""Start frame timing."""
		return time.perf_counter()
		
	def end_frame(self, start_time: float, metrics: PerformanceMetrics) -> None:
		"""End frame timing and update metrics."""
		frame_time = metrics.frame_time if metrics.frame_time > 0 else (time.perf_counter() - start_time) * 1000
		new_metrics = PerformanceMetrics(
			frame_time=frame_time,
			render_time=metrics.render_time,
			layout_time=metrics.layout_time,
			clustering_time=metrics.clustering_time,
			node_count=metrics.node_count,
			edge_count=metrics.edge_count,
			visible_node_count=metrics.visible_node_count,
			visible_edge_count=metrics.visible_edge_count,
			memory_usage=metrics.memory_usage,
			viewport_scale=metrics.viewport_scale,
			antialiasing_enabled=metrics.antialiasing_enabled,
			edge_bundling_enabled=metrics.edge_bundling_enabled
		)
		self.current_metrics = new_metrics
		self.metrics_history.append(new_metrics)
		
	def get_optimization_suggestions(self) -> List[Tuple[str, bool]]:
		"""Get performance optimization suggestions with priority flags."""
		if not self.current_metrics:
			return []
			
		suggestions = []
		frame_time = self.current_metrics.frame_time
		
		# Critical optimizations (frame time > 33.3ms)
		if frame_time > self.critical_frame_time:
			suggestions.append(("Disable antialiasing", True))
			suggestions.append(("Reduce visible nodes using stricter LOD", True))
			suggestions.append(("Enable edge sampling", True))
			
		# Warning optimizations (frame time > 16.7ms)
		elif frame_time > self.warning_frame_time:
			if self.current_metrics.antialiasing_enabled:
				suggestions.append(("Consider disabling antialiasing", False))
			if self.current_metrics.visible_edge_count > 1000:
				suggestions.append(("Enable edge bundling", False))
			if self.current_metrics.viewport_scale < 0.5:
				suggestions.append(("Increase LOD aggressiveness", False))
				
		return suggestions
		
	def get_performance_stats(self) -> Dict[str, float]:
		"""Get current performance statistics."""
		if not self.metrics_history:
			return {}
			
		recent_metrics = list(self.metrics_history)[-10:]  # Last 10 frames
		
		return {
			'avg_fps': 1000.0 / statistics.mean(m.frame_time for m in recent_metrics),
			'avg_frame_time': statistics.mean(m.frame_time for m in recent_metrics),
			'avg_render_time': statistics.mean(m.render_time for m in recent_metrics),
			'avg_layout_time': statistics.mean(m.layout_time for m in recent_metrics),
			'avg_clustering_time': statistics.mean(m.clustering_time for m in recent_metrics),
			'avg_visible_nodes': statistics.mean(m.visible_node_count for m in recent_metrics),
			'avg_visible_edges': statistics.mean(m.visible_edge_count for m in recent_metrics)
		}
		
	def should_apply_optimization(self, current_frame_time: float) -> bool:
		"""Determine if optimizations should be applied."""
		if time.time() - self.last_optimization_time < self.optimization_cooldown:
			return False
			
		return current_frame_time > self.critical_frame_time
		
	def get_optimal_lod_settings(self) -> Dict[str, float]:
		"""Calculate optimal LOD settings based on performance."""
		if not self.current_metrics:
			return {}
			
		frame_time = self.current_metrics.frame_time
		visible_nodes = self.current_metrics.visible_node_count
		visible_edges = self.current_metrics.visible_edge_count
		
		# Adjust thresholds based on performance
		node_scale = min(1.0, self.target_frame_time / frame_time)
		edge_scale = min(1.0, self.target_frame_time / frame_time)
		
		return {
			'node_threshold': max(50, int(visible_nodes * node_scale)),
			'edge_threshold': max(100, int(visible_edges * edge_scale)),
			'cluster_threshold': min(0.5, 0.1 + (self.optimization_level * 0.1))
		}
		
	def update_optimization_level(self, frame_time: float) -> None:
		"""Update optimization level based on performance."""
		if frame_time > self.critical_frame_time:
			self.optimization_level = min(5, self.optimization_level + 1)
		elif frame_time < self.warning_frame_time:
			self.optimization_level = max(0, self.optimization_level - 1)
