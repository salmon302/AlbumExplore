from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath
from typing import Optional, Dict, Any
import math

from .base_view import BaseView
from ..state import ViewType, ViewState
from ..renderer import create_renderer
from albumexplore.gui.gui_logging import graphics_logger

class NetworkView(BaseView):
    """Network visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_state = ViewState(ViewType.NETWORK)
        self.renderer = create_renderer(ViewType.NETWORK)
        
        # Configure widget background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(palette)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # View state
        self.viewport_scale = 1.0
        self.viewport_x = 0
        self.viewport_y = 0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Double buffering
        self._buffer = None
        self._buffer_dirty = True

    def paintEvent(self, event):
        """Paint the network visualization."""
        # Update viewport state
        self.view_state.viewport_width = self.width()
        self.view_state.viewport_height = self.height()
        self.view_state.zoom_level = self.viewport_scale
        self.view_state.position = {"x": self.viewport_x, "y": self.viewport_y}
        
        # Get rendered data from renderer
        render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
        
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Fill background
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
            
            # Apply viewport transform
            painter.translate(self.width() / 2 + self.viewport_x,
                            self.height() / 2 + self.viewport_y)
            painter.scale(self.viewport_scale, self.viewport_scale)
            
            # Draw edges
            for edge in render_data.get("edges", []):
                painter.setPen(QPen(QColor(edge["color"]), edge["thickness"]))
                painter.drawLine(
                    edge["source_x"], edge["source_y"],
                    edge["target_x"], edge["target_y"]
                )
            
            # Draw nodes
            for node in render_data.get("nodes", []):
                color = QColor(node["color"])
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                
                size = node["size"]
                x = node["x"]
                y = node["y"]
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
                
                # Draw labels if zoomed in enough
                if self.viewport_scale > 0.5 and node.get("label"):
                    painter.setPen(QPen(Qt.GlobalColor.black))
                    text_rect = QRectF(x + size/2 + 5, y - 10, 200, 20)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft, node["label"])
                    
        finally:
            painter.end()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging and selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_x = event.position().x()
            self.drag_start_y = event.position().y()
            
            # Transform click position to scene coordinates
            scene_x = (event.position().x() - self.width()/2 - self.viewport_x) / self.viewport_scale
            scene_y = (event.position().y() - self.height()/2 - self.viewport_y) / self.viewport_scale
            
            # Check for node selection
            hit_node = None
            for node in self.nodes:
                dx = node.data.get('x', 0) - scene_x
                dy = node.data.get('y', 0) - scene_y
                if math.sqrt(dx*dx + dy*dy) < node.size/2:
                    hit_node = node
                    break
            
            if hit_node:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if hit_node.id in self.selected_ids:
                        self.selected_ids.remove(hit_node.id)
                    else:
                        self.selected_ids.add(hit_node.id)
                else:
                    self.selected_ids = {hit_node.id}
                self.selectionChanged.emit(self.selected_ids)
                self.update()
            else:
                self.is_dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging."""
        if self.is_dragging:
            dx = event.position().x() - self.drag_start_x
            dy = event.position().y() - self.drag_start_y
            
            self.viewport_x += dx
            self.viewport_y += dy
            
            self.drag_start_x = event.position().x()
            self.drag_start_y = event.position().y()
            
            self._buffer_dirty = True
            self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
            
        # Get mouse position in scene coordinates
        mouse_x = event.position().x()
        mouse_y = event.position().y()
        
        # Calculate zoom center in scene coordinates
        center_x = (mouse_x - self.width()/2 - self.viewport_x) / self.viewport_scale
        center_y = (mouse_y - self.height()/2 - self.viewport_y) / self.viewport_scale
        
        # Apply zoom
        old_scale = self.viewport_scale
        self.viewport_scale *= factor
        self.viewport_scale = max(0.1, min(10.0, self.viewport_scale))
        
        # Adjust viewport to keep mouse position fixed
        scale_change = self.viewport_scale - old_scale
        self.viewport_x -= center_x * scale_change
        self.viewport_y -= center_y * scale_change
        
        self._buffer_dirty = True
        self.update()








