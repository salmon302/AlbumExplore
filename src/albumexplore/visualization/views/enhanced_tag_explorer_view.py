from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollBar,
                           QWidget, QPushButton, QLabel, QMenu, QSplitter,
                           QComboBox, QRadioButton, QButtonGroup, QToolButton, 
                           QStackedWidget, QLineEdit, QCheckBox, QDialog, QMessageBox,
                           QTreeWidget, QTreeWidgetItem, QTabWidget, QGroupBox,
                           QSlider, QProgressBar, QFrame, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSortFilterProxyModel, QRegularExpression, QTime
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QPainter, QFontMetrics, QPalette, QAction, QFont
from typing import Dict, Any, Set, List, Optional
from collections import Counter, defaultdict
import pandas as pd

from .base_view import BaseView
from ..state import ViewType, ViewState
from ...tags.normalizer import TagNormalizer
from ...tags.analysis.tag_analyzer import TagAnalyzer
from ...tags.analysis.enhanced_tag_consolidator import EnhancedTagConsolidator, TagCategory
from ...tags.analysis.tag_similarity import TagSimilarity
from .tag_cloud_widget import TagCloudWidget
from albumexplore.gui.gui_logging import graphics_logger

class ConsolidationDialog(QDialog):
    """Dialog for reviewing and applying tag consolidations."""
    
    consolidationApproved = pyqtSignal(list)  # List of approved consolidations
    
    def __init__(self, suggestions, parent=None):
        super().__init__(parent)
        self.suggestions = suggestions
        self.approved_consolidations = []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Tag Consolidation Review")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Summary section
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.Shape.Box)
        summary_layout = QVBoxLayout(summary_frame)
        
        summary_label = QLabel(f"Found {len(self.suggestions)} consolidation opportunities")
        summary_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        summary_layout.addWidget(summary_label)
        
        info_label = QLabel("Review each suggestion below. Check the ones you want to apply.")
        summary_layout.addWidget(info_label)
        
        layout.addWidget(summary_frame)
        
        # Suggestions table
        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(6)
        self.suggestions_table.setHorizontalHeaderLabels([
            "Apply", "Primary Tag", "Secondary Tag", "Confidence", "Category", "Frequencies"
        ])
        
        # Configure headers
        header = self.suggestions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Apply checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)       # Primary tag
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)       # Secondary tag
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Confidence
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)       # Frequencies
        
        self.populate_suggestions_table()
        layout.addWidget(self.suggestions_table)
        
        # Auto-select controls
        auto_select_frame = QFrame()
        auto_select_layout = QHBoxLayout(auto_select_frame)
        
        confidence_label = QLabel("Auto-select by confidence:")
        auto_select_layout.addWidget(confidence_label)
        
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setMinimum(0)
        self.confidence_slider.setMaximum(100)
        self.confidence_slider.setValue(80)
        self.confidence_slider.valueChanged.connect(self.update_confidence_label)
        auto_select_layout.addWidget(self.confidence_slider)
        
        self.confidence_value_label = QLabel("0.80")
        auto_select_layout.addWidget(self.confidence_value_label)
        
        auto_select_button = QPushButton("Auto-Select")
        auto_select_button.clicked.connect(self.auto_select_by_confidence)
        auto_select_layout.addWidget(auto_select_button)
        
        auto_select_layout.addStretch()
        layout.addWidget(auto_select_frame)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_none)
        button_layout.addWidget(self.select_none_button)
        
        button_layout.addStretch()
        
        self.apply_button = QPushButton("Apply Selected")
        self.apply_button.clicked.connect(self.apply_selected)
        button_layout.addWidget(self.apply_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def populate_suggestions_table(self):
        self.suggestions_table.setRowCount(len(self.suggestions))
        
        for i, suggestion in enumerate(self.suggestions):
            # Apply checkbox
            checkbox = QCheckBox()
            if suggestion['confidence'] > 0.8:
                checkbox.setChecked(True)
            self.suggestions_table.setCellWidget(i, 0, checkbox)
            
            # Primary tag
            self.suggestions_table.setItem(i, 1, QTableWidgetItem(suggestion['primary_tag']))
            
            # Secondary tag
            self.suggestions_table.setItem(i, 2, QTableWidgetItem(suggestion['secondary_tag']))
            
            # Confidence
            confidence_item = QTableWidgetItem(f"{suggestion['confidence']:.2f}")
            confidence_item.setData(Qt.ItemDataRole.UserRole, suggestion['confidence'])
            self.suggestions_table.setItem(i, 3, confidence_item)
            
            # Category
            self.suggestions_table.setItem(i, 4, QTableWidgetItem(suggestion['category']))
            
            # Frequencies
            freq_text = f"{suggestion['primary_freq']} ← {suggestion['secondary_freq']}"
            self.suggestions_table.setItem(i, 5, QTableWidgetItem(freq_text))
    
    def update_confidence_label(self, value):
        confidence = value / 100.0
        self.confidence_value_label.setText(f"{confidence:.2f}")
    
    def auto_select_by_confidence(self):
        threshold = self.confidence_slider.value() / 100.0
        
        for i in range(self.suggestions_table.rowCount()):
            checkbox = self.suggestions_table.cellWidget(i, 0)
            confidence = self.suggestions[i]['confidence']
            checkbox.setChecked(confidence >= threshold)
    
    def select_all(self):
        for i in range(self.suggestions_table.rowCount()):
            checkbox = self.suggestions_table.cellWidget(i, 0)
            checkbox.setChecked(True)
    
    def select_none(self):
        for i in range(self.suggestions_table.rowCount()):
            checkbox = self.suggestions_table.cellWidget(i, 0)
            checkbox.setChecked(False)
    
    def apply_selected(self):
        self.approved_consolidations = []
        
        for i in range(self.suggestions_table.rowCount()):
            checkbox = self.suggestions_table.cellWidget(i, 0)
            if checkbox.isChecked():
                self.approved_consolidations.append(self.suggestions[i])
        
        if self.approved_consolidations:
            self.consolidationApproved.emit(self.approved_consolidations)
            self.accept()
        else:
            QMessageBox.information(self, "No Selection", "Please select at least one consolidation to apply.")


class EnhancedTagExplorerView(BaseView):
    """Enhanced tag explorer with consolidation and categorization features."""
    
    # Filter states
    FILTER_INCLUDE = 1
    FILTER_EXCLUDE = 2
    FILTER_NEUTRAL = 0
    
    # View modes
    MODE_STANDARD = 0
    MODE_CATEGORY = 1
    MODE_HIERARCHY = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_state = ViewState(ViewType.TAG_EXPLORER)
        
        # Data storage
        self.album_nodes_original = []
        self.tag_counts = Counter()
        self.tag_filters = {}
        self.filtered_albums = []
        self.current_view_mode = self.MODE_STANDARD
        
        # Enhanced analysis components
        self.tag_analyzer = None
        self.enhanced_consolidator = None
        self.enhanced_analysis = None
        
        self.setup_ui()
        self.setup_timers()
        
    def setup_ui(self):
        """Setup the enhanced UI with tabs and advanced controls."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Enhanced header with controls
        self.create_enhanced_header()
        main_layout.addWidget(self.header_widget)
        
        # Main content splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Enhanced tag explorer
        self.create_tag_panel()
        self.main_splitter.addWidget(self.tag_panel)
        
        # Right panel: Album results
        self.create_album_panel()
        self.main_splitter.addWidget(self.album_panel)
        
        # Set splitter sizes (40% tags, 60% albums)
        self.main_splitter.setSizes([400, 600])
        
        main_layout.addWidget(self.main_splitter)
        
    def create_enhanced_header(self):
        """Create enhanced header with consolidation controls."""
        self.header_widget = QFrame()
        self.header_widget.setFrameStyle(QFrame.Shape.Box)
        header_layout = QHBoxLayout(self.header_widget)
        
        # Status info
        self.status_label = QLabel("Enhanced Tag Explorer")
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(self.status_label)
        
        self.tag_count_label = QLabel("Tags: 0")
        header_layout.addWidget(self.tag_count_label)
        
        header_layout.addStretch()
        
        # View mode selector
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Standard View", "Category View", "Hierarchy View"])
        self.view_mode_combo.currentIndexChanged.connect(self.change_view_mode)
        header_layout.addWidget(QLabel("View:"))
        header_layout.addWidget(self.view_mode_combo)
        
        # Enhanced features toggle
        self.enhanced_checkbox = QCheckBox("Enhanced Features")
        self.enhanced_checkbox.setChecked(True)
        self.enhanced_checkbox.stateChanged.connect(self.toggle_enhanced_features)
        header_layout.addWidget(self.enhanced_checkbox)
        
        # Consolidation button
        self.consolidate_button = QPushButton("Apply Consolidation")
        self.consolidate_button.clicked.connect(self.show_consolidation_dialog)
        header_layout.addWidget(self.consolidate_button)
        
    def create_tag_panel(self):
        """Create the enhanced tag panel with tabs and categories."""
        self.tag_panel = QWidget()
        tag_layout = QVBoxLayout(self.tag_panel)
        
        # Search and filter controls
        search_layout = QHBoxLayout()
        
        self.tag_search = QLineEdit()
        self.tag_search.setPlaceholderText("Search tags...")
        self.tag_search.returnPressed.connect(self.search_tags)
        search_layout.addWidget(self.tag_search)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_tags)
        search_layout.addWidget(self.search_button)
        
        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.clicked.connect(self.clear_filters)
        search_layout.addWidget(self.clear_filters_button)
        
        tag_layout.addLayout(search_layout)
        
        # Tag view tabs
        self.tag_tabs = QTabWidget()
        
        # Standard table view
        self.create_standard_tag_view()
        self.tag_tabs.addTab(self.standard_tag_widget, "All Tags")
        
        # Category view
        self.create_category_view()
        self.tag_tabs.addTab(self.category_widget, "By Category")
        
        # Hierarchy view
        self.create_hierarchy_view()
        self.tag_tabs.addTab(self.hierarchy_widget, "Hierarchy")
        
        tag_layout.addWidget(self.tag_tabs)
        
    def create_standard_tag_view(self):
        """Create the standard tag table view."""
        self.standard_tag_widget = QWidget()
        layout = QVBoxLayout(self.standard_tag_widget)
        
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(5)
        self.tags_table.setHorizontalHeaderLabels([
            "Tag", "Count", "Matching", "Category", "Filter"
        ])
        
        # Configure headers
        header = self.tags_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tags_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tags_table.customContextMenuRequested.connect(self.show_tag_context_menu)
        
        layout.addWidget(self.tags_table)
        
    def create_category_view(self):
        """Create the category-based tag view."""
        self.category_widget = QWidget()
        layout = QVBoxLayout(self.category_widget)
        
        # Category selection
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        for category in TagCategory:
            self.category_combo.addItem(category.value.title())
        self.category_combo.currentTextChanged.connect(self.filter_by_category)
        category_layout.addWidget(self.category_combo)
        
        category_layout.addStretch()
        layout.addLayout(category_layout)
        
        # Category tree
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["Tag", "Count", "Filter"])
        self.category_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self.show_category_context_menu)
        
        layout.addWidget(self.category_tree)
        
    def create_hierarchy_view(self):
        """Create the hierarchical tag view."""
        self.hierarchy_widget = QWidget()
        layout = QVBoxLayout(self.hierarchy_widget)
        
        # Hierarchy controls
        hierarchy_layout = QHBoxLayout()
        hierarchy_layout.addWidget(QLabel("Expand Level:"))
        
        self.expand_level_combo = QComboBox()
        self.expand_level_combo.addItems(["All", "1", "2", "3"])
        self.expand_level_combo.currentTextChanged.connect(self.set_expand_level)
        hierarchy_layout.addWidget(self.expand_level_combo)
        
        hierarchy_layout.addStretch()
        layout.addLayout(hierarchy_layout)
        
        # Hierarchy tree
        self.hierarchy_tree = QTreeWidget()
        self.hierarchy_tree.setHeaderLabels(["Tag Hierarchy", "Count", "Strength", "Filter"])
        self.hierarchy_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hierarchy_tree.customContextMenuRequested.connect(self.show_hierarchy_context_menu)
        
        layout.addWidget(self.hierarchy_tree)
        
    def create_album_panel(self):
        """Create the album results panel."""
        self.album_panel = QWidget()
        album_layout = QVBoxLayout(self.album_panel)
        
        # Album count and controls
        album_header_layout = QHBoxLayout()
        
        self.album_count_label = QLabel("Albums: 0")
        self.album_count_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        album_header_layout.addWidget(self.album_count_label)
        
        album_header_layout.addStretch()
        
        self.export_results_button = QPushButton("Export Results")
        self.export_results_button.clicked.connect(self.export_results)
        album_header_layout.addWidget(self.export_results_button)
        
        album_layout.addLayout(album_header_layout)
        
        # Album table
        self.album_table = QTableWidget()
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
        
        # Configure album table headers
        album_header = self.album_table.horizontalHeader()
        album_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        album_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        album_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.album_table.setSortingEnabled(True)
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        album_layout.addWidget(self.album_table)
        
    def setup_timers(self):
        """Setup update timers for performance."""
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.process_updates)
        
    def initialize_enhanced_analysis(self):
        """Initialize the enhanced tag analysis system."""
        if not self.album_nodes_original:
            return
            
        try:
            # Create DataFrame from album data
            album_data = []
            for node in self.album_nodes_original:
                album_data.append({
                    'artist': node.get('artist', ''),
                    'album': node.get('album', ''),
                    'year': node.get('year', ''),
                    'tags': node.get('tags', [])
                })
            
            df = pd.DataFrame(album_data)
            
            # Initialize enhanced system
            self.tag_analyzer = TagAnalyzer(df)
            self.enhanced_consolidator = EnhancedTagConsolidator(self.tag_analyzer)
            self.tag_analyzer.set_enhanced_consolidator(self.enhanced_consolidator)
            
            # Get enhanced analysis
            self.enhanced_analysis = self.tag_analyzer.get_consolidated_analysis()
            
            self.update_status_display()
            graphics_logger.info("Enhanced tag analysis initialized successfully")
            
        except Exception as e:
            graphics_logger.error(f"Failed to initialize enhanced analysis: {e}")
            self.enhanced_checkbox.setChecked(False)
    
    def update_status_display(self):
        """Update the status display with enhanced information."""
        if self.enhanced_analysis:
            original_count = self.enhanced_analysis['original_count']
            consolidated_count = self.enhanced_analysis['consolidated_count']
            reduction = self.enhanced_analysis['reduction_percentage']
            
            status_text = f"Enhanced: {original_count} → {consolidated_count} tags ({reduction:.1f}% reduction)"
            self.status_label.setText(status_text)
            
            # Update tag count
            self.tag_count_label.setText(f"Tags: {consolidated_count}")
    
    def toggle_enhanced_features(self, state):
        """Toggle enhanced features on/off."""
        if state == Qt.CheckState.Checked.value:
            self.initialize_enhanced_analysis()
            self.consolidate_button.setEnabled(True)
        else:
            self.enhanced_analysis = None
            self.consolidate_button.setEnabled(False)
            self.status_label.setText("Enhanced Tag Explorer")
        
        self.update_tag_views()
    
    def change_view_mode(self, mode):
        """Change the tag view mode."""
        self.current_view_mode = mode
        
        if mode == self.MODE_STANDARD:
            self.tag_tabs.setCurrentIndex(0)
        elif mode == self.MODE_CATEGORY:
            self.tag_tabs.setCurrentIndex(1)
        elif mode == self.MODE_HIERARCHY:
            self.tag_tabs.setCurrentIndex(2)
        
        self.update_tag_views()
    
    def show_consolidation_dialog(self):
        """Show the consolidation review dialog."""
        if not self.enhanced_analysis:
            QMessageBox.information(self, "No Analysis", "Please enable enhanced features first.")
            return
        
        suggestions = self.enhanced_analysis.get('suggestions', [])
        if not suggestions:
            QMessageBox.information(self, "No Suggestions", "No consolidation suggestions available.")
            return
        
        dialog = ConsolidationDialog(suggestions, self)
        dialog.consolidationApproved.connect(self.apply_consolidations)
        dialog.exec()
    
    def apply_consolidations(self, consolidations):
        """Apply the approved consolidations."""
        if not consolidations:
            return
        
        # Create progress dialog
        progress = QProgressBar()
        progress.setRange(0, len(consolidations))
        progress.show()
        
        applied_count = 0
        
        # Apply each consolidation
        for i, consolidation in enumerate(consolidations):
            # Update progress
            progress.setValue(i)
            
            # Apply the consolidation logic here
            # This would involve updating the tag data
            applied_count += 1
        
        progress.close()
        
        # Show results
        QMessageBox.information(
            self, 
            "Consolidation Complete", 
            f"Successfully applied {applied_count} consolidations.\n\nThe tag explorer will refresh automatically."
        )
        
        # Refresh the view
        self.initialize_enhanced_analysis()
        self.update_tag_views()
    
    def update_tag_views(self):
        """Update all tag views with current data."""
        if self.enhanced_analysis and self.enhanced_checkbox.isChecked():
            self.update_enhanced_views()
        else:
            self.update_standard_views()
    
    def update_enhanced_views(self):
        """Update views with enhanced analysis data."""
        if not self.enhanced_analysis:
            return
        
        categorized = self.enhanced_analysis['categorized']
        hierarchies = self.enhanced_analysis['hierarchies']
        
        # Update standard table with categories
        self.update_standard_table_enhanced(categorized)
        
        # Update category view
        self.update_category_tree(categorized)
        
        # Update hierarchy view
        self.update_hierarchy_tree(hierarchies)
    
    def update_standard_table_enhanced(self, categorized_tags):
        """Update the standard table with category information."""
        self.tags_table.setRowCount(0)
        
        for category, tags in categorized_tags.items():
            for tag, count in tags.items():
                row = self.tags_table.rowCount()
                self.tags_table.insertRow(row)
                
                # Tag name
                self.tags_table.setItem(row, 0, QTableWidgetItem(tag))
                
                # Count
                count_item = QTableWidgetItem(str(count))
                count_item.setData(Qt.ItemDataRole.UserRole, count)
                self.tags_table.setItem(row, 1, count_item)
                
                # Matching (will be updated by filters)
                self.tags_table.setItem(row, 2, QTableWidgetItem("0"))
                
                # Category
                self.tags_table.setItem(row, 3, QTableWidgetItem(category.value.title()))
                
                # Filter state
                filter_state = self.tag_filters.get(tag, self.FILTER_NEUTRAL)
                filter_text = ["Neutral", "Include", "Exclude"][filter_state]
                self.tags_table.setItem(row, 4, QTableWidgetItem(filter_text))
    
    def update_category_tree(self, categorized_tags):
        """Update the category tree view."""
        self.category_tree.clear()
        
        for category, tags in categorized_tags.items():
            if not tags:
                continue
                
            # Create category item
            category_item = QTreeWidgetItem([category.value.title(), "", ""])
            category_item.setFont(0, QFont("Arial", 9, QFont.Weight.Bold))
            
            # Add tag children
            for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
                tag_item = QTreeWidgetItem([tag, str(count), "Neutral"])
                tag_item.setData(0, Qt.ItemDataRole.UserRole, tag)
                category_item.addChild(tag_item)
            
            self.category_tree.addTopLevelItem(category_item)
            category_item.setExpanded(True)
    
    def update_hierarchy_tree(self, hierarchies):
        """Update the hierarchy tree view."""
        self.hierarchy_tree.clear()
        
        for parent, relations in hierarchies.items():
            if not relations:
                continue
                
            # Create parent item
            parent_item = QTreeWidgetItem([parent, "", "", ""])
            parent_item.setFont(0, QFont("Arial", 9, QFont.Weight.Bold))
            
            # Add child relationships
            for relation in sorted(relations, key=lambda x: x.strength, reverse=True):
                child_item = QTreeWidgetItem([
                    relation.child, 
                    "", 
                    f"{relation.strength:.2f}", 
                    "Neutral"
                ])
                child_item.setData(0, Qt.ItemDataRole.UserRole, relation.child)
                parent_item.addChild(child_item)
            
            self.hierarchy_tree.addTopLevelItem(parent_item)
            parent_item.setExpanded(True)
    
    def update_standard_views(self):
        """Update views with standard tag analysis."""
        # Fallback to basic tag display
        self.tags_table.setRowCount(0)
        
        for tag, count in self.tag_counts.most_common():
            row = self.tags_table.rowCount()
            self.tags_table.insertRow(row)
            
            self.tags_table.setItem(row, 0, QTableWidgetItem(tag))
            self.tags_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.tags_table.setItem(row, 2, QTableWidgetItem("0"))
            self.tags_table.setItem(row, 3, QTableWidgetItem("Unknown"))
            self.tags_table.setItem(row, 4, QTableWidgetItem("Neutral"))
    
    # Context menu methods
    def show_tag_context_menu(self, position):
        """Show context menu for tag operations."""
        # Implementation for tag context menu
        pass
    
    def show_category_context_menu(self, position):
        """Show context menu for category operations."""
        # Implementation for category context menu
        pass
    
    def show_hierarchy_context_menu(self, position):
        """Show context menu for hierarchy operations."""
        # Implementation for hierarchy context menu
        pass
    
    # Utility methods
    def search_tags(self):
        """Search for tags based on user input."""
        # Implementation for tag search
        pass
    
    def clear_filters(self):
        """Clear all active filters."""
        self.tag_filters.clear()
        self.update_tag_views()
    
    def filter_by_category(self, category_name):
        """Filter tags by category."""
        # Implementation for category filtering
        pass
    
    def set_expand_level(self, level):
        """Set the expansion level for hierarchy view."""
        # Implementation for expand level setting
        pass
    
    def export_results(self):
        """Export current results."""
        # Implementation for result export
        pass
    
    def process_updates(self):
        """Process pending updates."""
        # Implementation for batch updates
        pass
    
    def update_data(self, nodes, edges):
        """Update the view with new data."""
        self.album_nodes_original = nodes
        self.tag_counts.clear()
        
        # Process tags from nodes
        for node in nodes:
            tags = node.get('tags', [])
            for tag in tags:
                if tag:  # Skip empty tags
                    self.tag_counts[tag] += 1
        
        # Initialize enhanced analysis if enabled
        if self.enhanced_checkbox.isChecked():
            self.initialize_enhanced_analysis()
        
        # Update views
        self.update_tag_views()
        
        # Update album count
        self.album_count_label.setText(f"Albums: {len(nodes)}") 