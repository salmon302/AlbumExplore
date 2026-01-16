"""Table visualization view."""
from typing import Dict, Any
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                          QAbstractItemView, QVBoxLayout, QMenu,
                          QLineEdit, QHBoxLayout, QPushButton, QLabel, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from .base_view import BaseView
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger
from albumexplore.gui.favorites import get_favorites_manager

class TableView(BaseView):
    """Table visualization view."""
    
    sort_changed = pyqtSignal(str, str)  # column, direction
    show_similar_requested = pyqtSignal(str)  # album_id - signal to request similarity view
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.TABLE
        self._all_rows = []  # Cache all rows for filtering
        self._filtered_row_indices = []  # Indices of visible rows after filtering
        self._batch_size = 100  # Number of rows to render at once
        self._setup_ui()
        graphics_logger.debug("Table view initialized")
    
    def _setup_ui(self):
        """Set up UI elements."""
        # Create search bar
        layout = self.layout() or QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search artist, album, tags, genre, country, vocal style...")
        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.setToolTip("Clear search and show all rows")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.clear_search_btn)
        # "Only favorites" checkbox
        self.fav_only_checkbox = QCheckBox("Only favorites")
        self.fav_only_checkbox.setToolTip("Show only favorite albums in the table")
        # Connect checkbox to filter (stateChanged emits int, _apply_filter will handle optional arg)
        self.fav_only_checkbox.stateChanged.connect(self._apply_filter)
        search_layout.addWidget(self.fav_only_checkbox)

        layout.addLayout(search_layout)

        # Keyboard shortcut to focus search
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._focus_search)

        # Create table (add a favorites column at index 0)
        self.table = QTableWidget(self)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'Fav', 'Artist', 'Album', 'Year', 'Genre', 'Country', 'Vocal Style', 'Tags', 'Plays', 'Listeners'
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
        # Connect search signals
        self.search_input.textChanged.connect(self._apply_filter)
        self.clear_search_btn.clicked.connect(lambda: self.search_input.setText(''))
        
        # Favorites manager
        self._fav_mgr = get_favorites_manager()
        self._fav_mgr.favorites_changed.connect(self._on_favorites_changed)
    
    def update_data(self, render_data: Dict[str, Any], edges=None):
        """Update table data with batch rendering for performance."""
        super().update_data(render_data)
        
        if 'rows' not in render_data:
            return
        
        # Store all rows for filtering
        self._all_rows = render_data['rows']
        self._filtered_row_indices = list(range(len(self._all_rows)))
        
        # Initially render only first batch
        self._render_visible_rows()
        
        # Update selection
        self.table.clearSelection()
        if 'selected_ids' in render_data:
            selected_ids = set(render_data['selected_ids'])
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 1)  # artist column holds the id
                if item and item.data(Qt.ItemDataRole.UserRole) in selected_ids:
                    self.table.selectRow(row)
        
        graphics_logger.debug(f"Updated table view with {len(self._all_rows)} total rows, showing first {min(self._batch_size, len(self._all_rows))}")
        
        # Re-apply filter after populating rows so the search stays in effect
        try:
            current_search = self.search_input.text() if hasattr(self, 'search_input') else ''
            if current_search:
                self._apply_filter(current_search)
        except Exception:
            # Don't let filtering errors break the UI
            graphics_logger.exception("Error applying search filter after data update")
    
    def _render_visible_rows(self):
        """Render only visible rows for better performance."""
        visible_count = min(len(self._filtered_row_indices), self._batch_size)
        self.table.setRowCount(visible_count)
        
        for display_row in range(visible_count):
            data_row_idx = self._filtered_row_indices[display_row]
            row = self._all_rows[data_row_idx]
            self._populate_row(display_row, row)
    
    def _populate_row(self, row_idx: int, row: Dict[str, Any]):
        """Populate a single table row."""
        album_id = row.get('id')

        # Favorite button in column 0
        try:
            fav_btn = QPushButton(self)
            fav_btn.setFlat(True)
            fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_fav = self._fav_mgr.is_favorite(album_id) if album_id else False
            fav_btn.setText('★' if is_fav else '☆')
            fav_btn.setToolTip('Toggle favorite')
            # Closure to capture album_id and button reference
            def _make_handler(aid, btn):
                return lambda checked=False: self._toggle_favorite(aid, btn)
            fav_btn.clicked.connect(_make_handler(album_id, fav_btn))
            self.table.setCellWidget(row_idx, 0, fav_btn)
        except Exception:
            graphics_logger.exception('Failed to create favorite button')

        # Artist
        artist_data = row.get('artist', '')
        artist_name = str(artist_data) if artist_data is not None else ''
        item = QTableWidgetItem(artist_name)
        item.setData(Qt.ItemDataRole.UserRole, album_id)
        self.table.setItem(row_idx, 1, item)

        # Album
        self.table.setItem(row_idx, 2,
                         QTableWidgetItem(row.get('album', '')))

        # Year
        year_val = row.get('year', '')
        year_item = QTableWidgetItem()
        year_item.setData(Qt.ItemDataRole.DisplayRole, year_val)
        self.table.setItem(row_idx, 3, year_item)

        # Genre
        self.table.setItem(row_idx, 4,
                         QTableWidgetItem(row.get('genre', '')))

        # Country
        self.table.setItem(row_idx, 5,
                         QTableWidgetItem(row.get('country', '')))

        # Vocal style
        vocal_style_value = row.get('vocal_style', '')
        self.table.setItem(row_idx, 6,
                         QTableWidgetItem(vocal_style_value))

        # Tags
        tags = row.get('tags', [])
        self.table.setItem(row_idx, 7,
                         QTableWidgetItem(', '.join(tags)))

        # Plays (Last.fm)
        playcount = row.get('playcount')
        play_item = QTableWidgetItem(f"{playcount:,}" if playcount is not None else "")
        play_item.setData(Qt.ItemDataRole.DisplayRole, playcount if playcount is not None else 0)
        play_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row_idx, 8, play_item)

        # Listeners (Last.fm)
        listeners = row.get('listeners')
        list_item = QTableWidgetItem(f"{listeners:,}" if listeners is not None else "")
        list_item.setData(Qt.ItemDataRole.DisplayRole, listeners if listeners is not None else 0)
        list_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row_idx, 9, list_item)
    
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
                # Artist column (1) contains the album id
                if item.column() == 1:
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
        
        # Map column index to name (accounts for favorite column at index 0)
        columns = ['favorite', 'artist', 'album', 'year', 'genre', 'country', 'vocal_style', 'tags', 'playcount', 'listeners']
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
        album_item = self.table.item(row, 1)  # artist column contains album id
        if not album_item:
            return
        
        album_id = album_item.data(Qt.ItemDataRole.UserRole)
        if not album_id:
            return
        
        menu = QMenu(self)
        
        show_similar_action = QAction("Show Similar Albums", self)
        show_similar_action.triggered.connect(lambda: self._request_show_similar(album_id))
        menu.addAction(show_similar_action)
        
        try:
            fav_action = QAction("Toggle Favorite", self)
            fav_action.triggered.connect(lambda: self._toggle_favorite(album_id))
            menu.addAction(fav_action)
        except Exception:
            pass

        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def _request_show_similar(self, album_id: str):
        """Request to show similar albums for the given album."""
        graphics_logger.info(f"Requesting to show similar albums for: {album_id}")
        self.show_similar_requested.emit(album_id)

    def _toggle_favorite(self, album_id: str, btn: QPushButton = None):
        try:
            now_fav = self._fav_mgr.toggle(album_id)
            if btn is not None:
                btn.setText('★' if now_fav else '☆')
        except Exception:
            graphics_logger.exception('Error toggling favorite')

    def _on_favorites_changed(self):
        # Update favorite buttons for all rows
        try:
            for r in range(self.table.rowCount()):
                artist_item = self.table.item(r, 1)
                if not artist_item:
                    continue
                aid = artist_item.data(Qt.ItemDataRole.UserRole)
                w = self.table.cellWidget(r, 0)
                if isinstance(w, QPushButton):
                    w.setText('★' if self._fav_mgr.is_favorite(aid) else '☆')
            # Re-apply filter in case "Only favorites" is active so visibility updates
            try:
                self._apply_filter()
            except Exception:
                pass
        except Exception:
            graphics_logger.exception('Error refreshing favorite buttons')

    def _apply_filter(self, text=None):
        """Filter table rows by searching across multiple columns.

        The search is case-insensitive and treats whitespace-separated tokens as
        ANDed terms (all tokens must be present somewhere in the row text).
        """
        try:
            # Support being called from checkbox stateChanged which passes an int
            current_text = text if isinstance(text, str) else (self.search_input.text() if hasattr(self, 'search_input') else '')
            tokens = [t.strip().lower() for t in current_text.split() if t.strip()]

            only_favs = getattr(self, 'fav_only_checkbox', None) and self.fav_only_checkbox.isChecked()
            favs = self._fav_mgr.all() if only_favs else None

            # If no filters, show all rows
            if not tokens and not only_favs:
                self._filtered_row_indices = list(range(len(self._all_rows)))
                self._render_visible_rows()
                return

            # Filter rows based on search criteria
            self._filtered_row_indices = []
            for idx, row in enumerate(self._all_rows):
                # Check favorites filter
                if favs is not None:
                    aid = row.get('id')
                    if aid not in favs:
                        continue
                
                # Check search tokens if present
                if tokens:
                    # Build searchable text from all columns
                    searchable_parts = [
                        str(row.get('artist', '')),
                        str(row.get('album', '')),
                        str(row.get('year', '')),
                        str(row.get('genre', '')),
                        str(row.get('country', '')),
                        str(row.get('vocal_style', '')),
                        ', '.join(row.get('tags', []))
                    ]
                    combined_text = ' '.join(searchable_parts).lower()
                    
                    # All tokens must be present
                    if not all(tok in combined_text for tok in tokens):
                        continue
                
                # Row passes all filters
                self._filtered_row_indices.append(idx)
            
            # Re-render with filtered rows
            self._render_visible_rows()
            
        except Exception:
            graphics_logger.exception("Error during table search filtering")

    def _focus_search(self):
        if hasattr(self, 'search_input'):
            self.search_input.setFocus()
            self.search_input.selectAll()