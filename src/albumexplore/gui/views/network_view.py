"""Network visualization view."""
from typing import Dict, Any, Set, Optional, List, Tuple
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath
from PyQt6.QtCore import Qt, QPointF, QRectF
from .base_view import BaseView
from albumexplore.visualization.models import Point
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger

class NetworkView(BaseView):
    """Network visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.NETWORK
        self.setMouseTracking(True)
        
        # View state
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._dragging = False
        self._drag_start = None
        self._hovered_node = None
        self._selected_nodes: Set[str] = set()
        
        # Visual settings
        self._node_radius = 5.0
        self._hover_radius = 8.0
        self._edge_width = 1.0
        self._label_font_size = 10
        self._label_offset = 15
        self._hover_color = QColor("#ff6464")
        self._select_color = QColor("#64ff64")
        self._edge_color = QColor("#cccccc")
        self._node_color = QColor("#4287f5")
        
        # Performance optimization
        self._node_positions: Dict[str, QPointF] = {}
        self._node_bounds: Dict[str, QRectF] = {}
        self._visible_nodes: Set[str] = set()
        self._visible_edges: List[Tuple[str, str]] = []
        
        graphics_logger.debug("Network view initialized")
    
    def update_data(self, data: Dict[str, Any]):
        """Update visualization data."""
        super().update_data(data)
        
        # Update selection
        if 'selected_ids' in data:
            self._selected_nodes = set(data['selected_ids'])
        
        # Clear caches
        self._node_positions.clear()
        self._node_bounds.clear()
        self._visible_nodes.clear()
        self._visible_edges.clear()
        
        # Process nodes
        if 'nodes' in data:
            for node in data['nodes']:
                pos = QPointF(node['x'], node['y'])
                self._node_positions[node['id']] = pos
                
                # Calculate node bounds
                radius = self._node_radius
                if node['id'] in self._selected_nodes:
                    radius = self._hover_radius
                bounds = QRectF(
                    pos.x() - radius,
                    pos.y() - radius,
                    radius * 2,
                    radius * 2
                )
                self._node_bounds[node['id']] = bounds
        
        # Process edges
        if 'edges' in data:
            self._visible_edges = [(e['source'], e['target']) for e in data['edges']]
        
        self.update()
        graphics_logger.debug(f"Updated network view with {len(self._node_positions)} nodes")
    
    def paintEvent(self, event):
        """Paint the network visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Apply transformation
        painter.translate(self.width() / 2 + self._pan_x, self.height() / 2 + self._pan_y)
        painter.scale(self._zoom, self._zoom)
        
        # Draw edges
        pen = QPen(self._edge_color)
        pen.setWidthF(self._edge_width)
        painter.setPen(pen)
        
        for source, target in self._visible_edges:
            if source in self._node_positions and target in self._node_positions:
                source_pos = self._node_positions[source]
                target_pos = self._node_positions[target]
                painter.drawLine(source_pos, target_pos)
        
        # Draw nodes
        for node_id, pos in self._node_positions.items():
            if node_id in self._selected_nodes:
                color = self._select_color
                radius = self._hover_radius
            elif node_id == self._hovered_node:
                color = self._hover_color
                radius = self._hover_radius
            else:
                color = self._node_color
                radius = self._node_radius
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pos, radius, radius)
        
        # Draw labels for selected/hovered nodes
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = painter.font()
        font.setPointSize(self._label_font_size)
        painter.setFont(font)
        
        for node_id in self._selected_nodes | {self._hovered_node} - {None}:
            if node_id in self._node_positions:
                pos = self._node_positions[node_id]
                label = next((n['label'] for n in self._data['nodes'] 
                            if n['id'] == node_id), '')
                painter.drawText(
                    QPointF(pos.x() + self._label_offset,
                           pos.y() - self._label_offset),
                    label
                )
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()
            
            # Check for node selection
            node_id = self._find_node_at(event.pos())
            if node_id:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # Toggle selection
                    if node_id in self._selected_nodes:
                        self._selected_nodes.remove(node_id)
                    else:
                        self._selected_nodes.add(node_id)
                else:
                    # New selection
                    self._selected_nodes = {node_id}
                
                self.selection_changed.emit(self._selected_nodes)
                self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_start = None
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self._dragging and self._drag_start:
            # Pan view
            delta = event.pos() - self._drag_start
            self._pan_x += delta.x()
            self._pan_y += delta.y()
            self._drag_start = event.pos()
            self.update()
        else:
            # Update hover state
            node_id = self._find_node_at(event.pos())
            if node_id != self._hovered_node:
                self._hovered_node = node_id
                self.update()
    
    def wheelEvent(self, event):
        """Handle mouse wheel events."""
        # Zoom around mouse position
        old_zoom = self._zoom
        
        # Calculate zoom factor
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self._zoom = max(0.1, min(5.0, self._zoom * factor))
        
        # Adjust pan to keep mouse position fixed
        if old_zoom != self._zoom:
            mouse_pos = event.position()
            wx = (mouse_pos.x() - self.width() / 2 - self._pan_x) / old_zoom
            wy = (mouse_pos.y() - self.height() / 2 - self._pan_y) / old_zoom
            self._pan_x -= wx * (self._zoom - old_zoom)
            self._pan_y -= wy * (self._zoom - old_zoom)
            
            self.update()
    
    def _find_node_at(self, pos: QPointF) -> Optional[str]:
        """Find node at given screen position."""
        # Convert screen coordinates to graph coordinates
        x = (pos.x() - self.width() / 2 - self._pan_x) / self._zoom
        y = (pos.y() - self.height() / 2 - self._pan_y) / self._zoom
        
        # Check each node
        for node_id, node_pos in self._node_positions.items():
            dx = x - node_pos.x()
            dy = y - node_pos.y()
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Use larger radius for selected nodes
            radius = self._hover_radius if node_id in self._selected_nodes else self._node_radius
            if distance <= radius:
                return node_id
        
        return None