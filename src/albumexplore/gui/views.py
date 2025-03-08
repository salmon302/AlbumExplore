import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                           QGraphicsView, QGraphicsScene, QGraphicsItem, QHeaderView,
                           QSizePolicy, QGraphicsLineItem)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from .graphics_debug import init_graphics_debugging, GraphicsDebugMonitor
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QPalette
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.gui.gui_logging import gui_logger
from albumexplore.visualization.views.tag_explorer_view import TagExplorerView
from albumexplore.visualization.views.tag_graph_view import TagGraphView

class BaseViewWidget(QWidget):
    """Base class for all visualization view widgets."""
    selectionChanged = pyqtSignal(set)  # Emits set of selected node IDs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(self.__class__.__name__)
        self.graphics_debug = init_graphics_debugging(self)
        
        # Initialize selection tracking
        self.selected_ids = set()
        
        # Enhanced buffer management - ensure consistent background handling
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        
        # Create layout after setting attributes
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Set size policy and minimum size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 100)
        
        # Set explicit white background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        self.setPalette(palette)
        
        gui_logger.debug(f"{self.__class__.__name__} initialized with size {self.size()}")
    
    def resizeEvent(self, event):
        """Handle resize events with proper update management."""
        self.setUpdatesEnabled(False)
        try:
            super().resizeEvent(event)
            
            # For views with internal widgets, ensure they resize properly
            if hasattr(self, 'view'):
                self.view.resize(event.size())
            elif hasattr(self, 'table'):
                self.table.resize(event.size())
            
            # Check visibility after resize
            if hasattr(self, 'view'):
                visible = len(self.view.scene().items())
                total = getattr(self, '_total_items', visible)
                self.graphics_debug.log_view_update(self, visible, total)
            
        finally:
            self.setUpdatesEnabled(True)
            self.update()  # Force immediate repaint
            gui_logger.debug(f"{self.__class__.__name__} resized to {event.size()}")
    
    def showEvent(self, event):
        """Handle show events with proper initialization."""
        super().showEvent(event)
        
        # Ensure proper sizing of child widgets
        if hasattr(self, 'view'):
            self.view.resize(self.size())
            self.view.show()
            visible = len(self.view.scene().items())
            total = getattr(self, '_total_items', visible)
            self.graphics_debug.log_view_update(self, visible, total)
        elif hasattr(self, 'table'):
            self.table.resize(self.size())
            self.table.show()
            self.table.raise_()
        
        self.update()
        gui_logger.debug(f"{self.__class__.__name__} shown")
    
    def paintEvent(self, event):
        """Ensure proper background painting and buffer management."""
        self.graphics_debug.log_paint_event(self, "paint")
        painter = QPainter(self)
        
        # Fill background with solid white
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        # Paint child widgets
        super().paintEvent(event)
        
        # Verify buffer state
        viewport = self.rect()
        cleared = viewport.isValid()
        self.graphics_debug.log_buffer_state(self, cleared)
    
    def hideEvent(self, event):
        """Handle cleanup when widget is hidden."""
        gui_logger.debug(f"{self.__class__.__name__} hidden")
        super().hideEvent(event)
        
        # Ensure child widgets are hidden
        if hasattr(self, 'view'):
            self.view.hide()
        elif hasattr(self, 'table'):
            self.table.hide()

