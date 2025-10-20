from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollBar,
                           QWidget, QPushButton, QLabel, QMenu, QSplitter,
                           QComboBox, QRadioButton, QButtonGroup, QToolButton, 
                           QStackedWidget, QLineEdit, QCheckBox, QDialog, QMessageBox,
                           QListWidgetItem, QTabWidget, QFrame) # Added QDialog, QMessageBox, QListWidgetItem, QTabWidget, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSortFilterProxyModel, QRegularExpression, QTime, QEvent # Added QTime and QEvent
from PyQt6.QtCore import QThread, QObject
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
from ...gui.widgets.tag_filter_panel import TagFilterPanel # Added filter panel
from ...tags.filters import TagFilterState # Added filter state
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


# Background worker to compute raw_tag_counts and tag_to_album_nodes off the GUI thread
class TagProcessingWorker(QObject):
    """Worker that processes raw tags from album nodes in a background thread.

    Emits:
        progress(int): number of albums processed so far
        finished(dict, dict): raw_tag_counts (dict) and tag_to_album_nodes (dict)
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(object, object)

    def __init__(self, album_nodes):
        super().__init__()
        self.album_nodes = list(album_nodes)
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the worker."""
        self._cancelled = True

    def run(self):
        raw_counts = Counter()
        tag_to_nodes = defaultdict(list)
        tag_splitter = re.compile(r'[;,]')

        total = len(self.album_nodes)
        batch = max(1, total // 100)

        for i, node in enumerate(self.album_nodes, start=1):
            if getattr(self, '_cancelled', False):
                # Emit finished with partial results if cancelled
                try:
                    self.finished.emit(dict(raw_counts), dict(tag_to_nodes))
                except Exception:
                    pass
                return
            raw_tags_str = node.get('raw_tags') or node.get('genre', '')
            if raw_tags_str:
                tags = [t.strip() for t in tag_splitter.split(raw_tags_str) if t.strip()]
                for tag in tags:
                    raw_counts[tag] += 1
                    tag_to_nodes[tag].append(node)

            # Emit progress occasionally
            if i % batch == 0 or i == total:
                try:
                    self.progress.emit(i)
                except Exception:
                    pass

        # Convert Counter to dict for safe cross-thread transfer
        self.finished.emit(dict(raw_counts), dict(tag_to_nodes))

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
        # Store raw tag -> albums separately from processed mapping
        self.raw_tag_to_album_nodes = defaultdict(list)
        # Inverted index: processed tag -> list of album node dicts (used for fast previews and lookups)
        self.tag_to_album_nodes = defaultdict(list)
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
        self.tag_panel.setObjectName("tagPanel")
        self.tag_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.tag_panel.setMinimumWidth(250)  # Ensure minimum usable width
        tag_panel_layout = QVBoxLayout(self.tag_panel)
        tag_panel_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add filter header controls with better organization
        self.filter_header = QWidget()
        self.filter_header.setObjectName("filterHeader")
        self.filter_header.setMaximumHeight(80)  # Limit header height to preserve space for tables
        filter_header_layout = QVBoxLayout(self.filter_header)  # Use vertical layout for better organization
        filter_header_layout.setContentsMargins(5, 5, 5, 5)
        filter_header_layout.setSpacing(3)
        
        # Top row - Info and search
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tag_count_label = QLabel("Tags: 0")
        self.tag_count_label.setObjectName("tagCountLabel")
        top_layout.addWidget(self.tag_count_label)
        
        # Add progress indicator for large datasets
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Processing: %p%")
        self.progress_bar.setToolTip("Data processing progress")
        top_layout.addWidget(self.progress_bar)
        
        # Search input for tags
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("Search tags...")
        self.tag_search_input.setToolTip("Search tags (Ctrl+F to focus)")
        self.tag_search_input.returnPressed.connect(self._handle_tag_search)
        self.tag_search_input.textChanged.connect(self._handle_tag_search)  # Live search
        self.tag_search_input.setMaximumWidth(150)  # Limit width to save space
        top_layout.addWidget(self.tag_search_input)
        
        # Clear search button
        self.tag_search_clear_button = QPushButton("✖")
        self.tag_search_clear_button.clicked.connect(self._clear_tag_search)
        self.tag_search_clear_button.setMaximumWidth(30)  # Very compact
        self.tag_search_clear_button.setToolTip("Clear search (Esc)")
        top_layout.addWidget(self.tag_search_clear_button)
        
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
        
        # Action buttons with icons
        self.export_button = QPushButton("📊 Tags")
        self.export_button.setObjectName("exportTagsButton")
        self.export_button.setToolTip("Export tag data to console for analysis")
        self.export_button.clicked.connect(self._export_tag_data)
        bottom_layout.addWidget(self.export_button)
        
        self.export_albums_button = QPushButton("💾 Albums")
        self.export_albums_button.setObjectName("exportAlbumsButton")
        self.export_albums_button.setToolTip("Export filtered albums to CSV")
        self.export_albums_button.clicked.connect(self._export_filtered_albums)
        bottom_layout.addWidget(self.export_albums_button)
        
        # Visual separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #3f4449; padding: 0 5px;")
        bottom_layout.addWidget(separator1)
        
        self.manage_singles_button = QPushButton("• Singles")
        self.manage_singles_button.setObjectName("manageSinglesButton")
        self.manage_singles_button.setToolTip("Manage single-instance tags")
        self.manage_singles_button.clicked.connect(self._show_single_instance_dialog)
        bottom_layout.addWidget(self.manage_singles_button)
        
        # Visual separator
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #3f4449; padding: 0 5px;")
        bottom_layout.addWidget(separator2)
        
        self.clear_filters_button = QPushButton("✕ Clear")
        self.clear_filters_button.setObjectName("clearFiltersButton")
        self.clear_filters_button.setToolTip("Clear all tag filters (Ctrl+Shift+C)")
        self.clear_filters_button.clicked.connect(self.clear_tag_filters)
        bottom_layout.addWidget(self.clear_filters_button)
        
        # Add bulk action buttons
        self.include_selected_button = QPushButton("➕")
        self.include_selected_button.setObjectName("includeButton")
        self.include_selected_button.setToolTip("Include selected tags (Ctrl+I)")
        self.include_selected_button.clicked.connect(self._include_selected_tags)
        bottom_layout.addWidget(self.include_selected_button)
        
        self.exclude_selected_button = QPushButton("➖")
        self.exclude_selected_button.setObjectName("excludeButton")
        self.exclude_selected_button.setToolTip("Exclude selected tags (Ctrl+E)")
        self.exclude_selected_button.clicked.connect(self._exclude_selected_tags)
        bottom_layout.addWidget(self.exclude_selected_button)
        
        self.invert_filters_button = QPushButton("⇄")
        self.invert_filters_button.setObjectName("invertButton")
        self.invert_filters_button.setToolTip("Invert all filters (swap Include/Exclude)")
        self.invert_filters_button.clicked.connect(self._invert_filters)
        bottom_layout.addWidget(self.invert_filters_button)
        
        # Visual separator
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #3f4449; padding: 0 5px;")
        bottom_layout.addWidget(separator3)
        
        # Add layout reset button
        self.reset_layout_button = QPushButton("↻ Reset")
        self.reset_layout_button.setObjectName("resetLayoutButton")
        self.reset_layout_button.setToolTip("Reset layout to default proportions (Ctrl+R)")
        self.reset_layout_button.clicked.connect(self.reset_layout)
        bottom_layout.addWidget(self.reset_layout_button)
        
        # Add help button
        self.help_button = QPushButton("❓")
        self.help_button.setObjectName("helpButton")
        self.help_button.setToolTip("Show keyboard shortcuts and help (F1)")
        self.help_button.clicked.connect(self.show_layout_help)
        bottom_layout.addWidget(self.help_button)
        
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
        # Connect preview (hover) requests to handler
        self.atomic_widget.preview_requested.connect(self._on_atomic_preview_requested)
        
        # Add the atomic widget to the bottom row for easy access
        bottom_layout.addWidget(self.atomic_widget)
        
        # Add toggle button for new filter panel
        separator_panel = QLabel("|")
        separator_panel.setStyleSheet("color: #3f4449; padding: 0 5px;")
        bottom_layout.addWidget(separator_panel)
        
        self.toggle_filter_panel_button = QPushButton("🎯 Groups")
        self.toggle_filter_panel_button.setObjectName("toggleFilterPanelButton")
        self.toggle_filter_panel_button.setToolTip("Toggle advanced filter groups panel")
        self.toggle_filter_panel_button.setCheckable(True)
        self.toggle_filter_panel_button.setChecked(False)
        self.toggle_filter_panel_button.clicked.connect(self._toggle_filter_panel)
        bottom_layout.addWidget(self.toggle_filter_panel_button)
        
        # Create collapsible filter panel container with visual boundary
        self.filter_panel_container = QFrame()
        self.filter_panel_container.setObjectName("filterPanelContainer")
        self.filter_panel_container.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.filter_panel_container.setLineWidth(1)
        self.filter_panel_container.setVisible(False)
        self.filter_panel_container.setStyleSheet("""
            QFrame#filterPanelContainer {
                background-color: #0d0d0d;
                border: 1px solid #2a2d32;
                border-radius: 4px;
                margin: 1px;
            }
        """)
        
        filter_container_layout = QVBoxLayout(self.filter_panel_container)
        filter_container_layout.setContentsMargins(5, 5, 5, 5)
        filter_container_layout.setSpacing(5)
        
        # Create advanced filter panel
        self.filter_panel = TagFilterPanel(
            filter_state=None,  # Will be created
            available_tags=[]  # Will be populated when data loads
        )
        self.filter_panel.filtersChanged.connect(self._on_filter_panel_changed)
        filter_container_layout.addWidget(self.filter_panel)
        
        # Add resize handle for adjustable height
        self.filter_panel_resize_handle = QLabel("═")
        self.filter_panel_resize_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filter_panel_resize_handle.setStyleSheet("""
            QLabel {
                background: #1a1d21;
                color: #555;
                padding: 1px;
                font-size: 8px;
                border-top: 1px solid #2a2d32;
            }
            QLabel:hover {
                background: #2a2d32;
                color: #777;
                cursor: ns-resize;
            }
        """)
        self.filter_panel_resize_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self.filter_panel_resize_handle.mousePressEvent = self._start_resize_filter_panel
        self.filter_panel_resize_handle.mouseMoveEvent = self._resize_filter_panel
        self.filter_panel_resize_handle.mouseReleaseEvent = self._end_resize_filter_panel
        filter_container_layout.addWidget(self.filter_panel_resize_handle)
        
        # Track resize state
        self._filter_panel_resizing = False
        self._filter_panel_resize_start_y = 0
        self._filter_panel_start_height = 0
        
        # Set initial size constraints (adjustable) - more compact
        self.filter_panel_container.setMinimumHeight(120)
        self.filter_panel_container.setMaximumHeight(400)
        
        tag_panel_layout.addWidget(self.filter_panel_container)
        
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
        # Enable multi-selection with Ctrl+Click
        self.tags_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tags_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Enable mouse tracking so we can show hover previews for tags
        self.tags_table.setMouseTracking(True)
        self.tags_table.installEventFilter(self)
        # Connect click to cycle filter state for the clicked tag
        self.tags_table.cellClicked.connect(self._on_tag_table_cell_clicked)
        # Connect double-click to show preview
        self.tags_table.cellDoubleClicked.connect(self._on_tag_double_clicked)
        
        # Configure tag table headers for better responsiveness
        header = self.tags_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Tag name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        header.setStretchLastSection(False)  # Don't stretch the last section
        header.setSortIndicatorShown(True)
        # Show initial sort indicator consistent with default sort settings
        try:
            header.setSortIndicator(self.tags_sort_column, self.tags_sort_order)
        except Exception:
            pass
        header.sectionClicked.connect(self._handle_tag_sort)
        
        # Set optimal column widths
        self.tags_table.setColumnWidth(1, 80)   # Count column - wider for formatted numbers
        self.tags_table.setColumnWidth(2, 90)   # Matching column - wider for formatted numbers  
        self.tags_table.setColumnWidth(3, 80)   # Filter column
        
        self.tags_table.setShowGrid(True)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSortingEnabled(False) # Disable native sorting, will handle manually
        self.tags_sort_column = 1  # Default sort by count (index 1)
        self.tags_sort_order = Qt.SortOrder.DescendingOrder
        # self.tags_table.cellDoubleClicked.connect(self._cycle_tag_filter_state) # Ensure this is removed or commented
        # Improve row height and hide the vertical header for a cleaner look
        self.tags_table.verticalHeader().setDefaultSectionSize(24)
        self.tags_table.verticalHeader().setVisible(False)
        
        # Add tag views (table and cloud) to the QStackedWidget
        self.tag_views_stack.addWidget(self.tags_table)
        self.tag_cloud_widget = TagCloudWidget(self) # Initialize TagCloudWidget
        self.tag_cloud_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tag_cloud_widget.setMinimumHeight(250)  # Ensure minimum usable height for tag cloud
        self.tag_views_stack.addWidget(self.tag_cloud_widget)
        # If the tag cloud widget exposes a tagClicked signal, connect it to preview handler
        if hasattr(self.tag_cloud_widget, 'tagClicked'):
            try:
                self.tag_cloud_widget.tagClicked.connect(self._on_atomic_preview_requested)
            except Exception:
                # Some cloud widgets might use different signal signatures; ignore if incompatible
                pass
        
        # Add the QStackedWidget (tag_views_stack) to the tag_panel_layout
        tag_panel_layout.addWidget(self.tag_views_stack, 1)  # Give stretch factor of 1 to expand

        # Create the album panel, its layout, and its widgets (album_count_label, album_table)
        self.album_panel = QWidget()
        self.album_panel.setObjectName("albumPanel")
        self.album_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.album_panel.setMinimumWidth(300)  # Ensure minimum usable width
        album_panel_layout = QVBoxLayout(self.album_panel)
        album_panel_layout.setContentsMargins(5, 5, 5, 5)

        self.album_count_label = QLabel("Albums: 0")
        self.album_count_label.setMaximumHeight(25)  # Keep album header compact
        album_panel_layout.addWidget(self.album_count_label)

        self.album_table = QTableWidget() # Definition of self.album_table
        self.album_table.setColumnCount(7)
        self.album_table.setHorizontalHeaderLabels([
            "Artist",
            "Album",
            "Year",
            "Genre",
            "Country",
            "Vocal Style",
            "Tags"
        ])
        self.album_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.album_table.setMinimumHeight(200)  # Ensure minimum usable height for album table
        album_header = self.album_table.horizontalHeader()
        album_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        album_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        album_header.setStretchLastSection(True)  # Tags column stretches
        album_header.setSectionsClickable(True)
        album_header.setHighlightSections(True)
        album_header.setSortIndicatorShown(True)
        
        # Set reasonable initial column widths for albums
        self.album_table.setColumnWidth(0, 200)  # Artist column
        self.album_table.setColumnWidth(1, 250)  # Album column
        self.album_table.setColumnWidth(2, 80)   # Year column
        self.album_table.setColumnWidth(3, 220)  # Genre column
        self.album_table.setColumnWidth(4, 140)  # Country column
        self.album_table.setColumnWidth(5, 150)  # Vocal style column
        self.album_table.setSortingEnabled(True)
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setShowGrid(True)
        self.album_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.album_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Tidy album rows and hide vertical header
        self.album_table.verticalHeader().setDefaultSectionSize(26)
        self.album_table.verticalHeader().setVisible(False)
        
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
        
        # Add status bar at the bottom
        self.status_bar = QLabel("Ready")
        self.status_bar.setObjectName("statusBarLabel")
        self.status_bar.setMinimumHeight(28)
        self.status_bar.setMaximumHeight(28)
        main_layout.addWidget(self.status_bar)
        
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
        
        # Initialize atomic tag system state.
        # Defaulting to atomic mode provides better tag consolidation and a more useful UI for complex tags.
        self.atomic_mode = True
        self.data_interface = None  # Will be set when data is updated

        # Initialize data interface for atomic tag support
        self._initialize_data_interface()

        # Worker thread and object for heavy tag processing
        self._tag_worker_thread = None
        self._tag_worker = None

        # atomic_mode_changed already connected when the atomic widget was created above; avoid duplicate connections here

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
    
    def _format_number(self, num):
        """Format a number with comma separators for better readability."""
        try:
            return f"{int(num):,}"
        except (ValueError, TypeError):
            return str(num)

    def _reprocess_base_tag_data(self):
        """
        Recalculates tag counts and mappings from the original album node data.
        This should be called when normalization settings change or data is first loaded.
        Optimized for performance with large datasets.
        """
        # Decide whether to perform raw counting synchronously (small datasets)
        total_albums = len(self.album_nodes_original)
        if total_albums > 1000:
            # For large datasets, start background worker (which will call finalizer on finish)
            self._start_tag_processing_worker()
            return

        # Small dataset: perform raw counting synchronously, then finalize
        self._process_raw_counts_sync()
        self._finalize_tag_processing_from_raw()

    def _process_raw_counts_sync(self):
        """Synchronous processing of raw tag counts for small datasets."""
        self.raw_tag_counts.clear()
        self.raw_tag_to_album_nodes.clear()
        # Reset processed mapping; it will be rebuilt during finalization
        self.tag_to_album_nodes = defaultdict(list)
        tag_splitter = re.compile(r'[;,]')

        for node in self.album_nodes_original:
            raw_tags_str = node.get('raw_tags') or node.get('genre', '')
            if not raw_tags_str:
                continue
            tags = [t.strip() for t in tag_splitter.split(raw_tags_str) if t.strip()]
            for tag in tags:
                self.raw_tag_counts[tag] += 1
                self.raw_tag_to_album_nodes[tag].append(node)

    def _finalize_tag_processing_from_raw(self):
        """Finalize processing using already-populated self.raw_tag_counts and raw tag mappings.

        This performs normalization/atomic decomposition, builds self.tag_counts and normalized mapping,
        updates single-instance tags and refreshes views.
        """
        self.tag_counts.clear()
        self.normalized_mapping.clear()

        unique_raw_tags = list(self.raw_tag_counts.keys())
        is_normalizing = self.normalize_checkbox.isChecked()
        processed_mapping = defaultdict(list)

        if is_normalizing:
            graphics_logger.info(f"TagExplorerView: Finalizing processing with ENHANCED normalization (atomic mode: {self.tag_normalizer.get_atomic_mode()})")
            for raw_tag in unique_raw_tags:
                count = self.raw_tag_counts[raw_tag]
                source_nodes = self.raw_tag_to_album_nodes.get(raw_tag, [])

                if self.tag_normalizer.get_atomic_mode():
                    atomic_components = self.tag_normalizer.normalize_to_atomic(raw_tag)

                    if atomic_components:
                        for component in atomic_components:
                            self.tag_counts[component] += count
                            if source_nodes:
                                processed_mapping[component].extend(source_nodes)
                        self.normalized_mapping[raw_tag] = atomic_components
                    else:
                        # Fallback to enhanced normalization if atomic breakdown not available
                        normalized_tag = self.tag_normalizer.normalize_enhanced(raw_tag)
                        if normalized_tag:
                            self.tag_counts[normalized_tag] += count
                            if source_nodes:
                                processed_mapping[normalized_tag].extend(source_nodes)
                            self.normalized_mapping[raw_tag] = normalized_tag
                else:
                    # Use enhanced normalization for better tag consolidation
                    normalized_tag = self.tag_normalizer.normalize_enhanced(raw_tag)
                    if normalized_tag:
                        self.tag_counts[normalized_tag] += count
                        if source_nodes:
                            processed_mapping[normalized_tag].extend(source_nodes)
                        self.normalized_mapping[raw_tag] = normalized_tag
        else:
            graphics_logger.info("TagExplorerView: Finalizing processing without normalization")
            # Directly use raw counts and nodes
            self.tag_counts = Counter(self.raw_tag_counts)
            self.normalized_mapping = {tag: tag for tag in unique_raw_tags}
            for raw_tag in unique_raw_tags:
                source_nodes = self.raw_tag_to_album_nodes.get(raw_tag, [])
                if source_nodes:
                    processed_mapping[raw_tag].extend(source_nodes)

        # Replace processed tag-to-node mapping with the freshly built version
        self.tag_to_album_nodes = processed_mapping

        # Update single instance tags after reprocessing
        if self.tag_analyzer:
            self.single_instance_tags = self.tag_analyzer.find_single_instance_tags(self.tag_counts)
        else:
            self.single_instance_tags = {tag for tag, count in self.tag_counts.items() if count == 1}

        graphics_logger.info(f"TagExplorerView: Processed tags summary - Raw tags: {len(self.raw_tag_counts)}, Processed tags: {len(self.tag_counts)}")
        self.tag_count_label.setText(f"Tags: {len(self.tag_counts)}")
        
        # Update filter panel with available tags
        if hasattr(self, 'filter_panel') and self.filter_panel is not None:
            available_tags = list(self.tag_counts.keys())
            self.filter_panel.update_available_tags(available_tags)
            graphics_logger.debug(f"Updated filter panel with {len(available_tags)} available tags")

        # After finalization, re-apply filters and update views
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
                    # No atomic breakdown available, use enhanced normalization
                    normalized_tag = self.tag_normalizer.normalize_enhanced(raw_tag)
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
        Combines legacy tag table filters with advanced filter panel groups.
        Optimized for performance with large datasets.
        """
        # Temporarily disable updates during bulk processing
        self.setUpdatesEnabled(False)
        graphics_logger.debug(f"Applying tag filters. Normalization active: {self.tag_normalizer.is_active()}")
        graphics_logger.debug(f"Current tag_filters: {self.tag_filters}")

        # Get filter state from filter panel if visible
        filter_panel_state = None
        if hasattr(self, 'filter_panel') and self.filter_panel_container.isVisible():
            filter_panel_state = self.filter_panel.get_filter_state()
            graphics_logger.debug(f"Using filter panel with {len(filter_panel_state.groups)} groups")
        
        # Pre-compute filter sets for better performance (from legacy tag table)
        include_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_INCLUDE}
        exclude_filters = {tag for tag, state in self.tag_filters.items() if state == self.FILTER_EXCLUDE}
        
        # Combine exclusions from both sources
        all_exclusions = exclude_filters.copy()
        if filter_panel_state:
            all_exclusions.update(filter_panel_state.exclude_tags)
        
        # Early exit if no filters are active
        has_legacy_filters = bool(include_filters or exclude_filters)
        has_panel_filters = filter_panel_state and not filter_panel_state.is_empty()
        has_filters = has_legacy_filters or has_panel_filters

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
                            # Fallback to enhanced normalization if not in cache
                            fallback_normalized = self.tag_normalizer.normalize_enhanced(tag)
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

                # Check exclusions first (from both sources)
                if all_exclusions and all_exclusions.intersection(node_tags_set):
                    continue

                # Check legacy include filters (from tag table)
                legacy_match = True
                if include_filters:
                    legacy_match = bool(include_filters.intersection(node_tags_set))
                
                # Check filter panel groups (if active)
                panel_match = True
                if filter_panel_state and not filter_panel_state.is_empty():
                    # Pass the tag set to the filter state matches method
                    panel_match = filter_panel_state.matches(node_tags_set)
                
                # Album must match BOTH legacy filters AND panel filters (if active)
                if not legacy_match or not panel_match:
                    continue

                # If we reach here, the node matches all active filters
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
        
        # Update status bar with filter summary
        self._update_status_bar()

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
            # Tag column (Column 0) - bold and highlight if filtered
            tag_item = SortableTableWidgetItem(tag)
            tag_item.setToolTip(f"Tag: {tag}\nClick to cycle filter state\nCtrl+Click for multi-select")
            
            # Highlight if this tag has an active filter
            if filter_state != self.FILTER_NEUTRAL:
                font = tag_item.font()
                font.setBold(True)
                tag_item.setFont(font)
                # Light background color for filtered tags
                if filter_state == self.FILTER_INCLUDE:
                    tag_item.setBackground(QColor(40, 80, 40))  # Dark green tint
                elif filter_state == self.FILTER_EXCLUDE:
                    tag_item.setBackground(QColor(80, 40, 40))  # Dark red tint
            
            self.tags_table.setItem(row_position, 0, tag_item)

            # Count column (Column 1) - with formatting and right alignment
            count_item = SortableTableWidgetItem(self._format_number(count))
            count_item.setData(Qt.ItemDataRole.UserRole, int(count))
            count_item.setToolTip(f"Total occurrences: {self._format_number(count)}")
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tags_table.setItem(row_position, 1, count_item)
            
            # Matching column (Column 2) - with formatting and right alignment
            matching_item = SortableTableWidgetItem(self._format_number(matching_count))
            matching_item.setData(Qt.ItemDataRole.UserRole, int(matching_count))
            matching_item.setToolTip(f"Matching albums with current filters: {self._format_number(matching_count)}")
            matching_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tags_table.setItem(row_position, 2, matching_item)

            # Filter column (Column 3) - with color coding
            filter_text = "Neutral"
            filter_color = QColor(128, 128, 128)  # Gray
            
            if filter_state == self.FILTER_INCLUDE:
                filter_text = "Include"
                filter_color = QColor(76, 175, 80)  # Green
            elif filter_state == self.FILTER_EXCLUDE:
                filter_text = "Exclude"
                filter_color = QColor(244, 67, 54)  # Red
            
            filter_q_item = QTableWidgetItem(filter_text)
            filter_q_item.setData(Qt.ItemDataRole.UserRole, filter_state)
            filter_q_item.setToolTip(f"Filter state: {filter_text}")
            filter_q_item.setForeground(filter_color)
            filter_q_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            font = filter_q_item.font()
            font.setBold(True)
            filter_q_item.setFont(font)
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
    
    def _update_status_bar(self):
        """Update the status bar with filter summary."""
        include_count = sum(1 for state in self.tag_filters.values() if state == self.FILTER_INCLUDE)
        exclude_count = sum(1 for state in self.tag_filters.values() if state == self.FILTER_EXCLUDE)
        total_albums = len(self.album_nodes_original)
        filtered_albums = len(self.filtered_albums)
        
        status_parts = []
        
        if include_count > 0 or exclude_count > 0:
            filter_parts = []
            if include_count > 0:
                filter_parts.append(f"<span style='color: #66BB6A; font-weight: bold;'>➕ {include_count}</span>")
            if exclude_count > 0:
                filter_parts.append(f"<span style='color: #EF5350; font-weight: bold;'>➖ {exclude_count}</span>")
            status_parts.append(f"<b>Filters:</b> {' '.join(filter_parts)}")
        else:
            status_parts.append("<span style='color: #888;'>○ No active filters</span>")
        
        # Album count with visual indicator
        if filtered_albums < total_albums:
            percentage = (filtered_albums / total_albums * 100) if total_albums > 0 else 0
            status_parts.append(f"<b>Albums:</b> <span style='color: #64B5F6;'>{self._format_number(filtered_albums)}</span> of {self._format_number(total_albums)} <span style='color: #888;'>({percentage:.1f}%)</span>")
        else:
            status_parts.append(f"<b>Albums:</b> {self._format_number(filtered_albums)}")
        
        self.status_bar.setText("  •  ".join(status_parts))
    
    def _update_album_table_display(self):
        """Populate the album_table with data from self.filtered_albums. Optimized for performance."""
        # Disable sorting during bulk updates for better performance
        sorting_enabled = self.album_table.isSortingEnabled()
        self.album_table.setSortingEnabled(False)
        self.setUpdatesEnabled(False)
        
        # Clear existing rows efficiently
        self.album_table.setRowCount(0)
        
        # Set row count once for all albums
        num_albums = len(self.filtered_albums)
        
        # For very large datasets, consider virtual scrolling or pagination
        if num_albums > 10000:
            graphics_logger.info(f"Large album dataset ({num_albums} albums), using optimized display")
            self._update_album_table_large_dataset()
            self.setUpdatesEnabled(True)
            return
        
        self.album_table.setRowCount(num_albums)
        
        # Show progress for large datasets
        show_progress = num_albums > 2000
        if show_progress:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(num_albums)
            self.progress_bar.setValue(0)
        
        # Optimized batch processing with larger batches
        batch_size = 2000  # Increased from 1000 for better throughput
        
        for batch_start in range(0, num_albums, batch_size):
            batch_end = min(batch_start + batch_size, num_albums)
            
            # Pre-create all items for this batch for better memory locality
            batch_items = []
            
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
                        pass  # Silent failure, no need to log for every item
                
                genre_display = str(album_node.get('genre', '') or '')
                country_display = str(album_node.get('country', '') or '')

                vocal_style_display = album_node.get('vocal_style') or ''
                if not vocal_style_display and album_node.get('vocal_styles'):
                    vocal_style_display = ", ".join(str(v) for v in album_node['vocal_styles'] if v)

                # Format tags efficiently with full list in tooltip
                tags_list = album_node.get('tags', [])
                if isinstance(tags_list, list):
                    if tags_list:
                        tags_str = ", ".join(map(str, tags_list))
                        # Only create detailed tooltip if there are many tags
                        tags_tooltip = "\n".join(map(str, tags_list)) if len(tags_list) > 3 else tags_str
                    else:
                        tags_str = ""
                        tags_tooltip = ""
                else:
                    tags_str = str(tags_list)
                    tags_tooltip = tags_str
                
                # Store items for batch insertion
                tags_tooltip_text = f"All Tags:\n{tags_tooltip}" if tags_tooltip else "All Tags: (none)"

                batch_items.append((
                    row_position,
                    (artist, artist),
                    (album_title, album_title),
                    (year_display_string, year_sort_integer, f"Release Year: {year_display_string}"),
                    (genre_display, genre_display),
                    (country_display, country_display),
                    (vocal_style_display, vocal_style_display),
                    (tags_str, tags_tooltip_text)
                ))
            
            # Batch insert all items
            for row_pos, artist_data, album_data, year_data, genre_data, country_data, vocal_data, tags_data in batch_items:
                # Artist
                artist_item = QTableWidgetItem(artist_data[0])
                artist_item.setToolTip(artist_data[1])
                self.album_table.setItem(row_pos, 0, artist_item)

                # Album
                album_item = QTableWidgetItem(album_data[0])
                album_item.setToolTip(album_data[1])
                self.album_table.setItem(row_pos, 1, album_item)

                # Year
                year_item = QTableWidgetItem(year_data[0])
                if year_data[1] is not None:
                    year_item.setData(Qt.ItemDataRole.UserRole, year_data[1])
                year_item.setToolTip(year_data[2])
                self.album_table.setItem(row_pos, 2, year_item)

                # Genre
                genre_item = QTableWidgetItem(genre_data[0])
                genre_item.setToolTip(genre_data[1])
                self.album_table.setItem(row_pos, 3, genre_item)

                # Country
                country_item = QTableWidgetItem(country_data[0])
                country_item.setToolTip(country_data[1])
                self.album_table.setItem(row_pos, 4, country_item)

                # Vocal style
                vocal_item = QTableWidgetItem(vocal_data[0])
                vocal_item.setToolTip(vocal_data[1])
                self.album_table.setItem(row_pos, 5, vocal_item)

                # Tags
                tags_item = QTableWidgetItem(tags_data[0])
                tags_item.setToolTip(tags_data[1])
                self.album_table.setItem(row_pos, 6, tags_item)
            
            # Update progress less frequently
            if show_progress and batch_end % 4000 == 0:
                self.progress_bar.setValue(batch_end)
        
        # Final progress update
        if show_progress:
            self.progress_bar.setValue(num_albums)
            self.progress_bar.setVisible(False)
        
        # Re-enable sorting
        self.album_table.setSortingEnabled(sorting_enabled)
        self.setUpdatesEnabled(True)
        
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
            genre_display = str(album_node.get('genre', '') or '')
            country_display = str(album_node.get('country', '') or '')
            vocal_display = album_node.get('vocal_style') or ''
            if not vocal_display and album_node.get('vocal_styles'):
                vocal_display = ", ".join(str(v) for v in album_node['vocal_styles'] if v)

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
            self.album_table.setItem(i, 3, QTableWidgetItem(genre_display))
            self.album_table.setItem(i, 4, QTableWidgetItem(country_display))
            self.album_table.setItem(i, 5, QTableWidgetItem(vocal_display))
            self.album_table.setItem(i, 6, QTableWidgetItem(tags_str))
        
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

    def eventFilter(self, source, event):
        """Handle hover events over the tags table to show preview samples."""
        if source is self.tags_table:
            if event.type() == QEvent.Type.MouseMove:
                pos = event.position()
                # Convert to integer coordinates
                x, y = int(pos.x()), int(pos.y())
                item = self.tags_table.itemAt(x, y)
                if item and item.column() == 0:
                    tag_name = item.text()
                    # Trigger preview handler
                    self._on_atomic_preview_requested(tag_name)
                else:
                    # Clear preview if moving over non-tag area
                    self.atomic_widget.show_preview_samples('', [])
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                # Clear preview when leaving the widget
                self.atomic_widget.show_preview_samples('', [])

        return super().eventFilter(source, event)
    
    def _add_album_data(self, data_node):
        """Add new album data to the view's original data store."""
        self.album_nodes_original.append(data_node)
        # Maintain inverted index incrementally for responsiveness
        try:
            self._index_album_node(data_node)
        except Exception:
            # Fallback to full reprocess if incremental indexing fails
            graphics_logger.debug("Incremental indexing failed; full reprocess recommended")
    
    def _remove_album_data(self, data_node):
        """Remove album data from the view's original data store."""
        try:
            self.album_nodes_original.remove(data_node)
            # Maintain inverted index
            try:
                self._unindex_album_node(data_node)
            except Exception:
                graphics_logger.debug("Incremental unindexing failed; full reprocess recommended")
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
                # Update in place and maintain index
                old_node = self.album_nodes_original[i]
                self.album_nodes_original[i] = data_node
                try:
                    self._unindex_album_node(old_node)
                    self._index_album_node(data_node)
                except Exception:
                    graphics_logger.debug("Incremental reindexing on modify failed; full reprocess recommended")
                return
        graphics_logger.warning(f"Attempted to modify a node not found in album_nodes_original: ID {node_id_to_modify}")

    def _index_album_node(self, node):
        """Add an album node to the inverted index based on processed tags."""
        raw_tags_str = node.get('raw_tags') or node.get('genre', '')
        if not raw_tags_str:
            return

        tags = [t.strip() for t in re.split(r'[;,]', raw_tags_str) if t.strip()]
        if not tags:
            return

        # Update raw tag mapping
        for tag in tags:
            self.raw_tag_to_album_nodes[tag].append(node)

        if not self.tag_normalizer.is_active():
            for tag in tags:
                self.tag_to_album_nodes[tag].append(node)
            return

        if self.tag_normalizer.get_atomic_mode():
            for tag in tags:
                atomic_components = self.tag_normalizer.normalize_to_atomic(tag)
                if atomic_components:
                    for component in atomic_components:
                        self.tag_to_album_nodes[component].append(node)
                    self.normalized_mapping.setdefault(tag, atomic_components)
                else:
                    # Use enhanced normalization for fallback
                    normalized_tag = self.tag_normalizer.normalize_enhanced(tag)
                    if normalized_tag:
                        self.tag_to_album_nodes[normalized_tag].append(node)
                        self.normalized_mapping.setdefault(tag, normalized_tag)
        else:
            for tag in tags:
                # Use enhanced normalization for better tag consolidation
                normalized_tag = self.tag_normalizer.normalize_enhanced(tag)
                if normalized_tag:
                    self.tag_to_album_nodes[normalized_tag].append(node)
                    self.normalized_mapping.setdefault(tag, normalized_tag)

    def _unindex_album_node(self, node):
        """Remove an album node from the inverted index."""
        raw_tags_str = node.get('raw_tags') or node.get('genre', '')
        if not raw_tags_str:
            return

        tags = [t.strip() for t in re.split(r'[;,]', raw_tags_str) if t.strip()]
        if not tags:
            return

        # Remove from raw mapping
        for tag in tags:
            node_list = self.raw_tag_to_album_nodes.get(tag)
            if node_list:
                self.raw_tag_to_album_nodes[tag] = [n for n in node_list if n is not node]
                if not self.raw_tag_to_album_nodes[tag]:
                    del self.raw_tag_to_album_nodes[tag]

        if not self.tag_normalizer.is_active():
            for tag in tags:
                node_list = self.tag_to_album_nodes.get(tag)
                if node_list:
                    self.tag_to_album_nodes[tag] = [n for n in node_list if n is not node]
                    if not self.tag_to_album_nodes[tag]:
                        del self.tag_to_album_nodes[tag]
            return

        if self.tag_normalizer.get_atomic_mode():
            for tag in tags:
                atomic_components = self.tag_normalizer.normalize_to_atomic(tag)
                if atomic_components:
                    for component in atomic_components:
                        node_list = self.tag_to_album_nodes.get(component)
                        if node_list:
                            self.tag_to_album_nodes[component] = [n for n in node_list if n is not node]
                            if not self.tag_to_album_nodes[component]:
                                del self.tag_to_album_nodes[component]
                else:
                    # Use enhanced normalization for fallback
                    normalized_tag = self.tag_normalizer.normalize_enhanced(tag)
                    if normalized_tag:
                        node_list = self.tag_to_album_nodes.get(normalized_tag)
                        if node_list:
                            self.tag_to_album_nodes[normalized_tag] = [n for n in node_list if n is not node]
                            if not self.tag_to_album_nodes[normalized_tag]:
                                del self.tag_to_album_nodes[normalized_tag]
        else:
            for tag in tags:
                # Use enhanced normalization for better tag consolidation
                normalized_tag = self.tag_normalizer.normalize_enhanced(tag)
                if normalized_tag:
                    node_list = self.tag_to_album_nodes.get(normalized_tag)
                    if node_list:
                        self.tag_to_album_nodes[normalized_tag] = [n for n in node_list if n is not node]
                        if not self.tag_to_album_nodes[normalized_tag]:
                            del self.tag_to_album_nodes[normalized_tag]

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
        
        # Clear the LRU cache since normalization settings changed
        self._cached_normalize_tag.cache_clear()
        
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
        
        # Also clear filter panel if it exists
        if hasattr(self, 'filter_panel') and self.filter_panel is not None:
            self.filter_panel.get_filter_state().clear_all()
            # Force UI update
            for group_id in list(self.filter_panel.group_widgets.keys()):
                self.filter_panel._remove_group_widget(group_id)
            # Clear exclusions
            filter_state = self.filter_panel.get_filter_state()
            for tag in list(filter_state.exclude_tags):
                self.filter_panel._remove_exclusion_chip(tag)
                filter_state.exclude_tags.discard(tag)
            self.filter_panel._update_summary()
        
        self.apply_tag_filters() # This will refresh tables and matching counts
        self.update_status_message(f"Cleared {filter_count} tag filters")
        graphics_logger.info("All tag filters cleared.")
    
    def _include_selected_tags(self):
        """Include all selected tags."""
        selected_rows = set(item.row() for item in self.tags_table.selectedItems())
        count = 0
        for row in selected_rows:
            item = self.tags_table.item(row, 0)
            if item:
                self.tag_filters[item.text()] = self.FILTER_INCLUDE
                count += 1
        if count > 0:
            self.apply_tag_filters()
            self.update_status_message(f"Included {count} tags", 2000)
    
    def _exclude_selected_tags(self):
        """Exclude all selected tags."""
        selected_rows = set(item.row() for item in self.tags_table.selectedItems())
        count = 0
        for row in selected_rows:
            item = self.tags_table.item(row, 0)
            if item:
                self.tag_filters[item.text()] = self.FILTER_EXCLUDE
                count += 1
        if count > 0:
            self.apply_tag_filters()
            self.update_status_message(f"Excluded {count} tags", 2000)
    
    def _invert_filters(self):
        """Invert all current filters (swap Include and Exclude)."""
        count = 0
        for tag, state in list(self.tag_filters.items()):
            if state == self.FILTER_INCLUDE:
                self.tag_filters[tag] = self.FILTER_EXCLUDE
                count += 1
            elif state == self.FILTER_EXCLUDE:
                self.tag_filters[tag] = self.FILTER_INCLUDE
                count += 1
        if count > 0:
            self.apply_tag_filters()
            self.update_status_message(f"Inverted {count} filters", 2000)
    
    def _on_tag_double_clicked(self, row, column):
        """Show preview of albums for the double-clicked tag without applying filter."""
        item = self.tags_table.item(row, 0)
        if item:
            tag_name = item.text()
            self._show_tag_preview(tag_name)
    
    def _show_tag_preview(self, tag_name):
        """Show a preview dialog of albums containing the specified tag."""
        # Get albums for this tag from the inverted index
        processed_tag = tag_name
        if self.tag_normalizer.is_active():
            processed_tag = self._get_normalized_tag_for_processing(tag_name)
        
        nodes = self.tag_to_album_nodes.get(processed_tag, [])
        
        if not nodes:
            QMessageBox.information(self, "No Albums", f"No albums found with tag '{tag_name}'")
            return
        
        # Create preview dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Albums with tag: {tag_name}")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel(f"Found {len(nodes)} album(s) with tag '{tag_name}'")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)
        
        # Preview table
        preview_table = QTableWidget()
        preview_table.setColumnCount(7)
        preview_table.setHorizontalHeaderLabels([
            "Artist",
            "Album",
            "Year",
            "Genre",
            "Country",
            "Vocal Style",
            "Tags"
        ])
        preview_table.setRowCount(len(nodes))
        preview_table.setAlternatingRowColors(True)
        preview_table.setSortingEnabled(True)
        preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Populate preview table
        for i, node in enumerate(nodes):
            artist = node.get('artist', '')
            album = node.get('album', node.get('title', ''))
            year = str(node.get('release_year') or node.get('year') or '')
            genre = str(node.get('genre', '') or '')
            country = str(node.get('country', '') or '')
            vocal = node.get('vocal_style') or ''
            if not vocal and node.get('vocal_styles'):
                vocal = ", ".join(str(v) for v in node['vocal_styles'] if v)
            tags = ', '.join(map(str, node.get('tags', [])))
            
            preview_table.setItem(i, 0, QTableWidgetItem(artist))
            preview_table.setItem(i, 1, QTableWidgetItem(album))
            preview_table.setItem(i, 2, QTableWidgetItem(year))
            preview_table.setItem(i, 3, QTableWidgetItem(genre))
            preview_table.setItem(i, 4, QTableWidgetItem(country))
            preview_table.setItem(i, 5, QTableWidgetItem(vocal))
            preview_table.setItem(i, 6, QTableWidgetItem(tags))
        
        preview_table.resizeColumnsToContents()
        layout.addWidget(preview_table)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()
    
    def _export_filtered_albums(self):
        """Export the currently filtered albums to a CSV file."""
        if not self.filtered_albums:
            QMessageBox.warning(self, "No Albums", "No albums to export. Apply filters first.")
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            import csv
            from datetime import datetime
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"filtered_albums_{timestamp}.csv"
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Filtered Albums",
                default_filename,
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Write CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['Artist', 'Album', 'Year', 'Genre', 'Country', 'Vocal Style', 'Tags', 'Raw Tags'])
                
                # Write data
                for node in self.filtered_albums:
                    artist = node.get('artist', '')
                    album = node.get('album', node.get('title', ''))
                    year = node.get('release_year') or node.get('year') or ''
                    genre = node.get('genre', '')
                    country = node.get('country', '')
                    vocal = node.get('vocal_style') or ''
                    if not vocal and node.get('vocal_styles'):
                        vocal = ", ".join(str(v) for v in node['vocal_styles'] if v)
                    tags = ', '.join(map(str, node.get('tags', [])))
                    raw_tags = node.get('raw_tags', '')
                    
                    writer.writerow([artist, album, year, genre, country, vocal, tags, raw_tags])
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(self.filtered_albums)} albums to:\n{file_path}"
            )
            graphics_logger.info(f"Exported {len(self.filtered_albums)} filtered albums to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export albums:\n{str(e)}")
            graphics_logger.error(f"Failed to export filtered albums: {e}", exc_info=True)

    def _handle_tag_search(self):
        """Handle tag search from the input field."""
        search_text = self.tag_search_input.text().strip()
        if not search_text:
            # If search is cleared, show all rows
            for i in range(self.tags_table.rowCount()):
                self.tags_table.setRowHidden(i, False)
            return
            
        # Manual filter for QTableWidget with performance optimization
        search_lower = search_text.lower()
        visible_count = 0
        for i in range(self.tags_table.rowCount()):
            item = self.tags_table.item(i, 0) # Tag name is in column 0
            if item:
                # Simple case-insensitive search
                is_match = search_lower in item.text().lower()
                self.tags_table.setRowHidden(i, not is_match)
                if is_match:
                    visible_count += 1
        
        # Update label to show search results
        total_tags = self.tags_table.rowCount()
        self.tag_count_label.setText(f"Tags: {visible_count}/{total_tags}")
    
    def _clear_tag_search(self):
        """Clear the tag search input and show all tags."""
        self.tag_search_input.clear()
        self.tag_count_label.setText(f"Tags: {len(self.tag_counts)}")

    def _on_tag_table_cell_clicked(self, row, column):
        """Cycle the filter state for the tag(s) clicked. Supports multi-select with Ctrl."""
        from PyQt6.QtWidgets import QApplication
        
        # Get selected rows for multi-select support
        selected_rows = set(item.row() for item in self.tags_table.selectedItems())
        
        if not selected_rows:
            selected_rows = {row}
        
        # Determine the new state based on the clicked row
        clicked_item = self.tags_table.item(row, 0)
        if not clicked_item:
            return
            
        clicked_tag = clicked_item.text()
        current_state = self.tag_filters.get(clicked_tag, self.FILTER_NEUTRAL)
        
        # Cycle states: Neutral -> Include -> Exclude -> Neutral
        if current_state == self.FILTER_NEUTRAL:
            new_state = self.FILTER_INCLUDE
        elif current_state == self.FILTER_INCLUDE:
            new_state = self.FILTER_EXCLUDE
        else:
            new_state = self.FILTER_NEUTRAL
        
        # Apply to all selected rows
        modified_count = 0
        for selected_row in selected_rows:
            tag_item = self.tags_table.item(selected_row, 0)
            if tag_item:
                tag_name = tag_item.text()
                if new_state == self.FILTER_NEUTRAL:
                    if tag_name in self.tag_filters:
                        del self.tag_filters[tag_name]
                        modified_count += 1
                else:
                    self.tag_filters[tag_name] = new_state
                    modified_count += 1
        
        # Update status message if multiple tags were modified
        if modified_count > 1:
            state_name = "Include" if new_state == self.FILTER_INCLUDE else "Exclude" if new_state == self.FILTER_EXCLUDE else "Neutral"
            self.update_status_message(f"Set {modified_count} tags to {state_name}", 2000)
        
        # Re-apply filters and update views
        self.apply_tag_filters()

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
        
        # 5. Create and export DataFrames for detailed analysis
        try:
            # Create raw tags DataFrame (input tags prior to normalization)
            raw_export_data = []
            for tag in sorted(self.raw_tag_counts.keys()):
                raw_export_data.append({
                    "Tag": tag,
                    "Count": self.raw_tag_counts[tag],
                    "Normalized Form": self._get_normalized_tag_display(tag),
                    "Filter State": self.tag_filters.get(tag, self.FILTER_NEUTRAL)
                })
            raw_df = pd.DataFrame(raw_export_data)
            
            # Create normalized/atomic tags DataFrame (processed tags)
            normalized_export_data = []
            for tag in sorted(self.tag_counts.keys()):
                normalized_export_data.append({
                    "Tag": tag,
                    "Count": self.tag_counts[tag],
                    "Matching Count": self.matching_counts.get(tag, 0),
                    "Is Single": tag in self.single_instance_tags,
                    "Filter State": self.tag_filters.get(tag, self.FILTER_NEUTRAL)
                })
            normalized_df = pd.DataFrame(normalized_export_data)
            
            # Use a dialog to show both dataframes in separate tabs
            self._show_export_dialog(raw_df, normalized_df)
            
        except Exception as e:
            graphics_logger.error(f"Failed to create and export tag DataFrame: {e}", exc_info=True)
            
        graphics_logger.info("--- End of Tag Data Export ---")

    def _show_export_dialog(self, raw_df, normalized_df):
        """Shows a dialog with the exported data in separate tabs with options to save."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Tag Data Export")
        dialog.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout(dialog)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Raw Tags Tab
        raw_tab_widget = QWidget()
        raw_tab_layout = QVBoxLayout(raw_tab_widget)
        
        # Add info label for raw tags
        raw_info_label = QLabel(f"Raw Input Tags (before normalization): {len(raw_df)} unique tags")
        raw_info_label.setStyleSheet("font-weight: bold; color: #333; padding: 5px;")
        raw_tab_layout.addWidget(raw_info_label)
        
        raw_table = QTableWidget()
        raw_table.setRowCount(len(raw_df))
        raw_table.setColumnCount(len(raw_df.columns))
        raw_table.setHorizontalHeaderLabels(raw_df.columns)
        
        for i, row in raw_df.iterrows():
            for j, col in enumerate(raw_df.columns):
                raw_table.setItem(i, j, QTableWidgetItem(str(row[col])))
                
        raw_table.resizeColumnsToContents()
        raw_tab_layout.addWidget(raw_table)
        
        raw_save_button = QPushButton("Save Raw Tags to CSV")
        raw_save_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        
        def save_raw_csv():
            from PyQt6.QtWidgets import QFileDialog
            
            # Show file dialog to get save path
            path, _ = QFileDialog.getSaveFileName(dialog, "Save Raw Tags CSV", "raw_tags_export.csv", "CSV Files (*.csv)")
            
            if path:
                try:
                    raw_df.to_csv(path, index=False)
                    QMessageBox.information(dialog, "Success", f"Raw tags successfully saved to {path}")
                except Exception as e:
                    QMessageBox.warning(dialog, "Error", f"Failed to save file: {e}")
        
        raw_save_button.clicked.connect(save_raw_csv)
        raw_tab_layout.addWidget(raw_save_button)
        
        # Normalized/Atomic Tags Tab
        normalized_tab_widget = QWidget()
        normalized_tab_layout = QVBoxLayout(normalized_tab_widget)
        
        # Add info label for normalized tags
        mode_text = "atomic processing" if self.tag_normalizer.get_atomic_mode() else "normalization"
        normalized_info_label = QLabel(f"Processed Tags (after {mode_text}): {len(normalized_df)} unique tags")
        normalized_info_label.setStyleSheet("font-weight: bold; color: #333; padding: 5px;")
        normalized_tab_layout.addWidget(normalized_info_label)
        
        normalized_table = QTableWidget()
        normalized_table.setRowCount(len(normalized_df))
        normalized_table.setColumnCount(len(normalized_df.columns))
        normalized_table.setHorizontalHeaderLabels(normalized_df.columns)
        
        for i, row in normalized_df.iterrows():
            for j, col in enumerate(normalized_df.columns):
                normalized_table.setItem(i, j, QTableWidgetItem(str(row[col])))
                
        normalized_table.resizeColumnsToContents()
        normalized_tab_layout.addWidget(normalized_table)
        
        normalized_save_button = QPushButton("Save Processed Tags to CSV")
        normalized_save_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")
        
        def save_normalized_csv():
            from PyQt6.QtWidgets import QFileDialog
            
            # Show file dialog to get save path
            default_name = "atomic_tags_export.csv" if self.tag_normalizer.get_atomic_mode() else "normalized_tags_export.csv"
            path, _ = QFileDialog.getSaveFileName(dialog, "Save Processed Tags CSV", default_name, "CSV Files (*.csv)")
            
            if path:
                try:
                    normalized_df.to_csv(path, index=False)
                    tag_type = "Atomic" if self.tag_normalizer.get_atomic_mode() else "Normalized"
                    QMessageBox.information(dialog, "Success", f"{tag_type} tags successfully saved to {path}")
                except Exception as e:
                    QMessageBox.warning(dialog, "Error", f"Failed to save file: {e}")
        
        normalized_save_button.clicked.connect(save_normalized_csv)
        normalized_tab_layout.addWidget(normalized_save_button)
        
        # Add tabs to tab widget
        tab_widget.addTab(raw_tab_widget, "Raw Input Tags")
        tab_widget.addTab(normalized_tab_widget, "Processed Tags")
        
        # Add tab widget to main layout
        layout.addWidget(tab_widget)
        
        # Add overall save both button
        button_layout = QHBoxLayout()
        save_both_button = QPushButton("Save Both Datasets")
        save_both_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px; }")
        
        def save_both_csv():
            from PyQt6.QtWidgets import QFileDialog
            import os
            
            # Show directory dialog to save both files
            directory = QFileDialog.getExistingDirectory(dialog, "Select Directory to Save Both CSV Files")
            
            if directory:
                try:
                    raw_path = os.path.join(directory, "raw_tags_export.csv")
                    normalized_name = "atomic_tags_export.csv" if self.tag_normalizer.get_atomic_mode() else "normalized_tags_export.csv"
                    normalized_path = os.path.join(directory, normalized_name)
                    
                    raw_df.to_csv(raw_path, index=False)
                    normalized_df.to_csv(normalized_path, index=False)
                    
                    QMessageBox.information(dialog, "Success", 
                                          f"Both datasets saved successfully:\n• Raw tags: {raw_path}\n• Processed tags: {normalized_path}")
                except Exception as e:
                    QMessageBox.warning(dialog, "Error", f"Failed to save files: {e}")
        
        save_both_button.clicked.connect(save_both_csv)
        button_layout.addWidget(save_both_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _toggle_atomic_mode(self, enabled):
        """Toggle between standard and atomic tag modes."""
        self.atomic_mode = enabled
        
        # Update the tag normalizer to use atomic mode
        self.tag_normalizer.set_atomic_mode(enabled)
        
        # Clear the LRU cache since atomic mode changed
        self._cached_normalize_tag.cache_clear()
        
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

    def _on_atomic_preview_requested(self, tag_name: str):
        """Handle hover preview requests for a tag. Return sample album titles."""
        samples = []

        # Use inverted index for fast lookup (keys are processed tag names)
        processed_tag = tag_name
        if self.tag_normalizer.is_active():
            # We attempt to normalize the incoming tag for lookup; if normalization returns list, use first
            processed_tag = self._get_normalized_tag_for_processing(tag_name)

        nodes = self.tag_to_album_nodes.get(processed_tag)

        if nodes:
            for node in nodes[:5]:
                artist = node.get('artist', '')
                title = node.get('album', node.get('title', ''))
                year = node.get('release_year') or node.get('year') or ''
                samples.append(f"{artist} - {title} ({year})")
        else:
            # Fallback to scanning if mapping not available for the processed tag
            tag_norm = processed_tag
            for node in self.album_nodes_original:
                raw_tags_str = node.get('raw_tags') or node.get('genre', '')
                if not raw_tags_str:
                    continue
                tags = [t.strip() for t in re.split(r'[;,]', raw_tags_str) if t.strip()]
                if self.tag_normalizer.is_active():
                    proc_tags = [self._get_normalized_tag_for_processing(t) for t in tags]
                else:
                    proc_tags = tags
                if tag_norm in proc_tags:
                    artist = node.get('artist', '')
                    title = node.get('album', node.get('title', ''))
                    year = node.get('release_year') or node.get('year') or ''
                    samples.append(f"{artist} - {title} ({year})")
                    if len(samples) >= 5:
                        break

        self.atomic_widget.show_preview_samples(tag_name, samples)
            
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
        """Shows the tag context menu with multi-select support and filter panel integration."""
        item = self.tags_table.itemAt(position)
        if not item:
            return

        row = item.row()
        tag_item = self.tags_table.item(row, 0)
        if not tag_item:
            return
            
        tag_name = tag_item.text()
        
        # Get selected tags for multi-select operations
        selected_rows = set(item.row() for item in self.tags_table.selectedItems())
        selected_tags = []
        for selected_row in selected_rows:
            item = self.tags_table.item(selected_row, 0)
            if item:
                selected_tags.append(item.text())
        
        menu = QMenu()
        
        # Single tag actions
        if len(selected_tags) == 1:
            include_action = menu.addAction(f"Include '{tag_name}'")
            exclude_action = menu.addAction(f"Exclude '{tag_name}'")
            neutral_action = menu.addAction(f"Clear filter for '{tag_name}'")
            menu.addSeparator()
            
            # Enhanced filter panel actions
            if hasattr(self, 'filter_panel') and self.filter_panel is not None:
                filter_menu = menu.addMenu("Add to Filter Group")
                
                # List existing groups
                for group_widget in self.filter_panel.group_widgets.values():
                    group = group_widget.get_group()
                    group_action = filter_menu.addAction(f"Group {group.group_id}: {group.name}")
                    group_action.setData(group.group_id)
                
                # Add "New Group" option
                filter_menu.addSeparator()
                new_group_action = filter_menu.addAction("➕ Add to New Group")
                new_group_action.setData("__new__")
                
                menu.addSeparator()
                exclude_action_panel = menu.addAction(f"➖ Add to Exclusions")
                menu.addSeparator()
            
            preview_action = menu.addAction(f"Preview albums with '{tag_name}'")
        else:
            # Multi-select actions
            include_action = menu.addAction(f"Include {len(selected_tags)} selected tags")
            exclude_action = menu.addAction(f"Exclude {len(selected_tags)} selected tags")
            neutral_action = menu.addAction(f"Clear filters for {len(selected_tags)} selected tags")
            preview_action = None
            
            # Multi-select filter panel actions
            if hasattr(self, 'filter_panel') and self.filter_panel is not None:
                menu.addSeparator()
                filter_menu = menu.addMenu(f"Add {len(selected_tags)} tags to Group")
                
                for group_widget in self.filter_panel.group_widgets.values():
                    group = group_widget.get_group()
                    group_action = filter_menu.addAction(f"Group {group.group_id}: {group.name}")
                    group_action.setData(group.group_id)
                
                filter_menu.addSeparator()
                new_group_action = filter_menu.addAction("➕ Add to New Group")
                new_group_action.setData("__new__")
                
                menu.addSeparator()
                exclude_action_panel = menu.addAction(f"➖ Add {len(selected_tags)} tags to Exclusions")

        action = menu.exec(self.tags_table.mapToGlobal(position))

        # Handle filter panel actions
        if hasattr(self, 'filter_panel') and self.filter_panel is not None:
            # Check if it's a group action
            if action and hasattr(action, 'data') and callable(action.data):
                group_id = action.data()
                if group_id:
                    if group_id == "__new__":
                        # Create new group and add tags
                        for tag in selected_tags:
                            self.filter_panel.add_tag_to_group(tag, None)  # None creates new group
                        return
                    else:
                        # Add to existing group
                        for tag in selected_tags:
                            self.filter_panel.add_tag_to_group(tag, group_id)
                        return
            
            # Check if it's exclusion action
            if len(selected_tags) == 1 and 'exclude_action_panel' in locals() and action == exclude_action_panel:
                self.filter_panel.add_exclusion(tag_name)
                return
            elif len(selected_tags) > 1 and 'exclude_action_panel' in locals() and action == exclude_action_panel:
                for tag in selected_tags:
                    self.filter_panel.add_exclusion(tag)
                return

        # Handle legacy filter actions
        if action == include_action:
            for tag in selected_tags:
                self.tag_filters[tag] = self.FILTER_INCLUDE
        elif action == exclude_action:
            for tag in selected_tags:
                self.tag_filters[tag] = self.FILTER_EXCLUDE
        elif action == neutral_action:
            for tag in selected_tags:
                if tag in self.tag_filters:
                    del self.tag_filters[tag]
        elif preview_action and action == preview_action:
            self._show_tag_preview(tag_name)
            return  # Don't apply filters for preview
        else:
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
        # Start the background worker to process raw tag counts
        self._start_tag_processing_worker()

    def _save_splitter_state(self):
        """Save the current splitter state to settings."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AlbumExplore", "TagExplorerView")
            settings.setValue("splitter_sizes", self.splitter.sizes())
            graphics_logger.debug(f"Saved splitter state: {self.splitter.sizes()}")
        except Exception as e:
            graphics_logger.debug(f"Could not save splitter state: {e}")

    def _start_tag_processing_worker(self):
        """Start a QThread worker to build raw_tag_counts and tag_to_album_nodes."""
        # If a worker is already running, ignore
        if self._tag_worker_thread is not None:
            return

        try:
            # Create worker and thread
            self._tag_worker = TagProcessingWorker(self.album_nodes_original)
            thread = QThread(self)
            self._tag_worker.moveToThread(thread)
            thread.started.connect(self._tag_worker.run)
            self._tag_worker.progress.connect(self._on_tag_worker_progress)
            self._tag_worker.finished.connect(self._on_tag_worker_finished)
            # When the thread finishes, ensure cleanup
            self._tag_worker.finished.connect(thread.quit)
            self._tag_worker.finished.connect(self._tag_worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self._tag_worker_thread = thread
            thread.start()

            # Show a QProgressDialog with cancel support
            try:
                from PyQt6.QtWidgets import QProgressDialog
                self._progress_dialog = QProgressDialog("Processing tags...", "Cancel", 0, max(1, len(self.album_nodes_original)), self)
                self._progress_dialog.setWindowTitle("Processing Tags")
                self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                self._progress_dialog.canceled.connect(lambda: getattr(self._tag_worker, 'cancel', lambda: None)())
                self._progress_dialog.show()
            except Exception:
                # Fallback to inline progress bar when dialog unavailable
                if hasattr(self, 'progress_bar'):
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setRange(0, max(1, len(self.album_nodes_original)))
                    self.progress_bar.setValue(0)

        except Exception as e:
            graphics_logger.error(f"Failed to start tag processing worker: {e}")

    def _on_tag_worker_progress(self, processed_count: int):
        """Update UI progress from worker."""
        try:
            # Update either the dialog or the inline progress bar
            if hasattr(self, '_progress_dialog') and self._progress_dialog is not None:
                try:
                    self._progress_dialog.setValue(processed_count)
                except Exception:
                    pass
            elif hasattr(self, 'progress_bar'):
                self.progress_bar.setValue(processed_count)
            percent = int((processed_count / max(1, len(self.album_nodes_original))) * 100)
            self.tag_count_label.setText(f"Processing tags: {processed_count} ({percent}%)")
        except Exception:
            pass

    def _on_tag_worker_finished(self, raw_counts_dict, tag_to_nodes_dict):
        """Handle completion of background raw tag processing."""
        try:
            # Convert back to Counters and dict-of-lists
            self.raw_tag_counts = Counter(raw_counts_dict)
            # Rebuild raw tag -> nodes mapping from worker output
            self.raw_tag_to_album_nodes = defaultdict(list)
            for k, v in tag_to_nodes_dict.items():
                # v may be a list of node dicts already
                self.raw_tag_to_album_nodes[k].extend(v)

            # Reset processed mapping before finalization
            self.tag_to_album_nodes = defaultdict(list)

            # Hide progress UI (dialog or inline bar)
            try:
                if hasattr(self, '_progress_dialog') and self._progress_dialog is not None:
                    self._progress_dialog.close()
                    self._progress_dialog = None
                elif hasattr(self, 'progress_bar'):
                    self.progress_bar.setVisible(False)
            except Exception:
                pass

            # Clear stored thread reference
            if self._tag_worker_thread is not None:
                try:
                    self._tag_worker_thread.quit()
                except Exception:
                    pass
                self._tag_worker_thread = None
                self._tag_worker = None

            # Finalize processing on main thread (normalization + UI update)
            # We already have fresh raw counts, so avoid calling _reprocess_base_tag_data()
            # which would detect a large dataset and spin up another background worker.
            self._finalize_tag_processing_from_raw()

        except Exception as e:
            graphics_logger.error(f"Error handling tag worker finished: {e}", exc_info=True)
    
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
            
            # Esc to clear search
            clear_search_shortcut = QShortcut(QKeySequence("Esc"), self)
            clear_search_shortcut.activated.connect(self._clear_tag_search)
            
            # F1 to show help
            help_shortcut = QShortcut(QKeySequence("F1"), self)
            help_shortcut.activated.connect(self.show_layout_help)
            
            # Ctrl+I to include selected tags
            include_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
            include_shortcut.activated.connect(self._include_selected_tags)
            
            # Ctrl+E to exclude selected tags
            exclude_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
            exclude_shortcut.activated.connect(self._exclude_selected_tags)
            
            graphics_logger.debug("Keyboard shortcuts setup complete")
            
        except Exception as e:
            graphics_logger.debug(f"Could not setup keyboard shortcuts: {e}")
    
    def _toggle_view_mode(self):
        """Toggle between table and cloud view modes."""
        current_index = self.view_mode_combo.currentIndex()
        new_index = 1 - current_index  # Toggle between 0 and 1
        self.view_mode_combo.setCurrentIndex(new_index)
    
    def _toggle_filter_panel(self, checked: bool):
        """Toggle visibility of the advanced filter panel."""
        self.filter_panel_container.setVisible(checked)
        
        if checked:
            # Update available tags when showing panel
            available_tags = list(self.tag_counts.keys()) if self.tag_counts else []
            self.filter_panel.update_available_tags(available_tags)
            
            # Sync existing filters to panel if using legacy mode
            self._sync_legacy_to_panel()
            
            # Restore saved height if available
            self._restore_filter_panel_height()
            
            graphics_logger.info("Advanced filter panel shown")
        else:
            # Save current height before hiding
            self._save_filter_panel_height()
            graphics_logger.info("Advanced filter panel hidden")
    
    def _on_filter_panel_changed(self):
        """Handle changes from the advanced filter panel."""
        if not self.filter_panel_container.isVisible():
            return
        
        # Just reapply filters - both systems work together now
        self.apply_tag_filters()
        
        graphics_logger.debug("Filter panel changed, filters reapplied")
    
    def _sync_legacy_to_panel(self):
        """Sync legacy tag_filters dict to the filter panel (one-time when opening)."""
        if not self.tag_filters:
            return
        
        # Only sync if panel is empty - don't overwrite existing groups
        filter_state = self.filter_panel.get_filter_state()
        if not filter_state.is_empty():
            graphics_logger.debug("Filter panel already has groups, skipping legacy sync")
            return
        
        # Add include filters to first group
        include_tags = [tag for tag, state in self.tag_filters.items() if state == self.FILTER_INCLUDE]
        if include_tags:
            for tag in include_tags:
                self.filter_panel.add_tag_to_group(tag, None)  # None creates/uses first group
        
        # Add exclude filters to exclusions
        exclude_tags = [tag for tag, state in self.tag_filters.items() if state == self.FILTER_EXCLUDE]
        for tag in exclude_tags:
            self.filter_panel.add_exclusion(tag)
        
        graphics_logger.debug(f"Synced {len(include_tags)} includes and {len(exclude_tags)} excludes to filter panel")
    

    
    def _start_resize_filter_panel(self, event):
        """Start resizing the filter panel."""
        self._filter_panel_resizing = True
        self._filter_panel_resize_start_y = event.globalPosition().y()
        self._filter_panel_start_height = self.filter_panel_container.height()
        event.accept()
    
    def _resize_filter_panel(self, event):
        """Resize the filter panel while dragging."""
        if not self._filter_panel_resizing:
            return
        
        # Calculate new height
        delta_y = event.globalPosition().y() - self._filter_panel_resize_start_y
        new_height = max(120, min(400, self._filter_panel_start_height + int(delta_y)))
        
        # Apply new height
        self.filter_panel_container.setFixedHeight(new_height)
        event.accept()
    
    def _end_resize_filter_panel(self, event):
        """End resizing the filter panel."""
        if self._filter_panel_resizing:
            self._filter_panel_resizing = False
            # Save the new height but keep it fixed
            current_height = self.filter_panel_container.height()
            self._save_filter_panel_height()
            # Keep the height fixed at the current size
            self.filter_panel_container.setFixedHeight(current_height)
            event.accept()
    
    def _save_filter_panel_height(self):
        """Save the current filter panel height to settings."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AlbumExplore", "TagExplorerView")
            settings.setValue("filter_panel_height", self.filter_panel_container.height())
            graphics_logger.debug(f"Saved filter panel height: {self.filter_panel_container.height()}")
        except Exception as e:
            graphics_logger.debug(f"Could not save filter panel height: {e}")
    
    def _restore_filter_panel_height(self):
        """Restore the saved filter panel height from settings."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AlbumExplore", "TagExplorerView")
            saved_height = settings.value("filter_panel_height")
            if saved_height:
                height = int(saved_height)
                # Validate height is within bounds
                height = max(120, min(400, height))
                self.filter_panel_container.setFixedHeight(height)
                graphics_logger.debug(f"Restored filter panel height: {height}")
            else:
                # Set default height on first use - compact
                self.filter_panel_container.setFixedHeight(180)
        except Exception as e:
            graphics_logger.debug(f"Could not restore filter panel height: {e}")
            self.filter_panel_container.setFixedHeight(180)
    
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
            <li>Click column headers to sort tables</li>
            <li>Hover over items to see full content in tooltips</li>
            </ul>
            
            <p><b>Keyboard Shortcuts:</b></p>
            <ul>
            <li><b>Ctrl+R</b> - Reset layout to default proportions</li>
            <li><b>Ctrl+F</b> - Focus search box</li>
            <li><b>Esc</b> - Clear search</li>
            <li><b>Ctrl+T</b> - Toggle between table and cloud view</li>
            <li><b>Ctrl+Shift+C</b> - Clear all tag filters</li>
            <li><b>Ctrl+I</b> - Include selected tags</li>
            <li><b>Ctrl+E</b> - Exclude selected tags</li>
            <li><b>F1</b> - Show this help</li>
            </ul>
            
            <p><b>Tag Filtering:</b></p>
            <ul>
            <li>Click on a tag name to cycle filter states (Neutral → Include → Exclude)</li>
            <li><b>Double-click</b> a tag to preview its albums without filtering</li>
            <li><b>Ctrl+Click</b> to select multiple tags and filter them together</li>
            <li>Right-click on tags for filtering options</li>
            <li>Use <b>+ button</b> to include selected tags, <b>- button</b> to exclude</li>
            <li>Use <b>⇄ button</b> to invert all filters (swap Include/Exclude)</li>
            <li>Search box filters the tag list in real-time</li>
            <li>Numbers are formatted with commas for readability</li>
            <li><span style='color: #4CAF50;'>Green</span> = Include filter, <span style='color: #F44336;'>Red</span> = Exclude filter</li>
            <li>Filtered tags are highlighted with bold text and background color</li>
            </ul>
            
            <p><b>Performance:</b></p>
            <ul>
            <li>Large datasets are processed in the background</li>
            <li>Progress bar shows processing status</li>
            <li>Tables support sorting by clicking column headers</li>
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
        background_hex = "#121212"
        surface_hex = "#181818"
        raised_hex = "#202124"
        border_hex = "#2a2d32"
        hover_hex = "#2c3239"
        text_primary_hex = "#f1f3f4"
        text_muted_hex = "#9aa0a6"
        accent_hex = "#64b5f6"
        accent_hover_hex = "#81c9ff"
        accent_pressed_hex = "#4aa4e3"
        success_hex = "#7bd88f"
        danger_hex = "#f77676"
        control_base_hex = "#2c323a"
        control_hover_hex = "#37414b"
        control_pressed_hex = "#425163"

        background_color = QColor(background_hex)
        surface_color = QColor(surface_hex)
        raised_color = QColor(raised_hex)
        text_color = QColor(text_primary_hex)
        accent_color = QColor(accent_hex)

        font = self.font()
        font.setPointSize(10)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, background_color)
        palette.setColor(QPalette.ColorRole.Base, surface_color)
        palette.setColor(QPalette.ColorRole.AlternateBase, raised_color)
        palette.setColor(QPalette.ColorRole.WindowText, text_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        palette.setColor(QPalette.ColorRole.Button, QColor(control_base_hex))
        palette.setColor(QPalette.ColorRole.ButtonText, text_color)
        palette.setColor(QPalette.ColorRole.Highlight, accent_color)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(background_hex))
        palette.setColor(QPalette.ColorRole.ToolTipBase, raised_color)
        palette.setColor(QPalette.ColorRole.ToolTipText, text_color)

        for widget in (
            self,
            self.tag_panel,
            self.album_panel,
            self.filter_header,
            self.tags_table,
            self.album_table,
            self.status_bar,
            self.progress_bar,
        ):
            widget.setPalette(palette)
            widget.setFont(font)
            widget.setAutoFillBackground(True)

        stylesheet = f"""
            QWidget {{
                background-color: {background_hex};
                color: {text_primary_hex};
                font-size: 10pt;
            }}
            QWidget#filterHeader {{
                background-color: {surface_hex};
                border-bottom: 1px solid {border_hex};
                padding: 6px 10px;
            }}
            QWidget#tagPanel, QWidget#albumPanel {{
                background-color: {surface_hex};
            }}
            QLabel#statusBarLabel {{
                background-color: {raised_hex};
                color: {text_primary_hex};
                padding: 6px 12px;
                border-top: 1px solid {border_hex};
                font-size: 10pt;
                font-weight: 500;
            }}
            QLabel {{
                color: {text_primary_hex};
            }}
            QLabel#tagCountLabel {{
                color: {accent_hex};
                font-weight: 600;
            }}
            QLineEdit {{
                background-color: {control_base_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                padding: 4px 8px;
                color: {text_primary_hex};
            }}
            QLineEdit:focus {{
                border-color: {accent_hex};
                background-color: {raised_hex};
            }}
            QPushButton {{
                background-color: {control_base_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                padding: 4px 10px;
                color: {text_primary_hex};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {control_hover_hex};
                border-color: {accent_hex};
            }}
            QPushButton:pressed {{
                background-color: {control_pressed_hex};
                border-color: {accent_pressed_hex};
            }}
            QPushButton:disabled {{
                color: {text_muted_hex};
                border-color: {border_hex};
            }}
            QWidget#filterHeader QPushButton {{
                min-height: 28px;
            }}
            QWidget#filterHeader QPushButton:pressed {{
                color: {background_hex};
            }}
            QPushButton#includeButton {{
                color: {success_hex};
                border-color: #2f6f4a;
                font-size: 16pt;
                font-weight: bold;
            }}
            QPushButton#includeButton:hover {{
                background-color: #1e3b2b;
                border-color: {success_hex};
            }}
            QPushButton#excludeButton {{
                color: {danger_hex};
                border-color: #703646;
                font-size: 16pt;
                font-weight: bold;
            }}
            QPushButton#excludeButton:hover {{
                background-color: #3b1e24;
                border-color: {danger_hex};
            }}
            QPushButton#clearFiltersButton {{
                color: {accent_hex};
                border-color: {accent_hex};
            }}
            QPushButton#clearFiltersButton:hover {{
                background-color: {control_hover_hex};
            }}
            QPushButton#invertButton, QPushButton#resetLayoutButton, QPushButton#helpButton {{
                color: {accent_hex};
            }}
            QPushButton#invertButton:hover, QPushButton#resetLayoutButton:hover, QPushButton#helpButton:hover {{
                color: {accent_hover_hex};
            }}
            QPushButton#exportTagsButton, QPushButton#exportAlbumsButton, QPushButton#manageSinglesButton {{
                border-color: {border_hex};
            }}
            QPushButton#exportTagsButton:hover, QPushButton#exportAlbumsButton:hover, QPushButton#manageSinglesButton:hover {{
                border-color: {accent_hex};
            }}
            QComboBox {{
                background-color: {control_base_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                padding: 4px 24px 4px 8px;
                color: {text_primary_hex};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {raised_hex};
                selection-background-color: {accent_hex};
                selection-color: {background_hex};
            }}
            QCheckBox {{
                spacing: 6px;
                color: {text_primary_hex};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 1px solid {border_hex};
                background-color: {surface_hex};
            }}
            QCheckBox::indicator:checked {{
                border: 1px solid {accent_hex};
                background-color: {accent_hex};
            }}
            QTableWidget {{
                gridline-color: {border_hex};
                background-color: {surface_hex};
                alternate-background-color: {raised_hex};
                selection-background-color: {accent_hex};
                selection-color: {background_hex};
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QTableWidget::item:hover {{
                background-color: {hover_hex};
            }}
            QHeaderView::section {{
                background-color: {raised_hex};
                color: {text_primary_hex};
                border: none;
                border-right: 1px solid {border_hex};
                padding: 6px 8px;
            }}
            QHeaderView::section:horizontal {{
                border-bottom: 1px solid {border_hex};
            }}
            QHeaderView::section:selected {{
                background-color: {accent_hex};
                color: {background_hex};
            }}
            QScrollBar:vertical {{
                background: {surface_hex};
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {raised_hex};
                border-radius: 6px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent_hex};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QSplitter::handle {{
                background-color: {raised_hex};
                width: 5px;
            }}
            QSplitter::handle:hover {{
                background-color: {accent_hex};
            }}
            QProgressBar {{
                background-color: {surface_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                text-align: center;
                color: {text_primary_hex};
            }}
            QProgressBar::chunk {{
                background-color: {accent_hex};
            }}
        """
        self.setStyleSheet(stylesheet)