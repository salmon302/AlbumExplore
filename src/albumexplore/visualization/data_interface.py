"""Data interface for visualization system."""
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from ..database.queries import get_albums_with_tags, get_related_albums, get_album_tags
from ..database.models import Album, Tag
from .models import VisualNode, VisualEdge

@dataclass
class DataConfig:
    """Configuration for data interface."""
    max_nodes: int = 1000
    max_edges: int = 2000
    min_edge_weight: float = 0.1
    include_tags: bool = True
    filter_by_year: Optional[int] = None
    filter_by_genre: Optional[str] = None
    tag_threshold: int = 2

class DataInterface:
    """Interface between data sources and visualization."""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._node_cache: Dict[str, VisualNode] = {}
        self._edge_cache: Dict[Tuple[str, str], VisualEdge] = {}
        self._tag_cache: Dict[str, Set[str]] = {}
        self._config = DataConfig()
    
    def configure(self, **kwargs):
        """Update configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def get_visible_data(self) -> Tuple[List[VisualNode], List[VisualEdge]]:
        """Get currently visible nodes and edges."""
        if not self.session:
            return [], []
            
        # Get all albums with their tags
        albums = get_albums_with_tags(self.session)
        nodes = []
        edges = []
        
        # Create nodes for each album
        for album in albums:
            node = self._create_or_get_node(album)
            if node:
                nodes.append(node)
        
        return nodes, edges
    
    def _create_or_get_node(self, album: Album) -> Optional[VisualNode]:
        """Create or get cached node."""
        if album.id in self._node_cache:
            return self._node_cache[album.id]
        
        # Get tags if needed
        tags = set()
        if self._config.include_tags:
            if album.id not in self._tag_cache:
                self._tag_cache[album.id] = {t.name for t in album.tags}
            tags = self._tag_cache[album.id]
        
        # Create node
        node = VisualNode(
            id=str(album.id),
            label=f"{album.artist} - {album.title}",
            size=10.0 + len(tags),
            color="#4287f5",  # Default blue
            data={
                'artist': album.artist,
                'title': album.title,
                'year': album.release_year,
                'genre': album.genre,
                'country': album.country,
                'tags': list(tags),
                'type': 'row'  # Indicate this is a table row
            }
        )
        
        self._node_cache[album.id] = node
        return node
    
    def _create_or_get_edge(self, source_id: str, target_id: str, weight: float) -> Optional[VisualEdge]:
        """Create or get cached edge."""
        key = (source_id, target_id) if source_id < target_id else (target_id, source_id)
        
        if key in self._edge_cache:
            return self._edge_cache[key]
        
        edge = VisualEdge(
            source=str(source_id),
            target=str(target_id),
            weight=weight,
            thickness=1.0 + weight * 2.0
        )
        
        self._edge_cache[key] = edge
        return edge
    
    def cleanup(self):
        """Clean up resources."""
        self._node_cache.clear()
        self._edge_cache.clear()
        self._tag_cache.clear()
        if self.session:
            self.session.close()
            self.session = None

