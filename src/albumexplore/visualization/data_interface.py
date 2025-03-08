from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from albumexplore.gui.gui_logging import gui_logger as logger  # Import gui_logger as logger
from ..database import models
from .models import VisualNode, VisualEdge
from functools import lru_cache
import re

class DataInterface:
    """Interface for accessing and transforming data for visualizations."""
    
    def __init__(self, db: Session, cache_size: int = 1000):
        logger.debug("DataInterface initialized")
        self.db = db
        self._setup_caches(cache_size)
        self._visible_region = None
        self._loaded_chunks = {}
        self._chunk_size = 500
        self._tag_normalizer = TagNormalizer()

    def _setup_caches(self, cache_size: int):
        """Configure LRU caches for frequently accessed data."""
        self.get_albums = lru_cache(maxsize=cache_size)(self._get_albums_impl)
        self.get_tags = lru_cache(maxsize=cache_size)(self._get_tags_impl)
        self.get_tag_relationships = lru_cache(maxsize=cache_size)(self._get_tag_relationships_impl)

    def set_visible_region(self, bounds: Tuple[float, float, float, float]):
        """Update visible region for dynamic loading."""
        self._visible_region = bounds
        self._update_visible_chunks()

    def _update_visible_chunks(self):
        """Load data chunks for visible region."""
        if not self._visible_region:
            return

        min_x, max_x, min_y, max_y = self._visible_region
        chunk_x = int(min_x / self._chunk_size)
        chunk_y = int(min_y / self._chunk_size)
        chunks_w = int((max_x - min_x) / self._chunk_size) + 2
        chunks_h = int((max_y - min_y) / self._chunk_size) + 2

        new_chunks = set()
        for x in range(chunk_x, chunk_x + chunks_w):
            for y in range(chunk_y, chunk_y + chunks_h):
                chunk_key = (x, y)
                new_chunks.add(chunk_key)
                if chunk_key not in self._loaded_chunks:
                    self._load_chunk(chunk_key)

        # Unload distant chunks
        to_unload = set(self._loaded_chunks.keys()) - new_chunks
        for chunk_key in to_unload:
            del self._loaded_chunks[chunk_key]

    def _load_chunk(self, chunk_key: Tuple[int, int]):
        """Load data for a specific spatial chunk."""
        x, y = chunk_key
        x_start = x * self._chunk_size
        y_start = y * self._chunk_size
        
        # Load nodes in chunk region
        nodes = self.db.query(models.Album).filter(
            models.Album.x.between(x_start, x_start + self._chunk_size),
            models.Album.y.between(y_start, y_start + self._chunk_size)
        ).options(joinedload(models.Album.tags)).all()
        
        # Load edges connected to nodes in chunk
        node_ids = [n.id for n in nodes]
        edges = self._get_chunk_edges(node_ids)
        
        self._loaded_chunks[chunk_key] = {
            'nodes': nodes,
            'edges': edges,
            'last_access': func.now()
        }

    def _get_chunk_edges(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Get edges connected to nodes in chunk."""
        if not node_ids:
            return []

        # Get direct connections
        connections = self.get_album_connections(node_ids)
        
        # Get tag-based connections with strength
        tag_connections = self.db.query(
            models.album_tags.c.album_id,
            models.album_tags.c.tag_id,
            models.TagRelation.strength
        ).join(
            models.TagRelation,
            models.album_tags.c.tag_id == models.TagRelation.source_tag_id
        ).filter(
            models.album_tags.c.album_id.in_(node_ids)
        ).all()

        # Combine connections
        all_connections = connections.copy()
        for conn in tag_connections:
            all_connections.append({
                'source': conn.album_id,
                'target': conn.tag_id,
                'weight': conn.strength,
                'type': 'tag'
            })

        return all_connections

    def get_visible_data(self) -> Tuple[List[VisualNode], List[VisualEdge]]:
        """Get all data currently visible in the viewport."""
        logger.debug("Getting visible data...")
        try:
            # For table view and initial loading, get all data
            albums = self.db.query(models.Album).options(
                joinedload(models.Album.tags)
            ).all()
            
            logger.debug(f"Retrieved {len(albums)} albums from database")
            
            # Create nodes with proper data initialization
            nodes = []
            for album in albums:
                # Extract tags and genre safely
                album_tags = [tag.name for tag in album.tags] if album.tags else []
                genre = next((tag.name for tag in album.tags if hasattr(tag, 'category') and tag.category == "genre"), "")
                
                # Create node with complete data structure
                node = VisualNode(
                    id=str(album.id),
                    label=album.title,
                    size=10,  # Default size
                    color="#4287f5",  # Default blue
                    data={
                        "type": "row",  # Required for table view
                        "artist": album.artist,
                        "title": album.title,
                        "year": album.release_year if album.release_year else "",
                        "tags": album_tags,
                        "genre": genre,
                        # Include additional metadata for filtering
                        "release_date": album.release_date.isoformat() if album.release_date else "",
                        "vocal_style": album.vocal_style if album.vocal_style else "",
                        "country": album.country if album.country else "",
                        # Add x,y coordinates for non-table views
                        "x": 0,
                        "y": 0
                    }
                )
                nodes.append(node)
            
            logger.debug(f"Created {len(nodes)} visual nodes")
            
            # For initial view (table), no edges needed
            edges = []
            
            return nodes, edges

        except Exception as e:
            logger.error(f"Error getting visible data: {str(e)}", exc_info=True)
            raise

    def _convert_to_visual_nodes(self, albums: List[models.Album]) -> List[VisualNode]:
        """Convert album models to visual nodes."""
        return [
            VisualNode(
                id=album.id,
                label=album.title,
                size=len(album.tags) * 2,
                color=self._get_node_color(album)
            ) for album in albums
        ]

    def _convert_to_visual_edges(self, connections: List[Dict[str, Any]]) -> List[VisualEdge]:
        """Convert connection dicts to visual edges."""
        return [
            VisualEdge(
                source=conn['source'],
                target=conn['target'],
                weight=conn.get('weight', 1.0)
            ) for conn in connections
        ]

    def _get_node_color(self, album: models.Album) -> str:
        """Calculate node color based on album attributes."""
        # Implement color calculation based on album attributes
        return "#4287f5"  # Default blue

    def _get_albums_impl(self, page: int = 0, filters: Optional[Dict[str, Any]] = None) -> Tuple[List[models.Album], int]:
        """Get all albums without pagination."""
        logger.debug(f"Getting all albums, filters={filters}")
        try:
            query = self.db.query(models.Album).options(
                joinedload(models.Album.tags)
            )
            
            if filters:
                if 'year_range' in filters:
                    year_range = filters['year_range']
                    start_year = year_range[0] if isinstance(year_range, tuple) else year_range['start']
                    end_year = year_range[1] if isinstance(year_range, tuple) else year_range['end']
                    query = query.filter(models.Album.release_year.between(start_year, end_year))
                
                if 'tags' in filters:
                    query = query.join(models.album_tags).join(models.Tag)
                    query = query.filter(models.Tag.id.in_(filters['tags']))
                
                if 'vocal_style' in filters:
                    query = query.filter(models.Album.vocal_style == filters['vocal_style'])

            # Get total count
            total = query.count()
            # Get all albums without pagination
            albums = query.all()
            logger.debug(f"Retrieved {len(albums)} albums out of {total} total")
            return albums, total
        except Exception as e:
            logger.error(f"Error getting albums: {str(e)}")
            raise
    
    def _get_tags_impl(self, category: Optional[str] = None) -> List[models.Tag]:
        """Get tags with optimized loading."""
        query = self.db.query(models.Tag).options(
            joinedload(models.Tag.parent_tags),
            joinedload(models.Tag.child_tags)
        )
        if category:
            query = query.filter(models.Tag.category == category)
        return query.all()
    
    def _get_tag_relationships_impl(self, min_strength: float = 0.0) -> List[models.TagRelation]:
        """Get tag relationships with bulk loading."""
        logger.debug(f"Getting tag relationships (min_strength={min_strength})")
        try:
            return self.db.query(models.TagRelation).filter(
                models.TagRelation.strength >= min_strength
            ).all()
        except Exception as e:
            logger.error(f"Error getting tag relationships: {str(e)}")
            raise
    
    def get_album_connections(self, album_ids: List[str]) -> List[Dict[str, Any]]:
        """Get connections between albums with optimized bulk loading."""
        logger.debug(f"Getting album connections: {album_ids}")
        try:
            if not album_ids:
                return []
            
            # Bulk load all required data in a single query
            albums = self.db.query(models.Album).filter(
                models.Album.id.in_(album_ids)
            ).options(
                joinedload(models.Album.tags)
            ).all()
            
            # Process connections in memory
            connections = []
            album_tags = {
                album.id: set(t.name for t in album.tags)
                for album in albums
            }
            
            for i, album1 in enumerate(albums):
                for album2 in albums[i+1:]:
                    shared_tags = album_tags[album1.id] & album_tags[album2.id]
                    if shared_tags:
                        connections.append({
                            'source': album1.id,
                            'target': album2.id,
                            'shared_tags': list(shared_tags),
                            'weight': len(shared_tags),
                            'thickness': 2.0
                        })
            
            return connections
        except Exception as e:
            logger.error(f"Error getting album connections: {str(e)}")
            raise

    def clear_caches(self):
        """Clear all LRU caches."""
        self.get_albums.cache_clear()
        self.get_tags.cache_clear()
        self.get_tag_relationships.cache_clear()
        self._loaded_chunks.clear()

    def normalize_tag(self, tag: str) -> str:
        """Normalize a tag to its canonical form."""
        return self._tag_normalizer.normalize(tag)

import json
import os
import re
from typing import Dict, Any

class TagNormalizer:
    """Handles tag normalization and variant consolidation."""
    
    def __init__(self):
        self._load_config()
        self._variant_cache = {}
        
    def _load_config(self):
        """Load normalization rules from config file."""
        config_path = os.path.join(os.path.dirname(__file__), '../config/tag_rules.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            self._substitutions = config.get('substitutions', {})
            self._prefix_standardization = config.get('prefix_standardization', {})
            self._category_mapping = config.get('category_mapping', {})
        except Exception as e:
            logger.error(f"Error loading tag rules: {e}")
            # Fall back to default rules
            self._substitutions = {}
            self._prefix_standardization = {}
            self._category_mapping = {}
        
    def normalize(self, tag: str) -> str:
        """Convert a tag to its normalized form."""
        if not tag:
            return tag
            
        # Convert to lowercase and strip whitespace
        tag = tag.lower().strip()
        
        # Check cache first
        if tag in self._variant_cache:
            return self._variant_cache[tag]
            
        # Apply basic substitutions
        normalized = tag
        for pattern, replacement in self._substitutions.items():
            if re.search(pattern, normalized):
                # Extract the base genre if present
                base = re.search(r'(?:metal|rock|hardcore|punk|prog|fusion)$', normalized)
                if base:
                    normalized = replacement.format(base.group(0))
                    break
        
        # Standardize prefixes
        for full, short in self._prefix_standardization.items():
            if normalized.startswith(full):
                normalized = normalized.replace(full, short, 1)
        
        # Cache the result
        self._variant_cache[tag] = normalized
        return normalized
        
    def get_category(self, tag: str) -> str:
        """Get the category for a tag based on the config mappings."""
        normalized = self.normalize(tag)
        
        for category, tags in self._category_mapping.items():
            if normalized in tags:
                return category
                
        # Try to infer category from tag name
        if any(word in normalized for word in ['metal', 'metalcore', 'core']):
            return 'metal'
        if any(word in normalized for word in ['rock', 'prog-', 'psychedelic']):
            return 'rock'
        if 'jazz' in normalized or 'fusion' in normalized:
            return 'fusion'
        if any(word in normalized for word in ['experimental', 'avant', 'noise']):
            return 'experimental'
            
        return 'other'
        
    def add_variant(self, variant: str, canonical: str):
        """Register a new variant mapping."""
        self._variant_cache[variant.lower().strip()] = canonical.lower().strip()
    
    def clear_cache(self):
        """Clear the variant cache."""
        self._variant_cache.clear()
        
    def reload_config(self):
        """Reload the configuration file."""
        self._load_config()
        self.clear_cache()

