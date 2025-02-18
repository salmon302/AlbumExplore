from typing import List, Dict, Tuple, Optional
import math
from dataclasses import dataclass
from .models import VisualNode, VisualEdge, Point
from .physics.force_params import ForceParams

@dataclass

class Quadrant:
	x: float
	y: float
	width: float
	height: float
	mass: float = 0.0
	center_x: float = 0.0
	center_y: float = 0.0
	nodes: List[str] = None
	children: Dict[str, 'Quadrant'] = None

	def __post_init__(self):
		self.nodes = []
		self.children = {}

class BarnesHutTree:
	def __init__(self, theta: float = 0.5):
		self.theta = theta
		self.root: Optional[Quadrant] = None

	def build(self, positions: Dict[str, Point], bounds: Tuple[float, float, float, float]):
		min_x, max_x, min_y, max_y = bounds
		self.root = Quadrant(min_x, min_y, max_x - min_x, max_y - min_y)
		
		for node_id, pos in positions.items():
			self._insert(self.root, node_id, pos, positions)

	def _insert(self, quad: Quadrant, node_id: str, pos: Point, positions: Dict[str, Point]) -> bool:
		if not (quad.x <= pos.x <= quad.x + quad.width and
				quad.y <= pos.y <= quad.y + quad.height):
			return False

		quad.mass += 1.0
		quad.center_x = ((quad.center_x * (quad.mass - 1.0) + pos.x) / quad.mass)
		quad.center_y = ((quad.center_y * (quad.mass - 1.0) + pos.y) / quad.mass)

		if len(quad.nodes) < 4 and not quad.children:
			quad.nodes.append(node_id)
			return True

		if not quad.children:
			self._split(quad)
			for old_id in quad.nodes:
				self._insert_to_children(quad, old_id, positions[old_id], positions)
			quad.nodes.clear()

		return self._insert_to_children(quad, node_id, pos, positions)

	def _split(self, quad: Quadrant):
		w2 = quad.width / 2
		h2 = quad.height / 2
		quad.children = {
			'nw': Quadrant(quad.x, quad.y, w2, h2),
			'ne': Quadrant(quad.x + w2, quad.y, w2, h2),
			'sw': Quadrant(quad.x, quad.y + h2, w2, h2),
			'se': Quadrant(quad.x + w2, quad.y + h2, w2, h2)
		}

	def _insert_to_children(self, quad: Quadrant, node_id: str, pos: Point, positions: Dict[str, Point]) -> bool:
		for child in quad.children.values():
			if self._insert(child, node_id, pos, positions):
				return True
		return False

