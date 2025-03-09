"""Custom viewport widget with double buffering support."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPaintEvent, QResizeEvent

class DoubleBufferedViewport(QWidget):
    """A custom viewport widget that uses double buffering for smooth rendering."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Enable attributes for optimized painting
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        
        # Keep track of buffer state
        self._needs_full_repaint = True
        
    def paintEvent(self, event: QPaintEvent):
        """Handle paint events with double buffering."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Only redraw the region that needs updating unless full repaint is needed
        if self._needs_full_repaint:
            painter.setClipRect(self.rect())
            self._needs_full_repaint = False
        else:
            painter.setClipRegion(event.region())
            
        # Paint the widget
        super().paintEvent(event)
        
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize events."""
        super().resizeEvent(event)
        # Force full repaint on resize
        self._needs_full_repaint = True