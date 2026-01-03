"""
Operator widgets for drag-and-drop query building.

Provides draggable operator buttons (AND, OR, NOT, parentheses) that can be
added to filter groups to build complex boolean queries.
"""

from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag, QCursor
from enum import Enum


class OperatorType(Enum):
    """Types of operators supported."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    GROUP = "( )"  # Grouping operator for nested expressions


class OperatorWidget(QPushButton):
    """
    Draggable operator widget for building boolean queries.
    
    Can be dragged from a palette or between groups.
    Right-click to delete.
    
    Signals:
        deleteRequested: Emitted when user right-clicks to delete
    """
    
    deleteRequested = pyqtSignal()
    
    def __init__(self, operator_type: OperatorType, draggable: bool = True, parent=None):
        """
        Initialize operator widget.
        
        Args:
            operator_type: Type of operator
            draggable: Whether this widget can be dragged
            parent: Parent widget
        """
        super().__init__(operator_type.value, parent)
        self.operator_type = operator_type
        self.draggable = draggable
        self.drag_start_position = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI styling."""
        # Base styling for operators
        base_style = """
            QPushButton {
                border-radius: 3px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 9px;
                min-width: 30px;
            }
        """
        
        # Color coding by operator type
        if self.operator_type == OperatorType.AND:
            color_style = """
                background: #2d5a3d;
                color: #e0e0e0;
                border: 1px solid #1f3f2a;
            }
            QPushButton:hover {
                background: #3d7a4d;
            """
        elif self.operator_type == OperatorType.OR:
            color_style = """
                background: #5a4d2d;
                color: #e0e0e0;
                border: 1px solid #3f351f;
            }
            QPushButton:hover {
                background: #7a6d3d;
            """
        elif self.operator_type == OperatorType.NOT:
            color_style = """
                background: #6d3030;
                color: #e0e0e0;
                border: 1px solid #4a1f1f;
            }
            QPushButton:hover {
                background: #8d4040;
            """
        else:  # GROUP
            color_style = """
                background: #3d3d4d;
                color: #c0c0c0;
                border: 1px solid #2d2d3d;
            }
            QPushButton:hover {
                background: #4d4d5d;
            """
        
        self.setStyleSheet(base_style + color_style)
        
        if self.draggable:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.setToolTip(f"{self.operator_type.value} operator (drag to group, right-click to delete)")
        else:
            self.setToolTip(f"{self.operator_type.value} operator")
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag start."""
        if event.button() == Qt.MouseButton.LeftButton and self.draggable:
            self.drag_start_position = event.pos()
            event.accept()  # Accept to start drag, prevent button click
            return
        elif event.button() == Qt.MouseButton.RightButton:
            # Don't call super() for right-click to prevent button activation
            event.accept()
            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to initiate drag."""
        if not self.draggable:
            return
        
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # Check if we've moved far enough to start a drag
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        
        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store operator type in mime data
        mime_data.setText(self.operator_type.value)
        mime_data.setData("application/x-operator", self.operator_type.value.encode())
        
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)
        
        # Reset drag position after drag completes
        self.drag_start_position = None
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to prevent button click after drag."""
        if self.draggable and self.drag_start_position is not None:
            # If we were preparing to drag, don't trigger button click
            self.drag_start_position = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click to delete."""
        if self.draggable:
            self.deleteRequested.emit()
            event.accept()
        else:
            event.ignore()


class OperatorPalette(QWidget):
    """
    Palette of draggable operators that can be added to filter groups.
    
    Provides a toolbar-like interface with all available operators.
    """
    
    def __init__(self, parent=None):
        """Initialize operator palette."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        
        # Add label
        from PyQt6.QtWidgets import QLabel
        label = QLabel("Operators:")
        label.setStyleSheet("font-weight: bold; font-size: 9px; color: #888;")
        layout.addWidget(label)
        
        # Add operator buttons
        for op_type in [OperatorType.AND, OperatorType.OR, OperatorType.NOT, 
                       OperatorType.GROUP]:
            operator = OperatorWidget(op_type, draggable=True)
            layout.addWidget(operator)
        
        layout.addStretch()
        
        # Style the palette
        self.setStyleSheet("""
            QWidget {
                background: #1a1d21;
                border: 1px solid #2a2d32;
                border-radius: 3px;
            }
        """)
