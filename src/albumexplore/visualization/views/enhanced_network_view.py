"""Enhanced network visualization with LOD and clustering support."""
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
from ..state import ViewState, ViewType
from ..spatial_grid import SpatialGrid
from .base_view import BaseView
from ..lod_system import LODSystem, ClusterManager
from ..cluster_engine import ClusterEngine, ClusterNode
from ..performance_optimizer import PerformanceOptimizer, PerformanceMetrics


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
        if not self.parent_view or not hasattr(self.parent_view, 'nodes') or not self.parent_view.nodes:
            # Clear with white background for empty state
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
            painter.end()
            return

        self.parent_view.start_performance_measure('frame')

        try:
            # Paint from buffer to widget
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw with composition mode that prevents transparency issues
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
        # Configure view attributes
        self.view_name = "EnhancedNetworkView"
        self.view_state = ViewState(ViewType.NETWORK)

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

        # Visibility tracking
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

        # Node/edge sets
        self.nodes = []
        self.edges = []
        self.selected_ids = set()

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
        # Find data extents
        if not self.nodes:
            return

        min_x = min(node.data.get('x', 0) for node in self.nodes)
        min_y = min(node.data.get('y', 0) for node in self.nodes)
        max_x = max(node.data.get('x', 0) for node in self.nodes)
        max_y = max(node.data.get('y', 0) for node in self.nodes)

        # Create spatial grid
        width = max(1000, max_x - min_x)
        height = max(1000, max_y - min_y)
        self.spatial_grid = SpatialGrid(width, height, self.spatial_cell_size)

        # Insert nodes
        for node in self.nodes:
            self.spatial_grid.insert(node)

    def _update_buffer(self) -> None:
        """Update the rendering buffer."""
        self._frame_start = time.time()
        self._buffer_dirty = True
        self.draw_widget.update()

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
            # Pan view
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
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Zoom centered on mouse position
        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Convert to view coordinates before zoom
        view_x = (mouse_x - self.draw_widget.width()/2) / self.viewport_scale - self.viewport_x/self.viewport_scale
        view_y = (mouse_y - self.draw_widget.height()/2) / self.viewport_scale - self.viewport_y/self.viewport_scale

        # Update zoom
        self.viewport_scale *= zoom_factor
        self.viewport_scale = max(0.1, min(10.0, self.viewport_scale))

        # Adjust to keep the point under the mouse fixed
        new_view_x = (mouse_x - self.draw_widget.width()/2) / self.viewport_scale - self.viewport_x/self.viewport_scale
        new_view_y = (mouse_y - self.draw_widget.height()/2) / self.viewport_scale - self.viewport_y/self.viewport_scale

        self.viewport_x += (new_view_x - view_x) * self.viewport_scale
        self.viewport_y += (new_view_y - view_y) * self.viewport_scale

        self._buffer_dirty = True
        self.update()

    def _node_at_pos(self, screen_x: float, screen_y: float) -> Optional[VisualNode]:
        """Find node at the given screen position."""
        if not self.nodes:
            return None

        view_x = (screen_x - self.draw_widget.width()/2) / self.viewport_scale - self.viewport_x/self.viewport_scale
        view_y = (screen_y - self.draw_widget.height()/2) / self.viewport_scale - self.viewport_y/self.viewport_scale

        search_radius = 10 / self.viewport_scale 
        if self.enable_spatial_index and self.spatial_grid:
            search_rect = QRectF(
                view_x - search_radius,
                view_y - search_radius,
                search_radius * 2,
                search_radius * 2
            )
            candidates = self.spatial_grid.query(search_rect)
        else:
            candidates = self.nodes

        closest_node = None
        min_dist = float('inf')

        for node in candidates:
            x = node.data.get('x', 0)
            y = node.data.get('y', 0)

            dx = x - view_x
            dy = y - view_y
            dist = math.sqrt(dx*dx + dy*dy)

            node_radius = node.size / 2 if hasattr(node, 'size') else 5

            if dist < min_dist and dist <= node_radius + search_radius:
                closest_node = node
                min_dist = dist

        return closest_node

    def _paint_to_buffer(self, buffer: QPixmap) -> None:
        """Paint content to buffer with optimized rendering."""
        if not buffer:
            graphics_logger.warning("Attempted to paint to null buffer")
            return

        start_time = time.time()

        painter = QPainter(buffer)
        try:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(buffer.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            painter.fillRect(buffer.rect(), Qt.GlobalColor.white)

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.translate(self.draw_widget.width()/2, self.draw_widget.height()/2)
            painter.scale(self.viewport_scale, self.viewport_scale)
            painter.translate(self.viewport_x / self.viewport_scale,
                            self.viewport_y / self.viewport_scale)

            view_rect = QRectF(
                -self.draw_widget.width()/(2*self.viewport_scale) - self.viewport_x/self.viewport_scale,
                -self.draw_widget.height()/(2*self.viewport_scale) - self.viewport_y/self.viewport_scale,
                self.draw_widget.width()/self.viewport_scale,
                self.draw_widget.height()/self.viewport_scale
            )

            if self.enable_spatial_index:
                self.visible_nodes = self.spatial_grid.query(view_rect)
            else:
                self.visible_nodes = [
                    node for node in self.nodes
                    if view_rect.contains(QPointF(
                        node.data.get('x', 0),
                        node.data.get('y', 0)
                    ))
                ]

            if self.enable_lod:
                lod_level = self.lod_system.get_lod_level(self.viewport_scale)
            else:
                lod_level = 0

            edge_start = time.time()
            path = QPainterPath()

            self.visible_edges = []
            visible_node_ids = {node.id for node in self.visible_nodes}

            for edge in self.edges:
                if (edge.source in visible_node_ids and
                    edge.target in visible_node_ids):
                    self.visible_edges.append(edge)

                    source = next(n for n in self.nodes if n.id == edge.source)
                    target = next(n for n in self.nodes if n.id == edge.target)

                    path.moveTo(source.data.get('x', 0), source.data.get('y', 0))
                    path.lineTo(target.data.get('x', 0), target.data.get('y', 0))

            edge_time = (time.time() - edge_start) * 1000
            log_performance_metric("Rendering", "edge_paint_time", f"{edge_time:.2f}ms")

            painter.setPen(QPen(QColor('#cccccc')))
            painter.drawPath(path)

            node_start = time.time()
            for node in self.visible_nodes:
                x = node.data.get('x', 0)
                y = node.data.get('y', 0)

                if not view_rect.contains(QPointF(x, y)):
                    continue

                size = node.size

                if lod_level > 0:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(node.color))
                    painter.drawEllipse(QPointF(x, y), size/2, size/2)
                else:
                    if node.data.get('is_cluster', False):
                        painter.setBrush(QBrush(QColor(node.color)))
                        painter.setPen(QPen(QColor(node.color).darker(120)))
                    else:
                        if node.id in self.selected_ids:
                            painter.setBrush(QBrush(QColor('#ff6464')))
                            painter.setPen(QPen(QColor('#ff6464')))
                        else:
                            painter.setBrush(QBrush(QColor(node.color)))
                            painter.setPen(QPen(QColor(node.color).darker(120)))

                    painter.drawEllipse(QPointF(x, y), size/2, size/2)

                    if self.viewport_scale > 0.5 and node.label:
                        painter.setPen(QPen(Qt.GlobalColor.black))
                        text_rect = painter.boundingRect(
                            QRectF(x + size, y - 10, 200, 20),
                            Qt.AlignmentFlag.AlignLeft,
                            node.label
                        )
                        painter.fillRect(
                            text_rect.adjusted(-2, -2, 2, 2),
                            QBrush(QColor(255, 255, 255, 220))
                        )
                        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft, node.label)

            node_time = (time.time() - node_start) * 1000
            log_performance_metric("Rendering", "node_paint_time", f"{node_time:.2f}ms")

        finally:
            painter.end()
            total_time = (time.time() - start_time) * 1000
            log_performance_metric("Rendering", "total_paint_time", f"{total_time:.2f}ms")

            if total_time > 33:
                self.performance_optimizer.optimize(self.performance_metrics)
