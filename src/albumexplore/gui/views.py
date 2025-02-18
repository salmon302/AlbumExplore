import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
						   QGraphicsView, QGraphicsScene, QGraphicsItem, QHeaderView,
						   QSizePolicy, QGraphicsLineItem)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.models import VisualNode, VisualEdge

class BaseViewWidget(QWidget):
	"""Base class for all visualization view widgets."""
	selectionChanged = pyqtSignal(set)  # Emits set of selected node IDs
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.layout = QVBoxLayout(self)
		self.selected_ids = set()
	
	def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
		"""Update view with new data."""
		raise NotImplementedError
	
	def apply_transition(self, transition_data: dict) -> None:
		"""Apply transition effect."""
		raise NotImplementedError

class TableViewWidget(BaseViewWidget):
	"""Table view implementation."""
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Create table widget
		self.table = QTableWidget(self)
		self.layout.addWidget(self.table)
		
		# Setup table properties
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
		self.table.setColumnCount(4)
		self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.table.setShowGrid(True)
		self.table.setAlternatingRowColors(True)
		
		# Ensure table expands to fill space
		self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		
		# Connect selection signal
		self.table.itemSelectionChanged.connect(self._handle_selection)
	
	def update_data(self, nodes: list[VisualNode], edges: list[VisualEdge]) -> None:
		"""Update table with new data."""
		print(f"Updating table with {len(nodes)} nodes")  # Debug log
		self.table.setRowCount(0)  # Clear existing rows
		self.table.setRowCount(len(nodes))
		
		for row, node in enumerate(nodes):
			if node.data.get("type") == "row":
				print(f"Setting row {row}: {node.data}")  # Debug log
				# Artist
				artist_item = QTableWidgetItem(str(node.data.get("artist", "")))
				self.table.setItem(row, 0, artist_item)
				
				# Album
				album_item = QTableWidgetItem(str(node.data.get("title", "")))
				self.table.setItem(row, 1, album_item)
				
				# Year
				year_item = QTableWidgetItem(str(node.data.get("year", "")))
				self.table.setItem(row, 2, year_item)
				
				# Tags
				tags = node.data.get("tags", [])
				tags_item = QTableWidgetItem(", ".join(str(tag) for tag in tags))
				self.table.setItem(row, 3, tags_item)
				
				# Store node ID for selection tracking
				for col in range(4):
					item = self.table.item(row, col)
					if item:
						item.setData(Qt.ItemDataRole.UserRole, node.id)
		
		self.table.resizeColumnsToContents()
		print("Table update complete")  # Debug log

	
	def apply_transition(self, transition_data: dict) -> None:
		"""Apply transition effect."""
		# For table view, we just update the selection state
		if 'shared_selections' in transition_data:
			self.selected_ids = set(transition_data['shared_selections'])
			self._update_selection()
	
	def _handle_selection(self):
		"""Handle table selection changes."""
		selected_ids = set()
		for item in self.table.selectedItems():
			node_id = item.data(Qt.ItemDataRole.UserRole)
			if node_id:
				selected_ids.add(node_id)
		
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
	
	def _update_selection(self):
		"""Update table selection state."""
		self.table.clearSelection()
		for row in range(self.table.rowCount()):
			item = self.table.item(row, 0)
			if item and item.data(Qt.ItemDataRole.UserRole) in self.selected_ids:
				self.table.selectRow(row)

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
		
		# Draw edges first (so they appear under nodes)
		for edge in edges:
			self._create_edge(edge)
		
		# Draw nodes
		for node in nodes:
			self._create_node(node)
		
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
		ViewType.ARC: ArcViewWidget
	}
	widget_class = view_map.get(view_type)
	if not widget_class:
		raise ValueError(f"No widget implementation for view type: {view_type}")
	return widget_class(parent)