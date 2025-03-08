"""Clustering engine for visualization nodes."""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import math
from .models import VisualNode, VisualEdge


class ClusterNode:
    """Represents a clustered set of nodes."""
    
    def __init__(self, node_ids: Set[str]):
        self.node_ids = node_ids
        self.size = len(node_ids)
        self.position = {'x': 0, 'y': 0}
        self.radius = 0
        self.color = "#4a90e2"
        self.label = f"Cluster ({self.size} nodes)"


class ClusterEngine:
    """Engine for clustering visualization nodes."""
    
    def __init__(self):
        self.clusters: List[ClusterNode] = []
        self.distance_threshold = 100.0
        self.min_cluster_size = 3
        self.max_clusters = 10
        self.node_lookup: Dict[str, VisualNode] = {}
        self.edge_weights: Dict[Tuple[str, str], float] = {}
    
    def update_clusters(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> List[ClusterNode]:
        """Update clusters based on node positions and connectivity."""
        if not nodes:
            return []
            
        # Reset state
        self.clusters = []
        self.node_lookup = {node.id: node for node in nodes}
        self.edge_weights = {}
        
        # Extract edge weights for connectivity-based clustering
        for edge in edges:
            edge_key = tuple(sorted([edge.source, edge.target]))
            self.edge_weights[edge_key] = edge.weight
        
        # Create clusters based on both proximity and connectivity
        self._create_clusters(nodes)
        
        # Cap the number of clusters
        if len(self.clusters) > self.max_clusters:
            # Keep clusters with most nodes
            self.clusters.sort(key=lambda c: c.size, reverse=True)
            self.clusters = self.clusters[:self.max_clusters]
        
        # Calculate cluster properties
        for cluster in self.clusters:
            self._calculate_cluster_properties(cluster)
        
        return self.clusters
    
    def _create_clusters(self, nodes: List[VisualNode]) -> None:
        """Create clusters using a hybrid approach."""
        visited = set()
        
        # Start with connectivity-based clustering
        adjacency_list = self._build_adjacency_list(nodes)
        
        # Process nodes by connectivity
        for node in sorted(nodes, key=lambda n: len(adjacency_list.get(n.id, [])), reverse=True):
            if node.id in visited:
                continue
            
            # Perform a breadth-first search
            cluster_nodes = self._grow_cluster(node.id, adjacency_list, visited)
            
            # Only create clusters above minimum size
            if len(cluster_nodes) >= self.min_cluster_size:
                self.clusters.append(ClusterNode(cluster_nodes))
    
    def _build_adjacency_list(self, nodes: List[VisualNode]) -> Dict[str, List[str]]:
        """Build an adjacency list from edges."""
        adjacency_list = defaultdict(list)
        
        # Add edges from edge_weights
        for (source, target), weight in self.edge_weights.items():
            adjacency_list[source].append((target, weight))
            adjacency_list[target].append((source, weight))
        
        # Add position-based connections
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes[i+1:], i+1):
                distance = self._distance(node1, node2)
                if distance <= self.distance_threshold:
                    # Inverse distance as weight (closer = stronger connection)
                    weight = max(0.1, 1.0 - (distance / self.distance_threshold))
                    adjacency_list[node1.id].append((node2.id, weight))
                    adjacency_list[node2.id].append((node1.id, weight))
        
        return adjacency_list
    
    def _grow_cluster(self, start_id: str, adjacency_list: Dict[str, List[str]], 
                     visited: Set[str]) -> Set[str]:
        """Grow a cluster starting from a seed node."""
        cluster = {start_id}
        queue = [start_id]
        visited.add(start_id)
        
        while queue:
            current = queue.pop(0)
            
            # Get neighbors sorted by connection strength
            neighbors = sorted(
                adjacency_list.get(current, []),
                key=lambda x: x[1],
                reverse=True
            )
            
            for neighbor_id, weight in neighbors:
                if weight < 0.3:  # Minimum connection strength threshold
                    continue
                    
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    cluster.add(neighbor_id)
                    queue.append(neighbor_id)
        
        return cluster
    
    def _calculate_cluster_properties(self, cluster: ClusterNode) -> None:
        """Calculate cluster position, radius, and other properties."""
        # Calculate weighted center of the cluster
        sum_x = 0.0
        sum_y = 0.0
        sum_weights = 0.0
        
        # Gather all nodes in the cluster
        nodes = []
        for node_id in cluster.node_ids:
            node = self.node_lookup.get(node_id)
            if not node:
                continue
                
            nodes.append(node)
            
            # Weight by node size if available
            weight = getattr(node, 'size', 1.0)
            x = node.data.get('x', 0.0)
            y = node.data.get('y', 0.0)
            
            sum_x += x * weight
            sum_y += y * weight
            sum_weights += weight
        
        if sum_weights > 0:
            cluster.position['x'] = sum_x / sum_weights
            cluster.position['y'] = sum_y / sum_weights
        
        # Calculate cluster radius as distance to furthest node
        max_distance = 0.0
        for node in nodes:
            x = node.data.get('x', 0.0)
            y = node.data.get('y', 0.0)
            dx = x - cluster.position['x']
            dy = y - cluster.position['y']
            distance = math.sqrt(dx*dx + dy*dy) + getattr(node, 'size', 10.0) / 2.0
            max_distance = max(max_distance, distance)
        
        # Set radius with padding
        cluster.radius = max_distance * 1.2
    
    def _distance(self, node1: VisualNode, node2: VisualNode) -> float:
        """Calculate Euclidean distance between nodes."""
        x1 = node1.data.get('x', 0.0)
        y1 = node1.data.get('y', 0.0)
        x2 = node2.data.get('x', 0.0)
        y2 = node2.data.get('y', 0.0)
        
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def get_cluster_boundaries(self) -> List[Dict[str, float]]:
        """Get cluster boundary information for rendering."""
        boundaries = []
        for cluster in self.clusters:
            boundaries.append({
                'x': cluster.position['x'],
                'y': cluster.position['y'],
                'radius': cluster.radius,
                'size': cluster.size
            })
        return boundaries
    
    def get_cluster_for_node(self, node_id: str) -> Optional[ClusterNode]:
        """Find which cluster a node belongs to."""
        for cluster in self.clusters:
            if node_id in cluster.node_ids:
                return cluster
        return None


