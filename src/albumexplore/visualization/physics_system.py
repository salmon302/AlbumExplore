from typing import List, Dict, Tuple, Optional, Set
import math
import random
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

@dataclass
class PhysicsState:
	"""Current state of physics simulation."""
	positions: Dict[str, Point]
	velocities: Dict[str, Point]
	forces: Dict[str, Point]
	total_kinetic_energy: float = float('inf')
	iterations: int = 0

class PhysicsSystem:
	"""Physics system for force-directed layout."""
	
	def __init__(self, params: ForceParams = None):
		self.params = params or ForceParams()
		self.state = PhysicsState(
			positions={},
			velocities={},
			forces={},
		)
		self._fixed_nodes: Set[str] = set()
		
	def initialize(self, nodes: List[VisualNode], width: float, height: float):
		"""Initialize physics state."""
		center_x = width / 2
		center_y = height / 2
		radius = min(width, height) * 0.4
		
		for i, node in enumerate(nodes):
			# Place nodes in a circle initially
			angle = (2 * math.pi * i) / len(nodes)
			x = center_x + radius * math.cos(angle)
			y = center_y + radius * math.sin(angle)
			
			# Store position
			self.state.positions[node.id] = Point(x, y)
			self.state.velocities[node.id] = Point(0.0, 0.0)
			self.state.forces[node.id] = Point(0.0, 0.0)
			
			# Update node position
			node.pos['x'] = x
			node.pos['y'] = y
			
		self.state.total_kinetic_energy = float('inf')
		self.state.iterations = 0
	
	def fix_node(self, node_id: str):
		"""Fix a node in place."""
		self._fixed_nodes.add(node_id)
	
	def unfix_node(self, node_id: str):
		"""Allow a node to move again."""
		self._fixed_nodes.discard(node_id)
	
	def _apply_repulsion(self, p1: Point, p2: Point) -> Tuple[float, float]:
		"""Calculate repulsion force between two points."""
		dx = p1.x - p2.x
		dy = p1.y - p2.y
		distance_sq = dx * dx + dy * dy
		
		if distance_sq < 0.01:
			dx = 0.1 * (0.5 - random.random())
			dy = 0.1 * (0.5 - random.random())
			distance_sq = dx * dx + dy * dy
		
		distance = math.sqrt(distance_sq)
		force = self.params.repulsion / distance_sq
		return force * dx / distance, force * dy / distance
	
	def _apply_spring_force(self, p1: Point, p2: Point, weight: float = 1.0) -> Tuple[float, float]:
		"""Calculate spring force between two points."""
		dx = p1.x - p2.x
		dy = p1.y - p2.y
		distance = math.sqrt(dx * dx + dy * dy)
		
		if distance < 0.01:
			return 0.0, 0.0
		
		force = self.params.spring_coefficient * (distance - self.params.spring_length)
		fx = force * dx / distance * weight
		fy = force * dy / distance * weight
		return fx, fy
	
	def _apply_center_gravity(self, p: Point, center: Point) -> Tuple[float, float]:
		"""Apply gravitational force toward center."""
		dx = center.x - p.x
		dy = center.y - p.y
		distance = math.sqrt(dx * dx + dy * dy)
		
		if distance < 0.01:
			return 0.0, 0.0
		
		force = self.params.gravitational_constant * distance
		return force * dx / distance, force * dy / distance
	
	def _apply_boundary_force(self, p: Point, width: float, height: float) -> Tuple[float, float]:
		"""Apply force to keep nodes within bounds."""
		margin = 20.0
		fx = fy = 0.0
		
		# Left boundary
		if p.x < margin:
			fx += self.params.boundary_force
		# Right boundary
		elif p.x > width - margin:
			fx -= self.params.boundary_force
		# Top boundary
		if p.y < margin:
			fy += self.params.boundary_force
		# Bottom boundary
		elif p.y > height - margin:
			fy -= self.params.boundary_force
			
		return fx, fy
	
	def step(self, nodes: List[VisualNode], edges: List[VisualEdge], width: float, height: float) -> bool:
		"""Perform one physics step."""
		if not nodes:
			return False
			
		# Clear forces
		for node_id in self.state.forces:
			self.state.forces[node_id] = Point(0.0, 0.0)
		
		# Center point for gravity
		center = Point(width / 2, height / 2)
		
		# Calculate repulsion between all nodes
		for i, node1 in enumerate(nodes):
			if node1.id in self._fixed_nodes:
				continue
				
			pos1 = self.state.positions[node1.id]
			
			# Node-node repulsion
			for node2 in nodes[i+1:]:
				pos2 = self.state.positions[node2.id]
				fx, fy = self._apply_repulsion(pos1, pos2)
				
				if node2.id not in self._fixed_nodes:
					self.state.forces[node2.id].x -= fx
					self.state.forces[node2.id].y -= fy
					
				self.state.forces[node1.id].x += fx
				self.state.forces[node1.id].y += fy
			
			# Center gravity
			gx, gy = self._apply_center_gravity(pos1, center)
			self.state.forces[node1.id].x += gx
			self.state.forces[node1.id].y += gy
			
			# Boundary forces
			bx, by = self._apply_boundary_force(pos1, width, height)
			self.state.forces[node1.id].x += bx
			self.state.forces[node1.id].y += by
		
		# Calculate spring forces for edges
		for edge in edges:
			if edge.source in self._fixed_nodes and edge.target in self._fixed_nodes:
				continue
				
			source_pos = self.state.positions[edge.source]
			target_pos = self.state.positions[edge.target]
			fx, fy = self._apply_spring_force(source_pos, target_pos, edge.weight)
			
			if edge.source not in self._fixed_nodes:
				self.state.forces[edge.source].x -= fx
				self.state.forces[edge.source].y -= fy
				
			if edge.target not in self._fixed_nodes:
				self.state.forces[edge.target].x += fx
				self.state.forces[edge.target].y += fy
		
		# Update velocities and positions
		self.state.total_kinetic_energy = 0.0
		temperature = self.params.temperature * (self.params.cooling_rate ** self.state.iterations)
		
		for node in nodes:
			if node.id in self._fixed_nodes:
				continue
				
			# Get current values
			force = self.state.forces[node.id]
			velocity = self.state.velocities[node.id]
			position = self.state.positions[node.id]
			
			# Update velocity with damping
			velocity.x = (velocity.x + force.x * self.params.time_step) * self.params.damping * temperature
			velocity.y = (velocity.y + force.y * self.params.time_step) * self.params.damping * temperature
			
			# Update position
			position.x += velocity.x * self.params.time_step
			position.y += velocity.y * self.params.time_step
			
			# Update node position
			node.pos['x'] = position.x
			node.pos['y'] = position.y
			
			# Update kinetic energy
			speed_squared = velocity.x * velocity.x + velocity.y * velocity.y
			self.state.total_kinetic_energy += speed_squared
		
		# Increment iteration count
		self.state.iterations += 1
		
		# Check convergence
		return (self.state.total_kinetic_energy > self.params.min_movement and 
				self.state.iterations < self.params.max_iterations)
	
	def reset(self):
		"""Reset physics state."""
		self.state = PhysicsState(
			positions={},
			velocities={},
			forces={},
		)
		self._fixed_nodes.clear()