"""Renderer implementations."""
import logging
from typing import Dict, Any, List
from .models import VisualNode, VisualEdge, Viewport
from .state import ViewType
from .chord_renderer import ChordRenderer
from .arc_renderer import ArcRenderer
from .base_renderer import RenderConfig, RendererBase

logger = logging.getLogger(__name__)

class NetworkRenderer(RendererBase):
    """Network view renderer."""
    
    def __init__(self, config: RenderConfig):
        self.config = config
        logger.debug("Initialized network renderer")
    
    def render(self, nodes: List[VisualNode], edges: List[VisualEdge],
               viewport: Viewport) -> Dict[str, Any]:
        """Render network visualization data."""
        logger.debug("Rendering network view with %d nodes and %d edges", 
                    len(nodes), len(edges))
        
        # Process nodes
        node_data = []
        visible_nodes = 0
        for node in nodes:
            if not node.visible:
                continue
            visible_nodes += 1
            
            # Calculate visual properties
            size = self.config.node_size_base
            if node.size > 0:
                size += node.size * self.config.node_size_scale
            
            if hasattr(viewport, 'selected_ids') and node.id in viewport.selected_ids:
                size *= self.config.highlight_scale
                color = self.config.selection_color
            else:
                color = node.color or self.config.default_node_color
            
            # Add node data
            node_data.append({
                'id': node.id,
                'label': node.label,
                'x': node.pos['x'],
                'y': node.pos['y'],
                'size': size,
                'color': color,
                'data': node.data,
                'selected': node.id in getattr(viewport, 'selected_ids', set())
            })
        
        # Process edges
        edge_data = []
        visible_edges = 0
        for edge in edges:
            if not edge.visible:
                continue
            visible_edges += 1
            
            # Calculate edge thickness with bundling consideration
            thickness = edge.thickness or self.config.edge_thickness_base
            if edge.weight > 0:
                thickness += edge.weight * self.config.edge_thickness_scale
            
            # Handle selected edges
            color = edge.color or self.config.default_edge_color
            if (hasattr(viewport, 'selected_ids') and 
                (edge.source in viewport.selected_ids or 
                 edge.target in viewport.selected_ids)):
                color = self.config.highlight_color
            
            # Add edge data
            edge_data.append({
                'source': edge.source,
                'target': edge.target,
                'weight': edge.weight,
                'thickness': thickness,
                'color': color,
                'data': edge.data,
                'bundled': edge.data.get('bundled', False)
            })
        
        logger.debug("Rendered %d visible nodes and %d visible edges", 
                    visible_nodes, visible_edges)
        
        return {
            'nodes': node_data,
            'edges': edge_data,
            'viewport': {
                'x': viewport.x,
                'y': viewport.y,
                'width': viewport.width,
                'height': viewport.height,
                'zoom': viewport.zoom,
                'selected_ids': getattr(viewport, 'selected_ids', set())
            }
        }
    
    def update_config(self, config: RenderConfig):
        """Update renderer configuration."""
        self.config = config
        logger.debug("Updated network renderer config")

class TableRenderer(RendererBase):
    """Table view renderer."""
    
    def __init__(self, config: RenderConfig):
        self.config = config
        logger.debug("Initialized table renderer")
    
    def render(self, nodes: List[VisualNode], edges: List[VisualEdge],
               viewport: Viewport) -> Dict[str, Any]:
        """Render table visualization data."""
        logger.debug("Rendering table view with %d nodes", len(nodes))
        
        # DEBUG: Print year values from nodes to help troubleshoot
        logger.debug("YEAR VALUES IN NODES:")
        for i, node in enumerate(nodes[:10]):  # Show first 10 nodes only
            if node.visible:
                year_val = node.data.get('year')
                logger.debug(f"Node {i}: Year = {year_val} (Type: {type(year_val)})")
        
        # Convert nodes to table rows
        rows = []
        visible_rows = 0
        for node in nodes:
            if not node.visible:
                continue
            
            # Skip invalid nodes (like placeholder 'nan' test data)
            if (not node.data.get('artist') or 
                str(node.data.get('artist')).lower() == 'nan' or
                not node.data.get('title') or 
                str(node.data.get('title')).lower() == 'nan'):
                continue
                
            visible_rows += 1
            
            # Create row from node data
            # Get album title from 'title' field or fallback to 'album'
            title = node.data.get('title', '')
            if not title and 'album' in node.data:
                title = node.data.get('album', '')
                
            # Make sure year is properly converted to string
            year = node.data.get('year', '')
            if year is not None:
                year = str(year)
            else:
                year = ''
            
            # Debug the year value
            logger.debug(f"Processing row: {title}, Year={year}, Original value: {node.data.get('year')}")
            
            row = {
                'id': node.id,
                'artist': node.data.get('artist', ''),
                'album': title,  # Use the processed title
                'title': title,  # Include both keys for compatibility
                'year': year,    # Ensure year is a string
                'country': node.data.get('country', ''),
                'tags': node.data.get('tags', []),
                'selected': node.id in getattr(viewport, 'selected_ids', set())
            }
            rows.append(row)
        
        logger.debug("Rendered %d visible rows", visible_rows)
        
        return {
            'type': 'table',
            'rows': rows,
            'selected_ids': getattr(viewport, 'selected_ids', set())
        }
    
    def update_config(self, config: RenderConfig):
        """Update renderer configuration."""
        self.config = config
        logger.debug("Updated table renderer config")

def create_renderer(view_type: ViewType, config: RenderConfig = None) -> RendererBase:
    """Create appropriate renderer for view type."""
    if config is None:
        config = RenderConfig()
        
    renderers = {
        ViewType.NETWORK: NetworkRenderer,
        ViewType.TABLE: TableRenderer,
        ViewType.CHORD: ChordRenderer,
        ViewType.ARC: ArcRenderer,
        ViewType.TAG_EXPLORER: TableRenderer,  # Temporarily use TableRenderer for TAG_EXPLORER
        ViewType.TAG_GRAPH: NetworkRenderer    # Temporarily use NetworkRenderer for TAG_GRAPH
    }
    
    renderer_class = renderers.get(view_type)
    if not renderer_class:
        raise ValueError(f"Unsupported view type: {view_type}")
    
    logger.info("Created %s renderer", view_type.name)
    return renderer_class(config)