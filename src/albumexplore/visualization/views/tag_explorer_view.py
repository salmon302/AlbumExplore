from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollBar,
                           QWidget, QPushButton, QLabel, QMenu, QSplitter,
                           QComboBox, QRadioButton, QButtonGroup, QToolButton, 
                           QStackedWidget, QLineEdit, QCheckBox, QDialog, QMessageBox) # Added QDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSortFilterProxyModel, QRegularExpression, QTime # Added QTime
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QPainter, QFontMetrics, QPalette, QAction # Added QAction
from typing import Dict, Any, Set, List, Optional
from collections import Counter, defaultdict
import pandas as pd # Added pandas import

from .base_view import BaseView
from ..state import ViewType, ViewState
from ...tags.normalizer import TagNormalizer
from ...tags.analysis.single_instance_handler import SingleInstanceHandler
from ...tags.analysis.tag_analyzer import TagAnalyzer
from ...tags.analysis.tag_similarity import TagSimilarity
from .tag_cloud_widget import TagCloudWidget
from .single_instance_dialog import SingleInstanceDialog # Added import
from albumexplore.gui.gui_logging import graphics_logger # Added import

# Ensure we're properly importing tag cloud widget
try:
    from .tag_cloud_widget import TagCloudWidget
    from .tag_cloud_widget import CloudTag
except ImportError as e:
    from albumexplore.gui.gui_logging import gui_logger
    gui_logger.error(f"Failed to import TagCloudWidget: {str(e)}")
    
    # Create a minimal fallback implementation to prevent crashes
    class CloudTag:
        def __init__(self, text, weight, x=0, y=0):
            self.text = text
            self.weight = weight
            self.x = x
            self.y = y
    
    class TagCloudWidget(QWidget):
        tagClicked = pyqtSignal(str)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.tags = {}
            
        def update_tags(self, tag_counts):
            pass
            
        def update_filter_states(self, tag_filters):
            pass

# Simple table widget item that provides proper sorting
class SortableTableWidgetItem(QTableWidgetItem):
    """Custom table widget item for proper sorting."""
    
    def __lt__(self, other):
        my_data = self.data(Qt.ItemDataRole.UserRole)
        other_data = other.data(Qt.ItemDataRole.UserRole)

        if my_data is not None and other_data is not None:
            # Try direct numeric comparison if types are already numeric
            if isinstance(my_data, (int, float)) and isinstance(other_data, (int, float)):
                return my_data < other_data
            
            # Try conversion to float if not directly numeric
            try:
                val_my_data = float(my_data)
                val_other_data = float(other_data)
                return val_my_data < val_other_data
            except (ValueError, TypeError):
                # If UserRole data cannot be converted to numeric, fall back to string comparison of display text
                return self.text() < other.text()
        
        # Fallback to default QTableWidgetItem comparison (based on display text)
        return super().__lt__(other)