class PhysicsSystem:
	def __init__(self, params: ForceParams = None):
		self.params = params or ForceParams()
		self.barnes_hut = BarnesHutTree()
		self.edge_bundling_threshold = 0.1
		self.min_edge_distance = 20.0
		self.theta = 0.8
		self._edge_cache = {}
		self._force_cache = {}
		self._position_history = {}  # Add position history for smoothing
		self._history_length = 3     # Number of frames to average

	def calculate_forces(self, nodes: List[VisualNode], edges: List[VisualEdge], 
						positions: Dict[str, Point], velocities: Dict[str, Point]) -> Dict[str, Point]:
		"""Calculate forces with optimized performance."""
		# Clear caches if too large
		if len(self._force_cache) > 2000:
			self._force_cache.clear()
		if len(self._edge_cache) > 2000:
			self._edge_cache.clear()

		# Skip Barnes-Hut for small graphs
		use_barnes_hut = len(nodes) > 50
		if use_barnes_hut:
			bounds = self._get_bounds(positions)
			self.barnes_hut.build(positions, bounds)

		# Process edges
		if len(edges) > 200:
			edge_key = hash(tuple(sorted((e.source, e.target) for e in edges)))
			if edge_key not in self._edge_cache:
				self._edge_cache[edge_key] = self._bundle_edges(edges, positions)
			edges = self._edge_cache[edge_key]

		# Calculate forces in batches
		forces = {}
		batch_size = min(50, len(nodes))
		for i in range(0, len(nodes), batch_size):
			batch = nodes[i:i + batch_size]
			for node in batch:
				pos = positions[node.id]
				cache_key = (node.id, round(pos.x, 1), round(pos.y, 1))
				
				if cache_key in self._force_cache:
					forces[node.id] = self._force_cache[cache_key]
					continue

				# Calculate forces
				if use_barnes_hut:
					fx, fy = self._apply_barnes_hut_forces(self.barnes_hut.root, pos)
				else:
					fx, fy = 0.0, 0.0

				# Add edge forces
				max_force = self.params.max_velocity * 2
				for edge in (e for e in edges if e.source == node.id or e.target == node.id):
					other_id = edge.target if edge.source == node.id else edge.source
					other_pos = positions[other_id]
					
					dx = other_pos.x - pos.x
					dy = other_pos.y - pos.y
					dist_sq = dx * dx + dy * dy
					
					if dist_sq < 0.01 or dist_sq > 250000:  # Skip if too close or too far
						continue
						
					dist = math.sqrt(dist_sq)
					force = min(dist * self.params.attraction * edge.weight, max_force)
					
					fx += (dx / dist) * force
					fy += (dy / dist) * force
					
					if abs(fx) > max_force or abs(fy) > max_force:
						fx = max_force if fx > 0 else -max_force
						fy = max_force if fy > 0 else -max_force
						break

				force = Point(fx, fy)
				self._force_cache[cache_key] = force
				forces[node.id] = force

		return self._apply_forces(forces, positions, velocities)

	def _get_bounds(self, positions: Dict[str, Point]) -> Tuple[float, float, float, float]:
		if not positions:
			return (0.0, 0.0, 0.0, 0.0)
		
		points = list(positions.values())
		min_x = min(p.x for p in points)
		max_x = max(p.x for p in points)
		min_y = min(p.y for p in points)
		max_y = max(p.y for p in points)
		
		return (min_x, max_x, min_y, max_y)

	def _calculate_node_forces(self, node: VisualNode, positions: Dict[str, Point], 
							 edges: List[VisualEdge]) -> Point:
		pos = positions[node.id]
		cache_key = (node.id, pos.x, pos.y)
		
		if cache_key in self._force_cache:
			return self._force_cache[cache_key]
		
		# Calculate repulsion using Barnes-Hut
		force_x, force_y = self._apply_barnes_hut_forces(self.barnes_hut.root, pos)
		
		# Calculate edge forces with early exit optimization
		max_force = self.params.max_velocity * 2
		for edge in edges:
			if edge.source == node.id or edge.target == node.id:
				other_id = edge.target if edge.source == node.id else edge.source
				other_pos = positions[other_id]
				
				dx = other_pos.x - pos.x
				dy = other_pos.y - pos.y
				distance_sq = dx * dx + dy * dy
				
				if distance_sq < 0.01:  # Early exit for very close nodes
					continue
					
				distance = math.sqrt(distance_sq)
				force = min(distance * self.params.attraction * edge.weight, max_force)
				
				force_x += (dx / distance) * force
				force_y += (dy / distance) * force
				
				# Early exit if forces are too high
				if abs(force_x) > max_force or abs(force_y) > max_force:
					force_x = max_force if force_x > 0 else -max_force
					force_y = max_force if force_y > 0 else -max_force
					break

		result = Point(force_x, force_y)
		self._force_cache[cache_key] = result
		return result


	def _apply_barnes_hut_forces(self, quad: Quadrant, pos: Point) -> Tuple[float, float]:
		if not quad or quad.mass == 0:
			return 0.0, 0.0

		dx = quad.center_x - pos.x
		dy = quad.center_y - pos.y
		distance_sq = dx * dx + dy * dy + 0.01

		if len(quad.nodes) == 1 or (quad.width * quad.width / distance_sq < self.theta * self.theta):
			distance = math.sqrt(distance_sq)
			force = self.params.repulsion * quad.mass / distance_sq
			return (dx / distance) * force, (dy / distance) * force
		
		total_fx = 0.0
		total_fy = 0.0
		for child in quad.children.values():
			fx, fy = self._apply_barnes_hut_forces(child, pos)
			total_fx += fx
			total_fy += fy
		return total_fx, total_fy

	def _bundle_edges(self, edges: List[VisualEdge], positions: Dict[str, Point]) -> List[VisualEdge]:
		bundled_edges = []
		edge_groups = {}
		
		# Group edges by similarity
		for edge in edges:
			src_pos = positions[edge.source]
			tgt_pos = positions[edge.target]
			angle = math.atan2(tgt_pos.y - src_pos.y, tgt_pos.x - src_pos.x)
			dist = math.sqrt((tgt_pos.x - src_pos.x)**2 + (tgt_pos.y - src_pos.y)**2)
			
			key = (round(angle / self.edge_bundling_threshold), round(dist / self.min_edge_distance))
			if key not in edge_groups:
				edge_groups[key] = []
			edge_groups[key].append(edge)
		
		# Create bundled edges
		for group in edge_groups.values():
			if len(group) > 1:
				# Combine edge weights
				total_weight = sum(e.weight for e in group)
				bundled_edge = VisualEdge(
					source=group[0].source,
					target=group[0].target,
					weight=total_weight
				)
				bundled_edges.append(bundled_edge)
			else:
				bundled_edges.extend(group)
		
		return bundled_edges

	def _smooth_position(self, node_id: str, new_pos: Point) -> Point:
		"""Apply position smoothing."""
		if node_id not in self._position_history:
			self._position_history[node_id] = []
		
		history = self._position_history[node_id]
		history.append(new_pos)
		
		if len(history) > self._history_length:
			history.pop(0)
		
		# Weighted average with more recent positions having higher weight
		weights = [i + 1 for i in range(len(history))]
		total_weight = sum(weights)
		
		x = sum(pos.x * w for pos, w in zip(history, weights)) / total_weight
		y = sum(pos.y * w for pos, w in zip(history, weights)) / total_weight
		
		return Point(x=x, y=y)

	def _apply_forces(self, forces: Dict[str, Point], positions: Dict[str, Point],
					 velocities: Dict[str, Point]) -> Dict[str, Point]:
		"""Apply forces with smoothing and stability improvements."""
		new_positions = {}
		
		for node_id, force in forces.items():
			vel = velocities[node_id]
			pos = positions[node_id]
			
			# Apply damping with velocity scaling
			scale = min(1.0, 50.0 / len(positions))  # Scale based on graph size
			vel.x = (vel.x + force.x * scale) * self.params.damping
			vel.y = (vel.y + force.y * scale) * self.params.damping
			
			# Progressive velocity limiting
			speed = math.sqrt(vel.x * vel.x + vel.y * vel.y)
			max_velocity = self.params.max_velocity * (1.0 - 0.5 * scale)
			if speed > max_velocity:
				vel.x *= max_velocity / speed
				vel.y *= max_velocity / speed
			
			# Calculate new position
			raw_pos = Point(
				x=pos.x + vel.x,
				y=pos.y + vel.y
			)
			
			# Apply position smoothing
			smoothed_pos = self._smooth_position(node_id, raw_pos)
			new_positions[node_id] = smoothed_pos
		
		return new_positions