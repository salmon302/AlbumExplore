"""Table visualization view module."""
from typing import List, Dict, Any, Set
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                            QVBoxLayout, QSizePolicy, QScrollBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
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
        
        # Create layout first
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create table widget with minimum size
        self.table = QTableWidget(self)
        self.table.setMinimumSize(800, 600)  # Set minimum size to ensure proper initial display
        layout.addWidget(self.table, stretch=1)
        
        # Configure table properties
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)
        
        # Configure header with fixed sizes first
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setVisible(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 250)  # Artist
        self.table.setColumnWidth(1, 300)  # Album
        self.table.setColumnWidth(2, 80)   # Year
        self.table.setColumnWidth(3, 400)  # Tags
        
        # Now set interactive resize mode and stretch last section
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Hide vertical header (row numbers)
        self.table.verticalHeader().setVisible(False)
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_direction = "asc"
        
        # Initialize selection tracking
        self.selected_ids = set()
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._handle_selection)
        header.sectionClicked.connect(self._handle_sort)
        
        # Set the layout
        self.setLayout(layout)
        
        # Force immediate geometry update
        self.updateGeometry()
        self.table.updateGeometry()
        gui_logger.debug("TableView initialized")

    def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
        """Update table with new data."""
        gui_logger.debug(f"Updating table data with {len(nodes)} nodes")
        
        # Block signals during update to prevent unnecessary redraws
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        
        try:
            self.table.clearContents()
            valid_nodes = [n for n in nodes if n.data.get("type") == "row"]
            gui_logger.debug(f"Found {len(valid_nodes)} valid row nodes")
            
            # Set row count
            self.table.setRowCount(len(valid_nodes))
            
            # Add all rows at once
            for row, node in enumerate(valid_nodes):
                year = node.data.get("year", "")
                items = [
                    (str(node.data.get("artist", "")), 0),
                    (str(node.data.get("title", "")), 1),
                    (str(year), 2),
                    (", ".join(str(tag) for tag in node.data.get("tags", [])), 3)
                ]
                
                for text, col in items:
                    item = QTableWidgetItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, node.id)
                    
                    # For year column, store numeric value for proper sorting
                    if col == 2 and year:
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, int(year))
                        except (ValueError, TypeError):
                            pass
                    
                    self.table.setItem(row, col, item)
            
            # Update selection and sorting
            self._update_selection()
            if self.sort_column is not None:
                self.table.sortItems(
                    self.sort_column,
                    Qt.SortOrder.AscendingOrder if self.sort_direction == "asc" else Qt.SortOrder.DescendingOrder
                )
            
            gui_logger.debug(f"Table updated with {self.table.rowCount()} rows")
            
        finally:
            # Re-enable updates and signals
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)
            # Force a complete repaint
            self.table.viewport().update()
            self.table.updateGeometry()

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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)
        
        # Configure header with fixed sizes first
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setVisible(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 250)  # Artist
        self.table.setColumnWidth(1, 300)  # Album
        self.table.setColumnWidth(2, 80)   # Year
        self.table.setColumnWidth(3, 400)  # Tags
        
        # Now set interactive resize mode and stretch last section
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Hide vertical header (row numbers)
        self.table.verticalHeader().setVisible(False)
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_direction = "asc"
        
        # Initialize selection tracking
        self.selected_ids = set()
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._handle_selection)
        header.sectionClicked.connect(self._handle_sort)
        
        # Set the layout
        self.setLayout(layout)
        
        # Force immediate geometry update
        self.updateGeometry()
        self.table.updateGeometry()
        gui_logger.debug("TableView initialized")

    def _handle_selection(self, selected_ids: Set[str] = None):
        """Handle table selection changes."""
        # Use instance variable for recursion protection
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            
            # If selected_ids is provided, update selection to match
            if selected_ids is not None:
                self.selected_ids = selected_ids
                self._update_selection()
                return

            # Otherwise, gather selection from table
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

    def _update_selection(self):
        """Update table selection state."""
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) in self.selected_ids:
                self.table.selectRow(row)

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