class TagExplorerView(BaseView):
    """Tag-based album exploration view."""
    
    # Enum-like constants for tag filter states
    FILTER_INCLUDE = 1
    FILTER_EXCLUDE = 2
    FILTER_NEUTRAL = 0
    
    # Enum-like constants for view modes
    MODE_TABLE = 0
    MODE_CLOUD = 1
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setUpdatesEnabled(False)
        self.view_state = ViewState(ViewType.TAG_EXPLORER)
        self.tag_normalizer = TagNormalizer()
        
        # For storing data
        self.album_nodes_original = [] # Store original album node data
        self.tag_counts = Counter()        # Processed tags (normalized or cleaned raw) for display and filtering, and their counts
        self.raw_tag_counts = Counter()    # Raw tag counts before any processing
        self.matching_counts = Counter()   # Tags in current filtered selection (reflects normalization state)
        self.tag_filters = {}              # Current filter state for each tag (keys are processed tags)
        self.filtered_albums = []          # Stores Node objects that match current filters
        self.normalized_mapping = {}       # Mapping from original raw to its processed form (primarily for reference)
        self.single_instance_tags = set()  # Tags that appear only once
        self.tag_mode = self.MODE_TABLE    # Current tag visualization mode
        
        # Advanced tag analysis components (initialized in process_tag_data)
        self.tag_analyzer = None
        self.tag_similarity = None
        self.single_instance_handler = None
        
        # Setup UI components
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create tag panel widget
        self.tag_panel = QWidget()
        self.tag_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        tag_panel_layout = QVBoxLayout(self.tag_panel)
        
        # Add tag filter controls
        self.filter_header = QWidget()
        filter_header_layout = QHBoxLayout(self.filter_header)
        filter_header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.tag_count_label = QLabel("Tags: 0")
        filter_header_layout.addWidget(self.tag_count_label)
        
        # Search input for tags
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("Search tags and press Enter...")
        self.tag_search_input.returnPressed.connect(self._handle_tag_search)
        filter_header_layout.addWidget(self.tag_search_input)
        
        self.tag_search_button = QPushButton("Search Tag")
        self.tag_search_button.clicked.connect(self._handle_tag_search)
        filter_header_layout.addWidget(self.tag_search_button)
        
        # Add view mode selector
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Table View", "Cloud View"])
        self.view_mode_combo.currentIndexChanged.connect(self._change_tag_view_mode)
        filter_header_layout.addWidget(self.view_mode_combo)
        
        # Add normalization toggle
        self.normalize_checkbox = QCheckBox("Normalize Tags")
        self.normalize_checkbox.setChecked(True)  # Default to normalization enabled
        self.normalize_checkbox.stateChanged.connect(self._toggle_normalization)
        filter_header_layout.addWidget(self.normalize_checkbox)
        
        filter_header_layout.addStretch()
        
        # Add export button
        self.export_button = QPushButton("Export Tags")
        self.export_button.setToolTip("Export tag data to console for analysis")
        self.export_button.clicked.connect(self._export_tag_data)
        filter_header_layout.addWidget(self.export_button)
        
        # Add single-instance tag management button
        self.manage_singles_button = QPushButton("Manage Singles")
        self.manage_singles_button.setToolTip("Manage single-instance tags")
        self.manage_singles_button.clicked.connect(self._show_single_instance_dialog)
        filter_header_layout.addWidget(self.manage_singles_button)
        
        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.clicked.connect(self.clear_tag_filters)
        filter_header_layout.addWidget(self.clear_filters_button)
        
        tag_panel_layout.addWidget(self.filter_header)
        
        # Create tag views stack
        self.tag_views_stack = QStackedWidget()
        
        # Create tag table
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(4)
        self.tags_table.setHorizontalHeaderLabels(["Tag", "Count", "Matching", "Filter"])
        
        # Configure tag table headers
        header = self.tags_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Tag name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Filter column
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        # header.setSortIndicatorShown(True) # Managed manually
        header.sectionClicked.connect(self._handle_tag_sort)
        
        self.tags_table.setShowGrid(True)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSortingEnabled(False) # Disable native sorting, will handle manually
        self.tags_sort_column = 1  # Default sort by count (index 1)
        self.tags_sort_order = Qt.SortOrder.DescendingOrder
        # self.tags_table.cellDoubleClicked.connect(self._cycle_tag_filter_state) # Ensure this is removed or commented

        # Add tag views (table and cloud) to the QStackedWidget
        self.tag_views_stack.addWidget(self.tags_table)
        self.tag_cloud_widget = TagCloudWidget(self) # Initialize TagCloudWidget
        self.tag_views_stack.addWidget(self.tag_cloud_widget)
        
        # Add the QStackedWidget (tag_views_stack) to the tag_panel_layout
        tag_panel_layout.addWidget(self.tag_views_stack)

        # Create the album panel, its layout, and its widgets (album_count_label, album_table)
        self.album_panel = QWidget()
        self.album_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        album_panel_layout = QVBoxLayout(self.album_panel)

        self.album_count_label = QLabel("Albums: 0")
        album_panel_layout.addWidget(self.album_count_label)

        self.album_table = QTableWidget() # Definition of self.album_table
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        album_header = self.album_table.horizontalHeader()
        album_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.album_table.setSortingEnabled(True)
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setShowGrid(True)
        self.album_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.album_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        album_panel_layout.addWidget(self.album_table)

        # Add both panels to the splitter
        self.splitter.addWidget(self.tag_panel)
        self.splitter.addWidget(self.album_panel)
        
        # Set initial sizes (30% for tags, 70% for albums)
        self.splitter.setSizes([300, 700])
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Setup right-click menu for tag table
        self.tags_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tags_table.customContextMenuRequested.connect(self._show_tag_context_menu)
        
        # Setup timers for batch processing
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_updates)
        self._pending_updates = []
        
        self._selection_timer = QTimer(self)
        self._selection_timer.setSingleShot(True)
        self._selection_timer.timeout.connect(self._process_selection)
        self._pending_selection = set()
        
        # Add paint optimization flags
        self._needs_full_update = False
        self._last_paint_time = 0
        self._paint_throttle = 16  # ~60fps
        
        # Set unified styling
        self._apply_unified_styling()
        
        self.setUpdatesEnabled(True)  # Re-enable updates
    
    def _process_selection(self):
        """Placeholder for processing pending selections."""
        graphics_logger.info("TagExplorerView._process_selection called (placeholder)")
        # Actual implementation will process self._pending_selection
        pass

    def _reprocess_base_tag_data(self):
        """
        Repopulate raw_tag_counts and tag_counts (and normalized_mapping)
        from album_nodes_original based on the current normalization state.
        self.tag_counts will hold tags ready for display and filtering.
        """
        self.raw_tag_counts.clear()
        self.tag_counts.clear()
        self.normalized_mapping.clear()

        is_normalization_active = self.tag_normalizer.is_active()

        for node in self.album_nodes_original:
            raw_tags_from_node = node.get("tags", [])

            for raw_tag in raw_tags_from_node:
                if not raw_tag:  # Skip empty raw tags
                    continue
                
                self.raw_tag_counts[raw_tag] += 1
                
                processed_tag_for_display_and_filtering = ""
                if is_normalization_active:
                    normalized_tag = self.tag_normalizer.normalize(raw_tag)
                    if normalized_tag:
                        processed_tag_for_display_and_filtering = normalized_tag
                        self.normalized_mapping[raw_tag] = normalized_tag
                    # If normalization results in an empty tag, it's effectively filtered out here for self.tag_counts
                else: # Normalization is not active, use the "cleaned" raw tag
                    cleaned_raw_tag = self.tag_normalizer.normalize(raw_tag) # normalizer.normalize also cleans when inactive
                    if cleaned_raw_tag:
                        processed_tag_for_display_and_filtering = cleaned_raw_tag
                
                if processed_tag_for_display_and_filtering:
                    self.tag_counts[processed_tag_for_display_and_filtering] += 1
        
        graphics_logger.debug(f"Reprocessed base tag data. Raw tags: {len(self.raw_tag_counts)}, Processed tags for display: {len(self.tag_counts)}")

    def apply_tag_filters(self):
        """Apply current tag filters to the album list and update views."""
        self.setUpdatesEnabled(False)
        graphics_logger.debug(f"Applying tag filters. Normalization active: {self.tag_normalizer.is_active()}")
        graphics_logger.debug(f"Current tag_filters: {self.tag_filters}")

        # Keys in self.tag_filters are processed tags (normalized or cleaned raw)
        include_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_INCLUDE}
        exclude_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_EXCLUDE}

        self.filtered_albums.clear()
        self.matching_counts.clear() # This will be populated with processed tags

        is_normalization_active = self.tag_normalizer.is_active()
        
        for node in self.album_nodes_original: # Iterate over the original stored nodes
            node_raw_tags = node.get("tags", [])
            
            # Determine the set of processed tags for the current node, based on normalization state
            current_node_processed_tags = []
            if is_normalization_active:
                normalized_node_tags = [self.tag_normalizer.normalize(tag) for tag in node_raw_tags]
                current_node_processed_tags = [tag for tag in normalized_node_tags if tag]
            else:
                cleaned_raw_node_tags = [self.tag_normalizer.normalize(tag) for tag in node_raw_tags] # normalizer also cleans
                current_node_processed_tags = [tag for tag in cleaned_raw_node_tags if tag]

            # Check if the node matches the include filters (filters use processed tags)
            if include_filters and not any(tag in include_filters for tag in current_node_processed_tags):
                continue

            # Check if the node matches the exclude filters
            if exclude_filters and any(tag in exclude_filters for tag in current_node_processed_tags):
                continue

            # If we reach here, the node matches the current filters
            self.filtered_albums.append(node) # Store the original node object
            for tag in current_node_processed_tags: # These are the processed tags that made the album match
                self.matching_counts[tag] += 1

        # Update tag views and album count label
        self._update_tag_views() 
        self._update_album_table_display() # ADDED: Update the album table display
        # self._update_album_count_label() # This is now called within _update_album_table_display

        self.setUpdatesEnabled(True)
    
    def _update_tag_views(self):
        """Update the tag views (table and cloud) with the current tag data."""
        self.setUpdatesEnabled(False)
        
        # self.matching_counts is populated by apply_tag_filters. No need to update it here.

        # Update tag table
        self.tags_table.setRowCount(0)
        # self.tag_counts contains processed tags (normalized or cleaned raw)
        for tag, count in self.tag_counts.items(): 
            filter_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL) # Keys in tag_filters match tags in tag_counts
            matching_count = self.matching_counts.get(tag, 0) # Keys in matching_counts also match
            row_position = self.tags_table.rowCount()
            self.tags_table.insertRow(row_position)

            # Tag column (Column 0)
            tag_item = SortableTableWidgetItem(tag)
            self.tags_table.setItem(row_position, 0, tag_item)

            # Count column (Column 1)
            count_item = SortableTableWidgetItem(str(count)) # Display string
            count_item.setData(Qt.ItemDataRole.UserRole, int(count)) # Store actual int for numeric sort
            self.tags_table.setItem(row_position, 1, count_item)
            
            # Matching column (Column 2)
            matching_item = SortableTableWidgetItem(str(matching_count)) # Display string
            matching_item.setData(Qt.ItemDataRole.UserRole, int(matching_count)) # Store actual int for numeric sort
            self.tags_table.setItem(row_position, 2, matching_item)

            # Filter column (Column 3)
            filter_text = "Neutral"
            if filter_state == self.FILTER_INCLUDE:
                filter_text = "Include"
            elif filter_state == self.FILTER_EXCLUDE:
                filter_text = "Exclude"
            # Use standard QTableWidgetItem for Filter column as it's not typically sorted by value
            filter_q_item = QTableWidgetItem(filter_text)
            filter_q_item.setData(Qt.ItemDataRole.UserRole, filter_state) # Store state if needed
            self.tags_table.setItem(row_position, 3, filter_q_item)

        # Update tag cloud widget
        self.tag_cloud_widget.update_tags(self.tag_counts)
        self.tag_cloud_widget.update_filter_states(self.tag_filters)
        
        # Sort the table based on the current sort column and order
        self.tags_table.sortItems(self.tags_sort_column, self.tags_sort_order)
        
        self.setUpdatesEnabled(True)
    
    def _update_album_count_label(self):
        """Update the album count label in the album panel."""
        self.album_count_label.setText(f"Albums: {len(self.filtered_albums)}")
    
    def _update_album_table_display(self):
        """Populate the album_table with data from self.filtered_albums."""
        # It's good practice to disable sorting during bulk updates for performance,
        # though self.album_table.setSortingEnabled(True) is set in __init__.
        # If issues arise, explicitly disable/enable sorting around population.
        # self.album_table.setSortingEnabled(False) 
        self.album_table.setRowCount(0) # Clear existing rows
        
        for album_node in self.filtered_albums:
            row_position = self.album_table.rowCount()
            self.album_table.insertRow(row_position)

            artist = album_node.get('artist', '')
            album_title = album_node.get('album', album_node.get('title', '')) 
            year_val = album_node.get('year', '')
            year_str = str(year_val)
            
            tags_list = album_node.get('tags', [])
            if isinstance(tags_list, list):
                tags_str = ", ".join(map(str, tags_list))
            else:
                tags_str = str(tags_list) # Fallback for unexpected type

            self.album_table.setItem(row_position, 0, QTableWidgetItem(artist))
            self.album_table.setItem(row_position, 1, QTableWidgetItem(album_title))
            
            year_item = QTableWidgetItem(year_str)
            # Attempt to set UserRole for potential numeric sorting if album_table uses SortableTableWidgetItem for year
            try:
                if year_val != '': # Avoid converting empty string
                    year_item.setData(Qt.ItemDataRole.UserRole, int(year_val))
            except (ValueError, TypeError):
                pass # Keep as text if not convertible to int
            self.album_table.setItem(row_position, 2, year_item)
            
            self.album_table.setItem(row_position, 3, QTableWidgetItem(tags_str))
        
        # self.album_table.setSortingEnabled(True) # Re-enable if disabled above
        # self.album_table.resizeColumnsToContents() # Optional: adjust column sizes

        self._update_album_count_label() # Ensure album count is also up-to-date

    def _process_updates(self):
        """Process pending updates to tag and album data."""
        self.setUpdatesEnabled(False)
        graphics_logger.debug(f"Processing {len(self._pending_updates)} pending updates.")
        
        changed = False
        for update in self._pending_updates:
            action, data_node = update # Assuming data is a node object
            if action == "add":
                self._add_album_data(data_node)
                changed = True
            elif action == "remove":
                self._remove_album_data(data_node)
                changed = True
            elif action == "modify":
                self._modify_album_data(data_node)
                changed = True
        
        self._pending_updates.clear()
        
        if changed:
            self._reprocess_base_tag_data() # Reprocess all tag data if original nodes changed
        
        self.apply_tag_filters()  # Reapply filters and update views
        
        self.setUpdatesEnabled(True)
    
    def _add_album_data(self, data_node):
        """Add new album data to the view's original data store."""
        self.album_nodes_original.append(data_node)
        # Actual tag counting is deferred to _reprocess_base_tag_data
    
    def _remove_album_data(self, data_node):
        """Remove album data from the view's original data store."""
        try:
            self.album_nodes_original.remove(data_node)
        except ValueError:
            graphics_logger.warning(f"Attempted to remove a node that was not in album_nodes_original: {data_node}")
        # Actual tag counting is deferred to _reprocess_base_tag_data

    def _modify_album_data(self, data_node):
        """Modify existing album data in the view's original data store."""
        # Assuming data_node has a unique identifier, e.g., in its .data attribute
        node_id_to_modify = data_node.data.get("id") # Example: using node.data['id']
        if node_id_to_modify is None:
            graphics_logger.warning("Cannot modify album data: node has no ID.")
            return
            
        for i, existing_node in enumerate(self.album_nodes_original):
            if existing_node.data.get("id") == node_id_to_modify:
                self.album_nodes_original[i] = data_node
                # Actual tag counting is deferred to _reprocess_base_tag_data
                return
        graphics_logger.warning(f"Attempted to modify a node not found in album_nodes_original: ID {node_id_to_modify}")

    def _change_tag_view_mode(self, index):
        """Change the tag view mode between table and cloud."""
        self.setUpdatesEnabled(False)
        self.tag_views_stack.setCurrentIndex(index)
        self.tag_mode = index
        
        # Update the display based on the new mode
        if index == self.MODE_TABLE:
            self.tags_table.setVisible(True)
            self.tag_cloud_widget.setVisible(False)
        else:
            self.tags_table.setVisible(False)
            self.tag_cloud_widget.setVisible(True)
            self.tag_cloud_widget.update_tags(self.tag_counts)  # Update cloud view
        
        self.setUpdatesEnabled(True)
    
    def _toggle_normalization(self, state):
        """Toggle tag normalization on or off."""
        self.setUpdatesEnabled(False) # Defer updates during processing
        if state == Qt.CheckState.Checked:
            self.tag_normalizer.set_active(True)
            graphics_logger.info("Tag normalization enabled.")
        else:
            self.tag_normalizer.set_active(False)
            graphics_logger.info("Tag normalization disabled.")
        
        # Clear existing filters as their context (normalized vs. raw keys) has changed.
        # User will need to re-apply filters if desired.
        self.tag_filters.clear()
        graphics_logger.debug("Tag filters cleared due to normalization change.")
        
        # Reprocess all tag data with the new normalization setting
        self._reprocess_base_tag_data() # This rebuilds self.tag_counts, self.raw_tag_counts

        # Apply filters (now empty) and update views accordingly
        self.apply_tag_filters() 
        self.setUpdatesEnabled(True)
    
    def clear_tag_filters(self):
        """Clear all active tag filters and refresh the view."""
        self.tag_filters.clear()
        self.apply_tag_filters() # This will refresh tables and matching counts
        graphics_logger.info("All tag filters cleared.")

    def _handle_tag_search(self):
        search_term_original = self.tag_search_input.text().strip()
        if not search_term_original:
            return

        # Process the search term according to the current normalization state
        # This ensures tag_to_filter_on matches the keys in self.tag_counts and self.tag_filters
        tag_to_filter_on = self.tag_normalizer.normalize(search_term_original) 

        if not tag_to_filter_on: 
            print(f"Search term '{search_term_original}' processed to an empty string or is invalid.")
            # self.tag_search_input.clear() # Optionally clear
            return
            
        # self.tag_counts contains the tags as they are currently displayed (normalized or cleaned raw)
        if tag_to_filter_on in self.tag_counts:
            # Apply this tag as an "include" filter
            self.tag_filters[tag_to_filter_on] = self.FILTER_INCLUDE
            
            self.apply_tag_filters() # This will refresh tables and matching counts
            
            # self.tag_search_input.clear() # Optionally clear after successful search

            # Scroll to the tag in the tags_table
            # The tag displayed in the table (item.text()) should be tag_to_filter_on
            for row in range(self.tags_table.rowCount()):
                item = self.tags_table.item(row, 0)
                if item and item.text() == tag_to_filter_on:
                    self.tags_table.scrollToItem(item, QTableWidget.ScrollHint.PositionAtCenter)
                    self.tags_table.selectRow(row) # Optionally select the row
                    break
        else:
            # Tag not found in the current displayable tag list (self.tag_counts)
            print(f"Tag '{search_term_original}' (searched as '{tag_to_filter_on}') not found in the current tag list.")
            # self.tag_search_input.clear() # Optionally clear if tag not found

    def _export_tag_data(self):
        """Exports tag data to the console for analysis."""
        graphics_logger.info("Exporting tag data...")
        # This is a placeholder. Implement actual export logic here.
        # For example, print raw_tag_counts, tag_counts, or filtered_albums tags.
        print("--- Raw Tag Counts ---")
        for tag, count in self.raw_tag_counts.most_common(20): # Print top 20 raw tags
            print(f"{tag}: {count}")
        print("\n--- Processed Tag Counts (Current Normalization) ---")
        for tag, count in self.tag_counts.most_common(20): # Print top 20 processed tags
            print(f"{tag}: {count}")
        
        if self.tag_normalizer.is_active():
            print("\n--- Normalized Tag Mappings ---")
            if self.normalized_mapping:
                for raw_tag, normalized_tag in self.normalized_mapping.items():
                    if raw_tag != normalized_tag: # Only print if actual change occurred
                        print(f"'{raw_tag}' -> '{normalized_tag}'")
            else:
                print("No tags were altered by normalization (or mapping is empty).")
        
        print("\n--- Tag Filters Active ---")
        if self.tag_filters:
            for tag, state in self.tag_filters.items():
                state_str = "INCLUDE" if state == self.FILTER_INCLUDE else "EXCLUDE" if state == self.FILTER_EXCLUDE else "NEUTRAL"
                print(f"{tag}: {state_str}")
        else:
            print("No active tag filters.")
        graphics_logger.info("Tag data export placeholder executed.")

    def _show_single_instance_dialog(self):
        """Shows a dialog to manage single-instance tags."""
        graphics_logger.info("Showing single-instance dialog (placeholder)...")
        # This is a placeholder. Implement actual dialog logic here.
        # Example:
        # if self.single_instance_handler:
        #     dialog = SingleInstanceDialog(self.single_instance_handler, self)
        #     dialog.exec()
        # else:
        #     QMessageBox.information(self, "Single Instance Tags", "Tag analysis data not yet available.")
        pass

    def _handle_tag_sort(self, column_index):
        """Handles sorting of the tag table when a header is clicked."""
        graphics_logger.debug(f"Tag table sort requested for column: {column_index}")
        
        # Column 3 (Filter) is not sortable by value, but we could cycle states or show menu.
        # For now, we make it non-sortable in the traditional sense.
        if column_index == 3:  
            return

        if self.tags_sort_column == column_index:
            self.tags_sort_order = Qt.SortOrder.DescendingOrder if self.tags_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.tags_sort_column = column_index
            self.tags_sort_order = Qt.SortOrder.AscendingOrder # Default to ascending for new column

        self._update_tag_views() # This will re-populate and apply sort via tags_table.sortItems

    def _show_tag_context_menu(self, position):
        """Shows the tag context menu."""
        item = self.tags_table.itemAt(position)
        if not item:
            return

        row = item.row()
        tag_item = self.tags_table.item(row, 0)
        if not tag_item:
            return
            
        tag_name = tag_item.text()

        menu = QMenu()
        include_action = menu.addAction("Include Tag")
        exclude_action = menu.addAction("Exclude Tag")
        neutral_action = menu.addAction("Set to Neutral")

        action = menu.exec(self.tags_table.mapToGlobal(position))

        if action == include_action:
            self.tag_filters[tag_name] = self.FILTER_INCLUDE
        elif action == exclude_action:
            self.tag_filters[tag_name] = self.FILTER_EXCLUDE
        elif action == neutral_action:
            if tag_name in self.tag_filters:
                del self.tag_filters[tag_name] # Or set to FILTER_NEUTRAL explicitly
        else: # No action or menu dismissed
            return
            
        self.apply_tag_filters()

    def update_data(self, nodes, edges):
        """Update the view with new album data (nodes) and tag relationships (edges)."""
        self.setUpdatesEnabled(False)
        graphics_logger.info(f"Updating data: {len(nodes)} nodes, {len(edges)} edges received.")

        # Store the new nodes; existing data is implicitly cleared by _reprocess_base_tag_data
        self.album_nodes_original = list(nodes) # Make a copy if nodes is an iterator or shared
        
        # Reprocess all tag data based on the new album_nodes_original and current normalization
        self._reprocess_base_tag_data()
        
        # Note: 'edges' are not currently used in this revised tag processing logic.
        # If they represent tag relationships that should affect counts or display,
        # _reprocess_base_tag_data or another method would need to handle them.
        if edges:
            graphics_logger.debug(f"Received {len(edges)} edges, but they are not currently processed by TagExplorerView's update_data.")

        # Apply filters (which might be empty or pre-existing) and update views
        self.apply_tag_filters()

        self.setUpdatesEnabled(True)

    def _apply_unified_styling(self):
        """Apply unified styling to all child widgets."""
        palette = self.palette()
        # Define your unified colors and fonts here
        background_color = QColor(30, 30, 30)
        foreground_color = QColor(220, 220, 220)
        header_color = QColor(50, 50, 50)
        accent_color = QColor(0, 120, 215)
        font = self.font()
        font.setPointSize(10)
        
        # Apply to all widgets recursively
        def apply_style_recursive(widget):
            widget.setAutoFillBackground(True)
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Window, background_color)
            palette.setColor(QPalette.ColorRole.WindowText, foreground_color)
            widget.setPalette(palette)
            widget.setFont(font)
            
            if isinstance(widget, QTableWidget):
                # Special handling for QTableWidget
                widget.setAlternatingRowColors(True)
                widget.setStyleSheet("QTableWidget::item { padding: 4px; }")
            
            for child in widget.findChildren(QWidget):
                apply_style_recursive(child)
        
        apply_style_recursive(self)
        
        # Header specific styling
        header = self.tags_table.horizontalHeader()
        header.setStyleSheet(f"QHeaderView::section {{ background-color: {header_color.name()}; padding: 4px; }}")
        header.setFont(font)
        
        # Accent color for selected items
        self.setStyleSheet(f"""
            QTableWidget::item:selected {{
                background-color: {accent_color.name()} !important;
                color: {foreground_color.name()} !important;
            }}
            QHeaderView::section:selected {{
                background-color: {accent_color.name()} !important;
                color: {foreground_color.name()} !important;
            }}
        """)