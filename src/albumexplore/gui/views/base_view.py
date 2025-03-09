"""Base view implementation."""
from typing import Set, Dict, Any
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from albumexplore.visualization.state import ViewType

class BaseView(QWidget):
    """Base class for visualization views."""
    
    # Signals
    selection_changed = pyqtSignal(set)  # Emits set of selected node IDs
    data_updated = pyqtSignal()  # Emits when data is updated
    size_changed = pyqtSignal(float, float)  # Emits when view size changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.TABLE  # Default view type
        self._selected_ids: Set[str] = set()
        self._data: Dict[str, Any] = {}
        self._is_processing_selection = False  # Flag to prevent recursion
        
    def update_data(self, data: Dict[str, Any]):
        """Update view data."""
        self._data = data
        self._handle_selection(data.get('selected_ids', set()))
        self.update()
        self.data_updated.emit()
    
    def _handle_selection(self, selected_ids: Set[str]):
        """Handle selection changes."""
        # Prevent recursion
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            if selected_ids != self._selected_ids:
                self._selected_ids = selected_ids
                self.selection_changed.emit(selected_ids)
        finally:
            self._is_processing_selection = False
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.size_changed.emit(self.width(), self.height())