"""Table visualization view."""
from typing import Dict, Any, List
from PyQt6.QtWidgets import (QTableView, QHeaderView, QAbstractItemView, 
                           QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                           QLabel, QCheckBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QItemSelectionModel
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QCursor

from .base_view import BaseView
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger
from albumexplore.gui.favorites import get_favorites_manager
from .table_model import AlbumTableModel, AlbumProxyModel

class TableView(BaseView):
    """Table visualization view."""
    
    sort_changed = pyqtSignal(str, str)  # column, direction
    show_similar_requested = pyqtSignal(str)  # album_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.TABLE
        self._fav_mgr = get_favorites_manager()
        
        # Setup models
        self.source_model = AlbumTableModel(self._fav_mgr)
        self.proxy_model = AlbumProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        
        self._setup_ui()
        
        # Signals
        self._fav_mgr.favorites_changed.connect(self._on_favorites_changed)
        graphics_logger.debug("Table view initialized with QTableView")
        
    def _setup_ui(self):
        """Set up UI elements."""
        layout = self.layout() or QVBoxLayout(self)
        layout.setSpacing(10)
        
        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search
        search_label = QLabel("Search:")
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Refine by artist, album, tags, etc...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        
        toolbar_layout.addWidget(search_label)
        toolbar_layout.addWidget(self.search_input, 1) # Stretch
        
        # Filters
        self.fav_only_checkbox = QCheckBox("❤️ Favorites only")
        self.fav_only_checkbox.setToolTip("Show only favorite albums")
        self.fav_only_checkbox.stateChanged.connect(self._on_fav_filter_changed)
        toolbar_layout.addWidget(self.fav_only_checkbox)
        
        layout.addLayout(toolbar_layout)

        # Keyboard shortcut for search
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.search_input.setFocus)
        
        # --- Table View ---
        self.table = QTableView(self)
        self.table.setModel(self.proxy_model)
        
        # Appearance
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        
        # Columns
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Vertical header (row numbers) - hide them for cleaner look
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32) # row height
        
        layout.addWidget(self.table)
        
        # --- Status Bar ---
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Interaction
        self.table.clicked.connect(self._on_table_clicked)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        
        # Context Menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Selection
        self.table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

    def update_data(self, render_data: Dict[str, Any], edges=None):
        """Update table data."""
        super().update_data(render_data)
        
        if 'rows' not in render_data:
            return
            
        rows = render_data['rows']
        self.source_model.set_data(rows)
        
        # Update selection if ids provided
        self._restore_selection(render_data.get('selected_ids', []))
        
        self._update_status()
        self._resize_columns_to_content()
        
    def _resize_columns_to_content(self):
        # Resize some columns to content, but keep some constrained
        # Fav
        self.table.setColumnWidth(AlbumTableModel.COL_FAV, 30)
        # Year
        self.table.setColumnWidth(AlbumTableModel.COL_YEAR, 50)
        # Stats
        self.table.setColumnWidth(AlbumTableModel.COL_PLAYS, 70)
        self.table.setColumnWidth(AlbumTableModel.COL_LISTENERS, 70)
        
        # Artist/Album get default width or initial resize
        if self.source_model.rowCount() > 0:
            self.table.resizeColumnToContents(AlbumTableModel.COL_ARTIST)
            self.table.resizeColumnToContents(AlbumTableModel.COL_ALBUM)
            
            # Cap width so they don't take over everything
            if self.table.columnWidth(AlbumTableModel.COL_ARTIST) > 300:
                self.table.setColumnWidth(AlbumTableModel.COL_ARTIST, 300)
            if self.table.columnWidth(AlbumTableModel.COL_ALBUM) > 300:
                self.table.setColumnWidth(AlbumTableModel.COL_ALBUM, 300)

    def _on_search_changed(self, text):
        self.proxy_model.set_filter_text(text)
        self._update_status()
        
    def _on_fav_filter_changed(self, state):
        self.proxy_model.set_fav_only(state == Qt.CheckState.Checked.value)
        self._update_status()
        
    def _update_status(self):
        total = self.source_model.rowCount()
        visible = self.proxy_model.rowCount()
        msg = f"Showing {visible:,} albums"
        if visible != total:
            msg += f" (filtered from {total:,})"
        self.status_label.setText(msg)

    def _on_table_clicked(self, index):
        if not index.isValid():
            return
            
        # Check if favorite column
        # Map proxy index to source index? No, data() handles logic but structure is same for cols
        if index.column() == AlbumTableModel.COL_FAV:
            # Toggle favorite
            source_idx = self.proxy_model.mapToSource(index)
            item_data = self.source_model.data(source_idx, Qt.ItemDataRole.UserRole)
            if item_data:
                aid = item_data.get('id')
                # Toggle via manager
                self._fav_mgr.toggle(aid)
                # The view will refresh via _on_favorites_changed
    
    def _on_table_double_clicked(self, index):
        if not index.isValid():
            return
        # Double click to show similar albums?
        source_idx = self.proxy_model.mapToSource(index)
        item_data = self.source_model.data(source_idx, Qt.ItemDataRole.UserRole)
        if item_data:
             self._request_show_similar(item_data.get('id'))

    def _on_favorites_changed(self):
        # Invalidate favorite column or whole model
        # Just notify data changed for all rows, col 0
        top_left = self.source_model.index(0, AlbumTableModel.COL_FAV)
        bottom_right = self.source_model.index(self.source_model.rowCount()-1, AlbumTableModel.COL_FAV)
        self.source_model.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        
    def _on_table_selection_changed(self, selected, deselected):
        if self._is_processing_selection:
            return

        # Calculate IDs from current selection
        calculated_ids = set()
        selection_model = self.table.selectionModel()
        
        # Map selected rows to source IDs
        # selection_model.selectedRows() returns indexes in proxy model
        for proxy_idx in selection_model.selectedRows():
            source_idx = self.proxy_model.mapToSource(proxy_idx)
            # Get ID from source model (UserRole + 1)
            aid = self.source_model.data(source_idx, Qt.ItemDataRole.UserRole + 1)
            if aid:
                calculated_ids.add(aid)
        
        # Let BaseView handle updates and emission
        super()._handle_selection(calculated_ids)

    def _restore_selection(self, selected_ids_list):
        if not selected_ids_list:
            return
            
        ids_set = set(selected_ids_list)
        
        # Block signals to avoid feedback loop
        self.table.blockSignals(True)
        self.table.selectionModel().clearSelection()
        
        # This implementation iterates visible rows.
        selection_mode = QItemSelectionModel.SelectionFlag.Valid | QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        
        for row in range(self.proxy_model.rowCount()):
            idx = self.proxy_model.index(row, 0)
            source_idx = self.proxy_model.mapToSource(idx)
            aid = self.source_model.data(source_idx, Qt.ItemDataRole.UserRole + 1)
            
            if aid in ids_set:
                self.table.selectionModel().select(idx, selection_mode)
                
        self.table.blockSignals(False)

    def _show_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return
            
        source_idx = self.proxy_model.mapToSource(index)
        item_data = self.source_model.data(source_idx, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
            
        album_id = item_data.get('id')
        
        menu = QMenu(self)
        
        similar_action = QAction("Show Similar Albums", self)
        similar_action.triggered.connect(lambda: self._request_show_similar(album_id))
        menu.addAction(similar_action)
        
        is_fav = self._fav_mgr.is_favorite(album_id)
        fav_action = QAction(f"{'Unfavorite' if is_fav else 'Favorite'} Album", self)
        fav_action.triggered.connect(lambda: self._fav_mgr.toggle(album_id))
        menu.addAction(fav_action)

        menu.exec(QCursor.pos())

    def _request_show_similar(self, album_id: str):
        graphics_logger.info(f"Requesting to show similar albums for: {album_id}")
        self.show_similar_requested.emit(album_id)