class TableViewWidget(BaseViewWidget):
    """Table view implementation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        gui_logger.debug("Initializing TableViewWidget")
        
        # Create table widget with proper initialization
        self.table = QTableWidget(self)
        self.table.setObjectName("albumTable")
        
        # Set explicit size policies
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Setup table properties
        self.table.setFrameStyle(QTableWidget.Shape.NoFrame)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        
        # Set fixed colors for alternating rows that won't disappear on selection
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
            }
            QTableWidget::item {
                color: black;
                border-bottom: 1px solid #eeeeee;
            }
            QTableWidget::item:selected {
                background-color: #c2dbf5;
                color: black;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: black;
                border: 1px solid #dcdcdc;
                padding: 4px;
            }
        """)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setVisible(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 250)  # Artist
        self.table.setColumnWidth(1, 300)  # Album
        self.table.setColumnWidth(2, 80)   # Year
        self.table.setColumnWidth(3, 400)  # Tags
        
        # Now set interactive resize mode and stretch last section
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Hide vertical header (row numbers)
        self.table.verticalHeader().setVisible(False)
        
        # Add table to layout and ensure it fills the widget
        self.layout.addWidget(self.table)
        
        # Connect selection signal
        self.table.itemSelectionChanged.connect(self._handle_selection)
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_direction = "asc"
        
        # Force immediate geometry update
        self.updateGeometry()
        self.table.updateGeometry()
        
        # Ensure table is visible after initialization
        self.table.show()
        self.table.raise_()
        
        gui_logger.debug(f"TableViewWidget initialized with size {self.size()}")

    def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
        """Update table with new data."""
        gui_logger.debug(f"Updating table data with {len(nodes)} nodes")
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            
            # Filter for row-type nodes
            valid_nodes = [n for n in nodes if n.data.get("type") == "row"]
            gui_logger.debug(f"Found {len(valid_nodes)} valid row nodes")
            
            # Set row count
            self.table.setRowCount(len(valid_nodes))
            
            for row, node in enumerate(valid_nodes):
                items = [
                    (str(node.data.get("artist", "")), 0),
                    (str(node.data.get("title", "")), 1),
                    (str(node.data.get("year", "")), 2),
                    (", ".join(str(tag) for tag in node.data.get("tags", [])), 3)
                ]
                
                for text, col in items:
                    item = QTableWidgetItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, node.id)
                    self.table.setItem(row, col, item)
            
            # Update selection state
            self._update_selection()
            
            # Apply current sorting if any
            if self.sort_column is not None:
                self.table.sortItems(
                    self.sort_column,
                    Qt.SortOrder.AscendingOrder if self.sort_direction == "asc" else Qt.SortOrder.DescendingOrder
                )
            
            gui_logger.debug(f"Table updated with {self.table.rowCount()} rows")
            
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()
            self.table.updateGeometry()

    def _handle_selection(self):
        """Handle table selection changes."""
        selected_ids = set()
        for item in self.table.selectedItems():
            node_id = item.data(Qt.ItemDataRole.UserRole)
            if node_id:
                selected_ids.add(node_id)
        
        if selected_ids != self.selected_ids:
            self.selected_ids = selected_ids
            self.selectionChanged.emit(selected_ids)

    def _update_selection(self):
        """Update table selection state."""
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) in self.selected_ids:
                self.table.selectRow(row)

    def showEvent(self, event):
        """Handle show events."""
        super().showEvent(event)
        # Ensure table resizes properly when shown
        self.table.resize(self.size())
        self.table.show()
        self.table.raise_()
        self.update()
        gui_logger.debug("Table view shown")

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        # Ensure table fills the widget when resized
        self.table.resize(event.size())
        self.update()
        gui_logger.debug(f"Table resized to {event.size()}")

    def hideEvent(self, event):
        """Handle cleanup when widget is hidden."""
        gui_logger.debug(f"{self.__class__.__name__} hidden")
        super().hideEvent(event)
        self.table.hide()

class NetworkViewWidget(BaseViewWidget):
	"""Network graph view implementation."""
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Create graphics view and scene
		self.scene = QGraphicsScene(self)
		self.view = QGraphicsView(self.scene)
		self.layout.addWidget(self.view)
		
		# Enable antialiasing
		self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Setup interaction flags
		self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
		self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		
		# Node tracking
		self.node_items = {}  # Maps node IDs to graphics items
		
		# Connect selection handling
		self.scene.selectionChanged.connect(self._handle_selection)
	
	def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
		"""Update network visualization with new data."""
		self.scene.clear()
		self.node_items.clear()
		
		# Store total items count for visibility tracking
		self._total_items = len(nodes) + len(edges)
		
		# Draw edges first (so they appear under nodes)
		for edge in edges:
			self._create_edge(edge)
		
		# Draw nodes
		for node in nodes:
			self._create_node(node)
		
		# Check for overlapping elements
		self.graphics_debug.log_overlap_check(self, self.scene.items())
		
		# Update selection state
		self._update_selection()
		
		# Fit view to content
		self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
	
	def _create_node(self, node: VisualNode) -> None:
		"""Create a node graphics item."""
		# Create node graphics item at origin
		item = self.scene.addEllipse(
			-node.size/2,  # Center the ellipse around (0,0)
			-node.size/2,
			node.size,
			node.size,
			QPen(QColor(node.color).darker()),
			QBrush(QColor(node.color))
		)
		
		# Set position from node data
		x = node.data.get('x', 0)
		y = node.data.get('y', 0)
		item.setPos(x, y)
		
		# Make item selectable and movable
		item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
		
		# Store node ID and data for selection tracking
		item.setData(0, node.id)
		item.setData(1, node.data)  # Store node data for animations
		self.node_items[node.id] = item

	
	def _create_edge(self, edge: VisualEdge) -> None:
		"""Create an edge graphics item."""
		if edge.source in self.node_items and edge.target in self.node_items:
			source_item = self.node_items[edge.source]
			target_item = self.node_items[edge.target]
			
			# Create line item
			line = QGraphicsLineItem()
			line.setPen(QPen(QColor(edge.color), edge.thickness))
			line.setZValue(-1)  # Ensure edges are drawn under nodes
			
			# Update line position
			source_pos = source_item.pos()
			target_pos = target_item.pos()
			line.setLine(source_pos.x(), source_pos.y(),
						target_pos.x(), target_pos.y())
			
			# Store source and target IDs with the line item
			line.setData(0, edge.source)
			line.setData(1, edge.target)
			
			self.scene.addItem(line)
	
	def apply_transition(self, transition_data: dict) -> None:
		"""Apply transition effect."""
		if transition_data['transition']['type'] == 'morph':
			# Use preserved positions for morphing
			positions = transition_data.get('preserved_positions', {})
			for node_id, pos in positions.items():
				if node_id in self.node_items:
					item = self.node_items[node_id]
					# Set position directly using scene coordinates
					item.setPos(pos['x'], pos['y'])
					# Update edges connected to this node
					self._update_connected_edges(node_id)
		
		# Update selection state
		if 'shared_selections' in transition_data:
			self.selected_ids = set(transition_data['shared_selections'])
			self._update_selection()

	def _update_connected_edges(self, node_id: str) -> None:
		"""Update edges connected to the given node."""
		node_item = self.node_items.get(node_id)
		if not node_item:
			return
			
		# Find and update all edges connected to this node
		for item in self.scene.items():
			if isinstance(item, QGraphicsLineItem):
				source_id = item.data(0)
				target_id = item.data(1)
				if source_id == node_id or target_id == node_id:
					source_item = self.node_items.get(source_id)
					target_item = self.node_items.get(target_id)
					if source_item and target_item:
						source_pos = source_item.pos()
						target_pos = target_item.pos()
						item.setLine(source_pos.x(), source_pos.y(),
								   target_pos.x(), target_pos.y())

	
	def _handle_selection(self):
		"""Handle scene selection changes."""
		selected_ids = {
			item.data(0) for item in self.scene.selectedItems()
			if item.data(0) is not None
		}
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
	
	def _update_selection(self):
		"""Update graphics items selection state."""
		for node_id, item in self.node_items.items():
			item.setSelected(node_id in self.selected_ids)

