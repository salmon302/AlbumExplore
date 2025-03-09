"""Tag relationships management."""
from typing import Dict, List, Set, Optional, Tuple
import networkx as nx
from ..normalizer import TagNormalizer
from ..analysis import TagAnalyzer, TagSimilarity

class TagRelationships:
    """Manages relationships between tags including hierarchies and variants."""
    
    def __init__(self, normalizer: TagNormalizer, analyzer: TagAnalyzer, similarity: TagSimilarity):
        """Initialize with required components."""
        self.normalizer = normalizer
        self.analyzer = analyzer
        self.similarity = similarity
        self.relationship_graph = nx.DiGraph()
        self._build_relationship_graph()
        
    def _build_relationship_graph(self):
        """Build the initial relationship graph from tag data."""
        # Add nodes for all tags
        for tag in self.analyzer.tag_counts:
            self.relationship_graph.add_node(tag, 
                                          count=self.analyzer.get_tag_frequency(tag),
                                          category=self.normalizer.get_category(tag))
        
        # Add hierarchical relationships based on tag patterns
        patterns = self.analyzer.get_common_patterns()
        for prefix, bases in patterns.items():
            for base in bases:
                full_tag = f"{prefix} {base}"
                if full_tag in self.analyzer.tag_counts and base in self.analyzer.tag_counts:
                    self.relationship_graph.add_edge(full_tag, base, type='specialization')
                    
        # Add variant relationships from similarity analysis
        clusters = self.similarity.find_similar_tag_clusters(min_similarity=0.8)
        for cluster in clusters:
            # Find the most frequent tag in cluster as canonical form
            canonical = max(cluster, key=lambda t: self.analyzer.get_tag_frequency(t))
            for variant in cluster:
                if variant != canonical:
                    self.relationship_graph.add_edge(variant, canonical, type='variant')
                    
    def get_tag_variants(self, tag: str) -> List[str]:
        """Get all variants of a tag."""
        variants = []
        
        # Check outgoing variant edges
        if tag in self.relationship_graph:
            for _, target in self.relationship_graph.out_edges(tag):
                if self.relationship_graph[tag][target]['type'] == 'variant':
                    variants.append(target)
                    
        # Check incoming variant edges
        for source, _ in self.relationship_graph.in_edges(tag):
            if self.relationship_graph[source][tag]['type'] == 'variant':
                variants.append(source)
                
        return variants
        
    def get_broader_tags(self, tag: str) -> List[str]:
        """Get broader (parent) tags."""
        broader = []
        
        if tag in self.relationship_graph:
            for _, target in self.relationship_graph.out_edges(tag):
                if self.relationship_graph[tag][target]['type'] == 'specialization':
                    broader.append(target)
                    
        return broader
        
    def get_narrower_tags(self, tag: str) -> List[str]:
        """Get narrower (child) tags."""
        narrower = []
        
        for source, _ in self.relationship_graph.in_edges(tag):
            if self.relationship_graph[source][tag]['type'] == 'specialization':
                narrower.append(source)
                
        return narrower
        
    def get_related_tags(self, tag: str, min_similarity: float = 0.6) -> List[Tuple[str, float]]:
        """Get related tags based on co-occurrence and similarity."""
        related = []
        
        # Get variants
        variants = self.get_tag_variants(tag)
        for variant in variants:
            related.append((variant, 1.0))
            
        # Get hierarchically related tags
        broader = self.get_broader_tags(tag)
        narrower = self.get_narrower_tags(tag)
        
        for btag in broader:
            related.append((btag, 0.9))
        for ntag in narrower:
            related.append((ntag, 0.9))
            
        # Get similar tags
        similar = self.similarity.find_similar_tags(tag, threshold=min_similarity)
        for sim_tag, score in similar:
            if sim_tag not in variants and sim_tag not in broader and sim_tag not in narrower:
                related.append((sim_tag, score))
                
        return sorted(related, key=lambda x: x[1], reverse=True)
        
    def suggest_canonical_form(self, tag: str) -> Optional[str]:
        """Suggest canonical form for a tag."""
        # First check normalized form
        normalized = self.normalizer.normalize(tag)
        if normalized != tag:
            return normalized
            
        # Check for variants
        for _, target in self.relationship_graph.out_edges(tag):
            if self.relationship_graph[tag][target]['type'] == 'variant':
                # Return the most frequent variant
                variants = self.get_tag_variants(tag)
                if variants:
                    return max(variants, key=lambda t: self.analyzer.get_tag_frequency(t))
                    
        return None
        
    def get_tag_hierarchy(self, root_tag: Optional[str] = None) -> Dict:
        """Get hierarchical representation of tags."""
        hierarchy = {}
        
        if root_tag:
            # Build hierarchy from specific root
            hierarchy = self._build_hierarchy_from_node(root_tag)
        else:
            # Find all root nodes (no incoming specialization edges)
            roots = [node for node in self.relationship_graph.nodes()
                    if not any(self.relationship_graph[src][node]['type'] == 'specialization'
                             for src, _ in self.relationship_graph.in_edges(node))]
            
            # Build hierarchy from each root
            for root in roots:
                hierarchy[root] = self._build_hierarchy_from_node(root)
                
        return hierarchy
        
    def _build_hierarchy_from_node(self, node: str) -> Dict:
        """Recursively build hierarchy from a node."""
        hierarchy = {'variants': self.get_tag_variants(node)}
        
        # Add narrower tags recursively
        narrower = self.get_narrower_tags(node)
        if narrower:
            hierarchy['narrower'] = {}
            for tag in narrower:
                hierarchy['narrower'][tag] = self._build_hierarchy_from_node(tag)
                
        return hierarchy
        
    def merge_tags(self, source: str, target: str):
        """Merge source tag into target tag."""
        if source == target:
            return
            
        # Update analyzer counts
        source_count = self.analyzer.tag_counts[source]
        self.analyzer.tag_counts[target] = self.analyzer.tag_counts.get(target, 0) + source_count
        del self.analyzer.tag_counts[source]
        
        # Update relationship graph
        if source in self.relationship_graph:
            # Redirect edges to target
            for _, dest in list(self.relationship_graph.out_edges(source)):
                edge_data = self.relationship_graph[source][dest]
                if dest != target:  # Avoid self-loops
                    self.relationship_graph.add_edge(target, dest, **edge_data)
                    
            for src, _ in list(self.relationship_graph.in_edges(source)):
                edge_data = self.relationship_graph[src][source]
                if src != target:  # Avoid self-loops
                    self.relationship_graph.add_edge(src, target, **edge_data)
                    
            # Remove source node
            self.relationship_graph.remove_node(source)
            
        # Update normalizer
        self.normalizer.add_variant(source, target)
        
        # Clear caches
        self.similarity.clear_cache()