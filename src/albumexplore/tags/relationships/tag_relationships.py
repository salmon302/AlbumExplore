"""Tag relationship management system."""
import networkx as nx
from typing import Dict, List, Tuple, Optional, Set

class TagRelationships:
    """Manages relationships between tags."""

    def __init__(self):
        """Initialize the relationship manager."""
        self.graph = nx.Graph()
        self.hierarchies: Dict[str, str] = {}  # child -> parent
        self._initialize_relationships()
    
    def _initialize_relationships(self):
        """Initialize basic tag relationships and hierarchies."""
        # Base genre hierarchies
        base_hierarchies = {
            'melodic death metal': 'death metal',
            'technical death metal': 'death metal',
            'atmospheric black metal': 'black metal',
            'progressive metal': 'metal',
            'death metal': 'metal',
            'black metal': 'metal',
            'doom metal': 'metal',
            'folk metal': 'metal',
            'power metal': 'metal',
            'gothic metal': 'metal',
            'symphonic metal': 'metal',
            'thrash metal': 'metal',
            'progressive rock': 'rock',
            'psychedelic rock': 'rock',
            'post-rock': 'rock',
            'art rock': 'rock',
            'folk rock': 'rock',
            'space rock': 'rock'
        }
        
        # Add hierarchies
        for child, parent in base_hierarchies.items():
            self.add_hierarchy(child, parent)
        
        # Add common relationships with weights
        relationships = [
            ('atmospheric', 'black metal', 0.8),
            ('technical', 'death metal', 0.8),
            ('progressive', 'metal', 0.7),
            ('symphonic', 'metal', 0.7),
            ('experimental', 'metal', 0.6),
            ('avant-garde', 'experimental', 0.8),
            ('post-metal', 'metal', 0.7),
            ('post-rock', 'rock', 0.7),
            ('psychedelic', 'progressive', 0.6),
            ('jazz fusion', 'jazz', 0.8),
            ('prog fusion', 'progressive', 0.7)
        ]
        
        for tag1, tag2, weight in relationships:
            self.add_relationship(tag1, tag2, weight)

    def add_hierarchy(self, child: str, parent: str):
        """Add a hierarchical relationship between tags."""
        self.hierarchies[child] = parent
        self.graph.add_edge(child, parent, type='hierarchy', weight=1.0)

    def add_relationship(self, tag1: str, tag2: str, weight: float = 0.5):
        """Add a weighted relationship between tags."""
        self.graph.add_edge(tag1, tag2, type='related', weight=weight)

    def get_related_tags(self, tag: str, min_weight: float = 0.0) -> List[Tuple[str, float]]:
        """Get related tags with their relationship strengths."""
        if tag not in self.graph:
            return []
        
        related = []
        for neighbor in self.graph.neighbors(tag):
            weight = self.graph[tag][neighbor]['weight']
            if weight >= min_weight:
                related.append((neighbor, weight))
        
        return sorted(related, key=lambda x: x[1], reverse=True)

    def get_parent_tags(self, tag: str) -> List[str]:
        """Get all parent tags in hierarchy."""
        parents = []
        current = tag
        while current in self.hierarchies:
            parent = self.hierarchies[current]
            parents.append(parent)
            current = parent
        return parents

    def get_child_tags(self, tag: str) -> List[str]:
        """Get immediate child tags in hierarchy."""
        return [child for child, parent in self.hierarchies.items() if parent == tag]

    def calculate_similarity(self, tag1: str, tag2: str) -> float:
        """Calculate similarity between two tags."""
        if tag1 == tag2:
            return 1.0
            
        if not (self.graph.has_node(tag1) and self.graph.has_node(tag2)):
            return 0.0
            
        try:
            # Use shortest path length as a similarity metric
            path_length = nx.shortest_path_length(self.graph, tag1, tag2)
            return 1.0 / (1.0 + path_length)  # Convert distance to similarity
        except nx.NetworkXNoPath:
            return 0.0

    def get_all_tags(self) -> Set[str]:
        """Get all tags in the relationship graph."""
        return set(self.graph.nodes())

    def get_tag_category(self, tag: str) -> str:
        """Get the high-level category of a tag."""
        parents = self.get_parent_tags(tag)
        if parents:
            return parents[-1]  # Return the highest level parent
        return tag  # Return the tag itself if no parents

    def merge_tags(self, source: str, target: str):
        """Merge source tag into target tag."""
        if source == target:
            return
            
        # Transfer relationships
        for neighbor in list(self.graph.neighbors(source)):
            if neighbor != target:
                weight = self.graph[source][neighbor]['weight']
                rel_type = self.graph[source][neighbor]['type']
                self.graph.add_edge(target, neighbor, weight=weight, type=rel_type)
        
        # Update hierarchies
        if source in self.hierarchies:
            self.hierarchies[target] = self.hierarchies[source]
        for child, parent in list(self.hierarchies.items()):
            if parent == source:
                self.hierarchies[child] = target
        
        # Remove source tag
        self.graph.remove_node(source)
        if source in self.hierarchies:
            del self.hierarchies[source]