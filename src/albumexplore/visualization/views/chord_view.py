from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QPixmap
import math

from .base_view import BaseView
from ..state import ViewType, ViewState
from ..chord_renderer import ChordRenderer
from albumexplore.gui.gui_logging import graphics_logger

class ChordView(BaseView):
    """Chord diagram visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_state = ViewState(ViewType.CHORD)
        self.renderer = ChordRenderer()
        self.setMinimumSize(400, 400)
        
        # Improved buffer management
        self._paint_buffer = None
        self._buffer_dirty = True
        self._buffer_lock = False
        self._cleanup_scheduled = False
        
        # Set up timer for deferred cleanup
        self._cleanup_timer = QTimer()
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._cleanup_resources)
    
    def update(self) -> None:
        """Override update to mark buffer as dirty."""
        self._buffer_dirty = True
        super().update()
        
    def paintEvent(self, event):
        if not hasattr(self, 'renderer') or not self.nodes or self._buffer_lock:
            # Call parent paintEvent to ensure background is properly painted
            super().paintEvent(event)
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
            
            # Paint buffer to widget with proper background handling
            painter = QPainter(self)
            
            # Call parent's background painting to ensure proper clearing
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), self._background_color)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Now draw from buffer
            if self._paint_buffer:
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
        
        # Clear buffer with transparency (not using QPixmap.fill again)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self._paint_buffer.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        try:
            # Update viewport dimensions in view state
            self.view_state.viewport_width = self.width()
            self.view_state.viewport_height = self.height()
            
            # Get rendered data from chord renderer
            render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
            
            # Calculate center coordinates
            center_x = self.width() / 2
            center_y = self.height() / 2
            max_dim = min(self.width(), self.height()) * 0.8
            radius = max_dim / 2
            
            # Draw chord connections first
            for chord in render_data.get('chords', []):
                path = QPainterPath()
                
                # Extract chord data
                source_idx = chord.get('source_idx', 0)
                target_idx = chord.get('target_idx', 0)
                source_start = chord.get('source_start', 0)
                source_end = chord.get('source_end', 0)
                target_start = chord.get('target_start', 0)
                target_end = chord.get('target_end', 0)
                
                # Convert angles from radians to cartesian coordinates
                source_start_x = center_x + radius * math.cos(source_start)
                source_start_y = center_y + radius * math.sin(source_start)
                source_end_x = center_x + radius * math.cos(source_end)
                source_end_y = center_y + radius * math.sin(source_end)
                
                target_start_x = center_x + radius * math.cos(target_start)
                target_start_y = center_y + radius * math.sin(target_start)
                target_end_x = center_x + radius * math.cos(target_end)
                target_end_y = center_y + radius * math.sin(target_end)
                
                # Draw bezier curve for chord
                path.moveTo(source_start_x, source_start_y)
                path.cubicTo(
                    center_x, center_y,
                    center_x, center_y,
                    target_end_x, target_end_y
                )
                path.lineTo(target_start_x, target_start_y)
                path.cubicTo(
                    center_x, center_y,
                    center_x, center_y,
                    source_end_x, source_end_y
                )
                path.closeSubpath()
                
                # Set color with transparency for better visual effect
                color = QColor(chord.get('color', '#808080'))
                color.setAlpha(120)  # Semi-transparent
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawPath(path)
            
            # Draw node arcs
            for arc in render_data.get('arcs', []):
                node_id = arc.get('id')
                start_angle = arc.get('start_angle', 0)
                end_angle = arc.get('end_angle', 0)
                
                # Convert to Qt angle format (16th of degrees, clockwise from 3 o'clock)
                start_deg = -math.degrees(start_angle) * 16
                span_deg = -math.degrees(end_angle - start_angle) * 16
                
                arc_rect = QRectF(
                    center_x - radius,
                    center_y - radius,
                    radius * 2,
                    radius * 2
                )
                
                # Determine if selected
                color = QColor(arc.get('color', '#404080'))
                if node_id in self.selected_ids:
                    color = QColor('#ff6464')  # Red for selected nodes
                
                # Slightly darker pen for outline
                pen = QPen(color.darker(120))
                pen.setWidth(2)
                
                painter.setPen(pen)
                painter.setBrush(QBrush(color))
                painter.drawPie(arc_rect, int(start_deg), int(span_deg))
            
            # Draw labels for nodes
            for label in render_data.get('labels', []):
                angle = label.get('angle', 0)
                text = label.get('text', '')
                
                # Position label outside the chord circle
                label_radius = radius * 1.05
                label_x = center_x + label_radius * math.cos(angle)
                label_y = center_y + label_radius * math.sin(angle)
                
                # Adjust text alignment based on position
                text_flags = Qt.AlignmentFlag.AlignCenter
                if angle < math.pi / 2 or angle > 3 * math.pi / 2:
                    text_flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                elif angle > math.pi / 2 and angle < 3 * math.pi / 2:
                    text_flags = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                
                # Draw text with white background for better readability
                text_rect = painter.fontMetrics().boundingRect(text)
                text_rect.moveCenter(QPointF(label_x, label_y).toPoint())
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 180)))  # Semi-transparent white
                painter.drawRect(text_rect.adjusted(-2, -2, 2, 2))
                
                painter.setPen(QPen(Qt.GlobalColor.black))
                painter.drawText(text_rect, text_flags, text)
                
        finally:
            painter.end()
            
    def resizeEvent(self, event) -> None:
        """Handle resize with proper buffer cleanup."""
        super().resizeEvent(event)
        self._buffer_dirty = True
        
        # Clean up old buffer to free memory
        if self._paint_buffer:
            self._paint_buffer = None
            
    def hideEvent(self, event) -> None:
        """Clean up resources when hidden."""
        super().hideEvent(event)
        self._schedule_cleanup()
        
    def _schedule_cleanup(self) -> None:
        """Schedule resource cleanup to avoid immediate buffer destruction during transitions."""
        if not self._cleanup_scheduled:
            self._cleanup_scheduled = True
            self._cleanup_timer.start(200)  # Wait 200ms before cleanup
            
    def _cleanup_resources(self) -> None:
        """Clean up buffers and resources."""
        graphics_logger.debug("Cleaning up ChordView resources")
        if self._paint_buffer:
            self._paint_buffer = None
        self._buffer_dirty = True
        self._cleanup_scheduled = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate relative mouse position from center
            center_x = self.width() / 2
            center_y = self.height() / 2
            dx = event.position().x() - center_x
            dy = event.position().y() - center_y
            
            # Convert to polar coordinates
            radius = math.sqrt(dx*dx + dy*dy)
            angle = math.atan2(dy, dx)
            if angle < 0:
                angle += 2 * math.pi
            
            # Check if click is on a node arc
            max_radius = min(self.width(), self.height()) * 0.4
            if radius <= max_radius:
                # Get rendered data to find which node was clicked
                render_data = self.renderer.render(self.nodes, self.edges, self.view_state)
                
                for arc in render_data.get('arcs', []):
                    start_angle = arc.get('start_angle', 0)
                    end_angle = arc.get('end_angle', 0)
                    
                    # Check if angle is within arc range
                    if start_angle <= angle <= end_angle:
                        node_id = arc.get('id')
                        if node_id:
                            self.update_selection({node_id})
                            break