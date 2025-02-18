from typing import List, Dict, Set, Tuple
import math
import numpy as np
from PyQt6.QtGui import QPainterPath
from PyQt6.QtCore import QPointF
from .models import VisualNode, VisualEdge
from .layout import Point

class ClusterEngine:
	def __init__(self, min_cluster_size: int = 3):
		self.min_cluster_size = min_cluster_size
		self._clusters: List[Set[str]] = []
		self._node_positions: Dict[str, Tuple[float, float]] = {}
		self._boundary_smoothing = 0.3
		self._cluster_padding = 20.0
		self._last_update_time = 0.0
		self._update_interval = 0.5  # seconds
		self._cached_boundaries = []
		self._cache_valid = False
		self._position_hash = 0

	def update_clusters(self, nodes: List[VisualNode], edges: List[VisualEdge], 
					   positions: Dict[str, Point], current_time: float = 0.0) -> List[QPainterPath]:
		"""Update cluster assignments with caching."""
		# Check if update is needed
		new_pos_hash = hash(tuple((node_id, pos.x, pos.y) for node_id, pos in positions.items()))
		if (current_time - self._last_update_time < self._update_interval and 
			self._cache_valid and new_pos_hash == self._position_hash):
			return self._cached_boundaries

		self._position_hash = new_pos_hash
		self._last_update_time = current_time
		self._node_positions = {node_id: (pos.x, pos.y) for node_id, pos in positions.items()}
		
		# Optimize adjacency matrix creation
		node_indices = {node.id: i for i, node in enumerate(nodes)}
		n = len(nodes)
		adj_matrix = np.zeros((n, n), dtype=np.float32)  # Use float32 for memory efficiency
		
		# Batch edge processing
		edge_pairs = [(node_indices[e.source], node_indices[e.target], e.weight) 
					  for e in edges if e.source in node_indices and e.target in node_indices]
		if edge_pairs:
			rows, cols, weights = zip(*edge_pairs)
			adj_matrix[rows, cols] = weights
			adj_matrix[cols, rows] = weights

		# Update clusters and boundaries
		self._clusters = self._spectral_clustering(adj_matrix, node_indices)
		self._cached_boundaries = self._generate_boundaries()
		self._cache_valid = True
		
		return self._cached_boundaries

	def _spectral_clustering(self, adj_matrix: np.ndarray, node_indices: Dict[str, int]) -> List[Set[str]]:
		"""Simple distance-based clustering without scipy dependency."""
		n = len(node_indices)
		if n == 0:
			return []
			
		# Convert indices back to node IDs
		reverse_indices = {i: node_id for node_id, i in node_indices.items()}
		
		# Simple distance-based clustering
		clusters = []
		used_nodes = set()
		
		for i in range(n):
			if i in used_nodes:
				continue
				
			# Start new cluster
			cluster = {reverse_indices[i]}
			used_nodes.add(i)
			
			# Find connected nodes
			for j in range(n):
				if j in used_nodes:
					continue
				if adj_matrix[i][j] > 0:  # If nodes are connected
					cluster.add(reverse_indices[j])
					used_nodes.add(j)
					
			if len(cluster) >= self.min_cluster_size:
				clusters.append(cluster)
		
		return clusters


	def _generate_boundaries(self) -> List[QPainterPath]:
		"""Generate smooth cluster boundaries with padding."""
		boundaries = []
		for cluster in self._clusters:
			if len(cluster) < 3:
				continue
				
			points = [self._node_positions[node_id] for node_id in cluster]
			if not points:
				continue
				
			# Add padding points around cluster
			padded_points = self._add_boundary_padding(points)
			
			# Create smooth hull
			hull = self._compute_smooth_hull(padded_points)
			if not hull:
				continue
				
			path = self._create_smooth_path(hull)
			boundaries.append(path)
			
		return boundaries

	def _add_boundary_padding(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
		"""Add padding points around cluster boundary."""
		if not points:
			return []
			
		# Calculate cluster centroid
		centroid_x = sum(p[0] for p in points) / len(points)
		centroid_y = sum(p[1] for p in points) / len(points)
		
		padded_points = []
		for x, y in points:
			# Calculate vector from centroid to point
			dx = x - centroid_x
			dy = y - centroid_y
			dist = np.sqrt(dx*dx + dy*dy)
			if dist > 0:
				# Add padded point
				pad_x = x + (dx/dist) * self._cluster_padding
				pad_y = y + (dy/dist) * self._cluster_padding
				padded_points.append((pad_x, pad_y))
			
		return padded_points

	def _create_smooth_path(self, hull_points: List[Tuple[float, float]]) -> QPainterPath:
		"""Create a smooth path with Bezier curves."""
		if not hull_points:
			return QPainterPath()
			
		path = QPainterPath()
		n_points = len(hull_points)
		
		# Start path
		path.moveTo(QPointF(hull_points[0][0], hull_points[0][1]))
		
		# Create smooth curves between points
		for i in range(n_points):
			p1 = hull_points[i]
			p2 = hull_points[(i + 1) % n_points]
			p3 = hull_points[(i + 2) % n_points]
			
			# Calculate control points
			ctrl1_x = p1[0] + (p2[0] - p1[0]) * self._boundary_smoothing
			ctrl1_y = p1[1] + (p2[1] - p1[1]) * self._boundary_smoothing
			ctrl2_x = p2[0] - (p3[0] - p2[0]) * self._boundary_smoothing
			ctrl2_y = p2[1] - (p3[1] - p2[1]) * self._boundary_smoothing
			
			# Add cubic curve
			path.cubicTo(
				QPointF(ctrl1_x, ctrl1_y),
				QPointF(ctrl2_x, ctrl2_y),
				QPointF(p2[0], p2[1])
			)
		
		return path

	def _compute_smooth_hull(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
		"""Compute smooth concave hull with reduced complexity."""
		hull = self._compute_concave_hull(points)
		if len(hull) <= 3:
			return hull
			
		# Simplify hull while maintaining shape
		simplified = []
		prev_point = hull[0]
		simplified.append(prev_point)
		
		for i in range(1, len(hull) - 1):
			curr_point = hull[i]
			next_point = hull[i + 1]
			
			# Calculate angles
			angle1 = np.arctan2(curr_point[1] - prev_point[1], 
							  curr_point[0] - prev_point[0])
			angle2 = np.arctan2(next_point[1] - curr_point[1], 
							  next_point[0] - curr_point[0])
			
			# Add point if angle change is significant
			if abs(angle1 - angle2) > 0.3:  # threshold in radians
				simplified.append(curr_point)
				prev_point = curr_point
		
		simplified.append(hull[-1])
		return simplified

	def _compute_concave_hull(self, points: List[Tuple[float, float]], 
							alpha: float = 2.0) -> List[Tuple[float, float]]:
		"""Compute simple convex hull for a set of points using Graham scan."""
		if len(points) < 3:
			return []
			
		def orientation(p: Tuple[float, float], q: Tuple[float, float], 
					   r: Tuple[float, float]) -> float:
			"""Return orientation of triplet (p, q, r)."""
			val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
			return val
		
		# Find bottom-most point (and left-most if tied)
		bottom_point = min(points, key=lambda p: (p[1], p[0]))
		
		# Sort points based on polar angle and distance from bottom_point
		sorted_points = sorted(
			[p for p in points if p != bottom_point],
			key=lambda p: (
				math.atan2(p[1] - bottom_point[1], p[0] - bottom_point[0]),
				(p[0] - bottom_point[0])**2 + (p[1] - bottom_point[1])**2
			)
		)
		
		# Initialize hull with first three points
		hull = [bottom_point]
		for p in sorted_points:
			while len(hull) > 1 and orientation(hull[-2], hull[-1], p) <= 0:
				hull.pop()
			hull.append(p)
		
		# Add first point to close the hull
		if len(hull) > 2:
			hull.append(hull[0])
			
		return hull

