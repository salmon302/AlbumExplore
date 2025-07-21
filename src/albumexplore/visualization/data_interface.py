"""Data interface for visualization system."""
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from ..database.queries import (
    get_albums_with_tags, get_related_albums, get_album_tags,
    get_albums_with_atomic_tags, get_atomic_tag_breakdown,
    filter_albums_by_atomic_components, get_atomic_tag_statistics,
    search_albums_by_atomic_tags
)
from ..database.models import Album, Tag, AtomicTag
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
    # Atomic tag configuration
    use_atomic_tags: bool = False
    show_atomic_breakdown: bool = True
    atomic_filter_mode: str = "any"  # "any" or "all"
    include_composite_in_atomic_search: bool = True

class DataInterface:
    """Interface between data sources and visualization."""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._node_cache: Dict[str, VisualNode] = {}
        self._edge_cache: Dict[Tuple[str, str], VisualEdge] = {}
        self._tag_cache: Dict[str, Set[str]] = {}
        self._atomic_tag_cache: Dict[str, Set[str]] = {}
        self._atomic_breakdown_cache: Dict[str, Dict] = {}
        self._config = DataConfig()
    
    def configure(self, **kwargs):
        """Update configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                # Clear relevant caches when configuration changes
                if key in ['use_atomic_tags', 'show_atomic_breakdown']:
                    self._clear_caches()
    
    def _clear_caches(self):
        """Clear all internal caches."""
        self._node_cache.clear()
        self._edge_cache.clear()
        self._tag_cache.clear()
        self._atomic_tag_cache.clear()
        self._atomic_breakdown_cache.clear()
    
    def get_visible_data(self) -> Tuple[List[VisualNode], List[VisualEdge]]:
        """Get currently visible nodes and edges."""
        if not self.session:
            return [], []
        
        # Choose data source based on atomic tag configuration
        if self._config.use_atomic_tags:
            albums = get_albums_with_atomic_tags(self.session)
        else:
            albums = get_albums_with_tags(self.session)
        
        nodes = []
        edges = []
        
        # Create nodes for each album
        for album in albums:
            node = self._create_or_get_node(album)
            if node:
                nodes.append(node)
        
        return nodes, edges
    
    def get_atomic_tag_data(self) -> Dict[str, Any]:
        """Get atomic tag statistics and breakdown data."""
        if not self.session:
            return {}
        
        return get_atomic_tag_statistics(self.session)
    
    def filter_by_atomic_tags(self, atomic_tag_names: List[str]) -> Tuple[List[VisualNode], List[VisualEdge]]:
        """Filter albums by atomic tag components."""
        if not self.session or not atomic_tag_names:
            return [], []
        
        match_all = self._config.atomic_filter_mode == "all"
        albums = filter_albums_by_atomic_components(
            self.session, atomic_tag_names, match_all
        )
        
        nodes = []
        for album in albums:
            node = self._create_or_get_node(album)
            if node:
                nodes.append(node)
        
        return nodes, []
    
    def search_by_atomic_tags(self, atomic_tag_names: List[str]) -> List[VisualNode]:
        """Search albums using atomic tag names."""
        if not self.session or not atomic_tag_names:
            return []
        
        albums = search_albums_by_atomic_tags(
            self.session, 
            atomic_tag_names,
            self._config.include_composite_in_atomic_search
        )
        
        nodes = []
        for album in albums:
            node = self._create_or_get_node(album)
            if node:
                nodes.append(node)
        
        return nodes
    
    def get_tag_atomic_breakdown(self, tag_name: str) -> Optional[Dict]:
        """Get atomic breakdown for a composite tag."""
        if not self.session:
            return None
        
        if tag_name in self._atomic_breakdown_cache:
            return self._atomic_breakdown_cache[tag_name]
        
        breakdown = get_atomic_tag_breakdown(self.session, tag_name)
        if breakdown:
            self._atomic_breakdown_cache[tag_name] = breakdown
        
        return breakdown
    
    def _create_or_get_node(self, album: Album) -> Optional[VisualNode]:
        """Create or get cached node."""
        if album.id in self._node_cache:
            return self._node_cache[album.id]
        
        # Get tags based on configuration
        tags = set()
        atomic_tags = set()
        
        if self._config.include_tags:
            if album.id not in self._tag_cache:
                self._tag_cache[album.id] = {t.name for t in album.tags}
            tags = self._tag_cache[album.id]
            
            # Get atomic tags if enabled
            if self._config.use_atomic_tags and hasattr(album, 'atomic_tags'):
                if album.id not in self._atomic_tag_cache:
                    self._atomic_tag_cache[album.id] = {at.name for at in album.atomic_tags}
                atomic_tags = self._atomic_tag_cache[album.id]
        
        # Create node
        # DEBUG: Log the original album.release_year
        from albumexplore.gui.gui_logging import graphics_logger # Temporary import for logging
        graphics_logger.debug(f"DataInterface: Creating/getting node for album '{album.title}'. DB album.release_year: {album.release_year} (type: {type(album.release_year)})")

        # Ensure year is an integer
        year = album.release_year
        if not isinstance(year, int) and album.release_date:
            try:
                year = album.release_date.year
            except AttributeError:
                year = None # Or some default

        # Prepare data for node
        node_data = {
            'artist': album.pa_artist_name_on_album,
            'title': album.title,
            'year': year,
            'genre': album.genre,
            'country': album.country,
            'raw_tags': album.raw_tags or album.genre, # Use raw_tags and fallback to genre
            'type': 'row',  # Indicate this is a table row
            'tags': list(tags),
            'atomic_tags': list(atomic_tags) if self._config.use_atomic_tags else []
        }

        node = VisualNode(
            id=str(album.id),
            label=f"{album.pa_artist_name_on_album} - {album.title}",
            size=10.0 + len(tags) + len(atomic_tags),
            color="#4287f5",  # Default blue
            data=node_data
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
        self._atomic_tag_cache.clear()
        self._atomic_breakdown_cache.clear()
        if self.session:
            self.session.close()
            self.session = None
    
    # Convenience methods for TagExplorerView compatibility
    def get_atomic_tags(self) -> List[Dict[str, Any]]:
        """Get list of all atomic tags for UI display."""
        if not self.session:
            return []
        
        try:
            atomic_tags = self.session.query(AtomicTag).all()
            return [
                {
                    'name': tag.name,
                    'category': tag.category or 'unknown',
                    'description': tag.description or '',
                    'rule_source': tag.rule_source or 'unknown'
                }
                for tag in atomic_tags
            ]
        except Exception:
            return []
    
    def get_atomic_tag_breakdown(self, tag_name: str) -> Optional[Dict]:
        """Get atomic breakdown for a composite tag (alias for get_tag_atomic_breakdown)."""
        return self.get_tag_atomic_breakdown(tag_name)
    
    def filter_albums_by_atomic_components(self, filter_criteria: List[str]) -> List[Dict]:
        """Filter albums by atomic tag components."""
        if not self.session or not filter_criteria:
            return []
        
        try:
            albums = filter_albums_by_atomic_components(self.session, filter_criteria)
            return [
                {
                    'id': album.id,
                    'artist': album.artist,
                    'album': album.album,
                    'year': album.year,
                    'tags': [tag.name for tag in album.tags] if album.tags else []
                }
                for album in albums
            ]
        except Exception:
            return []
    
    def get_albums_with_atomic_tags(self) -> List[Dict]:
        """Get all albums that have atomic tag associations."""
        if not self.session:
            return []
        
        try:
            albums = get_albums_with_atomic_tags(self.session)
            return [
                {
                    'id': album.id,
                    'artist': album.artist,
                    'album': album.album,
                    'year': album.year,
                    'tags': [tag.name for tag in album.tags] if album.tags else [],
                    'atomic_tags': [tag.name for tag in album.atomic_tags] if hasattr(album, 'atomic_tags') else []
                }
                for album in albums
            ]
        except Exception:
            return []

