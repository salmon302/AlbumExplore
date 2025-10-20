"""
Tag filter panel - main UI for managing tag filter groups.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QSizePolicy, QLineEdit, QCompleter)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence

from albumexplore.tags.filters import TagFilterState, TagFilterGroup
from albumexplore.gui.widgets.tag_group_widget import TagGroupWidget
from albumexplore.gui.widgets.tag_chip_widget import TagChip


class TagFilterPanel(QWidget):
    """
    Main panel for managing tag filters with groups.
    
    Contains:
    - Multiple TagGroupWidgets (with OR logic between them)
    - Exclusion tags section
    - Filter summary display
    - Controls for creating/managing groups
    
    Signals:
        filtersChanged(): Emitted when any filter changes
        tagAddedToGroup(str, str): Emitted when tag added (tag, group_id)
        tagRemovedFromGroup(str, str): Emitted when tag removed (tag, group_id)
    """
    
    filtersChanged = pyqtSignal()
    tagAddedToGroup = pyqtSignal(str, str)  # tag, group_id
    tagRemovedFromGroup = pyqtSignal(str, str)  # tag, group_id
    
    def __init__(self, filter_state: TagFilterState = None, available_tags: list = None, parent=None):
        """
        Initialize the filter panel.
        
        Args:
            filter_state: The TagFilterState to manage (creates new if None)
            available_tags: List of all available tags for autocomplete
            parent: Parent widget
        """
        super().__init__(parent)
        self.filter_state = filter_state or TagFilterState()
        self.available_tags = available_tags or []
        self.group_widgets = {}  # Map group_id -> TagGroupWidget
        
        self._setup_ui()
        self._populate_groups()
        self._populate_exclusions()
        self._update_summary()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Tag Filters")
        title.setStyleSheet("font-weight: bold; font-size: 11px; color: #bbb;")
        header_layout.addWidget(title)
        
        # Add query logic helper
        self.logic_helper = QLabel("Add tags to filter albums")
        self.logic_helper.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 9px;
                font-style: italic;
                padding: 2px 6px;
                background: #1a1d21;
                border-radius: 3px;
                margin-left: 6px;
            }
        """)
        self.logic_helper.setWordWrap(True)
        header_layout.addWidget(self.logic_helper, 1)
        
        header_layout.addStretch()
        
        # New group button
        self.new_group_button = QPushButton("+ Group")
        self.new_group_button.clicked.connect(self._on_new_group)
        self.new_group_button.setStyleSheet("""
            QPushButton {
                background: #2c5f8d;
                color: #e8e8e8;
                border: 1px solid #1a3a5a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a7db8;
                border-color: #2c5f8d;
            }
        """)
        header_layout.addWidget(self.new_group_button)
        
        # Clear all button
        self.clear_all_button = QPushButton("Clear")
        self.clear_all_button.clicked.connect(self._on_clear_all)
        self.clear_all_button.setStyleSheet("""
            QPushButton {
                background: #6d3030;
                color: #e8e8e8;
                border: 1px solid #4a1f1f;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #8d4040;
                border-color: #6d3030;
            }
        """)
        header_layout.addWidget(self.clear_all_button)
        
        main_layout.addLayout(header_layout)
        
        # Scrollable area for groups
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for groups
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.setSpacing(4)  # Tighter spacing
        # No stretch at bottom - let groups fill naturally
        
        scroll_area.setWidget(self.groups_container)
        main_layout.addWidget(scroll_area, stretch=1)
        
        # OR separator label (shown between groups)
        self.or_separator = QLabel("OR")
        self.or_separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.or_separator.setStyleSheet("""
            QLabel {
                background: #FFC107;
                color: #333;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 5px 0px;
            }
        """)
        self.or_separator.setVisible(False)
        
        # Exclusions section - compact at bottom
        exclusions_layout = QHBoxLayout()
        exclusions_layout.setSpacing(4)
        
        exclusions_label = QLabel("Exclude:")
        exclusions_label.setStyleSheet("font-weight: bold; color: #d88; font-size: 10px;")
        exclusions_layout.addWidget(exclusions_label)
        # Exclusion input field
        self.exclusion_input = QLineEdit()
        self.exclusion_input.setPlaceholderText("Add exclusion...")
        self.exclusion_input.setMaximumWidth(120)
        self.exclusion_input.setStyleSheet("""
            QLineEdit {
                background: #1a1d21;
                color: #ccc;
                border: 1px solid #2a2d32;
                border-radius: 2px;
                padding: 2px 4px;
                font-size: 10px;
            }
        """)
        self.exclusion_input.returnPressed.connect(self._on_add_exclusion_from_input)
        exclusions_layout.addWidget(self.exclusion_input)
        
        
        self.add_exclusion_button = QPushButton("+")
        self.add_exclusion_button.setFixedSize(18, 18)
        self.add_exclusion_button.setToolTip("Add exclusion tag")
        self.add_exclusion_button.clicked.connect(self._on_add_exclusion_from_input)
        self.add_exclusion_button.setStyleSheet("""
            QPushButton {
                background: #6d3030;
                color: #ddd;
                border: 1px solid #4a1f1f;
                border-radius: 9px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #8d4040;
            }
        """)
        exclusions_layout.addWidget(self.add_exclusion_button)
        
        # Exclusions chips container - inline
        self.exclusions_widget = QWidget()
        self.exclusions_layout = QHBoxLayout(self.exclusions_widget)
        self.exclusions_layout.setContentsMargins(0, 0, 0, 0)
        self.exclusions_layout.setSpacing(3)
        self.exclusions_layout.addStretch()
        exclusions_layout.addWidget(self.exclusions_widget, 1)
        
        main_layout.addLayout(exclusions_layout)
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for the filter panel."""
        # Ctrl+N to create new group
        new_group_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_group_shortcut.activated.connect(self._on_new_group)
        
        # Ctrl+Shift+C to clear all (already handled by TagExplorerView, but provide here too)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        clear_shortcut.activated.connect(self._on_clear_all)
    
    def _populate_groups(self):
        """Populate groups from filter state."""
        for group in self.filter_state.groups:
            self._add_group_widget(group)
    
    def _populate_exclusions(self):
        """Populate exclusion tags."""
        for tag in sorted(self.filter_state.exclude_tags):
            self._add_exclusion_chip(tag)
    
    def _add_group_widget(self, group: TagFilterGroup):
        """Add a group widget to the panel."""
        if group.group_id in self.group_widgets:
            return  # Already exists
        
        # Create widget
        widget = TagGroupWidget(group, self.available_tags)
        widget.tagAdded.connect(lambda tag, gid=group.group_id: self._on_tag_added_to_group(tag, gid))
        widget.tagRemoved.connect(lambda tag, gid=group.group_id: self._on_tag_removed_from_group(tag, gid))
        widget.groupDeleted.connect(lambda gid=group.group_id: self._on_group_deleted(gid))
        widget.tagDraggedOut.connect(lambda tag, gid=group.group_id: self._on_tag_dragged_out(tag, gid))
        widget.tagDroppedIn.connect(lambda tag, gid=group.group_id: self._on_tag_dropped_in(tag, gid))
        
        # Add OR separator if not first group
        if len(self.group_widgets) > 0:
            separator = QLabel("OR")
            separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            separator.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 transparent, 
                                              stop:0.45 #6d5199,
                                              stop:0.5 #7c5fb3,
                                              stop:0.55 #6d5199,
                                              stop:1 transparent);
                    color: #d0d0d0;
                    font-weight: bold;
                    font-size: 9px;
                    padding: 2px 6px;
                    margin: 3px 0px;
                }
            """)
            self.groups_layout.addWidget(separator)
        
        # Add widget to end
        self.groups_layout.addWidget(widget)
        
        self.group_widgets[group.group_id] = widget
    
    def _remove_group_widget(self, group_id: str):
        """Remove a group widget from the panel."""
        if group_id not in self.group_widgets:
            return
        
        widget = self.group_widgets[group_id]
        
        # Find and remove OR separator if needed
        widget_index = self.groups_layout.indexOf(widget)
        
        # Remove OR separator before this group (if exists and not first)
        if widget_index > 0:
            item = self.groups_layout.itemAt(widget_index - 1)
            if item and isinstance(item.widget(), QLabel):
                separator = item.widget()
                if separator.text() == "OR":
                    self.groups_layout.removeWidget(separator)
                    separator.deleteLater()
        # Or remove OR separator after this group (if this is first group)
        elif widget_index == 0 and self.groups_layout.count() > 2:
            item = self.groups_layout.itemAt(1)
            if item and isinstance(item.widget(), QLabel):
                separator = item.widget()
                if separator.text() == "OR":
                    self.groups_layout.removeWidget(separator)
                    separator.deleteLater()
        
        # Remove widget
        self.groups_layout.removeWidget(widget)
        widget.deleteLater()
        del self.group_widgets[group_id]
    
    def _add_exclusion_chip(self, tag: str):
        """Add an exclusion tag chip."""
        chip = TagChip(tag, color="#FFCCCC", removable=True)
        chip.removeClicked.connect(lambda t=tag: self._on_remove_exclusion(t))
        
        # Insert before stretch
        insert_index = self.exclusions_layout.count() - 1
        self.exclusions_layout.insertWidget(insert_index, chip)
    
    def _remove_exclusion_chip(self, tag: str):
        """Remove an exclusion tag chip."""
        # Find and remove the chip
        for i in range(self.exclusions_layout.count()):
            item = self.exclusions_layout.itemAt(i)
            if item and isinstance(item.widget(), TagChip):
                chip = item.widget()
                if chip.get_tag_text() == tag:
                    self.exclusions_layout.removeWidget(chip)
                    chip.deleteLater()
                    break
    
    def _update_summary(self):
        """Update the filter summary display."""
        self._update_logic_helper()
    
    def _update_logic_helper(self):
        """Update the helper text showing current query logic."""
        # Count total tags in groups
        total_tags = sum(len(g.tags) for g in self.filter_state.groups if not g.is_empty())
        num_groups = len([g for g in self.filter_state.groups if not g.is_empty()])
        num_exclusions = len(self.filter_state.exclude_tags)
        
        if not num_groups and not num_exclusions:
            self.logic_helper.setText("No filters active")
            return
        
        # Build compact summary
        parts = []
        if num_groups:
            parts.append(f"{num_groups} group{'s' if num_groups > 1 else ''} ({total_tags} tag{'s' if total_tags != 1 else ''})")
        if num_exclusions:
            parts.append(f"{num_exclusions} excluded")
        
        summary = " • ".join(parts)
        self.logic_helper.setText(summary)
    
    def _on_new_group(self):
        """Handle creating a new group."""
        group = self.filter_state.add_group()
        self._add_group_widget(group)
        self._update_summary()
        self.filtersChanged.emit()
    
    def _on_clear_all(self):
        """Handle clearing all filters."""
        # Clear all group widgets
        for group_id in list(self.group_widgets.keys()):
            self._remove_group_widget(group_id)
        
        # Clear all exclusion chips
        for tag in list(self.filter_state.exclude_tags):
            self._remove_exclusion_chip(tag)
        
        # Clear filter state
        self.filter_state.clear_all()
        
        self._update_summary()
        self.filtersChanged.emit()
    
    def _on_group_deleted(self, group_id: str):
        """Handle group deletion."""
        self.filter_state.remove_group(group_id)
        self._remove_group_widget(group_id)
        self._update_summary()
        self.filtersChanged.emit()
    
    def _on_tag_added_to_group(self, tag: str, group_id: str):
        """Handle tag added to a group."""
        self._update_summary()
        self.tagAddedToGroup.emit(tag, group_id)
        self.filtersChanged.emit()
    
    def _on_tag_removed_from_group(self, tag: str, group_id: str):
        """Handle tag removed from a group."""
        self._update_summary()
        self.tagRemovedFromGroup.emit(tag, group_id)
        self.filtersChanged.emit()
    
    def _on_remove_exclusion(self, tag: str):
        """Handle removing an exclusion."""
        if self.filter_state.remove_exclusion(tag):
            self._remove_exclusion_chip(tag)
            self._update_summary()
            self.filtersChanged.emit()
    
    def _on_add_exclusion_from_input(self):
        """Handle adding an exclusion from the input field."""
        tag = self.exclusion_input.text().strip()
        if not tag:
            return
        
        # Add exclusion
        if self.filter_state.add_exclusion(tag):
            self._add_exclusion_chip(tag)
            self._update_summary()
            self.filtersChanged.emit()
            # Clear input
            self.exclusion_input.clear()
    
    def add_tag_to_group(self, tag: str, group_id: str = None):
        """
        Programmatically add a tag to a group.
        
        Args:
            tag: Tag to add
            group_id: Group ID (uses/creates first group if None)
        """
        if group_id is None:
            # Use first group or create one
            if not self.filter_state.groups:
                self._on_new_group()
            group_id = self.filter_state.groups[0].group_id
        
        if group_id in self.group_widgets:
            self.group_widgets[group_id].add_tag(tag)
    
    def add_exclusion(self, tag: str):
        """Programmatically add an exclusion tag."""
        if self.filter_state.add_exclusion(tag):
            self._add_exclusion_chip(tag)
            self._update_summary()
            self.filtersChanged.emit()
    
    def get_filter_state(self) -> TagFilterState:
        """Get the current filter state."""
        return self.filter_state
    
    def set_filter_state(self, filter_state: TagFilterState):
        """Set a new filter state (replaces current)."""
        # Clear existing
        self._on_clear_all()
        
        # Set new state
        self.filter_state = filter_state
        
        # Populate from new state
        self._populate_groups()
        self._populate_exclusions()
        self._update_summary()
        self.filtersChanged.emit()
    
    def update_available_tags(self, tags: list):
        """Update the list of available tags for autocomplete."""
        self.available_tags = tags
        for widget in self.group_widgets.values():
            widget.update_available_tags(tags)
        
        # Update exclusion input autocomplete
        if tags and hasattr(self, 'exclusion_input'):
            completer = QCompleter(tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.exclusion_input.setCompleter(completer)
    
    def set_results_count(self, count: int):
        """Update the results count display - now integrated into logic helper."""
        # Results count is now shown in the main status bar instead
        pass
    
    def is_empty(self) -> bool:
        """Check if there are no active filters."""
        return self.filter_state.is_empty()
    
    def _on_tag_dragged_out(self, tag: str, source_group_id: str):
        """Handle tag being dragged out of a group."""
        # Tag will be removed from source when dropped elsewhere
        pass
    
    def _on_tag_dropped_in(self, tag: str, target_group_id: str):
        """Handle tag being dropped into a group."""
        # Check if tag exists in another group and remove it
        for group_id, widget in self.group_widgets.items():
            if group_id != target_group_id:
                if tag in widget.get_group().tags:
                    widget.remove_tag(tag)
        
        # The tag has already been added by the group widget
        # Just ensure filters are updated
        self._update_summary()
        self.filtersChanged.emit()
