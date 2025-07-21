from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollBar,
                           QWidget, QPushButton, QLabel, QMenu, QSplitter,
                           QComboBox, QRadioButton, QButtonGroup, QToolButton, 
                           QStackedWidget, QLineEdit, QCheckBox, QDialog, QMessageBox,
                           QListWidgetItem) # Added QDialog, QMessageBox, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSortFilterProxyModel, QRegularExpression, QTime # Added QTime
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QPainter, QFontMetrics, QPalette, QAction # Added QAction
from typing import Dict, Any, Set, List, Optional
from collections import Counter, defaultdict
import pandas as pd # Added pandas import
import re # Added re import
import logging # Added logging import

from .base_view import BaseView
from ..state import ViewType, ViewState
from ...tags.normalizer import TagNormalizer
from ...tags.analysis.single_instance_handler import SingleInstanceHandler
from ...tags.analysis.tag_analyzer import TagAnalyzer
from ...tags.analysis.tag_similarity import TagSimilarity
from .tag_cloud_widget import TagCloudWidget
from .single_instance_dialog import SingleInstanceDialog # Added import
from ...gui.widgets.atomic_tag_widget import AtomicTagWidget # Added atomic tag widget
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
        # Enable atomic mode by default for better tag consolidation
        self.tag_normalizer.set_atomic_mode(True)
        
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
        self.splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing completely
        self.splitter.setHandleWidth(5)  # Make splitter handle more visible
        
        # Create tag panel widget
        self.tag_panel = QWidget()
        self.tag_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.tag_panel.setMinimumWidth(250)  # Ensure minimum usable width
        tag_panel_layout = QVBoxLayout(self.tag_panel)
        tag_panel_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add filter header controls with better organization
        self.filter_header = QWidget()
        self.filter_header.setMaximumHeight(80)  # Limit header height to preserve space for tables
        filter_header_layout = QVBoxLayout(self.filter_header)  # Use vertical layout for better organization
        filter_header_layout.setContentsMargins(5, 5, 5, 5)
        filter_header_layout.setSpacing(3)
        
        # Top row - Info and search
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tag_count_label = QLabel("Tags: 0")
        top_layout.addWidget(self.tag_count_label)
        
        # Add progress indicator for large datasets
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        top_layout.addWidget(self.progress_bar)
        
        # Search input for tags
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("Search tags...")
        self.tag_search_input.setToolTip("Search tags (Ctrl+F to focus)")
        self.tag_search_input.returnPressed.connect(self._handle_tag_search)
        self.tag_search_input.setMaximumWidth(150)  # Limit width to save space
        top_layout.addWidget(self.tag_search_input)
        
        self.tag_search_button = QPushButton("Search")
        self.tag_search_button.clicked.connect(self._handle_tag_search)
        self.tag_search_button.setMaximumWidth(60)  # Compact button
        top_layout.addWidget(self.tag_search_button)
        
        top_layout.addStretch()
        
        # Bottom row - Controls and actions
        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add view mode selector
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Table", "Cloud"])
        self.view_mode_combo.setToolTip("Switch view mode (Ctrl+T)")
        self.view_mode_combo.currentIndexChanged.connect(self._change_tag_view_mode)
        self.view_mode_combo.setMaximumWidth(80)  # Compact combo
        bottom_layout.addWidget(self.view_mode_combo)
        
        # Add normalization toggle
        self.normalize_checkbox = QCheckBox("Normalize")
        self.normalize_checkbox.setChecked(True)  # Default to normalization enabled
        self.normalize_checkbox.stateChanged.connect(self._toggle_normalization)
        bottom_layout.addWidget(self.normalize_checkbox)
        
        bottom_layout.addStretch()
        
        # Action buttons - make them more compact
        self.export_button = QPushButton("Export")
        self.export_button.setToolTip("Export tag data to console for analysis")
        self.export_button.clicked.connect(self._export_tag_data)
        self.export_button.setMaximumWidth(60)
        bottom_layout.addWidget(self.export_button)
        
        self.manage_singles_button = QPushButton("Singles")
        self.manage_singles_button.setToolTip("Manage single-instance tags")
        self.manage_singles_button.clicked.connect(self._show_single_instance_dialog)
        self.manage_singles_button.setMaximumWidth(60)
        bottom_layout.addWidget(self.manage_singles_button)
        
        self.clear_filters_button = QPushButton("Clear")
        self.clear_filters_button.setToolTip("Clear all tag filters (Ctrl+Shift+C)")
        self.clear_filters_button.clicked.connect(self.clear_tag_filters)
        self.clear_filters_button.setMaximumWidth(50)
        bottom_layout.addWidget(self.clear_filters_button)
        
        # Add layout reset button
        self.reset_layout_button = QPushButton("Reset Layout")
        self.reset_layout_button.setToolTip("Reset layout to default proportions (Ctrl+R)")
        self.reset_layout_button.clicked.connect(self.reset_layout)
        self.reset_layout_button.setMaximumWidth(80)
        bottom_layout.addWidget(self.reset_layout_button)
        
        # Add both rows to the header
        filter_header_layout.addWidget(top_row)
        filter_header_layout.addWidget(bottom_row)
        
        tag_panel_layout.addWidget(self.filter_header)
        
        # Add atomic tag widget
        self.atomic_widget = AtomicTagWidget()
        self.atomic_widget.setVisible(True)  # Make visible so users can access atomic mode
        self.atomic_widget.atomic_mode_changed.connect(self._on_atomic_mode_toggle)
        self.atomic_widget.tag_filter_changed.connect(self._on_atomic_filter_changed)
        self.atomic_widget.breakdown_requested.connect(self._on_atomic_breakdown_requested)
        
        # Add the atomic widget to the bottom row for easy access
        bottom_layout.addWidget(self.atomic_widget)
        
        # Create tag views stack
        self.tag_views_stack = QStackedWidget()
        self.tag_views_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tag_views_stack.setMinimumHeight(300)  # Ensure minimum usable height for tag views
        
        # Create tag table
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(4)
        self.tags_table.setHorizontalHeaderLabels(["Tag", "Count", "Matching", "Filter"])
        self.tags_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tags_table.setMinimumHeight(250)  # Ensure minimum usable height for tag table
        
        # Configure tag table headers for better responsiveness
        header = self.tags_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Tag name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Filter column
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        header.setStretchLastSection(False)  # Don't stretch the last section
        # header.setSortIndicatorShown(True) # Managed manually
        header.sectionClicked.connect(self._handle_tag_sort)
        
        # Set reasonable minimum column widths
        self.tags_table.setColumnWidth(1, 60)   # Count column
        self.tags_table.setColumnWidth(2, 70)   # Matching column  
        self.tags_table.setColumnWidth(3, 70)   # Filter column
        
        self.tags_table.setShowGrid(True)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSortingEnabled(False) # Disable native sorting, will handle manually
        self.tags_sort_column = 1  # Default sort by count (index 1)
        self.tags_sort_order = Qt.SortOrder.DescendingOrder
        # self.tags_table.cellDoubleClicked.connect(self._cycle_tag_filter_state) # Ensure this is removed or commented

        # Add tag views (table and cloud) to the QStackedWidget
        self.tag_views_stack.addWidget(self.tags_table)
        self.tag_cloud_widget = TagCloudWidget(self) # Initialize TagCloudWidget
        self.tag_cloud_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tag_cloud_widget.setMinimumHeight(250)  # Ensure minimum usable height for tag cloud
        self.tag_views_stack.addWidget(self.tag_cloud_widget)
        
        # Add the QStackedWidget (tag_views_stack) to the tag_panel_layout
        tag_panel_layout.addWidget(self.tag_views_stack, 1)  # Give stretch factor of 1 to expand

        # Create the album panel, its layout, and its widgets (album_count_label, album_table)
        self.album_panel = QWidget()
        self.album_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.album_panel.setMinimumWidth(300)  # Ensure minimum usable width
        album_panel_layout = QVBoxLayout(self.album_panel)
        album_panel_layout.setContentsMargins(5, 5, 5, 5)

        self.album_count_label = QLabel("Albums: 0")
        self.album_count_label.setMaximumHeight(25)  # Keep album header compact
        album_panel_layout.addWidget(self.album_count_label)

        self.album_table = QTableWidget() # Definition of self.album_table
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        self.album_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.album_table.setMinimumHeight(200)  # Ensure minimum usable height for album table
        album_header = self.album_table.horizontalHeader()
        album_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        album_header.setStretchLastSection(True)  # Tags column stretches
        
        # Set reasonable initial column widths for albums
        self.album_table.setColumnWidth(0, 200)  # Artist column
        self.album_table.setColumnWidth(1, 250)  # Album column
        self.album_table.setColumnWidth(2, 80)   # Year column
        self.album_table.setSortingEnabled(True)
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setShowGrid(True)
        self.album_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.album_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        album_panel_layout.addWidget(self.album_table, 1)  # Give stretch factor of 1 to expand

        # Add both panels to the splitter
        self.splitter.addWidget(self.tag_panel)
        self.splitter.addWidget(self.album_panel)
        
        # Set initial sizes with better proportions (40% for tags, 60% for albums)
        # and allow user to resize as needed
        self.splitter.setSizes([400, 600])
        self.splitter.setStretchFactor(0, 2)  # Tag panel stretch factor
        self.splitter.setStretchFactor(1, 3)  # Album panel stretch factor
        
        # Connect splitter moved signal to save settings
        self.splitter.splitterMoved.connect(self._save_splitter_state)
        
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
        
        # Initialize atomic tag system state
        self.atomic_mode = True  # Default to atomic mode for better consolidation
        self.data_interface = None  # Will be set when data is updated
        
        # Initialize data interface for atomic tag support
        self._initialize_data_interface()
        
        # Connect atomic widget signals properly
        self.atomic_widget.atomic_mode_changed.connect(self._on_atomic_mode_toggle)
        
        # Performance optimization attributes
        self._tag_processing_cache = {}
        self._normalization_cache = {}
        self._deferred_timer = None
        self._filter_timer = None
        
        # Load saved splitter state if available
        self._load_splitter_state()
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()

        self.setUpdatesEnabled(True)  # Re-enable updates
    
    def _process_selection(self):
        """Process pending selection changes."""
        self.apply_tag_filters()

    def _get_normalized_tag_display(self, tag):
        """Get a display-friendly normalized form of a tag.
        
        In atomic mode, this returns a comma-separated list of atomic components.
        In standard mode, this returns the single normalized tag.
        """
        normalized = self.normalized_mapping.get(tag, tag)
        
        if isinstance(normalized, list):
            # Atomic mode: return comma-separated list of components
            return ', '.join(normalized) if normalized else tag
        else:
            # Standard mode: return the single normalized tag
            return normalized if normalized else tag
    
    def _get_normalized_tag_for_processing(self, tag):
        """Get normalized tag(s) for internal processing.
        
        In atomic mode, this returns the first atomic component for backward compatibility.
        In standard mode, this returns the single normalized tag.
        """
        normalized = self.normalized_mapping.get(tag)
        
        if isinstance(normalized, list):
            # Atomic mode: return first component for backward compatibility
            return normalized[0] if normalized else tag
        else:
            # Standard mode: return the single normalized tag
            return normalized if normalized else tag

    def _reprocess_base_tag_data(self):
        """
        Recalculates tag counts and mappings from the original album node data.
        This should be called when normalization settings change or data is first loaded.
        Optimized for performance with large datasets.
        """
        self.raw_tag_counts.clear()
        self.tag_counts.clear()
        self.normalized_mapping.clear()

        total_albums = len(self.album_nodes_original)
        graphics_logger.info(f"TagExplorerView: Processing {total_albums} album nodes for tags")

        # Pre-compile regex for better performance
        tag_splitter = re.compile(r'[;,]')
        
        # Batch process albums for better performance
        batch_size = 1000
        processed_albums = 0
        
        # Show progress bar for large datasets
        if total_albums > 2000:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(total_albums)
            self.progress_bar.setValue(0)
        
        for batch_start in range(0, total_albums, batch_size):
            batch_end = min(batch_start + batch_size, total_albums)
            
            # Process batch
            for i in range(batch_start, batch_end):
                album_node = self.album_nodes_original[i]
                
                # Fallback to 'genre' if 'raw_tags' is not present
                raw_tags_str = album_node.get('raw_tags') or album_node.get('genre', '')
                
                # Debug log for first few albums only
                if i < 3:
                    album_title = album_node.get('title', 'Unknown')
                    graphics_logger.debug(f"TagExplorerView: Album {i} '{album_title}': raw_tags_str='{raw_tags_str}'")
                
                if raw_tags_str:
                    # Use pre-compiled regex for better performance
                    tags = [tag.strip() for tag in tag_splitter.split(raw_tags_str) if tag.strip()]
                    
                    # Debug log for first few albums with tags only
                    if i < 3 and tags:
                        graphics_logger.debug(f"TagExplorerView: Album {i} processed tags: {tags}")
                    
                    # Batch update counters
                    for tag in tags:
                        self.raw_tag_counts[tag] += 1
            
            processed_albums = batch_end
            
            # Update progress bar
            if total_albums > 2000:
                self.progress_bar.setValue(processed_albums)
                self.tag_count_label.setText(f"Processing tags: {processed_albums}/{total_albums}")
            
            # Log progress for large datasets
            if total_albums > 5000 and processed_albums % 5000 == 0:
                graphics_logger.info(f"TagExplorerView: Processed {processed_albums}/{total_albums} albums...")
        
        # Hide progress bar
        if total_albums > 2000:
            self.progress_bar.setVisible(False)
        
        # Process tags using the enhanced TagNormalizer which handles both atomic and standard modes
        is_normalizing = self.normalize_checkbox.isChecked()
        
        if is_normalizing:
            graphics_logger.info(f"TagExplorerView: Processing with normalization (atomic mode: {self.tag_normalizer.get_atomic_mode()})")
            # Use the enhanced normalizer which can handle both atomic and standard modes
            unique_raw_tags = list(self.raw_tag_counts.keys())
            
            # Process tags using the normalizer's atomic-aware methods
            for raw_tag in unique_raw_tags:
                count = self.raw_tag_counts[raw_tag]
                
                if self.tag_normalizer.get_atomic_mode():
                    # Get atomic components
                    atomic_components = self.tag_normalizer.normalize_to_atomic(raw_tag)
                    for component in atomic_components:
                        self.tag_counts[component] += count
                    # Map to full atomic components list for proper debugging/logging
                    if atomic_components:
                        self.normalized_mapping[raw_tag] = atomic_components
                else:
                    # Standard normalization
                    normalized_tag = self.tag_normalizer.normalize(raw_tag)
                    if normalized_tag:
                        self.tag_counts[normalized_tag] += count
                        self.normalized_mapping[raw_tag] = normalized_tag
        else:
            graphics_logger.info("TagExplorerView: Processing without normalization")
            # If not normalizing, the processed tags are the same as the raw tags
            self.tag_counts = self.raw_tag_counts.copy()
            # Use dict comprehension for better performance
            self.normalized_mapping = {tag: tag for tag in self.raw_tag_counts.keys()}

        # Update single instance tags after reprocessing
        if self.tag_analyzer:
            self.single_instance_tags = self.tag_analyzer.find_single_instance_tags(self.tag_counts)
        else:
            # Use set comprehension for better performance
            self.single_instance_tags = {tag for tag, count in self.tag_counts.items() if count == 1}

        # Log summary after processing
        graphics_logger.info(f"TagExplorerView: Processed tags summary - Raw tags: {len(self.raw_tag_counts)}, Processed tags: {len(self.tag_counts)}")
        
        # Update tag count label
        self.tag_count_label.setText(f"Tags: {len(self.tag_counts)}")
        
        # After reprocessing, we should re-apply filters and update views
        self.apply_tag_filters()

    def _process_atomic_tags(self):
        """Process tags using atomic tag decomposition."""
        graphics_logger.info("TagExplorerView: Starting atomic tag processing")
        
        # Clear existing counts
        self.tag_counts.clear()
        self.normalized_mapping.clear()
        
        # Use the integrated TagNormalizer for atomic processing
        try:
            # Process each raw tag through atomic decomposition
            for raw_tag, count in self.raw_tag_counts.items():
                # Get atomic breakdown for this tag using the normalizer
                atomic_components = self.tag_normalizer.normalize_to_atomic(raw_tag)
                
                if atomic_components:
                    # Use atomic components
                    for component in atomic_components:
                        self.tag_counts[component] += count
                    
                    # Map the original tag to its full atomic components list for proper debugging/logging
                    if atomic_components:
                        self.normalized_mapping[raw_tag] = atomic_components
                    
                    if len(atomic_components) > 1:
                        graphics_logger.debug(f"Decomposed '{raw_tag}' into {len(atomic_components)} atomic components: {atomic_components}")
                else:
                    # No atomic breakdown available, use standard normalization
                    normalized_tag = self.tag_normalizer.normalize(raw_tag)
                    if normalized_tag:
                        self.tag_counts[normalized_tag] += count
                        self.normalized_mapping[raw_tag] = normalized_tag
            
            graphics_logger.info(f"TagExplorerView: Atomic processing complete. {len(self.tag_counts)} atomic tags found")
            
        except Exception as e:
            graphics_logger.error(f"Error in atomic tag processing: {e}")
            # Fallback to standard normalization
            graphics_logger.info("Falling back to standard normalization")
            for raw_tag, count in self.raw_tag_counts.items():
                normalized_tag = self.tag_normalizer.normalize(raw_tag)
                if normalized_tag:
                    self.tag_counts[normalized_tag] += count
                    self.normalized_mapping[raw_tag] = normalized_tag

    def apply_tag_filters(self):
        """
        Filters albums based on the current tag filters and updates the view.
        Optimized for performance with large datasets.
        """
        # Temporarily disable updates during bulk processing
        self.setUpdatesEnabled(False)
        graphics_logger.debug(f"Applying tag filters. Normalization active: {self.tag_normalizer.is_active()}")
        graphics_logger.debug(f"Current tag_filters: {self.tag_filters}")

        # Pre-compute filter sets for better performance
        include_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_INCLUDE}
        exclude_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_EXCLUDE}
        
        # Early exit if no filters are active
        has_filters = bool(include_filters or exclude_filters)

        self.filtered_albums.clear()
        self.matching_counts.clear()

        is_normalization_active = self.tag_normalizer.is_active()
        
        # Pre-compile regex for better performance if needed
        tag_splitter = re.compile(r'[;,]')
        
        # Batch process albums for better performance
        total_albums = len(self.album_nodes_original)
        batch_size = 1000
        processed_albums = 0
        
        for batch_start in range(0, total_albums, batch_size):
            batch_end = min(batch_start + batch_size, total_albums)
            batch_filtered_albums = []
            batch_matching_counts = Counter()
            
            for i in range(batch_start, batch_end):
                node = self.album_nodes_original[i]
                
                # Get raw tags from the node data - optimized
                raw_tags_str = node.get('raw_tags') or node.get('genre', '')
                if not raw_tags_str:
                    # No tags means no match if include filters exist
                    if not include_filters:
                        batch_filtered_albums.append(node)
                    continue
                
                # Split tags efficiently
                node_raw_tags = [tag.strip() for tag in tag_splitter.split(raw_tags_str) if tag.strip()]
                if not node_raw_tags:
                    if not include_filters:
                        batch_filtered_albums.append(node)
                    continue
                
                # Determine the set of processed tags for the current node, based on normalization state
                if is_normalization_active:
                    # Use cached normalization mapping where possible
                    current_node_processed_tags = []
                    for tag in node_raw_tags:
                        normalized_tag = self._get_normalized_tag_for_processing(tag)
                        if normalized_tag == tag and tag not in self.normalized_mapping:
                            # Fallback normalization if not in cache
                            fallback_normalized = self.tag_normalizer.normalize(tag)
                            if fallback_normalized:
                                self.normalized_mapping[tag] = fallback_normalized
                                normalized_tag = fallback_normalized
                        if normalized_tag:
                            current_node_processed_tags.append(normalized_tag)
                else:
                    # In non-normalized mode, use cached mapping or create it
                    current_node_processed_tags = []
                    for tag in node_raw_tags:
                        processed_tag = self._get_normalized_tag_for_processing(tag)
                        current_node_processed_tags.append(processed_tag)

                # Early exit if no filters are active
                if not has_filters:
                    batch_filtered_albums.append(node)
                    for tag in current_node_processed_tags:
                        batch_matching_counts[tag] += 1
                    continue

                # Convert to set for faster membership testing
                node_tags_set = set(current_node_processed_tags)

                # Check include filters
                if include_filters and not include_filters.intersection(node_tags_set):
                    continue

                # Check exclude filters
                if exclude_filters and exclude_filters.intersection(node_tags_set):
                    continue

                # If we reach here, the node matches the current filters
                batch_filtered_albums.append(node)
                for tag in current_node_processed_tags:
                    batch_matching_counts[tag] += 1
            
            # Merge batch results
            self.filtered_albums.extend(batch_filtered_albums)
            self.matching_counts.update(batch_matching_counts)
            
            processed_albums = batch_end
            
            # Log progress for large datasets
            if total_albums > 5000 and processed_albums % 5000 == 0:
                graphics_logger.debug(f"TagExplorerView: Filtered {processed_albums}/{total_albums} albums...")

        # Update views efficiently
        self._update_tag_views() 
        self._update_album_table_display()

        self.setUpdatesEnabled(True)
    
    def _update_tag_views(self):
        """Update the tag views (table and cloud) with the current tag data. Optimized for performance."""
        self.setUpdatesEnabled(False)
        
        # Clear table efficiently
        self.tags_table.setRowCount(0)
        
        # Prepare data for batch insertion
        tag_data = []
        for tag, count in self.tag_counts.items(): 
            filter_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL)
            matching_count = self.matching_counts.get(tag, 0)
            tag_data.append((tag, count, matching_count, filter_state))
        
        # Set row count once
        self.tags_table.setRowCount(len(tag_data))
        
        # Batch populate table
        for row_position, (tag, count, matching_count, filter_state) in enumerate(tag_data):
            # Tag column (Column 0)
            tag_item = SortableTableWidgetItem(tag)
            self.tags_table.setItem(row_position, 0, tag_item)

            # Count column (Column 1)
            count_item = SortableTableWidgetItem(str(count))
            count_item.setData(Qt.ItemDataRole.UserRole, int(count))
            self.tags_table.setItem(row_position, 1, count_item)
            
            # Matching column (Column 2)
            matching_item = SortableTableWidgetItem(str(matching_count))
            matching_item.setData(Qt.ItemDataRole.UserRole, int(matching_count))
            self.tags_table.setItem(row_position, 2, matching_item)

            # Filter column (Column 3)
            filter_text = "Neutral"
            if filter_state == self.FILTER_INCLUDE:
                filter_text = "Include"
            elif filter_state == self.FILTER_EXCLUDE:
                filter_text = "Exclude"
            
            filter_q_item = QTableWidgetItem(filter_text)
            filter_q_item.setData(Qt.ItemDataRole.UserRole, filter_state)
            self.tags_table.setItem(row_position, 3, filter_q_item)

        # Update tag cloud widget efficiently
        if hasattr(self.tag_cloud_widget, 'update_tags'):
            self.tag_cloud_widget.update_tags(self.tag_counts)
            self.tag_cloud_widget.update_filter_states(self.tag_filters)
        
        # Sort the table based on the current sort column and order
        self.tags_table.sortItems(self.tags_sort_column, self.tags_sort_order)
        
        self.setUpdatesEnabled(True)
    
    def _update_album_count_label(self):
        """Update the album count label in the album panel."""
        self.album_count_label.setText(f"Albums: {len(self.filtered_albums)}")
    
    def _update_album_table_display(self):
        """Populate the album_table with data from self.filtered_albums. Optimized for performance."""
        # Disable sorting during bulk updates for better performance
        sorting_enabled = self.album_table.isSortingEnabled()
        self.album_table.setSortingEnabled(False)
        
        # Clear existing rows efficiently
        self.album_table.setRowCount(0)
        
        # Set row count once for all albums
        num_albums = len(self.filtered_albums)
        
        # For very large datasets, consider virtual scrolling or pagination
        if num_albums > 10000:
            graphics_logger.info(f"Large album dataset ({num_albums} albums), using optimized display")
            self._update_album_table_large_dataset()
            return
        
        self.album_table.setRowCount(num_albums)
        
        # Show progress for large datasets
        show_progress = num_albums > 2000
        if show_progress:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(num_albums)
            self.progress_bar.setValue(0)
        
        # Batch process albums for better performance with large datasets
        batch_size = 1000
        
        for batch_start in range(0, num_albums, batch_size):
            batch_end = min(batch_start + batch_size, num_albums)
            
            # Process batch
            for i in range(batch_start, batch_end):
                album_node = self.filtered_albums[i]
                row_position = i
                
                artist = album_node.get('artist', '')
                album_title = album_node.get('album', album_node.get('title', ''))
                
                # Get year value efficiently
                year_value_from_node = album_node.get('release_year') or album_node.get('year')
                year_display_string = ""
                year_sort_integer = None
                
                if year_value_from_node is not None and str(year_value_from_node).strip():
                    year_display_string = str(year_value_from_node)
                    try:
                        year_sort_integer = int(float(year_value_from_node))
                    except (ValueError, TypeError):
                        # Log only for debugging if needed
                        if graphics_logger.isEnabledFor(logging.DEBUG):
                            graphics_logger.debug(f"Could not convert year '{year_value_from_node}' to int for album '{album_title}'")
                
                # Format tags efficiently
                tags_list = album_node.get('tags', [])
                if isinstance(tags_list, list):
                    tags_str = ", ".join(map(str, tags_list)) if tags_list else ""
                else:
                    tags_str = str(tags_list)
                
                # Create and set items
                self.album_table.setItem(row_position, 0, QTableWidgetItem(artist))
                self.album_table.setItem(row_position, 1, QTableWidgetItem(album_title))
                
                year_item = QTableWidgetItem(year_display_string)
                if year_sort_integer is not None:
                    year_item.setData(Qt.ItemDataRole.UserRole, year_sort_integer)
                self.album_table.setItem(row_position, 2, year_item)
                
                self.album_table.setItem(row_position, 3, QTableWidgetItem(tags_str))
            
            # Update progress
            if show_progress:
                self.progress_bar.setValue(batch_end)
        
        # Hide progress bar
        if show_progress:
            self.progress_bar.setVisible(False)
        
        # Re-enable sorting
        self.album_table.setSortingEnabled(sorting_enabled)
        
        # Update album count label
        self._update_album_count_label()
        
    def _update_album_table_large_dataset(self):
        """Handle very large datasets with simplified display."""
        # For datasets over 10k albums, show a simplified view with pagination
        max_display = 5000
        actual_count = len(self.filtered_albums)
        
        # Show only first N albums
        display_albums = self.filtered_albums[:max_display]
        self.album_table.setRowCount(len(display_albums))
        
        # Populate with simplified data
        for i, album_node in enumerate(display_albums):
            artist = album_node.get('artist', '')
            album_title = album_node.get('album', album_node.get('title', ''))
            year = str(album_node.get('release_year') or album_node.get('year') or '')
            
            # Simplified tags display
            tags_list = album_node.get('tags', [])
            if isinstance(tags_list, list) and len(tags_list) > 3:
                tags_str = f"{', '.join(map(str, tags_list[:3]))}... (+{len(tags_list)-3} more)"
            elif isinstance(tags_list, list):
                tags_str = ", ".join(map(str, tags_list))
            else:
                tags_str = str(tags_list)
            
            self.album_table.setItem(i, 0, QTableWidgetItem(artist))
            self.album_table.setItem(i, 1, QTableWidgetItem(album_title))
            self.album_table.setItem(i, 2, QTableWidgetItem(year))
            self.album_table.setItem(i, 3, QTableWidgetItem(tags_str))
        
        # Update label to show limitation
        self.album_count_label.setText(f"Albums: {actual_count} (showing first {max_display})")
        
        # Log the limitation
        graphics_logger.info(f"Large dataset: showing {max_display} of {actual_count} albums for performance")

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
        filter_count = len(self.tag_filters)
        self.tag_filters.clear()
        self.apply_tag_filters() # This will refresh tables and matching counts
        self.update_status_message(f"Cleared {filter_count} tag filters")
        graphics_logger.info("All tag filters cleared.")

    def _handle_tag_search(self):
        """Handle tag search from the input field."""
        search_text = self.tag_search_input.text().strip()
        if not search_text:
            # If search is cleared, reset the view
            self._update_tag_views()
            return
            
        # Create a filtered model for the tag table
        # NOTE: This assumes we are using a QTableView with a model.
        # Since we use QTableWidget, we need to manually filter rows.
        
        # Manual filter for QTableWidget
        for i in range(self.tags_table.rowCount()):
            item = self.tags_table.item(i, 0) # Tag name is in column 0
            if item:
                # Simple case-insensitive search
                is_match = search_text.lower() in item.text().lower()
                self.tags_table.setRowHidden(i, not is_match)

    def _export_tag_data(self):
        """Exports various tag-related data for analysis."""
        graphics_logger.info("--- Exporting Tag Data ---")
        
        # 1. Basic counts
        graphics_logger.info(f"Total unique tags (current mode): {len(self.tag_counts)}")
        graphics_logger.info(f"Total raw tags: {len(self.raw_tag_counts)}")
        
        # 2. Filtered data
        included_tags = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_INCLUDE}
        excluded_tags = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_EXCLUDE}
        graphics_logger.info(f"Included tags ({len(included_tags)}): {included_tags}")
        graphics_logger.info(f"Excluded tags ({len(excluded_tags)}): {excluded_tags}")
        graphics_logger.info(f"Filtered album count: {len(self.filtered_albums)}")
        
        # 3. Normalization info
        if self.normalize_checkbox.isChecked():
            graphics_logger.info("Normalization is ON.")
            # Log a sample of the normalization mapping with proper display format
            sample_items = list(self.normalized_mapping.items())[:10]
            sample_mapping = {k: self._get_normalized_tag_display(k) for k, v in sample_items}
            graphics_logger.info(f"Normalization mapping sample: {sample_mapping}")
        else:
            graphics_logger.info("Normalization is OFF.")
            
        # 4. Single-instance tags
        graphics_logger.info(f"Single-instance tags found: {len(self.single_instance_tags)}")
        
        # 5. Create and export a DataFrame for detailed analysis
        try:
            # Consolidate all tags from both raw and normalized counts
            all_tags = set(self.raw_tag_counts.keys()) | set(self.tag_counts.keys())
            
            export_data = []
            for tag in sorted(list(all_tags)):
                export_data.append({
                    "Tag": tag,
                    "Raw Count": self.raw_tag_counts.get(tag, 0),
                    "Processed Count": self.tag_counts.get(tag, 0),
                    "Matching Count": self.matching_counts.get(tag, 0),
                    "Is Single": tag in self.single_instance_tags,
                    "Normalized Form": self._get_normalized_tag_display(tag),
                    "Filter State": self.tag_filters.get(tag, self.FILTER_NEUTRAL)
                })
            
            df = pd.DataFrame(export_data)
            
            # Use a dialog to show the dataframe content or save it
            self._show_export_dialog(df)
            
        except Exception as e:
            graphics_logger.error(f"Failed to create and export tag DataFrame: {e}", exc_info=True)
            
        graphics_logger.info("--- End of Tag Data Export ---")

    def _show_export_dialog(self, df):
        """Shows a dialog with the exported data in a table and an option to save."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Exported Tag Data")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        
        for i, row in df.iterrows():
            for j, col in enumerate(df.columns):
                table.setItem(i, j, QTableWidgetItem(str(row[col])))
                
        table.resizeColumnsToContents()
        
        save_button = QPushButton("Save to CSV")
        
        def save_csv():
            from PyQt6.QtWidgets import QFileDialog
            
            # Show file dialog to get save path
            path, _ = QFileDialog.getSaveFileName(dialog, "Save CSV", "", "CSV Files (*.csv)")
            
            if path:
                try:
                    df.to_csv(path, index=False)
                    QMessageBox.information(dialog, "Success", f"Successfully saved to {path}")
                except Exception as e:
                    QMessageBox.warning(dialog, "Error", f"Failed to save file: {e}")
        
        save_button.clicked.connect(save_csv)
        
        layout.addWidget(table)
        layout.addWidget(save_button)
        
        dialog.exec()

    def _toggle_atomic_mode(self, enabled):
        """Toggle between standard and atomic tag modes."""
        self.atomic_mode = enabled
        
        # Update the tag normalizer to use atomic mode
        self.tag_normalizer.set_atomic_mode(enabled)
        
        # Show/hide atomic widget controls based on mode
        self.atomic_widget.setVisible(enabled)
        
        # Log the mode change
        mode_str = "ATOMIC" if enabled else "STANDARD"
        graphics_logger.info(f"TagExplorerView: Switching to {mode_str} mode")
        
        # Clear existing filters as their context has changed
        self.tag_filters.clear()
        graphics_logger.debug("Tag filters cleared due to atomic mode change.")
        
        # Reprocess all tag data with the new mode
        self._reprocess_base_tag_data()
        
        # Update atomic filter if in atomic mode
        if enabled and self.data_interface:
            self._update_atomic_filter()
        
        # Force update of the display
        self._update_tag_views()
        self._update_album_table_display()
        
    def _on_atomic_mode_toggle(self, enabled):
        """Handle atomic mode toggle from the atomic widget."""
        self._toggle_atomic_mode(enabled)
        
    def _initialize_data_interface(self):
        """Initialize data interface for atomic tag operations."""
        try:
            from ..data_interface import DataInterface
            from ...database import get_session
            
            # Create data interface with database session
            session = get_session()
            self.data_interface = DataInterface(session)
            graphics_logger.info("TagExplorerView: Data interface initialized for atomic tag support")
            
        except Exception as e:
            graphics_logger.warning(f"TagExplorerView: Could not initialize data interface: {e}")
            self.data_interface = None
    
    def set_data_interface(self, data_interface):
        """Set the data interface for atomic tag operations."""
        self.data_interface = data_interface
        graphics_logger.info("TagExplorerView: Data interface set externally")
        
    def _on_atomic_filter_changed(self, filter_criteria):
        """Handle atomic tag filter changes."""
        if not self.atomic_mode or not filter_criteria:
            return
        
        graphics_logger.info(f"Atomic filter changed: {filter_criteria}")
        
        # Convert atomic filter criteria to regular tag filters
        # Each atomic component should be treated as an include filter
        for atomic_tag in filter_criteria:
            self.tag_filters[atomic_tag] = self.FILTER_INCLUDE
        
        # Apply the updated filters
        self.apply_tag_filters()
            
    def _on_atomic_breakdown_requested(self, tag_name):
        """Handle requests to show atomic breakdown for a tag."""
        if not self.tag_normalizer:
            return
        
        # Get atomic breakdown using the tag normalizer
        atomic_components = self.tag_normalizer.normalize_to_atomic(tag_name)
        
        if atomic_components and len(atomic_components) > 1:
            # Create breakdown data structure for the atomic widget
            breakdown_data = {
                'composite_tag': tag_name,
                'component_count': len(atomic_components),
                'decomposition_confidence': 'High',  # Assuming high confidence for rule-based decomposition
                'atomic_components': [
                    {
                        'name': component,
                        'category': 'unknown',  # Could be enhanced with category mapping
                        'rule_source': 'tag_normalizer'
                    }
                    for component in atomic_components
                ]
            }
            
            # Update the breakdown display in the atomic widget
            self.atomic_widget.show_breakdown(breakdown_data)
        else:
            # No breakdown available
            self.atomic_widget.show_breakdown(None)
            
    def _update_atomic_filter(self):
        """Update the atomic filter display based on current mode."""
        if self.atomic_mode and self.tag_normalizer:
            # Get atomic tag statistics from the normalizer
            stats = self.tag_normalizer.get_atomic_statistics()
            
            # Create atomic tags list for the atomic widget
            # Extract unique atomic components from current tag counts
            atomic_tags = []
            for tag_name in self.tag_counts.keys():
                atomic_tags.append({
                    'name': tag_name,
                    'category': 'unknown',  # Could be enhanced with proper categorization
                    'description': f'Atomic tag: {tag_name}',
                    'rule_source': 'tag_normalizer'
                })
            
            # Update the atomic widget with the atomic tags
            self.atomic_widget.update_atomic_data(stats, atomic_tags)
        
    def _show_single_instance_dialog(self):
        """Shows the dialog for managing single-instance tags."""
        if not self.single_instance_tags:
            QMessageBox.information(self, "No Single-Instance Tags", "No single-instance tags were found in the current dataset.")
            return
            
        dialog = SingleInstanceDialog(list(self.single_instance_tags), self)
        if dialog.exec():
            # Future: Handle updates from the dialog if needed
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
        """Update the view with new album data (nodes) and tag relationships (edges). Optimized for performance."""
        self.setUpdatesEnabled(False)
        graphics_logger.info(f"Updating data: {len(nodes)} nodes, {len(edges)} edges received.")

        # Store the new nodes; existing data is implicitly cleared by _reprocess_base_tag_data
        self.album_nodes_original = list(nodes) # Make a copy if nodes is an iterator or shared
        
        # Clear caches
        self._clear_performance_caches()
        
        # Use deferred processing for large datasets
        if len(nodes) > 1000:
            graphics_logger.info("Large dataset detected, using deferred processing")
            self._schedule_deferred_processing()
        else:
            # Process immediately for smaller datasets
            self._reprocess_base_tag_data()
            self.apply_tag_filters()

        self.setUpdatesEnabled(True)
        
    def _clear_performance_caches(self):
        """Clear performance-related caches."""
        # Clear any caches that might have been built up
        if hasattr(self, '_tag_processing_cache'):
            self._tag_processing_cache.clear()
        if hasattr(self, '_normalization_cache'):
            self._normalization_cache.clear()
            
    def _schedule_deferred_processing(self):
        """Schedule deferred processing for large datasets."""
        if self._deferred_timer is None:
            self._deferred_timer = QTimer(self)
            self._deferred_timer.setSingleShot(True)
            self._deferred_timer.timeout.connect(self._process_deferred_data)
        
        # Start processing after a short delay to allow UI to update
        self._deferred_timer.start(100)
        
    def _process_deferred_data(self):
        """Process data in the background for large datasets."""
        graphics_logger.info("Starting deferred data processing...")
        
        # Update status to show we're processing
        if hasattr(self, 'tag_count_label'):
            self.tag_count_label.setText("Processing large dataset...")
        
        # Process data
        self._reprocess_base_tag_data()
        
        # Schedule filter application
        if self._filter_timer is None:
            self._filter_timer = QTimer(self)
            self._filter_timer.setSingleShot(True)
            self._filter_timer.timeout.connect(self.apply_tag_filters)
        
        self._filter_timer.start(50)

    def _save_splitter_state(self):
        """Save the current splitter state to settings."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AlbumExplore", "TagExplorerView")
            settings.setValue("splitter_sizes", self.splitter.sizes())
            graphics_logger.debug(f"Saved splitter state: {self.splitter.sizes()}")
        except Exception as e:
            graphics_logger.debug(f"Could not save splitter state: {e}")
    
    def _load_splitter_state(self):
        """Load the saved splitter state from settings."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AlbumExplore", "TagExplorerView")
            saved_sizes = settings.value("splitter_sizes")
            if saved_sizes:
                # Convert to integers if they were saved as strings
                if isinstance(saved_sizes, list):
                    sizes = [int(size) for size in saved_sizes]
                    # Validate that sizes make sense (both positive, reasonable proportions)
                    if len(sizes) == 2 and all(size > 50 for size in sizes):
                        self.splitter.setSizes(sizes)
                        graphics_logger.debug(f"Loaded splitter state: {sizes}")
                        return
            graphics_logger.debug("No valid saved splitter state found, using defaults")
        except Exception as e:
            graphics_logger.debug(f"Could not load splitter state: {e}")
    
    def reset_layout(self):
        """Reset the layout to default proportions."""
        default_sizes = [400, 600]
        self.splitter.setSizes(default_sizes)
        self._save_splitter_state()
        self.update_status_message("Layout reset to default proportions")
        graphics_logger.info("Layout reset to default proportions")
    
    def get_layout_info(self):
        """Get current layout information for debugging."""
        current_sizes = self.splitter.sizes()
        total_width = sum(current_sizes)
        if total_width > 0:
            tag_percent = (current_sizes[0] / total_width) * 100
            album_percent = (current_sizes[1] / total_width) * 100
            return {
                'sizes': current_sizes,
                'tag_panel_percent': round(tag_percent, 1),
                'album_panel_percent': round(album_percent, 1),
                'total_width': total_width
            }
        return {'error': 'No width available'}
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for better usability."""
        try:
            from PyQt6.QtGui import QShortcut, QKeySequence
            from PyQt6.QtCore import Qt
            
            # Ctrl+R to reset layout
            reset_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
            reset_shortcut.activated.connect(self.reset_layout)
            
            # Ctrl+F to focus search
            search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
            search_shortcut.activated.connect(lambda: self.tag_search_input.setFocus())
            
            # Ctrl+Shift+C to clear filters
            clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
            clear_shortcut.activated.connect(self.clear_tag_filters)
            
            # Ctrl+T to toggle between table and cloud view
            toggle_view_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
            toggle_view_shortcut.activated.connect(self._toggle_view_mode)
            
            graphics_logger.debug("Keyboard shortcuts setup complete")
            
        except Exception as e:
            graphics_logger.debug(f"Could not setup keyboard shortcuts: {e}")
    
    def _toggle_view_mode(self):
        """Toggle between table and cloud view modes."""
        current_index = self.view_mode_combo.currentIndex()
        new_index = 1 - current_index  # Toggle between 0 and 1
        self.view_mode_combo.setCurrentIndex(new_index)
    
    def show_layout_help(self):
        """Show help dialog with layout and keyboard shortcuts information."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            help_text = """
            <h3>Tag Explorer Layout Help</h3>
            
            <p><b>Layout Features:</b></p>
            <ul>
            <li>Drag the splitter between panels to resize</li>
            <li>Minimum sizes prevent panels from becoming unusable</li>
            <li>Layout proportions are automatically saved</li>
            </ul>
            
            <p><b>Keyboard Shortcuts:</b></p>
            <ul>
            <li><b>Ctrl+R</b> - Reset layout to default proportions</li>
            <li><b>Ctrl+F</b> - Focus search box</li>
            <li><b>Ctrl+T</b> - Toggle between table and cloud view</li>
            <li><b>Ctrl+Shift+C</b> - Clear all tag filters</li>
            </ul>
            
            <p><b>Tips:</b></p>
            <ul>
            <li>Right-click on tags for filtering options</li>
            <li>Use the search box to quickly find specific tags</li>
            <li>The Reset Layout button restores default proportions</li>
            </ul>
            """
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Layout Help")
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setText(help_text)
            msg_box.exec()
            
        except Exception as e:
            graphics_logger.error(f"Could not show help dialog: {e}")
    
    def update_status_message(self, message, duration=3000):
        """Update status message (if status bar is available)."""
        # This could be enhanced to show messages in a status bar if one is added
        # For now, just log the message
        graphics_logger.info(f"Status: {message}")
        
        # Could also temporarily update a label
        if hasattr(self, 'tag_count_label'):
            original_text = self.tag_count_label.text()
            self.tag_count_label.setText(message)
            
            # Restore original text after duration
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.tag_count_label.setText(original_text))

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