class ChordViewWidget(BaseViewWidget):
	"""Chord diagram view implementation."""
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Create graphics view and scene
		self.scene = QGraphicsScene(self)
		self.view = QGraphicsView(self.scene)
		self.layout.addWidget(self.view)
		
		# Enable antialiasing
		self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Node tracking
		self.node_items = {}  # Maps node IDs to graphics items
		
		# Connect selection handling
		self.scene.selectionChanged.connect(self._handle_selection)
	
	def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
		"""Update chord diagram with new data."""
		self.scene.clear()
		self.node_items.clear()
		
		if not nodes:
			return
		
		# Calculate layout
		center = QPointF(0, 0)
		radius = 200  # Base radius
		angle_step = 2 * 3.14159 / len(nodes)
		
		# Create nodes in circular layout
		for i, node in enumerate(nodes):
			angle = i * angle_step
			x = center.x() + radius * math.cos(angle)
			y = center.y() + radius * math.sin(angle)
			self._create_node(node, QPointF(x, y))
		
		# Create edges as Bezier curves
		for edge in edges:
			self._create_edge(edge)
		
		# Update selection state
		self._update_selection()
		
		# Fit view to content
		self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
	
	def _create_node(self, node: VisualNode, pos: QPointF) -> None:
		"""Create a node graphics item."""
		item = self.scene.addEllipse(
			-node.size/2,  # Center the ellipse around (0,0)
			-node.size/2,
			node.size,
			node.size,
			QPen(QColor(node.color).darker()),
			QBrush(QColor(node.color))
		)
		
		# Set position
		item.setPos(pos)
		
		# Make item selectable
		item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		
		# Store node ID and data
		item.setData(0, node.id)
		item.setData(1, node.data)
		self.node_items[node.id] = item
	
	def _create_edge(self, edge: VisualEdge) -> None:
		"""Create a curved edge between nodes."""
		if edge.source in self.node_items and edge.target in self.node_items:
			source_item = self.node_items[edge.source]
			target_item = self.node_items[edge.target]
			
			# Get node centers
			source_pos = source_item.pos()
			target_pos = target_item.pos()
			
			# Create control points for curve
			center = QPointF(0, 0)
			path = QPainterPath()
			path.moveTo(source_pos)
			path.quadTo(center, target_pos)
			
			# Create path item
			path_item = self.scene.addPath(
				path,
				QPen(QColor(edge.color), edge.thickness)
			)
			path_item.setZValue(-1)  # Ensure edges are drawn under nodes
	
	def apply_transition(self, transition_data: dict) -> None:
		"""Apply transition effect."""
		if transition_data['transition']['type'] == 'fade':
			# Handle fade transition
			# Note: In a real implementation, you would use QPropertyAnimation
			pass
		
		# Update selection state
		if 'shared_selections' in transition_data:
			self.selected_ids = set(transition_data['shared_selections'])
			self._update_selection()
	
	def _handle_selection(self):
		"""Handle scene selection changes."""
		selected_ids = {
			item.data(0) for item in self.scene.selectedItems()
			if item.data(0) is not None
		}
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
	
	def _update_selection(self):
		"""Update graphics items selection state."""
		for node_id, item in self.node_items.items():
			item.setSelected(node_id in self.selected_ids)

