from typing import List, Dict, Any, Tuple, Set
import math
import random
import time
from collections import defaultdict
from .models import VisualNode, VisualEdge, Point
from .physics.force_params import ForceParams
from .physics_system import PhysicsSystem


class MultiLevelLayout:
	"""Handles multilevel force-directed layout"""
	def __init__(self, nodes: List[VisualNode], edges: List[VisualEdge]):
		self.nodes = nodes
		self.edges = edges
		self.levels: List[Tuple[List[VisualNode], List[VisualEdge]]] = []
		
	def coarsen(self) -> None:
		"""Create hierarchical levels of the graph"""
		current_nodes = self.nodes.copy()
		current_edges = self.edges.copy()
		
		while len(current_nodes) > 100:  # Increased threshold
			matches = self._find_matches(current_nodes, current_edges)
			if not matches:
				break
			new_nodes, new_edges = self._collapse_matches(current_nodes, current_edges, matches)
			self.levels.append((current_nodes, current_edges))
			current_nodes = new_nodes
			current_edges = new_edges
		self.levels.append((current_nodes, current_edges))


	def _find_matches(self, nodes: List[VisualNode], 
					 edges: List[VisualEdge]) -> List[Tuple[str, str]]:
		"""Find pairs of nodes to collapse based on edge weights"""
		edge_weights = defaultdict(float)
		for edge in edges:
			edge_weights[(edge.source, edge.target)] = edge.weight
			
		matches = []
		used_nodes = set()
		
		# Sort edges by weight for better matching
		sorted_edges = sorted(edges, key=lambda e: e.weight, reverse=True)
		
		for edge in sorted_edges:
			if (edge.source not in used_nodes and 
				edge.target not in used_nodes):
				matches.append((edge.source, edge.target))
				used_nodes.add(edge.source)
				used_nodes.add(edge.target)
				
		return matches

	def _collapse_matches(self, nodes: List[VisualNode], 
						 edges: List[VisualEdge],
						 matches: List[Tuple[str, str]]) -> Tuple[List[VisualNode], List[VisualEdge]]:
		"""Collapse matched nodes into super-nodes"""
		new_nodes = []
		node_map = {}  # Maps original nodes to super-nodes
		
		# Create super-nodes
		for n1_id, n2_id in matches:
			super_id = f"super_{n1_id}_{n2_id}"
			super_node = VisualNode(
				id=super_id,
				label=f"SN_{len(new_nodes)}",
				size=sum(n.size for n in nodes if n.id in (n1_id, n2_id)),
				color=nodes[0].color,
				shape=nodes[0].shape,
				data={}
			)
			new_nodes.append(super_node)
			node_map[n1_id] = super_id
			node_map[n2_id] = super_id
			
		# Add unmatched nodes
		matched_ids = {id for pair in matches for id in pair}
		for node in nodes:
			if node.id not in matched_ids:
				new_nodes.append(node)
				node_map[node.id] = node.id
				
		# Create new edges
		new_edges = []
		edge_weights = defaultdict(float)
		
		for edge in edges:
			source = node_map[edge.source]
			target = node_map[edge.target]
			if source != target:
				edge_weights[(source, target)] += edge.weight
				
		for (source, target), weight in edge_weights.items():
			new_edges.append(VisualEdge(
				source=source,
				target=target,
				weight=weight,
				thickness=math.sqrt(weight),
				color=edges[0].color,
				data={}
			))
			
		return new_nodes, new_edges

def create_bundled_edge(edges: List[VisualEdge]) -> VisualEdge:
	"""Create a bundled edge from multiple edges."""
	weight = sum(e.weight for e in edges)
	base_thickness = 2.0  # Use fixed base thickness
	
	return VisualEdge(
		source=edges[0].source,
		target=edges[0].target,
		weight=weight,
		thickness=base_thickness,  # Use fixed base thickness
		color=edges[0].color,
		data={
			'bundled': True,
			'edges': edges,
			'initial_thickness': base_thickness
		}
	)

