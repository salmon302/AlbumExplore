from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QTimer  # Add QTimer import
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QPixmap
import math

from .base_view import BaseView
from ..state import ViewType, ViewState
from ..chord_renderer import ChordRenderer

class ChordView(BaseView):
	"""Chord diagram visualization."""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.view_state = ViewState(ViewType.CHORD)
		self.renderer = ChordRenderer()
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
			
			# Get rendered data from chord renderer
			render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
			
			# Center the visualization
			width = self.width()
			height = self.height()
			painter.translate(width/2, height/2)
			
			# Draw chords first (behind arcs)
			for chord in render_data.get('chords', []):
				path = QPainterPath()
				source_pos = chord.get('source_pos', {})
				target_pos = chord.get('target_pos', {})
				control1 = chord.get('control1', {})
				control2 = chord.get('control2', {})
				
				if source_pos and target_pos and control1 and control2:
					path.moveTo(source_pos['x'], source_pos['y'])
					path.cubicTo(
						control1['x'], control1['y'],
						control2['x'], control2['y'],
						target_pos['x'], target_pos['y']
					)
					
					color = QColor(chord.get('color', '#666666'))
					color.setAlpha(200)  # Increased opacity for better visibility
					pen = QPen(color)
					pen.setWidth(max(1, int(chord.get('thickness', 1))))  # Convert to int
					painter.setPen(pen)
					painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))
					painter.drawPath(path)
			
			# Draw node arcs
			for node in render_data.get('nodes', []):
				color = QColor(node.get('color', '#6464ff'))
				if node.get('selected', False):
					color = QColor('#ff6464')
				
				pen = QPen(color)
				pen.setWidth(2)
				painter.setPen(pen)
				
				# Draw filled arc
				radius = node.get('radius', 200)
				rect = QRectF(-radius, -radius, radius*2, radius*2)
				start_angle = int(node.get('start_angle', 0) * 180/math.pi * 16)
				span_angle = int((node.get('end_angle', math.pi/4) - node.get('start_angle', 0)) * 180/math.pi * 16)
				
				# Fill arc
				painter.setBrush(QBrush(color.lighter(150)))
				painter.drawPie(rect, start_angle, span_angle)
				
				# Draw label if space permits
				if span_angle > 200:  # Only draw label if arc is wide enough
					label = node.get('label', '')
					if label:
						# Calculate label position
						mid_angle = (node.get('start_angle', 0) + node.get('end_angle', math.pi/4)) / 2
						label_radius = radius * 1.1  # Place label outside the arc
						label_x = math.cos(mid_angle) * label_radius
						label_y = math.sin(mid_angle) * label_radius
						
						# Rotate text to follow arc
						painter.save()
						painter.translate(label_x, label_y)
						angle_deg = mid_angle * 180/math.pi
						if 90 < angle_deg < 270:
							angle_deg += 180
						painter.rotate(angle_deg)
						painter.setPen(QPen(Qt.GlobalColor.black))
						painter.drawText(QRectF(-50, -10, 100, 20), 
									Qt.AlignmentFlag.AlignCenter, 
									str(label))
						painter.restore()
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
			# Convert to relative coordinates
			x = event.position().x() - self.width()/2
			y = event.position().y() - self.height()/2
			
			# Get rendered data
			render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
			
			# Check if clicked on a node
			for node in render_data['nodes']:
				angle = math.atan2(y, x)
				if angle < 0:
					angle += 2 * math.pi
					
				radius = math.sqrt(x*x + y*y)
				if (node['start_angle'] <= angle <= node['end_angle'] and 
					abs(radius - node['radius']) < 10):
					self.update_selection({node['id']})
					break