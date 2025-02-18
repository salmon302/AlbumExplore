from PyQt6.QtWidgets import (
	QApplication, QWidget, QVBoxLayout, QHBoxLayout,
	QLabel, QLineEdit, QPushButton, QDialog, QFormLayout, QSpinBox,
	QToolTip, QMenu)
from PyQt6.QtCore import Qt, QPointF, QTimer, QElapsedTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QMouseEvent, QPaintEvent, QWheelEvent, QContextMenuEvent
from enum import Enum
from typing import Set, List, Dict, Any, Tuple, Optional
from ..models import Point
from ..layouts.custom_layouts import circular_layout, hierarchical_layout, radial_layout
import time
from ..info_display import InfoDisplay
import math
import random
import numpy as np
from ..physics_system import PhysicsSystem
from ..cluster_engine import ClusterEngine

from .base_view import BaseView
from ..models import VisualNode, VisualEdge
from ..state import ViewType, ViewState
from ..layout import ForceDirectedLayout, ForceParams


class DataPointsDialog(QDialog):

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Select Data Points")
		self.layout = QFormLayout(self)

		self.data_points_spinbox = QSpinBox()
		self.data_points_spinbox.setRange(1, 10000)  # Set reasonable range
		self.data_points_spinbox.setValue(100)  # Default value
		self.layout.addRow("Number of Data Points:", self.data_points_spinbox)

		self.buttons = QHBoxLayout()
		self.ok_button = QPushButton("OK")
		self.cancel_button = QPushButton("Cancel")
		self.buttons.addWidget(self.ok_button)
		self.buttons.addWidget(self.cancel_button)
		self.layout.addRow(self.buttons)

		self.ok_button.clicked.connect(self.accept)
		self.cancel_button.clicked.connect(self.reject)

	def get_data_points(self):
		return self.data_points_spinbox.value()

class QuadTree:
	def __init__(self, bounds, capacity=4):
		self.bounds = bounds  # (x, y, width, height)
		self.capacity = capacity
		self.points = []
		self.divided = False
		self.children = {}

	def subdivide(self):
		x, y, w, h = self.bounds
		w_half = w / 2
		h_half = h / 2
		
		self.children = {
			'nw': QuadTree((x, y, w_half, h_half)),
			'ne': QuadTree((x + w_half, y, w_half, h_half)),
			'sw': QuadTree((x, y + h_half, w_half, h_half)),
			'se': QuadTree((x + w_half, y + h_half, w_half, h_half))
		}
		self.divided = True

	def insert(self, point):
		if not self._contains(point):
			return False
			
		if len(self.points) < self.capacity and not self.divided:
			self.points.append(point)
			return True
			
		if not self.divided:
			self.subdivide()
			
		return any(child.insert(point) for child in self.children.values())

	def query_range(self, range_bounds):
		found = []
		if not self._intersects(range_bounds):
			return found
			
		for point in self.points:
			if self._point_in_range(point, range_bounds):
				found.append(point)
				
		if self.divided:
			for child in self.children.values():
				found.extend(child.query_range(range_bounds))
				
		return found

	def _contains(self, point):
		x, y, w, h = self.bounds
		px, py = point[1], point[2]  # Assuming point is (id, x, y)
		return (x <= px <= x + w and y <= py <= y + h)

	def _intersects(self, range_bounds):
		x1, y1, w1, h1 = self.bounds
		x2, y2, w2, h2 = range_bounds
		return not (x1 + w1 < x2 or x2 + w2 < x1 or
				   y1 + h1 < y2 or y2 + h2 < y1)

	def _point_in_range(self, point, range_bounds):
		x, y, w, h = range_bounds
		px, py = point[1], point[2]
		return (x <= px <= x + w and y <= py <= y + h)