class ForceDirectedLayout:
	def __init__(self, params: ForceParams = None):
		self.params = params or ForceParams()
		self.physics = PhysicsSystem(self.params)
		self.positions: Dict[str, Point] = {}
		self.velocities: Dict[str, Point] = {}
		self._nodes = None
		self._node_lookup = {}
		self.layout_iterations = 0

		
	def initialize_positions(self, nodes: List[VisualNode], width: float, height: float) -> None:
		"""Initialize node positions in a spiral layout for better distribution"""
		radius = min(width, height) * 0.3  # Reduced initial radius
		center_x = width / 2
		center_y = height / 2
		
		# Clear existing positions and velocities
		self.positions.clear()
		self.velocities.clear()
		
		# Place nodes in a spiral pattern
		angle = 0
		radius_step = radius / (len(nodes) + 1)
		current_radius = radius_step
		
		for node in nodes:
			self.positions[node.id] = Point(
				x=center_x + current_radius * math.cos(angle),
				y=center_y + current_radius * math.sin(angle)
			)
			self.velocities[node.id] = Point(x=0.0, y=0.0)
			
			# Adjust angle and radius for next node
			angle += math.pi * (3.0 - math.sqrt(5.0))  # Golden angle
			current_radius += radius_step / (2 * math.pi)
		
	def layout(self, nodes: List[VisualNode], edges: List[VisualEdge], width: float, height: float) -> Dict[str, Point]:
		"""Layout with improved stability."""
		self._nodes = nodes
		self._node_lookup = {node.id: node for node in nodes}
		
		# Handle single node case first
		if len(nodes) <= 1:
			if len(nodes) == 1:
				pos = Point(x=width/2, y=height/2)
				self.positions[nodes[0].id] = pos
				nodes[0].data = nodes[0].data or {}
				nodes[0].pos = nodes[0].pos or {}
				nodes[0].data['x'] = pos.x
				nodes[0].data['y'] = pos.y
				nodes[0].pos['x'] = pos.x
				nodes[0].pos['y'] = pos.y
			return self.positions

		# Initialize positions only if not already set
		positions_exist = all(
			hasattr(node, 'data') and isinstance(node.data, dict) and
			'x' in node.data and 'y' in node.data
			for node in nodes
		)
		
		if not positions_exist:
			self.initialize_positions(nodes, width, height)
		else:
			# Use existing positions
			for node in nodes:
				self.positions[node.id] = Point(
					x=node.data['x'],
					y=node.data['y']
				)
				self.velocities[node.id] = Point(x=0.0, y=0.0)
		
		# Bundle edges with stability
		bundled_edges = self._bundle_edges(edges)
		
		# Reduced iterations for better stability
		max_iter = min(3, max(1, len(nodes) // 100))
		
		# Apply forces with damping
		for i in range(max_iter):
			if self.apply_forces(nodes, bundled_edges):
				break
			# Increase damping with each iteration
			self.params.damping *= 1.1
		
		# Reset damping
		self.params.damping = 0.8
		
		# Scale positions smoothly
		self._scale_positions(width, height)
		
		# Update node positions atomically
		for node_id, pos in self.positions.items():
			node = self._node_lookup.get(node_id)
			if node:
				if not isinstance(node.data, dict):
					node.data = {}
				if not hasattr(node, 'pos'):
					node.pos = {}
				# Update all position representations atomically
				node.data['x'] = pos.x
				node.data['y'] = pos.y
				node.pos['x'] = pos.x
				node.pos['y'] = pos.y
		
		return self.positions


	def _update_grid(self, positions: Dict[str, Tuple[float, float]]) -> None:
		"""Update spatial partitioning grid"""
		self.grid_cells.clear()
		for node_id, pos in positions.items():
			cell_x = int(pos[0] / self.cell_size)
			cell_y = int(pos[1] / self.cell_size)
			cell = (cell_x, cell_y)
			if cell not in self.grid_cells:
				self.grid_cells[cell] = []
			self.grid_cells[cell].append(node_id)

	def _get_nearby_nodes(self, pos: Tuple[float, float]) -> Set[str]:
		"""Get nodes from nearby grid cells"""
		cell_x = int(pos[0] / self.cell_size)
		cell_y = int(pos[1] / self.cell_size)
		nearby = set()
		for dx in (-1, 0, 1):
			for dy in (-1, 0, 1):
				cell = (cell_x + dx, cell_y + dy)
				if cell in self.grid_cells:
					nearby.update(self.grid_cells[cell])
		return nearby

	def apply_forces(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> bool:
		"""Apply forces using the Barnes-Hut optimization"""
		if not self.positions:
			return True

		new_positions = self.physics.calculate_forces(nodes, edges, self.positions, self.velocities)
		
		# Calculate total movement
		total_movement = 0.0
		for node_id, new_pos in new_positions.items():
			old_pos = self.positions[node_id]
			dx = new_pos.x - old_pos.x
			dy = new_pos.y - old_pos.y
			total_movement += math.sqrt(dx * dx + dy * dy)
			self.positions[node_id] = new_pos

		avg_movement = total_movement / len(nodes)
		self.layout_iterations += 1
		
		return avg_movement < self.params.convergence_threshold



	def _bundle_edges(self, edges: List[VisualEdge]) -> List[VisualEdge]:
		"""Bundle edges that share similar paths with optimized grouping"""
		bundles = {}
		bundled = []
		
		# Group edges by endpoint distance for more efficient bundling
		for edge in edges:
			src_pos = self.positions[edge.source]
			tgt_pos = self.positions[edge.target]
			dist = math.sqrt((tgt_pos.x - src_pos.x)**2 + (tgt_pos.y - src_pos.y)**2)
			angle = math.atan2(tgt_pos.y - src_pos.y, tgt_pos.x - src_pos.x)
			
			# Use coarser grouping
			key = (round(angle, 1), round(dist, -1))  # Round angle to 0.1, distance to nearest 10
			if key not in bundles:
				bundles[key] = []
			bundles[key].append(edge)
		
		# Create bundled edges with early exit for small groups
		for edges_group in bundles.values():
			if len(edges_group) <= 2:  # Don't bundle small groups
				bundled.extend(edges_group)
			else:
				bundled.append(create_bundled_edge(edges_group))
		
		return bundled



	def _project_positions(self, source_nodes: List[VisualNode], target_nodes: List[VisualNode]) -> None:
		"""Project positions from source nodes to target nodes."""
		# Create mapping from source to target nodes
		node_map = {}
		for node in target_nodes:
			if '_' in node.id:  # Handle super-nodes
				source_id = node.id.split('_')[1]  # Get original node ID
				node_map[source_id] = node.id
			else:
				node_map[node.id] = node.id
		
		# Project positions
		for source_node in source_nodes:
			if source_node.id in self.positions:
				source_pos = self.positions[source_node.id]
				target_id = node_map.get(source_node.id)
				if target_id:
					self.positions[target_id] = Point(x=source_pos.x, y=source_pos.y)
					self.velocities[target_id] = Point(x=0.0, y=0.0)

	def _scale_positions(self, width: float, height: float) -> None:
		"""Scale node positions to fit within the specified dimensions."""
		if not self.positions:
			return
			
		# Find current bounds in one pass
		positions = list(self.positions.values())
		min_x = min(pos.x for pos in positions)
		max_x = max(pos.x for pos in positions)
		min_y = min(pos.y for pos in positions)
		max_y = max(pos.y for pos in positions)
		
		# Calculate scaling factors
		width_scale = (width * 0.9) / (max_x - min_x) if max_x != min_x else 1
		height_scale = (height * 0.9) / (max_y - min_y) if max_y != min_y else 1
		scale = min(width_scale, height_scale)
		
		# Calculate center offset
		center_x = width / 2
		center_y = height / 2
		
		# Scale and center positions
		for node_id, pos in self.positions.items():
			scaled_x = (pos.x - min_x) * scale
			scaled_y = (pos.y - min_y) * scale
			pos.x = scaled_x + (width - (max_x - min_x) * scale) / 2
			pos.y = scaled_y + (height - (max_y - min_y) * scale) / 2
			
			# Update node data and pos attributes
			for node in self._nodes:  # Store nodes as instance variable
				if node.id == node_id:
					if not isinstance(node.data, dict):
						node.data = {}
					if not hasattr(node, 'pos'):
						node.pos = {}
					node.data['x'] = pos.x
					node.data['y'] = pos.y
					node.pos['x'] = pos.x
					node.pos['y'] = pos.y
					break


