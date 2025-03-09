from typing import List, Dict, Any, Tuple, Set, Protocol, Optional
import math
import random
import time
from collections import defaultdict
from .models import VisualNode, VisualEdge, Point
from .physics.force_params import ForceParams
from .physics_system import PhysicsSystem
from albumexplore.gui.gui_logging import graphics_logger


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
    """Force-directed layout implementation."""
    
    def __init__(self, params: Optional[ForceParams] = None):
        self.params = params or ForceParams()
        self._velocities: Dict[str, Point] = {}
        self._forces: Dict[str, Point] = {}
        self.iteration = 0
        self.total_kinetic_energy = float('inf')
    
    def initialize(self, nodes: List[VisualNode], width: float, height: float):
        """Initialize layout with random positions."""
        margin = min(width, height) * 0.1
        
        for node in nodes:
            if not node.pos or ('x' not in node.pos or 'y' not in node.pos):
                # Random position within bounds
                node.pos = {
                    'x': margin + random.random() * (width - 2 * margin),
                    'y': margin + random.random() * (height - 2 * margin)
                }
            
            # Initialize velocity
            self._velocities[node.id] = Point(0.0, 0.0)
            self._forces[node.id] = Point(0.0, 0.0)
    
    def _calculate_forces(self, nodes: List[VisualNode], edges: List[VisualEdge]):
        """Calculate forces for current iteration."""
        # Reset forces
        for node_id in self._forces:
            self._forces[node_id] = Point(0.0, 0.0)
        
        # Calculate repulsion forces between all pairs of nodes
        for i, node1 in enumerate(nodes):
            pos1 = Point(node1.pos['x'], node1.pos['y'])
            
            # Node-node repulsion
            for node2 in nodes[i+1:]:
                pos2 = Point(node2.pos['x'], node2.pos['y'])
                dx = pos1.x - pos2.x
                dy = pos1.y - pos2.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance < 0.01:  # Prevent division by zero
                    distance = 0.01
                    dx = random.uniform(-0.1, 0.1)
                    dy = random.uniform(-0.1, 0.1)
                
                # Repulsion force
                force = self.params.repulsion / (distance * distance)
                fx = force * dx / distance
                fy = force * dy / distance
                
                # Apply forces to both nodes
                self._forces[node1.id].x += fx
                self._forces[node1.id].y += fy
                self._forces[node2.id].x -= fx
                self._forces[node2.id].y -= fy
        
        # Calculate spring forces for edges
        for edge in edges:
            # Get connected nodes
            source = next(n for n in nodes if n.id == edge.source)
            target = next(n for n in nodes if n.id == edge.target)
            
            # Calculate spring force
            dx = source.pos['x'] - target.pos['x']
            dy = source.pos['y'] - target.pos['y']
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < 0.01:
                continue
            
            # Force is proportional to difference from ideal length
            force = self.params.spring_coefficient * (distance - self.params.spring_length)
            fx = force * dx / distance
            fy = force * dy / distance
            
            # Weight force by edge weight
            fx *= edge.weight
            fy *= edge.weight
            
            # Apply forces
            self._forces[source.id].x -= fx
            self._forces[source.id].y -= fy
            self._forces[target.id].x += fx
            self._forces[target.id].y += fy
    
    def _update_positions(self, nodes: List[VisualNode], width: float, height: float):
        """Update node positions based on forces."""
        self.total_kinetic_energy = 0.0
        current_temperature = self.params.temperature * (self.params.cooling_rate ** self.iteration)
        
        for node in nodes:
            # Get current force
            force = self._forces[node.id]
            velocity = self._velocities[node.id]
            
            # Update velocity (with damping)
            velocity.x = (velocity.x + force.x * self.params.time_step) * self.params.damping
            velocity.y = (velocity.y + force.y * self.params.time_step) * self.params.damping
            
            # Apply temperature scaling
            velocity.x *= current_temperature
            velocity.y *= current_temperature
            
            # Update position
            node.pos['x'] += velocity.x * self.params.time_step
            node.pos['y'] += velocity.y * self.params.time_step
            
            # Constrain to bounds
            margin = 10.0
            node.pos['x'] = max(margin, min(width - margin, node.pos['x']))
            node.pos['y'] = max(margin, min(height - margin, node.pos['y']))
            
            # Update kinetic energy
            speed_squared = velocity.x * velocity.x + velocity.y * velocity.y
            self.total_kinetic_energy += speed_squared
    
    def step(self, nodes: List[VisualNode], edges: List[VisualEdge], 
             width: float, height: float) -> bool:
        """Perform one iteration of layout."""
        if not nodes:
            return False
            
        # Calculate forces
        self._calculate_forces(nodes, edges)
        
        # Update positions
        self._update_positions(nodes, width, height)
        
        # Update iteration count
        self.iteration += 1
        
        # Check if we've converged
        return (self.total_kinetic_energy > self.params.min_movement and 
                self.iteration < self.params.max_iterations)
    
    def adjust_parameters(self, node_count: int, edge_count: int):
        """Adjust layout parameters based on graph size."""
        # Scale forces based on graph density
        density = edge_count / (node_count * (node_count - 1)) if node_count > 1 else 0
        
        # Adjust repulsion based on number of nodes
        self.params.repulsion = 200.0 + 100.0 * math.log(node_count + 1)
        
        # Adjust spring length based on density
        self.params.spring_length = 50.0 + 200.0 * (1.0 - density)
        
        # Adjust other parameters for stability
        if node_count > 100:
            self.params.damping = 0.9
            self.params.time_step = 0.2
        elif node_count > 50:
            self.params.damping = 0.85
            self.params.time_step = 0.3
    
    def reset(self):
        """Reset layout state."""
        self._velocities.clear()
        self._forces.clear()
        self.iteration = 0
        self.total_kinetic_energy = float('inf')

