from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QPixmap
from typing import Dict, List, Set, Optional, Tuple
import math
import time
from albumexplore.gui.gui_logging import gui_logger

from ..models import VisualNode, VisualEdge
from ..state import ViewState, ViewType
from .base_view import BaseView
from ..lod_system import LODSystem, ClusterManager
from ..cluster_engine import ClusterEngine, ClusterNode
from ..performance_optimizer import PerformanceOptimizer, PerformanceMetrics

class SpatialGrid:
	def __init__(self, cell_size: float = 100.0):
		self.cell_size = cell_size
		self.grid: Dict[Tuple[int, int], List[VisualNode]] = {}
		
	def clear(self):
		self.grid.clear()
		
	def add_node(self, node: VisualNode):
		cell_x = int(node.data.get('x', 0) // self.cell_size)
		cell_y = int(node.data.get('y', 0) // self.cell_size)
		key = (cell_x, cell_y)
		if key not in self.grid:
			self.grid[key] = []
		self.grid[key].append(node)
		
	def get_nearby_nodes(self, x: float, y: float, radius: float) -> List[VisualNode]:
		cell_x = int(x // self.cell_size)
		cell_y = int(y // self.cell_size)
		radius_cells = int(math.ceil(radius / self.cell_size))
		
		nearby = []
		for dx in range(-radius_cells, radius_cells + 1):
			for dy in range(-radius_cells, radius_cells + 1):
				key = (cell_x + dx, cell_y + dy)
				if key in self.grid:
					nearby.extend(self.grid[key])
		return nearby

class EnhancedNetworkView(BaseView):
	"""Enhanced network visualization with LOD and clustering support."""
	def __init__(self, parent=None):
		super().__init__(parent)
		gui_logger.debug("EnhancedNetworkView initialized")
		self.view_state = ViewState(ViewType.NETWORK)
		
		# Enable Qt optimizations
		self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
		self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
		self.setAutoFillBackground(True)
		
		# Initialize systems
		self.lod_system = LODSystem()
		self.cluster_manager = ClusterManager(self.lod_system)
		self.cluster_engine = ClusterEngine()
		self.spatial_grid = SpatialGrid()
		
		# Double buffering setup with improved buffer management
		self._current_buffer = None
		self._next_buffer = None
		self._buffer_dirty = True
		self._buffer_swap_pending = False
		self.needs_full_redraw = True
		
		# Add update control with frame synchronization
		self._update_timer = QTimer(self)
		self._update_timer.setSingleShot(True)
		self._update_timer.setInterval(50)  # Reduce update frequency
		self._update_timer.timeout.connect(self._handle_update)
		self._update_pending = False
		
		# Frame timing control
		self._last_frame_time = time.time()
		self._frame_interval = 1.0 / 30.0  # Target 30 FPS
		
		# Optimization flags
		self.enable_antialiasing = True
		self.enable_edge_bundling = False
		
		# View state
		self.viewport_scale = 1.0
		self.viewport_x = 0
		self.viewport_y = 0
		self.dragging = False
		self.last_mouse_pos = None
		
		# Data state
		self.nodes: List[VisualNode] = []
		self.edges: List[VisualEdge] = []
		self.visible_nodes: List[VisualNode] = []
		self.visible_edges: List[VisualEdge] = []
		self.clusters: Dict[int, List[ClusterNode]] = {}
		
		# Visual properties
		self.node_colors = {
			'default': QColor('#4a90e2'),
			'selected': QColor('#e24a4a'),
			'cluster': QColor('#90a4ae')
		}

	def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
		"""Update visualization data with performance tracking."""
		gui_logger.debug(f"Updating data: {len(nodes)} nodes, {len(edges)} edges")
		self.start_performance_measure('update')
		
		super().update_data(nodes, edges)  # Call parent's update_data first
		
		try:
			# Create hierarchical clusters
			self.clusters = self.cluster_engine.create_hierarchical_clusters(nodes, edges)
			# Update visible elements based on current scale
			self._update_visible_elements()
			# Update spatial grid
			self.spatial_grid.clear()
			for node in self.visible_nodes:
				self.spatial_grid.add_node(node)
			# Initial layout
			self.adjust_viewport_to_content()
			self.needs_full_redraw = True
		except Exception as e:
			gui_logger.error(f"Error in update_data: {str(e)}")
			self.clusters = {}
			self.visible_nodes = nodes
			self.visible_edges = edges
		
		update_time = self.end_performance_measure('update')
		self.take_performance_snapshot({
			'update_time': update_time,
			'cluster_count': len(self.clusters)
		})
		
		self.update()

	def _update_visible_elements(self) -> None:
		"""Update visible nodes and edges based on LOD level."""
		try:
			# Get visible elements from cluster manager
			self.visible_nodes, self.visible_edges = self.cluster_manager.update_clusters(
				self.nodes, self.edges, self.viewport_scale)
			
			# Update cluster visibility based on current LOD level
			level = self.lod_system.get_level_for_scale(self.viewport_scale)
			if level.level > 0 and level.level in self.clusters:
				visible_clusters = self.clusters[level.level]
				# Add cluster representations to visible nodes
				for cluster in visible_clusters:
					if len(cluster.nodes) > 1:
						cluster_node = VisualNode(
							id=cluster.id,
							label=f"Cluster ({len(cluster.nodes)})",
							size=math.sqrt(len(cluster.nodes)) * 10,
							color=self.node_colors['cluster'].name(),
							shape='circle',
							data={'x': cluster.center[0], 'y': cluster.center[1],
								  'is_cluster': True, 'members': cluster.nodes}
						)
						self.visible_nodes.append(cluster_node)
		except Exception as e:
			gui_logger.error(f"Error in _update_visible_elements: {str(e)}")
			self.visible_nodes = self.nodes
			self.visible_edges = self.edges

	def update(self) -> None:
		"""Schedule update with frame rate limiting."""
		current_time = time.time()
		if current_time - self._last_frame_time >= self._frame_interval:
			self._buffer_dirty = True
			self._last_frame_time = current_time
			super().update()

	def _handle_update(self) -> None:
		"""Handle scheduled update."""
		self._update_pending = False
		self._buffer_dirty = True
		super().update()

	def paintEvent(self, event) -> None:
		"""Render with improved buffer swapping."""
		if not self.nodes:
			return

		self.start_performance_measure('frame')
		
		try:
			if self._buffer_dirty or not self._current_buffer:
				# Create new buffer only if needed
				if not self._next_buffer or self._next_buffer.size() != self.size():
					self._next_buffer = QPixmap(self.size())
				self._next_buffer.fill(Qt.GlobalColor.transparent)
				self._paint_to_buffer(self._next_buffer)
				
				# Swap buffers only when new content is ready
				old_buffer = self._current_buffer
				self._current_buffer = self._next_buffer
				self._next_buffer = old_buffer
				self._buffer_dirty = False
			
			# Draw current buffer
			painter = QPainter(self)
			if self._current_buffer:
				painter.drawPixmap(0, 0, self._current_buffer)
			painter.end()
			
		finally:
			frame_time = self.end_performance_measure('frame')
			self.take_performance_snapshot({
				'frame_time': frame_time,
				'viewport_scale': self.viewport_scale,
				'visible_node_count': len(self.visible_nodes),
				'visible_edge_count': len(self.visible_edges),
				'memory_usage': self._current_buffer.size().width() * 
							   self._current_buffer.size().height() * 4 if self._current_buffer else 0
			})
		
	def _paint_to_buffer(self, buffer: QPixmap) -> None:
		"""Paint content to buffer with optimized rendering."""
		if not buffer:
			return

		painter = QPainter(buffer)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		try:
			# Clear buffer with composition mode
			painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
			painter.fillRect(buffer.rect(), Qt.GlobalColor.transparent)
			painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
			
			# Apply viewport transformation
			painter.translate(self.width()/2, self.height()/2)
			painter.scale(self.viewport_scale, self.viewport_scale)
			painter.translate(self.viewport_x / self.viewport_scale,
							 self.viewport_y / self.viewport_scale)
			
			# Get visible area for culling
			view_rect = QRectF(
				-self.width()/(2*self.viewport_scale) - self.viewport_x/self.viewport_scale,
				-self.height()/(2*self.viewport_scale) - self.viewport_y/self.viewport_scale,
				self.width()/self.viewport_scale,
				self.height()/self.viewport_scale
			)
			
			# Draw edges in batches using QPainterPath
			path = QPainterPath()
			for edge in self.visible_edges:
				source = next((n for n in self.visible_nodes if n.id == edge.source), None)
				target = next((n for n in self.visible_nodes if n.id == edge.target), None)
				if source and target:
					path.moveTo(source.data.get('x', 0), source.data.get('y', 0))
					path.lineTo(target.data.get('x', 0), target.data.get('y', 0))
			
			# Draw all edges at once
			painter.setPen(QPen(QColor('#cccccc')))
			painter.drawPath(path)
			
			# Draw nodes that are in view
			for node in self.visible_nodes:
				x = node.data.get('x', 0)
				y = node.data.get('y', 0)
				
				if not view_rect.contains(QPointF(x, y)):
					continue
					
				size = node.size
				if node.data.get('is_cluster', False):
					painter.setBrush(QBrush(self.node_colors['cluster']))
					painter.setPen(QPen(self.node_colors['cluster'].darker(120)))
				else:
					color = self.node_colors['selected'] if node.id in self.selected_ids else self.node_colors['default']
					painter.setBrush(QBrush(color))
					painter.setPen(QPen(color.darker(120)))
				
				painter.drawEllipse(QPointF(x, y), size, size)
				
				if self.viewport_scale > 1.5:
					painter.setPen(QPen(Qt.GlobalColor.black))
					painter.drawText(x + size + 5, y, node.label)
		finally:
			painter.end()

	def render_to_pixmap(self) -> QPixmap:
		"""Render the network to a pixmap for double buffering."""
		pixmap = QPixmap(self.size())
		pixmap.fill(Qt.GlobalColor.white)
		painter = QPainter(pixmap)
		
		if self.enable_antialiasing:
			painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Apply viewport transformation
		painter.translate(self.width()/2, self.height()/2)
		painter.scale(self.viewport_scale, self.viewport_scale)
		painter.translate(self.viewport_x / self.viewport_scale,
						 self.viewport_y / self.viewport_scale)
		
		# Get visible area for culling
		view_rect = QRectF(
			-self.width()/(2*self.viewport_scale) - self.viewport_x/self.viewport_scale,
			-self.height()/(2*self.viewport_scale) - self.viewport_y/self.viewport_scale,
			self.width()/self.viewport_scale,
			self.height()/self.viewport_scale
		)
		
		# Draw edges in batches using QPainterPath
		path = QPainterPath()
		for edge in self.visible_edges:
			source = next((n for n in self.visible_nodes if n.id == edge.source), None)
			target = next((n for n in self.visible_nodes if n.id == edge.target), None)
			if source and target:
				path.moveTo(source.data.get('x', 0), source.data.get('y', 0))
				path.lineTo(target.data.get('x', 0), target.data.get('y', 0))
		
		# Draw all edges at once
		painter.setPen(QPen(QColor('#cccccc')))
		painter.drawPath(path)
		
		# Draw nodes that are in view
		for node in self.visible_nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			
			if not view_rect.contains(QPointF(x, y)):
				continue
				
			size = node.size
			if node.data.get('is_cluster', False):
				painter.setBrush(QBrush(self.node_colors['cluster']))
				painter.setPen(QPen(self.node_colors['cluster'].darker(120)))
			else:
				color = self.node_colors['selected'] if node.id in self.selected_ids else self.node_colors['default']
				painter.setBrush(QBrush(color))
				painter.setPen(QPen(color.darker(120)))
			
			painter.drawEllipse(QPointF(x, y), size, size)
			
			if self.viewport_scale > 1.5:
				painter.setPen(QPen(Qt.GlobalColor.black))
				painter.drawText(x + size + 5, y, node.label)
		
		painter.end()
		return pixmap

	def mousePressEvent(self, event) -> None:
		"""Handle mouse press with spatial grid optimization."""
		if event.button() == Qt.MouseButton.LeftButton:
			pos = self._get_scene_pos(event.position())
			
			# Use spatial grid for faster node lookup
			nearby_nodes = self.spatial_grid.get_nearby_nodes(pos[0], pos[1], 20)
			
			for node in nearby_nodes:
				x = node.data.get('x', 0)
				y = node.data.get('y', 0)
				size = node.size
				
				if math.sqrt((pos[0] - x)**2 + (pos[1] - y)**2) <= size:
					if node.data.get('is_cluster', False):
						self.selected_ids = {n.id for n in node.data['members']}
					else:
						self.selected_ids = {node.id}
					self.needs_full_redraw = True
					self.update()
					return
			
			# Start dragging if no node hit
			self.dragging = True
			self.last_mouse_pos = event.position()
			self.selected_ids.clear()
			self.needs_full_redraw = True
			self.update()

	def mouseReleaseEvent(self, event) -> None:
		"""Handle mouse release."""
		if event.button() == Qt.MouseButton.LeftButton:
			self.dragging = False
			self.last_mouse_pos = None

	def mouseMoveEvent(self, event) -> None:
		"""Handle mouse movement with smooth updates."""
		if self.dragging and self.last_mouse_pos:
			dx = event.position().x() - self.last_mouse_pos.x()
			dy = event.position().y() - self.last_mouse_pos.y()
			self.viewport_x += dx
			self.viewport_y += dy
			self.last_mouse_pos = event.position()
			self.needs_full_redraw = True
			self.update()

	def wheelEvent(self, event) -> None:
		"""Handle zooming with smooth updates."""
		factor = 1.1 if event.angleDelta().y() > 0 else 0.9
		self.viewport_scale *= factor
		self.viewport_scale = max(0.1, min(5.0, self.viewport_scale))
		
		self._update_visible_elements()
		self.needs_full_redraw = True
		self.update()

	def _get_scene_pos(self, screen_pos) -> tuple:
		"""Convert screen coordinates to scene coordinates."""
		x = (screen_pos.x() - self.width()/2) / self.viewport_scale - self.viewport_x / self.viewport_scale
		y = (screen_pos.y() - self.height()/2) / self.viewport_scale - self.viewport_y / self.viewport_scale
		return (x, y)

	def adjust_viewport_to_content(self) -> None:
		"""Adjust viewport to fit all visible content."""
		if not self.visible_nodes:
			return
			
		# Calculate bounds
		xs = [node.data.get('x', 0) for node in self.visible_nodes]
		ys = [node.data.get('y', 0) for node in self.visible_nodes]
		
		min_x, max_x = min(xs), max(xs)
		min_y, max_y = min(ys), max(ys)
		
		# Calculate scale to fit content
		width = max_x - min_x + 100
		height = max_y - min_y + 100
		
		scale_x = self.width() / width if width > 0 else 1
		scale_y = self.height() / height if height > 0 else 1
		self.viewport_scale = min(scale_x, scale_y, 2.0)
		
		# Center content
		self.viewport_x = -(min_x + max_x) * self.viewport_scale / 2
		self.viewport_y = -(min_y + max_y) * self.viewport_scale / 2

	def keyPressEvent(self, event) -> None:
		"""Handle key press events."""
		# Let base class handle Ctrl+C and Ctrl+P
		super().keyPressEvent(event)
