"""Table visualization view module."""
from typing import List, Dict, Any, Set
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                            QVBoxLayout, QSizePolicy, QScrollBar)
from PyQt6.QtCore import Qt
from albumexplore.gui.gui_logging import gui_logger

from .base_view import BaseView
from ..state import ViewType, ViewState
from ..models import VisualNode, VisualEdge

class TableView(BaseView):
    """Table visualization view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_state = ViewState(ViewType.TABLE)
        gui_logger.debug("Initializing TableView")
        
        # Store nodes for reuse
        self.nodes = []
        
        # Add recursion protection flag
        self._is_processing_selection = False
        
        # Create layout first
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create table widget with minimum size
        self.table = QTableWidget(self)
        self.table.setMinimumSize(800, 600)  # Set minimum size to ensure proper initial display
        layout.addWidget(self.table, stretch=1)
        
        # Configure table properties
        self.table.setColumnCount(5)  # Reduced from 6 to 5 (removed Genre column)
        self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Country", "Tags"])
        self.table.setShowGrid(True)
        # Disable alternating row colors to fix visibility issue
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        
        # Set a stylesheet to ensure all rows have consistent, visible backgrounds
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f0f0f0;
            }
            QTableWidget::item {
                background-color: white;
                color: black;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setVisible(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        
        # Set column widths - adjusted for 5 columns
        self.table.setColumnWidth(0, 200)  # Artist
        self.table.setColumnWidth(1, 250)  # Album
        self.table.setColumnWidth(2, 80)   # Year
        self.table.setColumnWidth(3, 100)  # Country
        header.setStretchLastSection(True)  # Tags column stretches
        
        # Hide row numbers
        self.table.verticalHeader().setVisible(False)
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_direction = "asc"
        
        # Initialize selection tracking
        self.selected_ids = set()
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._handle_selection)
        header.sectionClicked.connect(self._handle_sort)
        
        gui_logger.debug("TableView initialized")

    def update_data(self, data_or_nodes, edges=None):
        """Update table with new data. Supports both renderer data dict and direct nodes/edges updates."""
        if isinstance(data_or_nodes, dict):
            # Handle renderer data format
            if 'rows' not in data_or_nodes:
                return
                
            rows = data_or_nodes['rows']
            self.table.setRowCount(len(rows))
            
            for row_idx, row in enumerate(rows):
                # Artist
                item = QTableWidgetItem(row.get('artist', ''))
                item.setData(Qt.ItemDataRole.UserRole, row.get('id'))
                self.table.setItem(row_idx, 0, item)
                
                # Album - use 'album' key or 'title' as fallback
                self.table.setItem(row_idx, 1, QTableWidgetItem(row.get('album', row.get('title', ''))))
                
                # Year - ensure it's displayed as a string
                year_str = str(row.get('year', ''))
                self.table.setItem(row_idx, 2, QTableWidgetItem(year_str))
                
                # Country
                self.table.setItem(row_idx, 3, QTableWidgetItem(row.get('country', '')))
                
                # Tags
                tags = row.get('tags', [])
                self.table.setItem(row_idx, 4, QTableWidgetItem(', '.join(str(t) for t in tags)))
            
            # Update selection
            if 'selected_ids' in data_or_nodes:
                self.selected_ids = set(data_or_nodes['selected_ids'])
                self._update_selection()
        else:
            # Handle direct nodes/edges update
            self.table.blockSignals(True)
            
            try:
                self.table.clearContents()
                valid_nodes = [n for n in data_or_nodes if n.data.get("type") == "row"]
                self.table.setRowCount(len(valid_nodes))
                
                for row, node in enumerate(valid_nodes):
                    # Artist
                    artist_item = QTableWidgetItem(str(node.data.get("artist", "")))
                    artist_item.setData(Qt.ItemDataRole.UserRole, node.id)
                    self.table.setItem(row, 0, artist_item)
                    
                    # Album - use 'title' key for album data
                    album_title = str(node.data.get("title", ""))
                    self.table.setItem(row, 1, QTableWidgetItem(album_title))
                    
                    # Year - ensure it's displayed as a string
                    year_str = str(node.data.get("year", ""))
                    self.table.setItem(row, 2, QTableWidgetItem(year_str))
                    
                    # Country
                    self.table.setItem(row, 3, QTableWidgetItem(str(node.data.get("country", ""))))
                    
                    # Tags
                    tags = node.data.get("tags", [])
                    self.table.setItem(row, 4, QTableWidgetItem(', '.join(str(t) for t in tags)))
            finally:
                # Re-enable signals
                self.table.setUpdatesEnabled(True)
                self.table.blockSignals(False)
                # Force a complete repaint
                self.table.viewport().update()
                self.table.updateGeometry()
                
        gui_logger.debug(f"Updated table view with {self.table.rowCount()} rows")

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.table.setGeometry(self.rect())
        self.table.updateGeometry()
        gui_logger.debug(f"Table resized to {self.rect()}")

    def showEvent(self, event):
        """Handle show events."""
        super().showEvent(event)
        # Ensure table resizes properly when shown
        self.table.resize(self.size())
        self.table.show()
        self.table.raise_()
        # Force a complete repaint
        self.table.viewport().update()
        gui_logger.debug("Table view shown")

    def hideEvent(self, event):
        """Handle cleanup when widget is hidden."""
        super().hideEvent(event)
        self.table.hide()
        gui_logger.debug("Table view hidden")

    def _update_selection(self):
        """Update table selection state."""
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) in self.selected_ids:
                self.table.selectRow(row)

    def _handle_selection(self):
        """Handle table selection changes."""
        # Use instance variable for recursion protection
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            
            selected_ids = set()
            for item in self.table.selectedItems():
                node_id = item.data(Qt.ItemDataRole.UserRole)
                if node_id:
                    selected_ids.add(node_id)
            
            if selected_ids != self.selected_ids:
                self.selected_ids = selected_ids
                self.selectionChanged.emit(selected_ids)
        finally:
            self._is_processing_selection = False

    def _handle_sort(self, column_index):
        """Handle column header clicks for sorting."""
        if self.sort_column == column_index:
            # Toggle sort direction if same column
            self.sort_direction = "desc" if self.sort_direction == "asc" else "asc"
        else:
            self.sort_column = column_index
            self.sort_direction = "asc"
        
        self.table.sortItems(
            column_index,
            Qt.SortOrder.AscendingOrder if self.sort_direction == "asc" else Qt.SortOrder.DescendingOrder
        )