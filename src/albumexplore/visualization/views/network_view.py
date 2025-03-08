from PyQt6.QtWidgets import (
	QApplication, QWidget, QVBoxLayout, QHBoxLayout,
	QLabel, QLineEdit, QPushButton, QDialog, QFormLayout, QSpinBox,
	QToolTip, QMenu)
from ..debug import PerformanceDebugger
from PyQt6.QtCore import Qt, QPointF, QTimer, QElapsedTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QMouseEvent, QPaintEvent, QWheelEvent, QContextMenuEvent, QPainterPath
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
	"""Simple quadtree implementation for spatial indexing."""

	def __init__(self, rect, max_objects=10, max_depth=4, depth=0):
		self.rect = rect
		self.max_objects = max_objects
		self.max_depth = max_depth
		self.depth = depth
		self.objects = []
		self.nodes = []

	def insert(self, item):
		if self.nodes:
			index = self._get_index(item)
			if index != -1:
				self.nodes[index].insert(item)
				return

		self.objects.append(item)

		if len(self.objects) > self.max_objects and self.depth < self.max_depth:
			if not self.nodes:
				self._split()

			i = 0
			while i < len(self.objects):
				index = self._get_index(self.objects[i])
				if index != -1:
					self.nodes[index].insert(self.objects.pop(i))
				else:
					i += 1

	def _split(self):
		width = self.rect[2] / 2
		height = self.rect[3] / 2
		x = self.rect[0]
		y = self.rect[1]

		self.nodes = [
			QuadTree((x, y, width, height), self.max_objects, self.max_depth, self.depth + 1),
			QuadTree((x + width, y, width, height), self.max_objects, self.max_depth, self.depth + 1),
			QuadTree((x, y + height, width, height), self.max_objects, self.max_depth, self.depth + 1),
			QuadTree((x + width, y + height, width, height), self.max_objects, self.max_depth, self.depth + 1)
		]

	def _get_index(self, item):
		index = -1
		x = item.data.get('x', 0)
		y = item.data.get('y', 0)

		mid_x = self.rect[0] + self.rect[2] / 2
		mid_y = self.rect[1] + self.rect[3] / 2

		top = y < mid_y
		bottom = y >= mid_y
		left = x < mid_x
		right = x >= mid_x

		if left:
			if top:
				index = 0
			elif bottom:
				index = 2
		elif right:
			if top:
				index = 1
			elif bottom:
				index = 3

		return index

	def query(self, search_rect):
		result = []
		
		if not self._intersects(search_rect):
			return result

		for obj in self.objects:
			x = obj.data.get('x', 0)
			y = obj.data.get('y', 0)
			if search_rect[0] <= x <= search_rect[0] + search_rect[2] and \
			   search_rect[1] <= y <= search_rect[1] + search_rect[3]:
				result.append(obj)

		if self.nodes:
			for node in self.nodes:
				result.extend(node.query(search_rect))

		return result

	def _intersects(self, rect):
		return not (
			rect[0] + rect[2] < self.rect[0] or
			rect[0] > self.rect[0] + self.rect[2] or
			rect[1] + rect[3] < self.rect[1] or
			rect[1] > self.rect[1] + self.rect[3]
		)


class NetworkView(BaseView):
	"""Network visualization view."""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.view_state = ViewState(ViewType.NETWORK)
		
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
		
		# Node rendering properties
		self._node_size = 10
		self._edge_color = QColor(200, 200, 200)
		self._node_color = QColor(100, 100, 255)
		self._selected_color = QColor(255, 100, 100)
		
		# Double buffering
		self._buffer = None
		self._buffer_dirty = True

	def _paint_content(self, painter: QPainter) -> None:
		"""Paint the network visualization."""
		if not self.nodes:
			return
		
		# Enable antialiasing for smooth rendering
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Apply viewport transform
		painter.translate(self.width() / 2 + self.viewport_x, 
						self.height() / 2 + self.viewport_y)
		painter.scale(self.viewport_scale, self.viewport_scale)
		
		# Draw edges
		edge_pen = QPen(self._edge_color)
		edge_pen.setWidth(max(1, int(1.0 / self.viewport_scale)))
		painter.setPen(edge_pen)
		
		edge_path = QPainterPath()
		for edge in self.edges:
			source = next((n for n in self.nodes if n.id == edge.source), None)
			target = next((n for n in self.nodes if n.id == edge.target), None)
			if source and target:
				edge_path.moveTo(source.data.get('x', 0), source.data.get('y', 0))
				edge_path.lineTo(target.data.get('x', 0), target.data.get('y', 0))
		painter.drawPath(edge_path)
		
		# Draw nodes
		node_pen = QPen(Qt.PenStyle.NoPen)
		for node in self.nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			
			# Set node appearance
			if node.id in self.selected_ids:
				painter.setBrush(QBrush(self._selected_color))
			else:
				painter.setBrush(QBrush(self._node_color))
			painter.setPen(node_pen)
			
			# Draw node
			painter.drawEllipse(QPointF(x, y), self._node_size, self._node_size)
			
			# Draw label if zoomed in enough
			if self.viewport_scale > 0.5:
				painter.setPen(QPen(Qt.GlobalColor.black))
				painter.drawText(QPointF(x + self._node_size + 5, y), 
							   node.label if hasattr(node, 'label') else str(node.id))

	def mousePressEvent(self, event):
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

	def _node_at_pos(self, screen_x: float, screen_y: float) -> Optional[VisualNode]:
		"""Find node at the given screen position."""
		if not self.nodes:
			return None
			
		# Convert screen coordinates to scene coordinates
		scene_x = (screen_x - self.width()/2 - self.viewport_x) / self.viewport_scale
		scene_y = (screen_y - self.height()/2 - self.viewport_y) / self.viewport_scale
		
		# Find closest node within threshold
		threshold = self._node_size / self.viewport_scale
		closest_node = None
		min_dist = float('inf')
		
		for node in self.nodes:
			x = node.data.get('x', 0)
			y = node.data.get('y', 0)
			
			dx = x - scene_x
			dy = y - scene_y
			dist = math.sqrt(dx*dx + dy*dy)
			
			if dist <= threshold and dist < min_dist:
				closest_node = node
				min_dist = dist
				
		return closest_node








