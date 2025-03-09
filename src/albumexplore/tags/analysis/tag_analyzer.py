"""Tag analysis component."""
import networkx as nx
from collections import Counter, defaultdict
from typing import Dict, List, Set, Optional, Tuple
import pandas as pd

class TagAnalyzer:
    """Analyzes tag relationships and patterns."""
    
    def __init__(self, data: pd.DataFrame):
        """Initialize with album data containing tags.
        
        Args:
            data: DataFrame with 'tags' column containing lists of tags
        """
        self.data = data
        self.tag_counts = Counter()
        self.co_occurrences = defaultdict(lambda: defaultdict(int))
        self.relationship_graph = nx.DiGraph()
        self._analyze_data()
        
    def _analyze_data(self):
        """Perform initial data analysis."""
        # Calculate tag frequencies
        for tags in self.data['tags']:
            if isinstance(tags, list):
                # Update tag counts
                self.tag_counts.update(tags)
                
                # Calculate co-occurrences
                for i, tag1 in enumerate(tags):
                    for tag2 in tags[i+1:]:
                        self.co_occurrences[tag1][tag2] += 1
                        self.co_occurrences[tag2][tag1] += 1
                        
                # Build relationship graph
                for tag1 in tags:
                    # Initialize or update node count
                    if not self.relationship_graph.has_node(tag1):
                        self.relationship_graph.add_node(tag1, count=1, weight=0)
                    else:
                        if 'count' not in self.relationship_graph.nodes[tag1]:
                            self.relationship_graph.nodes[tag1]['count'] = 1
                        else:
                            self.relationship_graph.nodes[tag1]['count'] += 1
                            
                    # Add co-occurrence edges
                    for tag2 in tags:
                        if tag1 != tag2:
                            if not self.relationship_graph.has_edge(tag1, tag2):
                                self.relationship_graph.add_edge(tag1, tag2, weight=1)
                            else:
                                self.relationship_graph[tag1][tag2]['weight'] += 1
                                
    def get_tag_frequency(self, tag: str) -> int:
        """Get frequency count for a tag."""
        return self.tag_counts[tag]
        
    def get_co_occurrences(self, tag: str) -> Dict[str, int]:
        """Get co-occurrence counts for a tag."""
        return dict(self.co_occurrences[tag])
        
    def get_top_co_occurrences(self, tag: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequent co-occurring tags."""
        co_occurs = self.get_co_occurrences(tag)
        return sorted(co_occurs.items(), key=lambda x: x[1], reverse=True)[:limit]
        
    def get_common_patterns(self) -> Dict[str, Set[str]]:
        """Get common tag patterns like prefixes/suffixes."""
        patterns = defaultdict(set)
        
        for tag in self.tag_counts:
            parts = tag.split()
            if len(parts) > 1:
                # Get prefix patterns
                prefix = parts[0]
                if len(prefix) >= 3:  # Minimum prefix length
                    base = ' '.join(parts[1:])
                    patterns[prefix].add(base)
                    
                # Get suffix patterns
                suffix = parts[-1]
                if len(suffix) >= 3:  # Minimum suffix length
                    base = ' '.join(parts[:-1])
                    patterns[suffix].add(base)
                    
        # Filter out patterns that only occur once
        return {k: v for k, v in patterns.items() if len(v) > 1}
        
    def find_similar_tags(self, tag: str, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """Find tags similar to the given tag."""
        if tag not in self.relationship_graph:
            return []
            
        similar = []
        for other_tag in self.relationship_graph.nodes():
            if other_tag != tag:
                # Calculate similarity based on co-occurrences
                co_occur_weight = (self.co_occurrences[tag][other_tag] /
                                 max(self.tag_counts[tag], self.tag_counts[other_tag]))
                                 
                # Calculate similarity based on graph structure
                try:
                    path_length = nx.shortest_path_length(self.relationship_graph, tag, other_tag)
                    path_weight = 1.0 / (path_length + 1)
                except nx.NetworkXNoPath:
                    path_weight = 0.0
                    
                # Combine scores
                score = (co_occur_weight + path_weight) / 2
                
                if score >= threshold:
                    similar.append((other_tag, score))
                    
        return sorted(similar, key=lambda x: x[1], reverse=True)
        
    def get_tag_clusters(self, min_similarity: float = 0.3) -> List[Set[str]]:
        """Find clusters of similar tags."""
        # Create similarity graph
        sim_graph = nx.Graph()
        
        # Add edges between similar tags
        for tag in self.tag_counts:
            similar = self.find_similar_tags(tag, min_similarity)
            for other_tag, score in similar:
                sim_graph.add_edge(tag, other_tag, weight=score)
                
        # Find connected components (clusters)
        return [set(c) for c in nx.connected_components(sim_graph)]
        
    def get_hierarchical_relationships(self) -> Dict[str, List[str]]:
        """Get hierarchical relationships between tags."""
        hierarchy = {}
        
        for tag in self.tag_counts:
            parts = tag.split()
            if len(parts) > 1:
                # Check if last part exists as standalone tag
                parent = parts[-1]
                if parent in self.tag_counts:
                    if parent not in hierarchy:
                        hierarchy[parent] = []
                    hierarchy[parent].append(tag)
                    
        return hierarchy

    def calculate_relationships(self) -> Dict[Tuple[str, str], float]:
        """Calculate weighted relationships between tags."""
        relationships = {}
        total_albums = len(self.data)
        
        for tag1 in self.tag_counts:
            for tag2 in self.co_occurrences[tag1]:
                if tag1 < tag2:  # Only process each pair once
                    # Calculate normalized weight
                    co_occur_count = self.co_occurrences[tag1][tag2]
                    weight = co_occur_count / min(self.tag_counts[tag1], self.tag_counts[tag2])
                    
                    # Update relationship graph
                    if not self.relationship_graph.has_edge(tag1, tag2):
                        self.relationship_graph.add_edge(tag1, tag2, weight=weight)
                    else:
                        self.relationship_graph[tag1][tag2]['weight'] = weight
                    
                    relationships[(tag1, tag2)] = weight
        
        return relationships
