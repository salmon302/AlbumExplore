from typing import List, Dict, Tuple
import math
import random
from ..models import VisualNode, VisualEdge, Point

def circular_layout(nodes: List[VisualNode], width: float, height: float) -> Dict[str, Point]:
	"""Arrange nodes in a circular layout."""
	positions = {}
	if not nodes:
		return positions
		
	radius = min(width, height) * 0.35
	center_x = width / 2
	center_y = height / 2
	angle_step = 2 * math.pi / len(nodes)
	
	for i, node in enumerate(nodes):
		angle = i * angle_step
		x = center_x + radius * math.cos(angle)
		y = center_y + radius * math.sin(angle)
		positions[node.id] = Point(x=x, y=y)
	
	return positions

def hierarchical_layout(nodes: List[VisualNode], edges: List[VisualEdge], 
					   width: float, height: float) -> Dict[str, Point]:
	"""Arrange nodes in a hierarchical layout."""
	positions = {}
	if not nodes:
		return positions
	
	# Build adjacency list
	adj_list = {node.id: [] for node in nodes}
	for edge in edges:
		adj_list[edge.source].append(edge.target)
	
	# Find root nodes (nodes with no incoming edges)
	incoming_edges = {edge.target for edge in edges}
	root_nodes = [node.id for node in nodes if node.id not in incoming_edges]
	
	if not root_nodes:
		root_nodes = [nodes[0].id]  # Use first node if no clear roots
	
	# Assign levels through BFS
	levels = {}
	visited = set()
	queue = [(node_id, 0) for node_id in root_nodes]
	
	while queue:
		node_id, level = queue.pop(0)
		if node_id in visited:
			continue
			
		visited.add(node_id)
		if level not in levels:
			levels[level] = []
		levels[level].append(node_id)
		
		for neighbor in adj_list[node_id]:
			if neighbor not in visited:
				queue.append((neighbor, level + 1))
	
	# Position nodes by level
	max_level = max(levels.keys())
	level_height = height / (max_level + 1)
	
	for level, level_nodes in levels.items():
		y = level_height * level + level_height / 2
		level_width = width / (len(level_nodes) + 1)
		
		for i, node_id in enumerate(level_nodes, 1):
			x = level_width * i
			positions[node_id] = Point(x=x, y=y)
	
	return positions

def radial_layout(nodes: List[VisualNode], edges: List[VisualEdge],
				 width: float, height: float) -> Dict[str, Point]:
	"""Arrange nodes in a radial layout."""
	positions = {}
	if not nodes:
		return positions
	
	# Find central node (highest degree)
	node_degrees = {node.id: 0 for node in nodes}
	for edge in edges:
		node_degrees[edge.source] += 1
		node_degrees[edge.target] += 1
	
	center_node = max(node_degrees.items(), key=lambda x: x[1])[0]
	
	# Build distance map from center
	distances = {center_node: 0}
	queue = [(center_node, 0)]
	visited = {center_node}
	
	while queue:
		node_id, dist = queue.pop(0)
		for edge in edges:
			if edge.source == node_id and edge.target not in visited:
				distances[edge.target] = dist + 1
				queue.append((edge.target, dist + 1))
				visited.add(edge.target)
			elif edge.target == node_id and edge.source not in visited:
				distances[edge.source] = dist + 1
				queue.append((edge.source, dist + 1))
				visited.add(edge.source)
	
	# Position nodes by distance
	max_distance = max(distances.values())
	center_x = width / 2
	center_y = height / 2
	radius_step = min(width, height) * 0.35 / (max_distance + 1)
	
	# Position center node
	positions[center_node] = Point(x=center_x, y=center_y)
	
	# Group nodes by distance
	distance_groups = {}
	for node_id, distance in distances.items():
		if distance not in distance_groups:
			distance_groups[distance] = []
		distance_groups[distance].append(node_id)
	
	# Position nodes in concentric circles
	for distance, group_nodes in distance_groups.items():
		if distance == 0:
			continue
			
		radius = distance * radius_step
		angle_step = 2 * math.pi / len(group_nodes)
		
		for i, node_id in enumerate(group_nodes):
			angle = i * angle_step
			x = center_x + radius * math.cos(angle)
			y = center_y + radius * math.sin(angle)
			positions[node_id] = Point(x=x, y=y)
	
	return positions