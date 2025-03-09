"""GUI views for visualization system."""
from typing import Dict, Any, List, Set, Optional, Callable
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableView, 
                           QGraphicsView, QGraphicsScene)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.layout import ForceDirectedLayout
from albumexplore.gui.models import AlbumTableModel
from albumexplore.gui.gui_logging import graphics_logger

class BaseView(QWidget):
    """Base class for visualization views."""
    
    selection_changed = pyqtSignal(set)  # Emits selected node IDs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.selected_ids: Set[str] = set()
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up UI elements."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
    
    def update_data(self, render_data: Dict[str, Any]):
        """Update view with new data."""
        pass
    
    def apply_transition(self, transition_data: Dict[str, Any]):
        """Apply transition changes."""
        # Update selections
        if 'shared_selections' in transition_data:
            self.selected_ids = set(transition_data['shared_selections'])
            self.selection_changed.emit(self.selected_ids)

class TableView(BaseView):
    """Table visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableView(self)
        self.layout.addWidget(self.table)
        self.model = AlbumTableModel()
        self.table.setModel(self.model)
        
        # Connect selection handling
        self.table.selectionModel().selectionChanged.connect(self._handle_selection)
    
    def update_data(self, render_data: Dict[str, Any]):
        """Update table data."""
        if render_data.get("type") != "table":
            return
            
        self.model.set_data(render_data.get("rows", []))
        self._restore_selection()
    
    def apply_transition(self, transition_data: Dict[str, Any]):
        """Apply transition changes."""
        super().apply_transition(transition_data)
        self._restore_selection()
    
    def _restore_selection(self):
        """Restore selection state."""
        if not self.selected_ids:
            self.table.clearSelection()
            return
            
        selection_model = self.table.selectionModel()
        selection_model.clearSelection()
        
        # Find and select rows with matching IDs
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if self.model.data(index, Qt.ItemDataRole.UserRole) in self.selected_ids:
                selection_model.select(index, selection_model.SelectionFlag.Select)
    
    def _handle_selection(self, selected, deselected):
        """Handle table selection changes."""
        self.selected_ids = {
            self.model.data(self.model.index(row, 0), Qt.ItemDataRole.UserRole)
            for index in self.table.selectionModel().selectedIndexes()
            for row in {index.row()}
        }
        self.selection_changed.emit(self.selected_ids)

class NetworkView(BaseView):
    """Network visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.layout.addWidget(self.view)
        
        # View settings
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        # Setup handling
        self.layout = ForceDirectedLayout()
        self.node_items = {}
        self.edge_items = {}
        self._setup_animations()
    
    def _setup_animations(self):
        """Set up animation handling."""
        self.animation_timer = self.startTimer(16)  # ~60 FPS
        self.is_animating = False
    
    def update_data(self, render_data: Dict[str, Any]):
        """Update network data."""
        if render_data.get("type") != "network":
            return
        
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        
        # Draw edges first
        for edge in render_data.get("edges", []):
            edge_item = self.scene.addLine(
                edge["source_x"], edge["source_y"],
                edge["target_x"], edge["target_y"],
                QPen(QColor(edge["color"]), edge["thickness"])
            )
            edge_item.setOpacity(edge["opacity"])
            self.edge_items[edge["id"]] = edge_item
        
        # Draw nodes
        for node in render_data.get("nodes", []):
            node_item = self.scene.addEllipse(
                node["x"] - node["size"]/2,
                node["y"] - node["size"]/2,
                node["size"], node["size"],
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(node["color"]))
            )
            node_item.setOpacity(node["opacity"])
            node_item.setData(0, node["id"])
            self.node_items[node["id"]] = node_item
        
        # Update scene rect
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def apply_transition(self, transition_data: Dict[str, Any]):
        """Apply transition changes."""
        super().apply_transition(transition_data)
        
        # Apply positions if provided
        if "preserved_positions" in transition_data:
            for node_id, pos in transition_data["preserved_positions"].items():
                if node_id in self.node_items:
                    item = self.node_items[node_id]
                    item.setPos(pos["x"], pos["y"])
        
        # Update selections
        self._update_selections()
    
    def _update_selections(self):
        """Update visual selection state."""
        for node_id, item in self.node_items.items():
            selected = node_id in self.selected_ids
            item.setBrush(QBrush(QColor("#ff6464" if selected else "#4287f5")))
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Get item under cursor
            pos = self.view.mapToScene(event.pos())
            item = self.scene.itemAt(pos, self.view.transform())
            
            if item and item in self.node_items.values():
                node_id = item.data(0)
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if node_id in self.selected_ids:
                        self.selected_ids.remove(node_id)
                    else:
                        self.selected_ids.add(node_id)
                else:
                    self.selected_ids = {node_id}
                self._update_selections()
                self.selection_changed.emit(self.selected_ids)
            elif not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.selected_ids.clear()
                self._update_selections()
                self.selection_changed.emit(self.selected_ids)
        
        super().mousePressEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel events."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.view.scale(factor, factor)
        else:
            super().wheelEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        if self.scene.items():
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

def create_view(view_type: ViewType, parent=None) -> BaseView:
    """Create a view instance based on type."""
    view_classes = {
        ViewType.TABLE: TableView,
        ViewType.NETWORK: NetworkView,
    }
    
    view_class = view_classes.get(view_type)
    if not view_class:
        raise ValueError(f"Unsupported view type: {view_type}")
    
    return view_class(parent)