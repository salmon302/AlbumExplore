"""Level of Detail system for visualization optimization."""

from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from .models import VisualNode, VisualEdge
import math

@dataclass
class LODLevel:
	level: int
	node_threshold: int
	edge_threshold: int
	cluster_threshold: float
	visible_range: Tuple[float, float]
	edge_sampling_rate: float  # Add edge sampling rate

class LODSystem:
    """System for managing level of detail based on viewport zoom."""
    
    def __init__(self):
        self.zoom_level = 1.0
        self.lod_thresholds = [0.2, 0.5, 1.0, 2.0]
        self.current_lod = 0
        self.levels = [
            LODLevel(0, 50, 100, 0.1, (2.0, float('inf')), 1.0),     # Show all edges
            LODLevel(1, 75, 150, 0.2, (1.5, 2.0), 0.8),             # Show 80% edges
            LODLevel(2, 150, 300, 0.3, (1.0, 1.5), 0.5),            # Show 50% edges
            LODLevel(3, 300, 600, 0.4, (0.5, 1.0), 0.3),            # Show 30% edges
            LODLevel(4, 600, 1200, 0.5, (0.0, 0.5), 0.1)            # Show 10% edges
        ]
        self._edge_cache = {}  # Cache for edge visibility
    
    def update_zoom_level(self, zoom: float) -> int:
        """Update current zoom level and return the LOD level."""
        self.zoom_level = zoom
        self.current_lod = self.get_lod_level(zoom)
        return self.current_lod
    
    def get_lod_level(self, zoom: float) -> int:
        """Get LOD level for a given zoom level.
        
        Returns:
            int: LOD level. Higher numbers mean simpler rendering:
                 0: Full detail
                 1: Medium detail
                 2: Low detail
                 3: Minimal detail
        """
        if zoom <= self.lod_thresholds[0]:
            return 3  # Minimal detail
        elif zoom <= self.lod_thresholds[1]:
            return 2  # Low detail
        elif zoom <= self.lod_thresholds[2]:
            return 1  # Medium detail
        else:
            return 0  # Full detail
    
    def get_node_size_for_lod(self, node: VisualNode, base_size: float) -> float:
        """Get the appropriate node size for the current LOD level."""
        if not hasattr(node, '_lod_sizes'):
            node._lod_sizes = {
                0: base_size,
                1: base_size * 0.8,
                2: base_size * 0.6,
                3: base_size * 0.4
            }
        
        return node._lod_sizes.get(self.current_lod, base_size)
    
    def get_edge_thickness_for_lod(self, edge: VisualEdge, base_thickness: float) -> float:
        """Get the appropriate edge thickness for the current LOD level."""
        if self.current_lod == 0:
            return base_thickness
        elif self.current_lod == 1:
            return max(1.0, base_thickness * 0.8)
        elif self.current_lod == 2:
            return max(1.0, base_thickness * 0.6)
        else:
            return 1.0

    def get_level_for_scale(self, scale: float) -> LODLevel:
        """Get appropriate LOD level for current scale."""
        for level in self.levels:
            if level.visible_range[0] <= scale <= level.visible_range[1]:
                return level
        return self.levels[-1]  # Return lowest detail if no match

    def should_render_node(self, node: VisualNode, importance: float, level: LODLevel) -> bool:
        """Determine if a node should be rendered at current LOD level."""
        return importance >= level.cluster_threshold

    def should_render_edge(self, edge: VisualEdge, importance: float, level: LODLevel) -> bool:
        """Determine if an edge should be rendered with sampling."""
        cache_key = (edge.id, level.level)
        if cache_key not in self._edge_cache:
            # Deterministic sampling based on edge ID and importance
            sample_value = hash(str(edge.id)) % 100 / 100.0
            self._edge_cache[cache_key] = (
                sample_value <= level.edge_sampling_rate and 
                importance >= level.cluster_threshold
            )
        return self._edge_cache[cache_key]

