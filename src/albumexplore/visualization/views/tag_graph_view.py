from typing import Dict, List, Set, Tuple
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
                           QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
                           QPushButton, QHBoxLayout, QComboBox, QLabel, QSpinBox)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF, QTimer
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath

from .base_view import BaseView
from ..state import ViewType, ViewState
from ...tags.normalizer import TagNormalizer
from ...tags.rules.consolidation_rules import ConsolidationRules

import math
import networkx as nx


class TagNode(QGraphicsEllipseItem):
    """A node in the tag graph representing a single tag."""
    
    def __init__(self, tag: str, count: int, x: float, y: float, radius: float):
        super().__init__(0, 0, radius * 2, radius * 2)
        self.tag = tag
        self.count = count
        self.radius = radius
        self.normal_color = QColor(100, 149, 237)  # Cornflower blue
        self.selected_color = QColor(255, 140, 0)  # Dark orange
        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QBrush(self.normal_color))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        
        # Set position (center of the circle, not top-left corner)
        self.setPos(x - radius, y - radius)
        
        # Add text label
        self.label = QGraphicsTextItem(self)
        self.label.setPlainText(tag)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        
        # Center the text within the node
        br = self.label.boundingRect()
        self.label.setPos((radius*2 - br.width())/2, (radius*2 - br.height())/2)
    
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self.normal_color.lighter(120)))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.setBrush(QBrush(self.selected_color))
        else:
            self.setBrush(QBrush(self.normal_color))
        super().hoverLeaveEvent(event)


class TagEdge(QGraphicsLineItem):
    """An edge in the tag graph representing a relationship between tags."""
    
    def __init__(self, source_node: TagNode, target_node: TagNode, edge_type: str = "hierarchy"):
        # Calculate start and end points at the edges of the nodes
        source_center = source_node.pos() + QPointF(source_node.radius, source_node.radius)
        target_center = target_node.pos() + QPointF(target_node.radius, target_node.radius)
        
        # Direction vector
        direction = target_center - source_center
        length = math.sqrt(direction.x()**2 + direction.y()**2)
        if length == 0:
            normalized_direction = QPointF(0, 0)
        else:
            normalized_direction = QPointF(direction.x()/length, direction.y()/length)
        
        # Adjust start and end points to the edges of the nodes
        start = source_center + normalized_direction * source_node.radius
        end = target_center - normalized_direction * target_node.radius
        
        super().__init__(start.x(), start.y(), end.x(), end.y())
        
        # Set line style based on edge type
        pen = QPen()
        if edge_type == "hierarchy":
            pen.setWidth(2)
            pen.setColor(QColor(70, 130, 180))  # Steel blue
        elif edge_type == "similar":
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setColor(QColor(119, 136, 153))  # Light slate gray
        
        self.setPen(pen)
        self.setZValue(-1)  # Draw edges behind nodes
        self.source_node = source_node
        self.target_node = target_node
        self.edge_type = edge_type


