"""Node clustering engine for network visualization."""
from typing import Dict, Any, List
from dataclasses import dataclass
from .models import VisualNode
import math

@dataclass
class ClusterNode:
    """Represents a cluster of nodes."""
    id: str
    center_x: float
    center_y: float
    nodes: List[VisualNode]
    size: float = 1.0

class ClusterEngine:
    """Handles node clustering based on spatial proximity."""
    
    def __init__(self):
        self.clusters: Dict[str, ClusterNode] = {}
        self.min_distance = 50.0
        self.max_cluster_size = 20
        
    def update_clusters(self, nodes: List[VisualNode], scale: float) -> Dict[str, ClusterNode]:
        """Update clusters based on current viewport scale."""
        if scale > 0.5:  # Don't cluster when zoomed in
            return {}
            
        self.clusters.clear()
        return self.clusters


