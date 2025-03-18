from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QPixmap, QMouseEvent
from typing import Dict, List, Set, Optional, Tuple
import math
import time

from albumexplore.gui.gui_logging import (
    gui_logger, graphics_logger, performance_logger,
    log_graphics_event, log_performance_metric, log_interaction
)
from albumexplore.gui.graphics_debug import init_graphics_debugging

from ..models import VisualNode, VisualEdge
from ..state import ViewType, ViewState
from ..spatial_grid import SpatialGrid
from .base_view import BaseView
from ..lod_system import LODSystem, ClusterManager
from ..cluster_engine import ClusterEngine, ClusterNode
from ..performance_optimizer import PerformanceOptimizer, PerformanceMetrics
from ..renderer import create_renderer

class DrawWidget(QWidget):
    """Widget used for drawing the network visualization with optimized rendering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # For proper background handling
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAutoFillBackground(True)
        self.parent_view = parent

        # Set white background
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(palette)

    def paintEvent(self, event):
        """Draw the current network state from parent's buffer."""
        if not self.parent_view or not hasattr(self.parent_view, '_current_buffer'):
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
            painter.end()
            return

        self.parent_view._frame_start = time.time()

        try:
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            if self.parent_view._current_buffer:
                painter.drawPixmap(0, 0, self.parent_view._current_buffer)

            painter.end()

        finally:
            frame_time = (time.time() - self.parent_view._frame_start) * 1000
            metrics = {
                'frame_time': frame_time,
                'viewport_scale': self.parent_view.viewport_scale,
                'visible_node_count': len(self.parent_view.visible_nodes),
                'visible_edge_count': len(self.parent_view.visible_edges),
                'memory_usage': (self.parent_view._current_buffer.size().width() *
                                self.parent_view._current_buffer.size().height() * 4
                                if self.parent_view._current_buffer else 0)
            }
            self.parent_view.performance_metrics.update(metrics)

