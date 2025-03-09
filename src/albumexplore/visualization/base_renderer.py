"""Base renderer interface and common types."""
import logging
from typing import Dict, Any, List, Protocol
from dataclasses import dataclass
from .models import VisualNode, VisualEdge, Viewport

logger = logging.getLogger(__name__)

@dataclass
class RenderConfig:
    """Configuration for renderers."""
    node_size_base: float = 10.0
    node_size_scale: float = 2.0
    edge_thickness_base: float = 1.0
    edge_thickness_scale: float = 0.5
    highlight_scale: float = 1.5
    label_font_size: int = 10
    default_node_color: str = "#4287f5"
    default_edge_color: str = "#cccccc"
    highlight_color: str = "#ff6464"
    selection_color: str = "#64ff64"

class RendererBase(Protocol):
    """Base interface for all renderers."""
    
    def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
               viewport: Viewport) -> Dict[str, Any]:
        """Render visualization data."""
        ...
    
    def update_config(self, config: RenderConfig):
        """Update renderer configuration."""
        ...