class NetworkView(BaseView):
	"""Force-directed network visualization."""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.view_state = ViewState(ViewType.NETWORK)
		self.node_radius = 25
		self.setMinimumSize(800, 600)
		
		# Add path highlighting state
		self.highlighted_path = set()
		self.path_source = None
		self.path_target = None
		self.tooltip_text = None
		self.tooltip_pos = None
		
		# Add tooltip timer
		self.tooltip_timer = QTimer(self)
		self.tooltip_timer.setSingleShot(True)
		self.tooltip_timer.timeout.connect(self._show_tooltip)
		
		self.physics_system = PhysicsSystem()
		self.cluster_engine = ClusterEngine()
		self.search_text = ""
		self.filtered_nodes = set()
		self.show_clusters = True
		self.cluster_boundaries = []
		
		# Add search box
		self.search_layout = QHBoxLayout()
		self.search_input = QLineEdit()
		self.search_input.setPlaceholderText("Search nodes...")
		self.search_input.textChanged.connect(self._handle_search)
		self.search_layout.addWidget(self.search_input)
		
		main_layout = QVBoxLayout(self)
		main_layout.addLayout(self.search_layout)
		
		# Initialize layout timer with slower updates
		self.layout_timer = QTimer(self)
		self.layout_timer.timeout.connect(self.update_layout)
		self.layout_timer.setInterval(50)  # Reduce update frequency
		self.layout_iterations = 0
		self.max_iterations = 80  # Reduced max iterations
		
		# Add double buffering
		self.setProperty("paintOnScreen", False)
		self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)
		self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
		self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
		
		# Improve buffer management
		self._paint_buffer = None
		self._buffer_dirty = True
		self._buffer_lock = False
		self._cleanup_scheduled = False
		
		# Pre-allocate colors and pens
		self._regular_node_color = QColor('#4a90e2')
		self._selected_node_color = QColor('#e24a4a')
		self._regular_node_pen = QPen(self._regular_node_color.darker(120))
		self._selected_node_pen = QPen(self._selected_node_color.darker(120))
		self._regular_node_brush = QBrush(self._regular_node_color)
		self._selected_node_brush = QBrush(self._selected_node_color)
		
		# Initialize data structures
		self.nodes = []
		self.edges = []
		self.spatial_index = QuadTree((0, 0, 1000, 1000))
		self._edge_batches = {}
		self._node_lookup = {}
		self._visible_nodes_cache = {}
		self._edge_batches_cache = {}
		
		# Initialize performance monitoring
		self.frame_times = []
		self.layout_times = []
		self.render_times = []
		self.grid_times = []
		self.edge_times = []
		self.force_times = []
		self.apply_times = []
		self.max_samples = 60
		
		# Initialize timers
		self.last_frame_time = QElapsedTimer()
		self.last_render_time = QElapsedTimer()
		self.last_frame_time.start()
		self.last_render_time.start()
		
		self.show_debug = True
		
		# Viewport state
		self.viewport_x = 0
		self.viewport_y = 0
		self.viewport_scale = 1.2
		self.dragging = False
		self.last_mouse_pos = None
		
		# Initialize info display
		self.info_display = InfoDisplay()
		self.selected_node_info = None

	def get_data_points_selection(self):
		dialog = DataPointsDialog(self)
		result = dialog.exec()
		if result == QDialog.DialogCode.Accepted:
			return dialog.get_data_points()
		else:
			return None

	def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
		"""Update visualization data."""
		print(f"\nDEBUG: NetworkView.update_data entry")
		print(f"DEBUG: Initial nodes: {len(nodes)}, edges: {len(edges)}")
		
		num_data_points = self.get_data_points_selection()
		if num_data_points is None:
			print("DEBUG: User cancelled data points selection")
			return

		print(f"DEBUG: Selected {num_data_points} data points")
		
		self.nodes = nodes[:num_data_points]
		self.edges = edges
		self._node_lookup = {node.id: node for node in nodes}
		
		print(f"DEBUG: Node lookup created with {len(self._node_lookup)} entries")
		print(f"DEBUG: First node data sample: {self.nodes[0].data if self.nodes else 'No nodes'}")
		
		# Pre-compute edge batches by color
		self._edge_batches.clear()
		for edge in edges:
			if edge.color not in self._edge_batches:
				self._edge_batches[edge.color] = []
			self._edge_batches[edge.color].append(edge)
		
		print(f"DEBUG: Edge batches created: {len(self._edge_batches)} colors")
		
		# Initialize positions in a circular layout
		radius = min(self.width(), self.height()) * 0.3
		angle_step = 2 * math.pi / len(nodes) if nodes else 0
		
		for i, node in enumerate(nodes):
			if not isinstance(node.data, dict):
				node.data = {}
			if not hasattr(node, 'pos'):
				node.pos = {}
			
			angle = i * angle_step
			x = radius * math.cos(angle)
			y = radius * math.sin(angle)
			node.data['x'] = x
			node.data['y'] = y
			node.pos['x'] = x
			node.pos['y'] = y
		
		self.adjust_viewport_to_content()
		self.layout_iterations = 0
		self.layout_timer.start()
		super().update_data(nodes, edges)



	def start_layout(self) -> None:
		"""Start the force-directed layout animation."""
		self.layout_iterations = 0
		self.layout_timer.start(16)  # ~60 FPS

	def update(self) -> None:
		"""Override update to mark buffer as dirty."""
		self._buffer_dirty = True
		super().update()

	def paintEvent(self, event: QPaintEvent) -> None:
		"""Handle paint events with improved buffer management."""
		if not self.nodes or self._buffer_lock:
			return

		try:
			self._buffer_lock = True
			
			# Create or update buffer if needed
			if self._buffer_dirty or not self._paint_buffer or self._paint_buffer.size() != self.size():
				if self._paint_buffer:
					self._paint_buffer = None
				self._paint_buffer = QPixmap(self.size())
				self._paint_buffer.fill(Qt.GlobalColor.transparent)
				self._paint_to_buffer()
				self._buffer_dirty = False

			# Paint from buffer to widget
			painter = QPainter(self)
			painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
			painter.drawPixmap(0, 0, self._paint_buffer)
			painter.end()
			
		finally:
			self._buffer_lock = False

	def _paint_to_buffer(self) -> None:
		"""Paint content to buffer."""
		if not self._paint_buffer:
			return

		self.start_performance_measure('frame')
		
		painter = QPainter(self._paint_buffer)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Clear the buffer
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
		painter.fillRect(self._paint_buffer.rect(), Qt.GlobalColor.transparent)
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
		
		try:
			painter.save()
			painter.translate(self.width()/2, self.height()/2)
			painter.scale(self.viewport_scale, self.viewport_scale)
			painter.translate(self.viewport_x / self.viewport_scale, 
							self.viewport_y / self.viewport_scale)
			
			# Update caches if empty
			if not self._visible_nodes_cache:
				print("DEBUG: Updating empty visible nodes cache")
				self._update_visible_nodes()
			if not self._edge_batches_cache:
				print("DEBUG: Updating empty edge batches cache")
				self._update_edge_batches()
			
			print(f"DEBUG: Cache status after potential update - Nodes: {len(self._visible_nodes_cache)}, Edges: {len(self._edge_batches_cache)}")
			
			# Draw edges
			if self._edge_batches_cache:
				line_width = max(1, int(1.0 / self.viewport_scale))
				edge_pen = QPen()
				edge_pen.setWidth(line_width)
				
				for color, edges in self._edge_batches_cache.items():
					edge_pen.setColor(QColor(color))
					painter.setPen(edge_pen)
					for sx, sy, tx, ty in edges:
						painter.drawLine(int(sx), int(sy), int(tx), int(ty))
			
			# Draw cluster boundaries if enabled
			if self.show_clusters and self.cluster_boundaries:
				cluster_pen = QPen(QColor(100, 100, 100, 80))
				cluster_pen.setWidth(2)
				painter.setPen(cluster_pen)
				
				for boundary in self.cluster_boundaries:
					painter.drawPath(boundary)
			
			# Draw nodes
			node_pen_width = max(1, int(1.0 / self.viewport_scale))
			self._regular_node_pen.setWidth(node_pen_width)
			self._selected_node_pen.setWidth(node_pen_width)
			
			# Regular nodes
			painter.setPen(self._regular_node_pen)
			painter.setBrush(self._regular_node_brush)
			
			# Highlight searched nodes
			if self.search_text:
				highlight_pen = QPen(QColor('#ffd700'))
				highlight_pen.setWidth(3)
				painter.setPen(highlight_pen)
				painter.setBrush(Qt.BrushStyle.NoBrush)
				
				for node_id in self.filtered_nodes:
					if node_id in self._visible_nodes_cache:
						x, y, size = self._visible_nodes_cache[node_id]
						painter.drawEllipse(QPointF(x, y), size + 5, size + 5)
			
			for node_id, (x, y, size) in self._visible_nodes_cache.items():
				if node_id not in self.selected_ids:
					painter.drawEllipse(QPointF(x, y), size, size)
			
			# Selected nodes
			if self.selected_ids:
				painter.setPen(self._selected_node_pen)
				painter.setBrush(self._selected_node_brush)
				
				for node_id in self.selected_ids:
					if node_id in self._visible_nodes_cache:
						x, y, size = self._visible_nodes_cache[node_id]
						painter.drawEllipse(QPointF(x, y), size, size)

			
			# Draw labels only when zoomed in and for visible nodes
			if self.viewport_scale > 1.5:
				painter.setPen(QPen(Qt.GlobalColor.black))
				font = painter.font()
				font.setPointSizeF(8 / self.viewport_scale)
				painter.setFont(font)
				
				for node_id, (x, y, size) in self._visible_nodes_cache.items():
					node = self._node_lookup.get(node_id)
					if node and hasattr(node, 'label'):
						text_rect = painter.fontMetrics().boundingRect(str(node.label))
						text_rect.moveCenter(QPointF(x + size + text_rect.width()/2 + 5, y).toPoint())
						painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(node.label))
			
			painter.restore()
			
			# Draw debug info if enabled
			if self.show_debug:
				self._draw_debug_info(painter)
				
		finally:
			frame_time = self.end_performance_measure('frame')
			
			# Take performance snapshot with all metrics
			self.take_performance_snapshot({
				'frame_time': frame_time,
				'layout_time': sum(self.layout_times) / max(1, len(self.layout_times)) * 1000,
				'render_time': sum(self.render_times) / max(1, len(self.render_times)),
				'grid_time': sum(self.grid_times) / max(1, len(self.grid_times)) * 1000,
				'edge_time': sum(self.edge_times) / max(1, len(self.edge_times)) * 1000,
				'force_time': sum(self.force_times) / max(1, len(self.force_times)) * 1000,
				'apply_time': sum(self.apply_times) / max(1, len(self.apply_times)) * 1000,
				'viewport_scale': self.viewport_scale,
				'iteration': self.layout_iterations
			})
			
			painter.end()


	def _update_spatial_index(self):
		"""Update the spatial index with current node positions."""
		bounds = self.calculate_graph_boundaries()
		if bounds == (0, 0, 0, 0):
			self.spatial_index = QuadTree((0, 0, 1000, 1000))
			return

		min_x, max_x, min_y, max_y = bounds
		width = max_x - min_x
		height = max_y - min_y
		self.spatial_index = QuadTree((min_x, min_y, width, height))

		for node in self.nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			self.spatial_index.insert((node.id, x, y))

	def mousePressEvent(self, event: QMouseEvent) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			x = (event.position().x() - self.width()/2) / self.viewport_scale - self.viewport_x / self.viewport_scale
			y = (event.position().y() - self.height()/2) / self.viewport_scale - self.viewport_y / self.viewport_scale
			
			# Calculate view bounds
			scale_inv = 1.0 / self.viewport_scale
			half_width = self.width() * 0.5 * scale_inv
			half_height = self.height() * 0.5 * scale_inv
			viewport_x_scaled = self.viewport_x * scale_inv
			viewport_y_scaled = self.viewport_y * scale_inv
			
			view_bounds = (
				-half_width - viewport_x_scaled - 50,  # left
				half_width - viewport_x_scaled + 50,   # right
				-half_height - viewport_y_scaled - 50, # top
				half_height - viewport_y_scaled + 50   # bottom
			)
			
			# Use spatial index for hit detection within view bounds
			if (view_bounds[0] <= x <= view_bounds[1] and 
				view_bounds[2] <= y <= view_bounds[3]):
				nearby_nodes = self.spatial_index.query_range((x - 10, y - 10, 20, 20))
				for node_id, node_x, node_y in nearby_nodes:
					if node_id not in self._node_lookup:
						continue
						
					node = self._node_lookup[node_id]
					size = getattr(node, 'size', 10)
					
					if math.sqrt((x - node_x)**2 + (y - node_y)**2) <= size:
						self.selected_ids = {node.id}
						self.selected_node_info = self.info_display.get_node_details(node)
						self.update()
						return
			
			self.selected_ids = set()
			self.selected_node_info = None
			self.update()
			
			self.dragging = True
			self.last_mouse_pos = event.position()


	def mouseReleaseEvent(self, event: QMouseEvent) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			self.dragging = False
			self.last_mouse_pos = None

	def mouseMoveEvent(self, event: QMouseEvent) -> None:
		if self.dragging and self.last_mouse_pos:
			dx = event.position().x() - self.last_mouse_pos.x()
			dy = event.position().y() - self.last_mouse_pos.y()
			self.viewport_x += dx
			self.viewport_y += dy
			self.last_mouse_pos = event.position()
			self.update()
		else:
			# Handle tooltips
			x = (event.position().x() - self.width()/2) / self.viewport_scale - self.viewport_x / self.viewport_scale
			y = (event.position().y() - self.height()/2) / self.viewport_scale - self.viewport_y / self.viewport_scale
			
			node = self._find_node_at_position(x, y)
			if node:
				self.tooltip_text = self._get_node_tooltip(node)
				self.tooltip_pos = event.position()
				self.tooltip_timer.start(500)  # Show tooltip after 500ms
			else:
				self.tooltip_timer.stop()
				self.tooltip_text = None
			self.update()

	def wheelEvent(self, event: QWheelEvent) -> None:
		factor = 1.1 if event.angleDelta().y() > 0 else 0.9
		self.viewport_scale *= factor
		self.viewport_scale = max(0.1, min(5.0, self.viewport_scale))
		self.update()

	def calculate_graph_boundaries(self):
		"""Calculate the min/max coordinates of all nodes."""
		if not self.nodes:
			return 0, 0, 0, 0
			
		min_x = min(node.data.get('x', 0) for node in self.nodes)
		max_x = max(node.data.get('x', 0) for node in self.nodes)
		min_y = min(node.data.get('y', 0) for node in self.nodes)
		max_y = max(node.data.get('y', 0) for node in self.nodes)
		
		return min_x, max_x, min_y, max_y

	def adjust_viewport_to_content(self):
		"""Adjust viewport scale and position to fit all nodes."""
		min_x, max_x, min_y, max_y = self.calculate_graph_boundaries()
		
		# Calculate content dimensions
		content_width = max_x - min_x + 100  # Add padding
		content_height = max_y - min_y + 100
		
		# Calculate scale to fit content
		scale_x = self.width() / content_width if content_width > 0 else 1
		scale_y = self.height() / content_height if content_height > 0 else 1
		self.viewport_scale = min(scale_x, scale_y, 2.0)  # Cap at 2.0
		
		# Center the content
		self.viewport_x = -(min_x + max_x) * self.viewport_scale / 2
		self.viewport_y = -(min_y + max_y) * self.viewport_scale / 2

	def keyPressEvent(self, event):
		"""Handle key press events."""
		if event.key() == Qt.Key.Key_D:
			self.show_debug = not self.show_debug
			self.update()
		else:
			# Let base class handle Ctrl+C and Ctrl+P
			super().keyPressEvent(event)

	def copy_debug_info(self):
		"""Copy detailed debug information to clipboard."""
		try:
			# Calculate metrics with safety checks
			if self.frame_times:
				valid_times = [t for t in self.frame_times if 0 < t < 1000]  # Filter out invalid times
				if valid_times:
					avg_frame_time = sum(valid_times) / len(valid_times)
					fps = 1000 / avg_frame_time if avg_frame_time > 0 else 0
				else:
					avg_frame_time = 0
					fps = 0
			else:
				avg_frame_time = 0
				fps = 0
				
			# Calculate other timing metrics safely
			avg_layout_time = sum(self.layout_times) / max(1, len(self.layout_times))
			avg_grid_time = sum(self.grid_times) / max(1, len(self.grid_times))
			avg_edge_time = sum(self.edge_times) / max(1, len(self.edge_times))
			avg_force_time = sum(self.force_times) / max(1, len(self.force_times))
			avg_apply_time = sum(self.apply_times) / max(1, len(self.apply_times))
			avg_render_time = sum(self.render_times) / max(1, len(self.render_times))
			
			debug_info = [
				"Network Graph Performance Report",
				"============================",
				"",
				f"Performance Metrics:",
				f"- FPS: {fps:.1f}",
				f"- Frame Time: {avg_frame_time:.1f}ms",
				f"- Layout Time: {avg_layout_time*1000:.1f}ms",
				f"- Grid Time: {avg_grid_time*1000:.1f}ms",
				f"- Edge Time: {avg_edge_time*1000:.1f}ms",
				f"- Force Time: {avg_force_time*1000:.1f}ms",
				f"- Apply Time: {avg_apply_time*1000:.1f}ms",
				f"- Render Time: {avg_render_time:.1f}ms",
				"",
				f"Graph Statistics:",
				f"- Total Nodes: {len(self.nodes)}",
				f"- Total Edges: {len(self.edges)}",
				f"- Graph Density: {len(self.edges)/(len(self.nodes)**2):.3f}",
				"",
				f"Layout Parameters:",
				f"- Max Iterations: {self.max_iterations}",
				f"- Current Iteration: {self.layout_iterations}",
				f"- Viewport Scale: {self.viewport_scale:.2f}x",
				"",
				f"Memory Estimation:",
				f"- Per Node: ~200 bytes",
				f"- Per Edge: ~100 bytes",
				f"- Total: ~{(len(self.nodes) * 200 + len(self.edges) * 100) / 1024:.1f}KB",
				"",
				"Generated at: " + time.strftime("%Y-%m-%d %H:%M:%S")
			]
			
			clipboard = QApplication.clipboard()
			clipboard.setText("\n".join(debug_info))
			print("Debug information copied to clipboard")
		except Exception as e:
			print(f"Error copying debug info: {str(e)}")

	def _draw_debug_info(self, painter: QPainter) -> None:
		"""Draw performance debug information overlay."""
		if not self.show_debug:
			return

		painter.resetTransform()
		painter.setPen(Qt.GlobalColor.white)
		painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
		
		# Get performance report
		report = self.performance_debugger.get_performance_report()
		debug_info = report.split('\n')
		
		margin = 10
		line_height = 20
		panel_width = 200
		panel_height = len(debug_info) * line_height + margin * 2
		
		painter.drawRect(margin, margin, panel_width, panel_height)
		
		for i, text in enumerate(debug_info):
			painter.drawText(
				margin * 2,
				margin * 2 + i * line_height,
				text
			)


	def update_layout(self) -> None:
		"""Update force-directed layout positions with physics and clustering."""
		if not self.nodes or self.layout_iterations >= self.max_iterations:
			self.layout_timer.stop()
			return
			
		layout_start = time.perf_counter()
		
		# Update physics
		if self.layout_iterations % 5 == 0:  # Update clusters periodically
			self.cluster_boundaries = self.cluster_engine.update_clusters(
				self.nodes, self.edges, {
					node.id: Point(node.data.get('x', 0), node.data.get('y', 0))
					for node in self.nodes
				}
			)
		
		# Create adaptive force parameters
		params = ForceParams.adaptive(len(self.nodes))
		
		# Initialize layout with adaptive parameters
		layout = ForceDirectedLayout(params)
		max_width = self.width() / 3.0
		max_height = self.height() / 3.0
		
		# Create node lookup and filter edges
		node_ids = {node.id for node in self.nodes}
		valid_edges = [edge for edge in self.edges 
					  if edge.source in node_ids and edge.target in node_ids]
		
		# Process nodes in smaller chunks with proper edge filtering
		chunk_size = 25
		for i in range(0, len(self.nodes), chunk_size):
			chunk = self.nodes[i:i + chunk_size]
			chunk_node_ids = {node.id for node in chunk}
			
			# Only include edges where both source and target are in the current chunk
			chunk_edges = [edge for edge in valid_edges 
						  if edge.source in chunk_node_ids and 
							 edge.target in chunk_node_ids]
			
			try:
				positions = layout.layout(chunk, chunk_edges, max_width * 2, max_height * 2)
				
				# Update positions and invalidate caches
				for node in chunk:
					if node.id in positions:
						pos = positions[node.id]
						x = max(-max_width, min(max_width, pos.x))
						y = max(-max_height, min(max_height, pos.y))
						node.data['x'] = x
						node.data['y'] = y
						node.pos['x'] = x
						node.pos['y'] = y
				
				# Clear caches to force recalculation
				self._visible_nodes_cache.clear()
				self._edge_batches_cache.clear()
				
			except KeyError:
				continue
		
		# Update viewport and spatial index less frequently
		if self.layout_iterations % 100 == 0:
			self.adjust_viewport_to_content()
			self._update_spatial_index()
		
		self.layout_iterations += 1
		layout_time = time.perf_counter() - layout_start
		self.layout_times.append(layout_time)
		if len(self.layout_times) > self.max_samples:
			self.layout_times.pop(0)
		
		self.update()

	def _update_spatial_index(self):
		"""Update the spatial index with current node positions."""
		bounds = self.calculate_graph_boundaries()
		if bounds == (0, 0, 0, 0):
			self.spatial_index = QuadTree((0, 0, 1000, 1000))
			return

		min_x, max_x, min_y, max_y = bounds
		width = max_x - min_x
		height = max_y - min_y
		self.spatial_index = QuadTree((min_x, min_y, width, height))

		for node in self.nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			self.spatial_index.insert((node.id, x, y))




	def _handle_search(self, text: str) -> None:
		"""Handle search text changes and update filtered nodes."""
		self.search_text = text.lower()
		self.filtered_nodes = {
			node.id for node in self.nodes
			if self.search_text in str(node.label).lower()
		}
		self.update()

	def resizeEvent(self, event) -> None:
		"""Handle resize with proper buffer cleanup."""
		super().resizeEvent(event)
		if self._paint_buffer:
			self._paint_buffer = None
		self._buffer_dirty = True
		self.update()

	def hideEvent(self, event) -> None:
		"""Clean up resources when hidden."""
		super().hideEvent(event)
		if not self._cleanup_scheduled:
			self._cleanup_scheduled = True
			QTimer.singleShot(100, self._cleanup_resources)

	def _cleanup_resources(self) -> None:
		"""Clean up buffers and resources."""
		if self._paint_buffer:
			self._paint_buffer = None
		self._buffer_dirty = True
		self._cleanup_scheduled = False

	def _update_visible_nodes(self) -> None:
		"""Update cache of visible nodes with less frequent updates."""
		if not self._buffer_dirty and self._visible_nodes_cache:
			return
		# Only update if bounds have changed significantly
		scale_inv = 1.0 / self.viewport_scale
		half_width = self.width() * 0.5 * scale_inv
		half_height = self.height() * 0.5 * scale_inv
		viewport_x_scaled = self.viewport_x * scale_inv
		viewport_y_scaled = self.viewport_y * scale_inv
		
		new_bounds = (
			-half_width - viewport_x_scaled - 50,
			half_width - viewport_x_scaled + 50,
			-half_height - viewport_y_scaled - 50,
			half_height - viewport_y_scaled + 50
		)
		
		# Check if bounds have changed significantly
		if hasattr(self, '_last_bounds'):
			changes = [abs(new - old) for new, old in zip(new_bounds, self._last_bounds)]
			if max(changes) < 1.0:  # Only update if change is significant
				return
				
		self._last_bounds = new_bounds
		self._visible_nodes_cache.clear()
		
		# Only process nodes within view bounds
		for node in self.nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			
			if (new_bounds[0] <= x <= new_bounds[1] and 
				new_bounds[2] <= y <= new_bounds[3]):
				size = getattr(node, 'size', 10)
				self._visible_nodes_cache[node.id] = (x, y, size)


	def _find_node_at_position(self, x: float, y: float) -> Optional[VisualNode]:
		"""Find node at given position."""
		nearby_nodes = self.spatial_index.query_range((x - 10, y - 10, 20, 20))
		for node_id, node_x, node_y in nearby_nodes:
			if node_id not in self._node_lookup:
				continue
			node = self._node_lookup[node_id]
			size = getattr(node, 'size', 10)
			if math.sqrt((x - node_x)**2 + (y - node_y)**2) <= size:
				return node
		return None

	def _get_node_tooltip(self, node: VisualNode) -> str:
		"""Generate tooltip text for node."""
		details = []
		if hasattr(node, 'label'):
			details.append(f"Label: {node.label}")
		if isinstance(node.data, dict):
			if 'type' in node.data:
				details.append(f"Type: {node.data['type']}")
			if 'weight' in node.data:
				details.append(f"Weight: {node.data['weight']:.2f}")
		return "\n".join(details)

	def _show_tooltip(self) -> None:
		"""Show tooltip at current position."""
		if self.tooltip_text and self.tooltip_pos:
			QToolTip.showText(
				self.mapToGlobal(self.tooltip_pos.toPoint()),
				self.tooltip_text,
				self
			)

	def highlight_path(self, source_id: str, target_id: str) -> None:
		"""Highlight shortest path between two nodes."""
		if not (source_id in self._node_lookup and target_id in self._node_lookup):
			return
			
		self.path_source = source_id
		self.path_target = target_id
		self.highlighted_path = self._find_shortest_path(source_id, target_id)
		self.update()

	def _find_shortest_path(self, source_id: str, target_id: str) -> Set[Tuple[str, str]]:
		"""Find shortest path between two nodes using BFS."""
		if source_id == target_id:
			return set()
			
		queue = [(source_id, [])]
		visited = {source_id}
		edge_lookup = {
			(edge.source, edge.target): edge
			for edge in self.edges
		}
		
		while queue:
			current_id, path = queue.pop(0)
			
			for edge in self.edges:
				if edge.source == current_id and edge.target not in visited:
					if edge.target == target_id:
						return {(s, t) for s, t in path + [(current_id, edge.target)]}
					queue.append((edge.target, path + [(current_id, edge.target)]))
					visited.add(edge.target)
				elif edge.target == current_id and edge.source not in visited:
					if edge.source == target_id:
						return {(s, t) for s, t in path + [(edge.source, current_id)]}
					queue.append((edge.source, path + [(edge.source, current_id)]))
					visited.add(edge.source)
		
		return set()

	def _update_edge_batches(self) -> None:
		"""Update cache of edge batches for rendering."""
		if not self._edge_batches_cache:  # Only update if cache is empty
			edge_start = time.perf_counter()
			
			# Only process edges between visible nodes
			visible_node_ids = set(self._visible_nodes_cache.keys())
			
			for color, edges in self._edge_batches.items():
				batch = []
				for edge in edges:
					if (edge.source in visible_node_ids and 
						edge.target in visible_node_ids):
						source = self._node_lookup[edge.source]
						target = self._node_lookup[edge.target]
						
						sx = source.data.get('x', 0)
						sy = source.data.get('y', 0)
						tx = target.data.get('x', 0)
						ty = target.data.get('y', 0)
						
						batch.append((sx, sy, tx, ty))
				
				if batch:
					self._edge_batches_cache[color] = batch

			edge_time = time.perf_counter() - edge_start
			self.edge_times.append(edge_time)
			if len(self.edge_times) > self.max_samples:
				self.edge_times.pop(0)








