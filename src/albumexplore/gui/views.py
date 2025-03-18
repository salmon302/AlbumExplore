"""GUI views for visualization system."""
from typing import Dict, Any, List, Set, Optional, Callable
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from albumexplore.visualization.state import ViewType
from albumexplore.gui.models import AlbumTableModel
from albumexplore.gui.views.base_view import BaseView
from albumexplore.gui.gui_logging import graphics_logger

class TableView(BaseView):
    """Table visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableView(self)
        self.layout.addWidget(self.table)
        self.model = AlbumTableModel()
        self.table.setModel(self.model)
        
        # Connect selection handling
        self.table.selectionModel().selectionChanged.connect(self._handle_selection)
    
    def update_data(self, render_data: Dict[str, Any]):
        """Update table data."""
        if render_data.get("type") != "table":
            return
            
        self.model.set_data(render_data.get("rows", []))
        self._restore_selection()
    
    def apply_transition(self, transition_data: Dict[str, Any]):
        """Apply transition changes."""
        super().apply_transition(transition_data)
        self._restore_selection()
        
    def _restore_selection(self):
        """Restore selected rows."""
        if not hasattr(self.table, 'selectionModel'):
            return
            
        selection_model = self.table.selectionModel()
        if not selection_model:
            return
            
        selection_model.clearSelection()
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if self.model.data(index, role=Qt.ItemDataRole.UserRole) in self.selected_ids:
                selection_model.select(index, selection_model.SelectionFlag.Select)
    
    def _handle_selection(self, selected, deselected):
        """Handle table selection changes."""
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            selected_ids = {
                self.model.data(idx, role=Qt.ItemDataRole.UserRole)
                for idx in self.table.selectionModel().selectedIndexes()
            }
            self.selected_ids = selected_ids
            self.selection_changed.emit(selected_ids)
        finally:
            self._is_processing_selection = False

def create_view(view_type: ViewType, parent=None) -> BaseView:
    """Create a view instance based on type."""
    if view_type == ViewType.TABLE:
        return TableView(parent)
    # Other view types handled by visualization module
    return None