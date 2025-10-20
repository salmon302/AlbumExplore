"""
Tag chip widget - visual representation of a tag with remove button.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QPalette, QColor, QDrag


class TagChip(QWidget):
    """
    A visual tag chip with optional remove button.
    
    Supports drag-and-drop to move tags between groups.
    
    Signals:
        removeClicked: Emitted when the remove button is clicked
        dragStarted: Emitted when a drag operation starts
    """
    
    removeClicked = pyqtSignal()
    dragStarted = pyqtSignal(str)  # Emits tag text when drag starts
    
    def __init__(self, tag_text: str, color: str = None, removable: bool = True, draggable: bool = True, parent=None):
        """
        Initialize a tag chip.
        
        Args:
            tag_text: Text to display on the chip
            color: Background color (hex format like "#FFE0E0")
            removable: Whether to show remove button
            parent: Parent widget
        """
        super().__init__(parent)
        self.tag_text = tag_text
        self.color = color or "#E0E0E0"
        self.removable = removable
        self.draggable = draggable
        self._drag_start_pos = None
        
        self._setup_ui()
        self._apply_styling()
        
        # Enable drag-and-drop if draggable
        if self.draggable:
            self.setAcceptDrops(False)  # Chips don't accept drops, only initiate drags
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(3)
        
        # Tag label
        self.label = QLabel(self.tag_text)
        self.label.setStyleSheet("background: transparent; border: none; color: #ddd; font-size: 10px;")
        layout.addWidget(self.label)
        
        # Remove button (if removable)
        if self.removable:
            self.remove_button = QPushButton("×")
            self.remove_button.setFixedSize(QSize(12, 12))
            self.remove_button.clicked.connect(self.removeClicked.emit)
            self.remove_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #888;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #ddd;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                }
            """)
            layout.addWidget(self.remove_button)
    
    def _apply_styling(self):
        """Apply visual styling to the chip."""
        # Use darker, more subtle colors
        bg_color = self._make_darker(self.color)
        border_color = self._darken_color(bg_color, 0.7)
        
        self.setStyleSheet(f"""
            TagChip {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 1px;
            }}
            TagChip:hover {{
                background-color: {self._lighten_color(bg_color, 1.15)};
                border-color: {self._lighten_color(border_color, 1.2)};
            }}
        """)
        
        # Set size policy - more compact
        self.setMaximumHeight(20)
    
    def _make_darker(self, hex_color: str) -> str:
        """Make a color much darker for dark theme."""
        try:
            color = QColor(hex_color)
            h, s, v, a = color.getHsv()
            # Reduce value significantly for dark theme
            color.setHsv(h, max(50, s), min(80, v // 3), a)
            return color.name()
        except:
            return "#2a2d32"
    
    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """Darken a hex color."""
        try:
            color = QColor(hex_color)
            h, s, v, a = color.getHsv()
            color.setHsv(h, s, int(v * factor), a)
            return color.name()
        except:
            return "#1a1d21"
    
    def _lighten_color(self, hex_color: str, factor: float = 1.1) -> str:
        """Lighten a hex color."""
        try:
            color = QColor(hex_color)
            h, s, v, a = color.getHsv()
            color.setHsv(h, s, min(255, int(v * factor)), a)
            return color.name()
        except:
            return "#F0F0F0"
    
    def get_tag_text(self) -> str:
        """Get the tag text."""
        return self.tag_text
    
    def set_color(self, color: str):
        """Update the chip color."""
        self.color = color
        self._apply_styling()
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if self.draggable and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drag-and-drop."""
        if not self.draggable or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self._drag_start_pos is None:
            return
        
        # Check if we've moved far enough to start a drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.tag_text)
        mime_data.setData('application/x-tagchip', self.tag_text.encode())
        drag.setMimeData(mime_data)
        
        # Emit signal that drag started
        self.dragStarted.emit(self.tag_text)
        
        # Execute drag
        drag.exec(Qt.DropAction.MoveAction)