class ClusterManager:
    """Manager for node clustering to improve performance."""
    
    def __init__(self, lod_system: LODSystem):
        self.lod_system = lod_system
        self.clusters: Dict[int, List[VisualNode]] = {}
        self.cluster_centers: Dict[int, Tuple[float, float]] = {}
        self.node_importance: Dict[str, float] = {}
        self.clusters = []
        self.cluster_threshold_distance = 50.0
        self.min_cluster_size = 3
        self.enabled = True
    
    def update_clusters(self, nodes: List[VisualNode], edges: List[VisualEdge], 
                       scale: float) -> Tuple[List[VisualNode], List[VisualEdge]]:
        """Update clusters with optimized edge filtering."""
        if not self.enabled or len(nodes) < self.min_cluster_size * 2:
            self.clusters = []
            return
        
        # Implement a simple distance-based clustering
        self.clusters = []
        processed_nodes = set()
        
        for node in nodes:
            if node.id in processed_nodes:
                continue
                
            cluster_nodes = self._find_cluster_nodes(node, nodes)
            if len(cluster_nodes) >= self.min_cluster_size:
                self.clusters.append({
                    'center': self._calculate_cluster_center(cluster_nodes),
                    'nodes': cluster_nodes,
                    'size': len(cluster_nodes)
                })
                processed_nodes.update(node_id for node_id in cluster_nodes)
        
        level = self.lod_system.get_level_for_scale(scale)
        
        # Use set for faster lookups
        visible_node_ids = set()
        
        # Filter nodes first
        visible_nodes = []
        for node in nodes:
            importance = self.node_importance.get(node.id) or self.calculate_node_importance(node, edges)
            self.node_importance[node.id] = importance
            if self.lod_system.should_render_node(node, importance, level):
                visible_nodes.append(node)
                visible_node_ids.add(node.id)
        
        # Filter edges with sampling
        visible_edges = []
        edge_count = 0
        max_edges = level.edge_threshold
        
        for edge in edges:
            if (edge.source in visible_node_ids and 
                edge.target in visible_node_ids):
                importance = min(self.node_importance[edge.source], 
                               self.node_importance[edge.target])
                if (edge_count < max_edges and 
                    self.lod_system.should_render_edge(edge, importance, level)):
                    visible_edges.append(edge)
                    edge_count += 1
        
        return visible_nodes, visible_edges

    def _find_cluster_nodes(self, seed_node: VisualNode, all_nodes: List[VisualNode]) -> Set[str]:
        """Find nodes that belong to the same cluster as the seed node."""
        cluster_nodes = {seed_node.id}
        queue = [seed_node]
        
        while queue:
            current = queue.pop(0)
            current_x = current.data.get('x', 0)
            current_y = current.data.get('y', 0)
            
            for node in all_nodes:
                if node.id in cluster_nodes:
                    continue
                    
                node_x = node.data.get('x', 0)
                node_y = node.data.get('y', 0)
                distance = ((node_x - current_x) ** 2 + (node_y - current_y) ** 2) ** 0.5
                
                if distance <= self.cluster_threshold_distance:
                    cluster_nodes.add(node.id)
                    queue.append(node)
        
        return cluster_nodes
    
    def _calculate_cluster_center(self, node_ids: Set[str]) -> Dict[str, float]:
        """Calculate the center position of a cluster."""
        sum_x = 0.0
        sum_y = 0.0
        
        for node_id in node_ids:
            # This may need to be adjusted based on how nodes are stored
            # For now, assuming node data can be looked up directly
            node = self._get_node_by_id(node_id)
            if node:
                sum_x += node.data.get('x', 0)
                sum_y += node.data.get('y', 0)
        
        count = max(1, len(node_ids))
        return {
            'x': sum_x / count,
            'y': sum_y / count
        }
    
    def _get_node_by_id(self, node_id: str) -> Optional[VisualNode]:
        """Get node by ID - this would need to be implemented based on your data structure."""
        # This is a placeholder - replace with actual node lookup
        return None
    
    def get_visible_clusters(self, view_bounds: Dict[str, float]) -> List[Dict]:
        """Get clusters that are visible within the view bounds."""
        visible_clusters = []
        
        for cluster in self.clusters:
            center = cluster['center']
            if (view_bounds['x'] <= center['x'] <= view_bounds['x'] + view_bounds['width'] and
                view_bounds['y'] <= center['y'] <= view_bounds['y'] + view_bounds['height']):
                visible_clusters.append(cluster)
        
        return visible_clusters

    def calculate_node_importance(self, node: VisualNode, edges: List[VisualEdge]) -> float:
        """Calculate node importance based on connections and metadata."""
        # Count edges connected to this node
        edge_count = sum(1 for edge in edges if edge.source == node.id or edge.target == node.id)
        
        # Base importance on edge count and node metadata
        importance = math.log(edge_count + 1) * 0.5
        
        # Add weight for node attributes (can be customized)
        if hasattr(node, 'weight'):
            importance += node.weight * 0.3
            
        return min(1.0, importance)