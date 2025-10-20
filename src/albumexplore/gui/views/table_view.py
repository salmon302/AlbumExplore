"""Table visualization view."""
from typing import Dict, Any, Set, List
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                          QAbstractItemView, QVBoxLayout, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from .base_view import BaseView
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger

class TableView(BaseView):
    """Table visualization view."""
    
    sort_changed = pyqtSignal(str, str)  # column, direction
    show_similar_requested = pyqtSignal(str)  # album_id - signal to request similarity view
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.TABLE
        self._setup_ui()
        graphics_logger.debug("Table view initialized")
    
    def _setup_ui(self):
        """Set up UI elements."""
        # Create table
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Artist', 'Album', 'Year', 'Genre', 'Country', 'Vocal Style', 'Tags'
        ])
        
        # Configure selection
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Configure headers
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._handle_sort)
        
        # Configure layout
        layout = self.layout() or QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Enable context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._handle_selection)
    
    def update_data(self, render_data: Dict[str, Any], edges=None):
        """Update table data."""
        super().update_data(render_data)
        
        if 'rows' not in render_data:
            return
            
        rows = render_data['rows']
        self.table.setRowCount(len(rows))
        
        for row_idx, row in enumerate(rows):
            # Artist
            artist_data = row.get('artist', '')
            artist_name = str(artist_data) if artist_data is not None else ''
            item = QTableWidgetItem(artist_name)
            item.setData(Qt.ItemDataRole.UserRole, row.get('id'))
            self.table.setItem(row_idx, 0, item)
            
            # Album
            self.table.setItem(row_idx, 1, 
                             QTableWidgetItem(row.get('album', '')))
            
            # Year
            year_val = row.get('year', '')
            graphics_logger.debug(f"TableView: Populating year for row {row_idx}, album '{row.get('album', '')}', year: '{year_val}', type: {type(year_val)}") # DEBUG
            year_item = QTableWidgetItem()
            year_item.setData(Qt.ItemDataRole.DisplayRole, year_val)
            self.table.setItem(row_idx, 2, year_item)
            
            # Genre
            self.table.setItem(row_idx, 3, 
                             QTableWidgetItem(row.get('genre', '')))
            
            # Country
            self.table.setItem(row_idx, 4, 
                             QTableWidgetItem(row.get('country', '')))

            # Vocal style
            vocal_style_value = row.get('vocal_style', '')
            self.table.setItem(row_idx, 5,
                             QTableWidgetItem(vocal_style_value))
            
            # Tags
            tags = row.get('tags', [])
            self.table.setItem(row_idx, 6, 
                             QTableWidgetItem(', '.join(tags)))
        
        # Update selection
        self.table.clearSelection()
        if 'selected_ids' in render_data:
            selected_ids = set(render_data['selected_ids'])
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) in selected_ids:
                    self.table.selectRow(row)
        
        graphics_logger.debug(f"Updated table view with {len(rows)} rows")
    
    def _handle_selection(self, selected_ids=None):
        """Handle table selection changes."""
        # Use instance variable for recursion protection (defined in BaseView)
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            
            # Ignore the passed-in selected_ids parameter and calculate from table selection
            calculated_ids = set()
            for item in self.table.selectedItems():
                if item.column() == 0:  # Only process first column to avoid duplicates
                    node_id = item.data(Qt.ItemDataRole.UserRole)
                    if node_id:
                        calculated_ids.add(node_id)
            
            self.selection_changed.emit(calculated_ids)
        finally:
            self._is_processing_selection = False
            
    def _handle_sort(self, column_index: int):
        """Handle column header clicks for sorting."""
        current_direction = self.table.horizontalHeader().sortIndicatorOrder()
        direction = "desc" if current_direction == Qt.SortOrder.AscendingOrder else "asc"
        
        # Map column index to name
        columns = ['artist', 'album', 'year', 'genre', 'country', 'vocal_style', 'tags']
        if 0 <= column_index < len(columns):
            self.sort_changed.emit(columns[column_index], direction)
            
            # Update sort indicator
            self.table.horizontalHeader().setSortIndicator(
                column_index,
                Qt.SortOrder.DescendingOrder if direction == "desc"
                else Qt.SortOrder.AscendingOrder
            )
    
    def _show_context_menu(self, position):
        """Show context menu for table row."""
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        album_item = self.table.item(row, 0)
        if not album_item:
            return
        
        album_id = album_item.data(Qt.ItemDataRole.UserRole)
        if not album_id:
            return
        
        menu = QMenu(self)
        
        show_similar_action = QAction("Show Similar Albums", self)
        show_similar_action.triggered.connect(lambda: self._request_show_similar(album_id))
        menu.addAction(show_similar_action)
        
        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def _request_show_similar(self, album_id: str):
        """Request to show similar albums for the given album."""
        graphics_logger.info(f"Requesting to show similar albums for: {album_id}")
        self.show_similar_requested.emit(album_id)