class ArcViewWidget(BaseViewWidget):
	"""Arc diagram view implementation."""
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Create graphics view and scene
		self.scene = QGraphicsScene(self)
		self.view = QGraphicsView(self.scene)
		self.layout.addWidget(self.view)
		
		# Enable antialiasing
		self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Node tracking
		self.node_items = {}  # Maps node IDs to graphics items
		
		# Connect selection handling
		self.scene.selectionChanged.connect(self._handle_selection)
	
	def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
		"""Update arc diagram with new data."""
		self.scene.clear()
		self.node_items.clear()
		
		if not nodes:
			return
		
		# Calculate horizontal layout
		spacing = 50  # Space between nodes
		y_position = 0
		node_positions = {}
		
		# Position nodes horizontally
		for i, node in enumerate(nodes):
			x = i * spacing
			node_positions[node.id] = x
			self._create_node(node, QPointF(x, y_position))
		
		# Create arcs for edges
		for edge in edges:
			self._create_arc(edge, node_positions)
		
		# Update selection state
		self._update_selection()
		
		# Fit view to content
		self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
	
	def _create_node(self, node: VisualNode, pos: QPointF) -> None:
		"""Create a node graphics item."""
		item = self.scene.addEllipse(
			-node.size/2,  # Center the ellipse around (0,0)
			-node.size/2,
			node.size,
			node.size,
			QPen(QColor(node.color).darker()),
			QBrush(QColor(node.color))
		)
		
		# Set position
		item.setPos(pos)
		
		# Make item selectable
		item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		
		# Store node ID and data
		item.setData(0, node.id)
		item.setData(1, node.data)
		self.node_items[node.id] = item
	
	def _create_arc(self, edge: VisualEdge, node_positions: dict) -> None:
		"""Create an arc connecting two nodes."""
		if edge.source in self.node_items and edge.target in self.node_items:
			source_x = node_positions[edge.source]
			target_x = node_positions[edge.target]
			
			# Calculate arc height based on distance
			distance = abs(target_x - source_x)
			arc_height = -distance * 0.25  # Negative for upward arc
			
			# Create arc path
			path = QPainterPath()
			path.moveTo(source_x, 0)
			
			# Control points for quadratic curve
			control_x = (source_x + target_x) / 2
			control_y = arc_height
			
			path.quadTo(QPointF(control_x, control_y), QPointF(target_x, 0))
			
			# Create path item
			path_item = self.scene.addPath(
				path,
				QPen(QColor(edge.color), edge.thickness)
			)
			path_item.setZValue(-1)  # Ensure arcs are drawn under nodes
	
	def apply_transition(self, transition_data: dict) -> None:
		"""Apply transition effect."""
		if transition_data['transition']['type'] == 'morph':
			# Handle morphing from chord diagram
			# Note: In a real implementation, you would animate the unwrapping
			pass
		
		# Update selection state
		if 'shared_selections' in transition_data:
			self.selected_ids = set(transition_data['shared_selections'])
			self._update_selection()
	
	def _handle_selection(self):
		"""Handle scene selection changes."""
		selected_ids = {
			item.data(0) for item in self.scene.selectedItems()
			if item.data(0) is not None
		}
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
	
	def _update_selection(self):
		"""Update graphics items selection state."""
		for node_id, item in self.node_items.items():
			item.setSelected(node_id in self.selected_ids)

def create_view(view_type: ViewType, parent=None) -> BaseViewWidget:
	"""Create a view widget of the specified type."""
	view_map = {
		ViewType.TABLE: TableViewWidget,
		ViewType.NETWORK: NetworkViewWidget,
		ViewType.CHORD: ChordViewWidget,
		ViewType.ARC: ArcViewWidget,
		ViewType.TAG_EXPLORER: lambda p: TagExplorerView(p),
		ViewType.TAG_GRAPH: lambda p: TagGraphView(p)
	}
	widget_class = view_map.get(view_type)
	if not widget_class:
		raise ValueError(f"No widget implementation for view type: {view_type}")
	return widget_class(parent)