"""Layout engine for visualization system."""
from typing import List, Dict, Protocol
from .models import VisualNode, VisualEdge, Point
from .physics.force_params import ForceParams

class LayoutEngine(Protocol):
    """Interface for graph layout algorithms."""
    
    def compute_layout(self, nodes: List[VisualNode], edges: List[VisualEdge], 
                      width: float, height: float) -> Dict[str, Point]:
        """Compute layout positions for nodes."""
        ...
    
    def update_layout(self, nodes: List[VisualNode], edges: List[VisualEdge],
                     fixed_nodes: Dict[str, Point]) -> bool:
        """Update existing layout."""
        ...

class ForceLayout:
    """Force-directed layout implementation."""
    
    def __init__(self, params: ForceParams = None):
        from .physics_system import PhysicsSystem
        self.physics = PhysicsSystem(params)
    
    def compute_layout(self, nodes: List[VisualNode], edges: List[VisualEdge],
                      width: float, height: float) -> Dict[str, Point]:
        """Compute initial force-directed layout."""
        # Reset physics state
        self.physics.reset()
        
        # Initialize node positions
        self.physics.initialize(nodes, width, height)
        
        # Run physics simulation until stable
        while self.physics.step(nodes, edges, width, height):
            pass
        
        # Return final positions
        return self.physics.state.positions
    
    def update_layout(self, nodes: List[VisualNode], edges: List[VisualEdge],
                     fixed_nodes: Dict[str, Point]) -> bool:
        """Update existing layout with fixed nodes."""
        # Fix specified nodes
        for node_id, pos in fixed_nodes.items():
            self.physics.fix_node(node_id)
            if node_id in self.physics.state.positions:
                self.physics.state.positions[node_id] = pos
        
        # Run single physics step
        return self.physics.step(nodes, edges, 
                               max(n.pos['x'] for n in nodes if n.visible),
                               max(n.pos['y'] for n in nodes if n.visible))

class RadialLayout:
    """Radial layout implementation."""
    
    def compute_layout(self, nodes: List[VisualNode], edges: List[VisualEdge],
                      width: float, height: float) -> Dict[str, Point]:
        """Compute radial layout."""
        import math
        
        positions = {}
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) * 0.4
        
        # Sort nodes by some property (e.g., degree or weight)
        sorted_nodes = sorted(nodes, key=lambda n: len([e for e in edges 
            if e.source == n.id or e.target == n.id]), reverse=True)
        
        # Position nodes in a circle
        for i, node in enumerate(sorted_nodes):
            angle = (2 * math.pi * i) / len(nodes)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions[node.id] = Point(x, y)
            
            # Update node position
            node.pos['x'] = x
            node.pos['y'] = y
        
        return positions
    
    def update_layout(self, nodes: List[VisualNode], edges: List[VisualEdge],
                     fixed_nodes: Dict[str, Point]) -> bool:
        """Update radial layout (no dynamic updates)."""
        return False

def create_layout_engine(layout_type: str = "force", params: ForceParams = None) -> LayoutEngine:
    """Create layout engine based on type."""
    engines = {
        "force": lambda: ForceLayout(params),
        "radial": RadialLayout
    }
    
    engine_class = engines.get(layout_type)
    if not engine_class:
        raise ValueError(f"Unsupported layout type: {layout_type}")
        
    return engine_class()