class TagGraphView(BaseView):
    """Network visualization of tag relationships."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_state = ViewState(ViewType.TAG_GRAPH)
        self.tag_normalizer = TagNormalizer()
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Add controls
        controls = QHBoxLayout()
        
        # Layout type selector
        layout_label = QLabel("Layout:")
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Hierarchical", "Force-Directed", "Circular"])
        self.layout_combo.currentTextChanged.connect(self._update_layout)
        controls.addWidget(layout_label)
        controls.addWidget(self.layout_combo)
        
        # Minimum tag count filter
        count_label = QLabel("Min Count:")
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(10)
        self.count_spin.valueChanged.connect(self._filter_by_count)
        controls.addWidget(count_label)
        controls.addWidget(self.count_spin)
        
        # Relationship type filter
        relation_label = QLabel("Show:")
        self.relation_combo = QComboBox()
        self.relation_combo.addItems(["All", "Hierarchies Only", "Similar Tags Only"])
        self.relation_combo.currentTextChanged.connect(self._filter_relationships)
        controls.addWidget(relation_label)
        controls.addWidget(self.relation_combo)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Create graphics view
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        layout.addWidget(self.view)
        
        # Initialize graph data structures
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, TagNode] = {}
        self.edges: List[TagEdge] = []
        self.tag_counts: Dict[str, int] = {}
        
        # Animation timer for smooth transitions
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animation_step)
        self.animation_progress = 0.0
        self.old_positions = {}
        self.new_positions = {}
        
    def update_data(self, nodes, edges):
        """Update the graph with new data."""
        super().update_data(nodes, edges)
        
        # Reset graph
        self.graph.clear()
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        self.tag_counts.clear()
        
        # Calculate tag counts from albums
        for node in nodes:
            for tag in node.data.get('tags', []):
                normalized = self.tag_normalizer.normalize(tag, aggressive=True)
                self.tag_counts[normalized] = self.tag_counts.get(normalized, 0) + 1
        
        # Add nodes to graph for tags meeting minimum count
        min_count = self.count_spin.value()
        for tag, count in self.tag_counts.items():
            if count >= min_count:
                self.graph.add_node(tag, count=count)
        
        # Add hierarchical relationships
        for tag in list(self.graph.nodes):
            parents = self.tag_normalizer.get_tag_hierarchy(tag)[1:]
            for parent in parents:
                if parent in self.graph:
                    self.graph.add_edge(tag, parent, type="hierarchy")
        
        # Add similarity relationships from consolidation rules
        for tag1 in list(self.graph.nodes):
            canonical1 = ConsolidationRules.get_canonical_form(tag1)
            for tag2 in list(self.graph.nodes):
                if tag1 != tag2:
                    canonical2 = ConsolidationRules.get_canonical_form(tag2)
                    if canonical1 == canonical2:
                        self.graph.add_edge(tag1, tag2, type="similar")
        
        # Apply layout
        self._update_layout()
        
    def _update_layout(self):
        """Update the graph layout."""
        layout_type = self.layout_combo.currentText()
        
        # Store old positions for animation
        self.old_positions = {node: self.nodes[node].pos() + QPointF(self.nodes[node].radius, self.nodes[node].radius) 
                            if node in self.nodes else QPointF() 
                            for node in self.graph.nodes}
        
        # Calculate new layout
        if layout_type == "Hierarchical":
            pos = nx.spring_layout(self.graph, k=1, iterations=50)
        elif layout_type == "Force-Directed":
            pos = nx.kamada_kawai_layout(self.graph)
        else:  # Circular
            pos = nx.circular_layout(self.graph)
        
        # Scale and center the layout
        scale = min(self.view.width(), self.view.height()) * 0.8
        center = QPointF(self.view.width()/2, self.view.height()/2)
        
        self.new_positions = {}
        for node, (x, y) in pos.items():
            self.new_positions[node] = QPointF(x * scale + center.x(),
                                             y * scale + center.y())
        
        # Create nodes
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        
        for node_id, position in self.new_positions.items():
            count = self.tag_counts[node_id]
            # Scale node size based on count (with min/max limits)
            radius = max(20, min(50, 15 + 0.5 * math.log(count + 1)))
            node = TagNode(node_id, count, position.x(), position.y(), radius)
            self.scene.addItem(node)
            self.nodes[node_id] = node
        
        # Create edges
        self._update_edges()
        
        # Set scene rect
        self.view.setSceneRect(self.scene.itemsBoundingRect())
        
    def _animation_step(self):
        """Update node positions during animation."""
        self.animation_progress += 0.1
        if self.animation_progress >= 1.0:
            self.animation_timer.stop()
            self.animation_progress = 1.0
        
        # Update node positions
        for node_id, new_pos in self.new_positions.items():
            if node_id in self.nodes:
                old_pos = self.old_positions[node_id]
                current_pos = QPointF(
                    old_pos.x() + (new_pos.x() - old_pos.x()) * self.animation_progress,
                    old_pos.y() + (new_pos.y() - old_pos.y()) * self.animation_progress
                )
                node = self.nodes[node_id]
                node.setPos(current_pos.x() - node.radius, current_pos.y() - node.radius)
        
        # Update edges
        self._update_edges()
        
    def _update_edges(self):
        """Update edge positions to match nodes."""
        # Remove old edges
        for edge in self.edges:
            self.scene.removeItem(edge)
        self.edges.clear()
        
        # Create new edges
        relationship_filter = self.relation_combo.currentText()
        for source, target, data in self.graph.edges(data=True):
            if source in self.nodes and target in self.nodes:
                edge_type = data.get('type', 'hierarchy')
                
                # Apply relationship filter
                if relationship_filter == "Hierarchies Only" and edge_type != "hierarchy":
                    continue
                if relationship_filter == "Similar Tags Only" and edge_type != "similar":
                    continue
                
                # Create edge between nodes
                edge = TagEdge(self.nodes[source], self.nodes[target], edge_type)
                self.scene.addItem(edge)
                self.edges.append(edge)
    
    def _filter_by_count(self):
        """Filter nodes based on minimum tag count."""
        self.update_data(self.nodes, self.edges)
    
    def _filter_relationships(self):
        """Filter relationships based on type selection."""
        self._update_edges()
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.view.setFixedSize(self.size())
        if self.graph.number_of_nodes() > 0:
            self._update_layout()