class EnhancedNetworkView(BaseView):
    """Enhanced network visualization with LOD and clustering support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_name = "EnhancedNetworkView"
        self.view_state = ViewState(ViewType.NETWORK)
        self.renderer = create_renderer(ViewType.NETWORK)

        # Layout with high-quality draw surface
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Draw widget for rendering optimization
        self.draw_widget = DrawWidget(self)
        self.layout.addWidget(self.draw_widget)

        # Drawing-related properties
        self._next_buffer = None
        self._current_buffer = None
        self._buffer_dirty = True
        self._frame_start = 0

        # Viewport parameters
        self.viewport_scale = 1.0
        self.viewport_x = 0
        self.viewport_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

        # Node/edge sets
        self.nodes = []
        self.edges = []
        self.selected_ids = set()
        self.visible_nodes = []
        self.visible_edges = []

        # Optimize rendering with spatial indexing
        self.enable_spatial_index = True
        self.spatial_cell_size = 50
        self.spatial_grid = None

        # LOD (Level of Detail) support
        self.enable_lod = True
        self.lod_system = LODSystem()

        # Clustering support
        self.enable_clustering = False
        self.cluster_manager = ClusterManager()
        self.cluster_engine = ClusterEngine()

        # Performance tracking
        self.performance_optimizer = PerformanceOptimizer()
        self.performance_metrics = PerformanceMetrics()

        # Graphics debugging
        self.graphics_debug = init_graphics_debugging(self)

        # Initialize buffer update timer
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_buffer)

    def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
        """Update visualization data."""
        super().update_data(nodes, edges)

        # Initialize spatial grid
        if self.enable_spatial_index:
            self._init_spatial_grid()

        # Mark buffer as dirty
        self._buffer_dirty = True
        self.update()

    def _init_spatial_grid(self) -> None:
        """Initialize spatial grid for efficient node lookup."""
        if not self.nodes:
            return

        min_x = min(node.data.get('x', 0) for node in self.nodes)
        min_y = min(node.data.get('y', 0) for node in self.nodes)
        max_x = max(node.data.get('x', 0) for node in self.nodes)
        max_y = max(node.data.get('y', 0) for node in self.nodes)

        width = max(1000, max_x - min_x)
        height = max(1000, max_y - min_y)
        self.spatial_grid = SpatialGrid(width, height, self.spatial_cell_size)

        for node in self.nodes:
            self.spatial_grid.insert(node)

    def _update_buffer(self) -> None:
        """Update the rendering buffer."""
        if not self.draw_widget:
            return

        # Create new buffer if needed
        if (not self._next_buffer or 
            self._next_buffer.size() != self.draw_widget.size()):
            self._next_buffer = QPixmap(self.draw_widget.size())

        # Update viewport state
        self.view_state.viewport_width = self.draw_widget.width()
        self.view_state.viewport_height = self.draw_widget.height()
        self.view_state.zoom_level = self.viewport_scale
        self.view_state.position = {"x": self.viewport_x, "y": self.viewport_y}

        # Render using the renderer
        render_data = self.renderer.render(self.nodes, self.edges, self.view_state)

        # Paint to buffer
        self._paint_to_buffer(self._next_buffer)

        # Swap buffers
        self._current_buffer = self._next_buffer
        self._buffer_dirty = False

    def update(self) -> None:
        """Schedule a buffer update."""
        self._update_timer.start(0)

    def resizeEvent(self, event) -> None:
        """Handle widget resize."""
        super().resizeEvent(event)
        self._buffer_dirty = True

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for dragging and selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_x = event.position().x()
            self.drag_start_y = event.position().y()

            # Check for node selection
            node = self._node_at_pos(event.position().x(), event.position().y())
            if node:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if node.id in self.selected_ids:
                        self.selected_ids.remove(node.id)
                    else:
                        self.selected_ids.add(node.id)
                else:
                    self.selected_ids = {node.id}
                self.selectionChanged.emit(self.selected_ids)
                self._buffer_dirty = True
                self.update()
            else:
                self.is_dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
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

    def wheelEvent(self, event) -> None:
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

    def _paint_to_buffer(self, buffer: QPixmap) -> None:
        """Paint content to buffer with optimized rendering."""
        if not buffer:
            graphics_logger.warning("Attempted to paint to null buffer")
            return

        # Update viewport state
        self.view_state.viewport_width = self.draw_widget.width()
        self.view_state.viewport_height = self.draw_widget.height()
        self.view_state.zoom_level = self.viewport_scale
        self.view_state.position = {"x": self.viewport_x, "y": self.viewport_y}

        # Get rendered data
        render_data = self.renderer.render(self.nodes, self.edges, self.view_state)

        # Paint to buffer
        painter = QPainter(buffer)
        try:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(buffer.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            painter.fillRect(buffer.rect(), Qt.GlobalColor.white)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Apply viewport transform
            painter.translate(
                self.draw_widget.width()/2 + self.viewport_x,
                self.draw_widget.height()/2 + self.viewport_y
            )
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
                if node["selected"]:
                    painter.setBrush(QBrush(QColor('#ff6464')))
                    painter.setPen(QPen(QColor('#ff6464')))
                else:
                    painter.setBrush(QBrush(QColor(node["color"])))
                    painter.setPen(QPen(QColor(node["color"]).darker(120)))

                x = node["x"]
                y = node["y"]
                size = node["size"]
                painter.drawEllipse(QPointF(x, y), size/2, size/2)

                # Draw labels if zoomed in enough
                if self.viewport_scale > 0.5 and node.get("label"):
                    painter.setPen(QPen(Qt.GlobalColor.black))
                    text_rect = painter.boundingRect(
                        QRectF(x + size, y - 10, 200, 20),
                        Qt.AlignmentFlag.AlignLeft,
                        node["label"]
                    )
                    
                    # Draw text background
                    painter.fillRect(
                        text_rect.adjusted(-2, -2, 2, 2),
                        QBrush(QColor(255, 255, 255, 220))
                    )
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft, node["label"])

        finally:
            painter.end()

    def _node_at_pos(self, screen_x: float, screen_y: float) -> Optional[VisualNode]:
        """Find node at the given screen position."""
        # Transform screen coordinates to scene coordinates
        scene_x = (screen_x - self.width()/2 - self.viewport_x) / self.viewport_scale
        scene_y = (screen_y - self.height()/2 - self.viewport_y) / self.viewport_scale

        # Use spatial index if enabled
        if self.enable_spatial_index and self.spatial_grid:
            scene_pos = QPointF(scene_x, scene_y)
            nodes = self.spatial_grid.query(QRectF(
                scene_pos.x() - 5/self.viewport_scale,
                scene_pos.y() - 5/self.viewport_scale,
                10/self.viewport_scale,
                10/self.viewport_scale
            ))
        else:
            nodes = self.nodes

        # Find closest node within threshold
        closest_node = None
        min_dist = float('inf')
        for node in nodes:
            dx = node.data.get('x', 0) - scene_x
            dy = node.data.get('y', 0) - scene_y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < node.size/2 and dist < min_dist:
                min_dist = dist
                closest_node = node

        return closest_node
