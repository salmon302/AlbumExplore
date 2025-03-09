from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollBar,
                           QWidget, QPushButton, QLabel, QMenu, QSplitter,
                           QComboBox, QRadioButton, QButtonGroup, QToolButton, 
                           QStackedWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QTime
from PyQt6.QtGui import QColor, QPalette, QIcon, QAction, QPainter
from typing import Dict, Any, Set, List, Optional
from collections import Counter, defaultdict
import json

from .base_view import BaseView
from ..state import ViewType, ViewState
from ...tags.normalizer import TagNormalizer
from ...tags.analysis.single_instance_handler import SingleInstanceHandler
from ...tags.analysis.tag_analyzer import TagAnalyzer
from ...tags.analysis.tag_similarity import TagSimilarity
from .tag_cloud_widget import TagCloudWidget

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
        # Sort numerically if possible, otherwise as strings
        my_data = self.data(Qt.ItemDataRole.UserRole)
        other_data = other.data(Qt.ItemDataRole.UserRole)
        
        if my_data is not None and other_data is not None:
            return my_data < other_data
        
        return super().__lt__(other)


class DoubleBufferedViewport(QWidget):
    """Custom viewport for double buffering."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        super().paintEvent(event)


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
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)  # Avoid unnecessary background redraws
        self.setUpdatesEnabled(False)  # Disable updates during initialization
        self.view_state = ViewState(ViewType.TAG_EXPLORER)  # Fixed: Use TAG_EXPLORER instead of TABLE
        self.tag_normalizer = TagNormalizer()
        
        # For storing data
        self.tag_counts = Counter()        # All tags and their counts
        self.raw_tag_counts = Counter()    # Raw tag counts before normalization
        self.matching_counts = Counter()   # Tags in current filtered selection
        self.tag_filters = {}              # Current filter state for each tag
        self.filtered_albums = []          # Albums matching current filters
        self.normalized_mapping = {}       # Mapping from original to normalized tags
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
        
        # Add view mode selector
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Table View", "Cloud View"])
        self.view_mode_combo.currentIndexChanged.connect(self._change_tag_view_mode)
        filter_header_layout.addWidget(self.view_mode_combo)
        
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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._handle_tag_sort)
        
        self.tags_table.setShowGrid(True)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSortingEnabled(True)
        self.tags_sort_column = 1  # Default sort by count
        self.tags_sort_order = Qt.SortOrder.DescendingOrder
        self.tags_table.cellDoubleClicked.connect(self._cycle_tag_filter_state)
        
        # Create tag cloud view
        self.tag_cloud = TagCloudWidget()
        self.tag_cloud.tagClicked.connect(self._handle_tag_cloud_click)
        
        # Add both views to stack
        self.tag_views_stack.addWidget(self.tags_table)
        self.tag_views_stack.addWidget(self.tag_cloud)
        
        tag_panel_layout.addWidget(self.tag_views_stack)
        
        # Create album panel widget
        self.album_panel = QWidget()
        self.album_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        album_panel_layout = QVBoxLayout(self.album_panel)
        
        # Add album panel header
        self.album_header = QWidget()
        album_header_layout = QHBoxLayout(self.album_header)
        album_header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.album_count_label = QLabel("Albums: 0")
        album_header_layout.addWidget(self.album_count_label)
        
        album_header_layout.addStretch()
        
        album_panel_layout.addWidget(self.album_header)
        
        # Create album table
        self.album_table = QTableWidget()
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        
        # Configure album table headers
        album_header = self.album_table.horizontalHeader()
        album_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) 
        album_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        album_header.setSectionsClickable(True)
        album_header.setHighlightSections(True)
        album_header.setSortIndicatorShown(True)
        album_header.sectionClicked.connect(self._handle_album_sort)
        
        self.album_table.setShowGrid(True)
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.album_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.album_table.verticalHeader().setVisible(False)
        self.album_table.setSortingEnabled(True)
        
        # Connect signals
        self.album_table.itemSelectionChanged.connect(self._handle_album_selection_change)
        self.tags_table.cellDoubleClicked.connect(self._cycle_tag_filter_state)
        
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
        
        # Configure tables for optimized painting
        self.tags_table.setViewport(DoubleBufferedViewport())
        self.album_table.setViewport(DoubleBufferedViewport())
        
        # Set unified styling
        self._apply_unified_styling()
        
        self.setUpdatesEnabled(True)  # Re-enable updates
        self.show()
        
    def _apply_unified_styling(self):
        """Apply consistent styling to all components."""
        style = """
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                color: black;
            }
            QTableWidget::item {
                color: black;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: black;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: bold;
            }
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f5f5f5;
                color: black;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #dcdcdc;
            }
            QToolButton {
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px;
                color: black;
            }
            QToolButton:hover {
                background-color: #e8e8e8;
                border: 1px solid #ccc;
            }
            QLabel {
                color: black;
            }
            QSplitter {
                background-color: white;
            }
            QWidget {
                background-color: white;
                color: black;
            }
        """
        self.setStyleSheet(style)
    
    def update_data(self, nodes, edges):
        """Update view with new data."""
        super().update_data(nodes, edges)
        
        # Process the data
        self.process_tag_data(nodes)
        
        # Apply any existing filters
        self.apply_tag_filters()
        
    def process_tag_data(self, nodes):
        """Process tag data from the nodes."""
        self.raw_tag_counts = Counter()
        self.normalized_mapping = {}  # Map from original to normalized tags
        self.tag_counts = Counter()
        
        # First pass: collect raw tag counts and create normalization mapping
        for node in nodes:
            if 'tags' in node.data:
                for tag in node.data['tags']:
                    self.raw_tag_counts[tag] += 1
                    # Apply normalization to consolidate tags
                    normalized_tag = self.tag_normalizer.normalize(tag)
                    self.normalized_mapping[tag] = normalized_tag
                    self.tag_counts[normalized_tag] += 1
        
        # Update node data with normalized tags (in-memory only, doesn't affect database)
        for node in nodes:
            if 'tags' in node.data:
                # Create a new list with normalized tags
                normalized_tags = [self.normalized_mapping.get(tag, tag) for tag in node.data['tags']]
                # Remove duplicates that might appear after normalization
                node.data['normalized_tags'] = list(dict.fromkeys(normalized_tags))
        
        # Identify single-instance tags
        self.single_instance_tags = {tag for tag, count in self.raw_tag_counts.items() if count == 1}
        
        # Initialize tag analysis components if we have enough data
        if len(nodes) > 0:
            # Create a pandas DataFrame from the nodes for the tag analyzer
            import pandas as pd
            data = []
            for node in nodes:
                if 'tags' in node.data:
                    data.append({
                        'id': node.id,
                        'artist': node.data.get('artist', ''),
                        'title': node.data.get('title', ''),
                        'year': node.data.get('year', 0),
                        'tags': node.data.get('tags', [])
                    })
            
            if data:
                df = pd.DataFrame(data)
                self.tag_analyzer = TagAnalyzer(df)
                self.tag_similarity = TagSimilarity(self.tag_analyzer)
                self.single_instance_handler = SingleInstanceHandler(
                    self.tag_analyzer,
                    self.tag_normalizer,
                    self.tag_similarity
                )
                
                # Initialize relationships and identify single-instance tags
                self.tag_analyzer.calculate_relationships()
                self.single_instance_handler.identify_single_instance_tags()
        
        # Refresh the tag table with consolidated counts
        self.refresh_tag_table()
        
        # Update album table with all albums initially
        self.filtered_albums = self.nodes
        self.refresh_album_table()
    
    def refresh_tag_table(self):
        """Refresh the tag table with current data."""
        self.tags_table.setSortingEnabled(False)
        self.tags_table.setRowCount(len(self.tag_counts))
        
        for i, (tag, count) in enumerate(sorted(self.tag_counts.items())):
            # Tag column
            tag_item = SortableTableWidgetItem(tag)
            tag_item.setData(Qt.ItemDataRole.UserRole, tag.lower())  # For sorting
            tag_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.tags_table.setItem(i, 0, tag_item)
            
            # Count column
            count_item = SortableTableWidgetItem(str(count))
            count_item.setData(Qt.ItemDataRole.UserRole, count)  # For numeric sorting
            count_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.tags_table.setItem(i, 1, count_item)
            
            # Matching count column (initially same as count)
            matching_item = SortableTableWidgetItem(str(self.matching_counts.get(tag, count)))
            matching_item.setData(Qt.ItemDataRole.UserRole, self.matching_counts.get(tag, count))
            matching_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.tags_table.setItem(i, 2, matching_item)
            
            # Filter state column
            filter_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL)
            filter_text = ""
            if filter_state == self.FILTER_INCLUDE:
                filter_text = "✓"
            elif filter_state == self.FILTER_EXCLUDE:
                filter_text = "✕"
            
            filter_item = QTableWidgetItem(filter_text)
            filter_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            filter_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            
            # Set background color based on filter state
            if filter_state == self.FILTER_INCLUDE:
                filter_item.setBackground(QColor(200, 255, 200))  # Light green
            elif filter_state == self.FILTER_EXCLUDE:
                filter_item.setBackground(QColor(255, 200, 200))  # Light red
            
            self.tags_table.setItem(i, 3, filter_item)
        
        self.tags_table.setSortingEnabled(True)
        
        # Apply stored sort settings
        if self.tags_sort_column is not None:
            self.tags_table.sortItems(self.tags_sort_column, self.tags_sort_order)
            
        # Update tag count display
        self.tag_count_label.setText(f"Tags: {len(self.tag_counts)}")
        
        # Update tag cloud
        self.tag_cloud.update_tags(self.tag_counts)
        self.tag_cloud.update_filter_states(self.tag_filters)
    
    def refresh_album_table(self):
        """Refresh the album table with filtered data."""
        self.album_table.setUpdatesEnabled(False)
        self.album_table.setSortingEnabled(False)
        self.album_table.clearContents()
        self.album_table.setRowCount(len(self.filtered_albums))
        
        for i, album in enumerate(self.filtered_albums):
            data = album.data
            
            # Artist
            artist_item = SortableTableWidgetItem(data.get('artist', ''))
            artist_item.setData(Qt.ItemDataRole.UserRole, album.id)
            artist_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.album_table.setItem(i, 0, artist_item)
            
            # Album title
            title_item = SortableTableWidgetItem(data.get('title', ''))
            title_item.setData(Qt.ItemDataRole.UserRole, album.id)
            title_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.album_table.setItem(i, 1, title_item)
            
            # Year
            year_str = str(data.get('year', ''))
            year_item = SortableTableWidgetItem(year_str)
            year_item.setData(Qt.ItemDataRole.UserRole, data.get('year', 0))
            year_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.album_table.setItem(i, 2, year_item)
            
            # Tags - show original tags, not normalized ones
            tags_list = data.get('tags', [])
            tags_str = ', '.join(tags_list)
            tags_item = SortableTableWidgetItem(tags_str)
            tags_item.setData(Qt.ItemDataRole.UserRole, album.id)
            tags_item.setForeground(QColor(0, 0, 0))  # Explicitly set black text
            self.album_table.setItem(i, 3, tags_item)
        
        self.album_table.setSortingEnabled(True)
        
        # Update album count display
        self.album_count_label.setText(f"Albums: {len(self.filtered_albums)}")
        
        self.album_table.setUpdatesEnabled(True)
        self.album_table.viewport().update()
    
    def _cycle_tag_filter_state(self, row, column):
        """Cycle through filter states on double-click."""
        tag_item = self.tags_table.item(row, 0)
        if not tag_item:
            return
            
        tag = tag_item.text()
        current_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL)
        
        # Cycle through states: NEUTRAL -> INCLUDE -> EXCLUDE -> NEUTRAL
        if current_state == self.FILTER_NEUTRAL:
            self.tag_filters[tag] = self.FILTER_INCLUDE
        elif current_state == self.FILTER_INCLUDE:
            self.tag_filters[tag] = self.FILTER_EXCLUDE
        else:
            self.tag_filters[tag] = self.FILTER_NEUTRAL
            
        # Apply filters
        self.apply_tag_filters()
    
    def apply_tag_filters(self):
        """Apply tag filters to the album list."""
        # Start timer to measure performance
        start_time = QTime.currentTime()
        
        # If no filters are active, show all albums
        active_filters = {tag: state for tag, state in self.tag_filters.items() 
                         if state != self.FILTER_NEUTRAL}
        
        if not active_filters:
            self.filtered_albums = self.nodes
            self.matching_counts = self.tag_counts.copy()
            self.refresh_album_table()
            self.refresh_tag_table()
            return
        
        # Separate include and exclude filters for more efficient processing
        include_tags = {tag for tag, state in active_filters.items() if state == self.FILTER_INCLUDE}
        exclude_tags = {tag for tag, state in active_filters.items() if state == self.FILTER_EXCLUDE}
        
        # Pre-filter albums using set operations for better performance
        candidate_albums = []
        
        # First apply include filters (must have all included tags)
        if include_tags:
            for node in self.nodes:
                # Use faster set operations for filtering
                if include_tags.issubset(set(node.data.get('normalized_tags', []))):
                    candidate_albums.append(node)
        else:
            candidate_albums = self.nodes.copy()
        
        # Then apply exclude filters (must not have any excluded tags)
        if exclude_tags:
            self.filtered_albums = []
            for node in candidate_albums:
                node_tags = set(node.data.get('normalized_tags', []))
                if not exclude_tags.intersection(node_tags):  # No intersection with exclude tags
                    self.filtered_albums.append(node)
        else:
            self.filtered_albums = candidate_albums
        
        # Calculate matching counts using Counter for better performance
        self.matching_counts = Counter()
        tag_collection = []
        for album in self.filtered_albums:
            tag_collection.extend(album.data.get('normalized_tags', []))
        self.matching_counts.update(tag_collection)
        
        # Update both tables
        self.refresh_album_table()
        self.refresh_tag_table()
        
        # If any albums were selected, update selection to match filtered set
        if self.selected_ids:
            new_selection = {node_id for node_id in self.selected_ids 
                           if any(node.id == node_id for node in self.filtered_albums)}
            
            if new_selection != self.selected_ids:
                self.update_selection(new_selection)
        
        # Log performance metrics
        elapsed_ms = start_time.msecsTo(QTime.currentTime())
        if elapsed_ms > 100:  # Only log if filtering took significant time
            from albumexplore.gui.gui_logging import performance_logger
            performance_logger.debug(f"Tag filtering took {elapsed_ms}ms for {len(self.nodes)} albums with {len(active_filters)} filters")
    
    def _export_tag_data(self):
        """Export tag data to console for analysis."""
        print("\n===== TAG EXPLORER DATA ANALYSIS =====")
        
        # Basic stats
        print(f"Total unique raw tags: {len(self.raw_tag_counts)}")
        print(f"Total unique normalized tags: {len(self.tag_counts)}")
        print(f"Consolidation ratio: {len(self.tag_counts)/len(self.raw_tag_counts):.2f}")
        
        # Calculate variants per normalized tag
        variants_per_tag = defaultdict(list)
        for original, normalized in self.normalized_mapping.items():
            if original != normalized:  # Only track actual changes
                variants_per_tag[normalized].append(original)
        
        # Tags with the most variants
        print("\n--- TAGS WITH MOST VARIANTS ---")
        for normalized, variants in sorted(variants_per_tag.items(), 
                                          key=lambda x: len(x[1]), reverse=True)[:20]:
            print(f"{normalized} ({self.tag_counts[normalized]}): {len(variants)} variants")
            # Show up to 5 variants
            for variant in variants[:5]:
                print(f"  - {variant} ({self.raw_tag_counts[variant]})")
            if len(variants) > 5:
                print(f"  - ... and {len(variants)-5} more")
        
        # Most popular tags after normalization
        print("\n--- TOP 20 NORMALIZED TAGS ---")
        for tag, count in self.tag_counts.most_common(20):
            variants = variants_per_tag.get(tag, [])
            print(f"{tag}: {count} occurrences, {len(variants)} variants")
        
        # Tags that were never consolidated (single-instance tags)
        single_instance_tags = [tag for tag, count in self.raw_tag_counts.items()
                               if count == 1 and tag == self.normalized_mapping.get(tag, tag)]
        print(f"\n--- SINGLE-INSTANCE TAGS ({len(single_instance_tags)}) ---")
        print(f"Sample of 20: {', '.join(single_instance_tags[:20])}")
        
        # If we have the single instance handler, show suggestions
        if self.single_instance_handler:
            suggestions = self.single_instance_handler.get_consolidation_suggestions()
            if suggestions:
                print("\n--- SUGGESTED NORMALIZATIONS FOR SINGLE-INSTANCE TAGS ---")
                for tag, tag_suggestions in list(suggestions.items())[:20]:  # Show top 20
                    if tag_suggestions:
                        best_suggestion = tag_suggestions[0]  # First suggestion is highest confidence
                        print(f"{tag} -> {best_suggestion[0]} (confidence: {best_suggestion[1]:.2f}, reason: {best_suggestion[2]})")
                
                # Show stats on suggestions
                high_confidence = sum(1 for tag_suggestions in suggestions.values()
                                     if tag_suggestions and tag_suggestions[0][1] >= 0.8)
                medium_confidence = sum(1 for tag_suggestions in suggestions.values()
                                       if tag_suggestions and 0.5 <= tag_suggestions[0][1] < 0.8)
                low_confidence = sum(1 for tag_suggestions in suggestions.values()
                                    if tag_suggestions and tag_suggestions[0][1] < 0.5)
                
                print(f"\nSuggestion confidence levels:")
                print(f"  High confidence (>=0.8): {high_confidence}")
                print(f"  Medium confidence (0.5-0.8): {medium_confidence}")
                print(f"  Low confidence (<0.5): {low_confidence}")
                print(f"  No suggestions: {len(single_instance_tags) - len(suggestions)}")
        
        # Export full data for deeper analysis
        print("\n--- EXPORTING FULL DATA ---")
        analysis_data = {
            "raw_tag_counts": dict(self.raw_tag_counts),
            "normalized_tag_counts": dict(self.tag_counts),
            "normalization_mapping": self.normalized_mapping,
            "single_instance_tags": single_instance_tags
        }
        
        print("Data analysis complete. Check console output for results.")
        return analysis_data
    
    def clear_tag_filters(self):
        """Clear all tag filters."""
        self.tag_filters.clear()
        self.apply_tag_filters()
    
    def _handle_tag_sort(self, column_index):
        """Handle sorting of tag table."""
        self.tags_sort_column = column_index
        self.tags_sort_order = self.tags_table.horizontalHeader().sortIndicatorOrder()
    
    def _handle_album_sort(self, column_index):
        """Handle sorting of album table."""
        # Sort is handled automatically by QTableWidget
        pass
    
    def _handle_album_selection_change(self):
        """Handle album selection changes."""
        selected_ids = set()
        for item in self.album_table.selectedItems():
            node_id = item.data(Qt.ItemDataRole.UserRole)
            if node_id and isinstance(node_id, str):
                selected_ids.add(node_id)
        
        self._pending_selection = selected_ids
        if not self._selection_timer.isActive():
            self._selection_timer.start(50)  # Process selection every 50ms
    
    def _process_selection(self):
        """Process pending selection changes."""
        if self._pending_selection != self.selected_ids:
            self.update_selection(self._pending_selection)
            
    def _show_single_instance_dialog(self):
        """Show dialog for managing single-instance tags."""
        if not self.single_instance_handler:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Not Available",
                "Single-instance tag management is not available. Please load data first."
            )
            return
            
        dialog = SingleInstanceDialog(
            self,
            self.single_instance_handler,
            self.tag_normalizer
        )
        
        # Connect the changes_applied signal
        dialog.changes_applied.connect(self._handle_tag_changes)
        
        # Show the dialog
        dialog.exec()
        
    def _handle_tag_changes(self, changes):
        """Handle changes from the single-instance dialog."""
        if not changes:
            return
            
        # Reprocess tag data to apply changes
        self.process_tag_data(self.nodes)
        
        # Refresh the view
        self.refresh_tag_table()
        self.refresh_album_table()
    
    def _show_tag_context_menu(self, position):
        """Show context menu for tag table."""
        row = self.tags_table.rowAt(position.y())
        if row < 0:
            return
            
        tag_item = self.tags_table.item(row, 0)
        if not tag_item:
            return
            
        tag = tag_item.text()
        menu = QMenu(self)
        
        include_action = QAction("Include", self)
        include_action.triggered.connect(lambda: self._set_tag_filter(tag, self.FILTER_INCLUDE))
        menu.addAction(include_action)
        
        exclude_action = QAction("Exclude", self)
        exclude_action.triggered.connect(lambda: self._set_tag_filter(tag, self.FILTER_EXCLUDE))
        menu.addAction(exclude_action)
        
        neutral_action = QAction("Clear Filter", self)
        neutral_action.triggered.connect(lambda: self._set_tag_filter(tag, self.FILTER_NEUTRAL))
        menu.addAction(neutral_action)
        
        menu.addSeparator()
        
        select_all_action = QAction("Select All Albums With This Tag", self)
        select_all_action.triggered.connect(lambda: self._select_albums_by_tag(tag))
        menu.addAction(select_all_action)
        
        menu.exec(self.tags_table.mapToGlobal(position))
    
    def _set_tag_filter(self, tag, state):
        """Set filter state for a specific tag."""
        self.tag_filters[tag] = state
        self.apply_tag_filters()
    
    def _select_albums_by_tag(self, tag):
        """Select all albums that have the specified tag."""
        album_ids = set()
        for node in self.filtered_albums:
            # Use normalized tags for selection
            if 'normalized_tags' in node.data and tag in node.data['normalized_tags']:
                album_ids.add(node.id)
        
        self.update_selection(album_ids)
        
        # Also select the corresponding rows in the album table
        self.album_table.clearSelection()
        for row in range(self.album_table.rowCount()):
            for col in range(self.album_table.columnCount()):
                item = self.album_table.item(row, col)
                if item and item.data(Qt.ItemDataRole.UserRole) in album_ids:
                    item.setSelected(True)
                    break
    
    def _process_updates(self):
        """Process pending updates."""
        # This would handle batch updates if needed
        pass
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.splitter.resize(self.size())
    
    def paintEvent(self, event):
        """Handle paint events with throttling."""
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        if current_time - self._last_paint_time < self._paint_throttle and not self._needs_full_update:
            event.accept()
            return
            
        super().paintEvent(event)
        self._last_paint_time = current_time
        self._needs_full_update = False
    
    def _change_tag_view_mode(self, index):
        """Change the tag view mode."""
        self.tag_mode = index
        self.tag_views_stack.setCurrentIndex(index)
    
    def _handle_tag_cloud_click(self, tag):
        """Handle tag click in the tag cloud."""
        current_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL)
        
        # Cycle through states: NEUTRAL -> INCLUDE -> EXCLUDE -> NEUTRAL
        if current_state == self.FILTER_NEUTRAL:
            self.tag_filters[tag] = self.FILTER_INCLUDE
        elif current_state == self.FILTER_INCLUDE:
            self.tag_filters[tag] = self.FILTER_EXCLUDE
        else:
            self.tag_filters[tag] = self.FILTER_NEUTRAL
            
        # Update tag cloud filter states
        self.tag_cloud.update_filter_states(self.tag_filters)
        
        # Apply filters
        self.apply_tag_filters()
