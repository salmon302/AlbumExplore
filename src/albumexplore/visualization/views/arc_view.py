from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QPixmap
import math

from .base_view import BaseView
from ..state import ViewType, ViewState
from ..arc_renderer import ArcRenderer

class ArcView(BaseView):
	"""Arc diagram visualization."""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.view_state = ViewState(ViewType.ARC)
		self.renderer = ArcRenderer()
		self.setMinimumSize(400, 400)
		
		# Improve buffer management
		self.setProperty("paintOnScreen", False)
		self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)
		self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
		self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
		
		self._paint_buffer = None
		self._buffer_dirty = True
		self._buffer_lock = False
		self._cleanup_scheduled = False
	
	def update(self) -> None:
		"""Override update to mark buffer as dirty."""
		self._buffer_dirty = True
		super().update()

	def paintEvent(self, event):
		if not hasattr(self, 'renderer') or not self.nodes or self._buffer_lock:
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

	def _paint_to_buffer(self):
		"""Paint content to buffer."""
		if not self._paint_buffer:
			return

		painter = QPainter(self._paint_buffer)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Clear the buffer
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
		painter.fillRect(self._paint_buffer.rect(), Qt.GlobalColor.transparent)
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
		
		try:
			# Update viewport dimensions in view state
			self.view_state.viewport_width = self.width()
			self.view_state.viewport_height = self.height()
			
			# Get rendered data from arc renderer
			render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
			
			# Draw arcs first (connections)
			for arc in render_data.get('arcs', []):
				path = QPainterPath()
				points = arc.get('path', [])
				if len(points) >= 3:  # Need at least start, control, and end points
					start, control, end = points[:3]  # Take first three points
					
					path.moveTo(start[0], start[1])
					path.quadTo(control[0], control[1], end[0], end[1])
					
					color = QColor(arc.get('color', '#666666'))
					color.setAlpha(200)  # Increased opacity
					pen = QPen(color)
					pen.setWidth(max(1, round(arc.get('thickness', 1))))
					painter.setPen(pen)
					painter.drawPath(path)
			
			# Draw nodes
			for node in render_data.get('nodes', []):
				color = QColor(node.get('color', '#6464ff'))
				if node.get('selected', False):
					color = QColor('#ff6464')
				
				painter.setBrush(QBrush(color))
				painter.setPen(Qt.PenStyle.NoPen)
				
				size = node.get('size', 20)  # Increased default size
				rect = QRectF(node.get('x', 0) - size/2, node.get('y', 0) - size/2, size, size)
				painter.drawEllipse(rect)
				
				# Draw label with background for better visibility
				if node.get('label'):
					label_rect = QRectF(node.get('x', 0) - size*2, node.get('y', 0) + size*1.5, size*4, size)  # Adjusted positioning
					text = str(node.get('label'))
					
					# Draw text background
					painter.setPen(Qt.PenStyle.NoPen)
					painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
					bg_rect = label_rect.adjusted(-5, -2, 5, 2)
					painter.drawRect(bg_rect)
					
					# Draw text
					painter.setPen(QPen(Qt.GlobalColor.black))
					painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, text)
		finally:
			painter.end()
	
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

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			# Get rendered data
			render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
			
			# Check if clicked on a node
			for node in render_data.get('nodes', []):
				dx = event.position().x() - node.get('x', 0)
				dy = event.position().y() - node.get('y', 0)
				if math.sqrt(dx*dx + dy*dy) < node.get('size', 10)/2:
					self.update_selection({node.get('id')})
					break