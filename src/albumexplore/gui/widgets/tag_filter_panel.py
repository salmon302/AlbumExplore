"""
Tag filter panel - main UI for managing tag filter groups.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QSizePolicy, QLineEdit, QCompleter, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence, QPalette, QColor

from albumexplore.tags.filters import TagFilterState, TagFilterGroup, FilterOperator
from albumexplore.gui.widgets.operator_widget import OperatorPalette
# Conditional import - TokenizedQueryInput may not exist yet
try:
    from .tokenized_query_input import TokenizedQueryInput
    HAS_TOKENIZED_INPUT = True
except ImportError:
    HAS_TOKENIZED_INPUT = False
    TokenizedQueryInput = None
    
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
    
    # New signals for parent interaction
    includeSelectedRequest = pyqtSignal()
    excludeSelectedRequest = pyqtSignal()

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
    
    def _update_placeholder_visibility(self):
        """Show/hide placeholder based on whether groups exist."""
        has_groups = len(self.group_widgets) > 0
        if hasattr(self, 'empty_placeholder'):
            self.empty_placeholder.setVisible(not has_groups)

    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(3)
        
        # Fix tooltip colors
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2a2d32"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f1f3f4"))
        self.setPalette(palette)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        # New: Action Buttons (Include/Exclude Selection)
        self.btn_include = QPushButton("Include")
        self.btn_include.setToolTip("Add selected tags to filters (Ctrl+I)")
        self.btn_include.setStyleSheet("background-color: #2e4a30; font-weight: bold; padding: 2px 8px; border-radius: 2px;")
        self.btn_include.clicked.connect(self.includeSelectedRequest.emit)
        header_layout.addWidget(self.btn_include)

        self.btn_exclude = QPushButton("Exclude")
        self.btn_exclude.setToolTip("Exclude selected tags from filters (Ctrl+E)")
        self.btn_exclude.setStyleSheet("background-color: #4a2e2e; font-weight: bold; padding: 2px 8px; border-radius: 2px;")
        self.btn_exclude.clicked.connect(self.excludeSelectedRequest.emit)
        header_layout.addWidget(self.btn_exclude)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        header_layout.addWidget(line)

        # Active checkbox
        self.active_checkbox = QCheckBox("Tag Filters")
        self.active_checkbox.setChecked(self.filter_state.active)
        self.active_checkbox.toggled.connect(self._on_active_toggled)
        self.active_checkbox.setStyleSheet("font-weight: bold; font-size: 10px; color: #bbb;")
        header_layout.addWidget(self.active_checkbox)
        
        # Add Group Operator Toggle
        self.group_operator_button = QPushButton("ANY Group")
        self.group_operator_button.setToolTip("Click to switch between matching ANY group (OR) or ALL groups (AND)")
        self.group_operator_button.setCheckable(True)
        self.group_operator_button.clicked.connect(self._toggle_group_operator)
        self._update_group_operator_ui()
        header_layout.addWidget(self.group_operator_button)
        
        # Add query logic helper
        self.logic_helper = QLabel("Add tags to filter albums")
        self.logic_helper.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 9px;
                font-style: italic;
                padding: 2px 6px;
                border-radius: 3px;
                margin-left: 6px;
            }
        """)
        self.logic_helper.setWordWrap(False)
        self.logic_helper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header_layout.addWidget(self.logic_helper)
        
        # New group button
        self.new_group_button = QPushButton("+ Group")
        self.new_group_button.clicked.connect(self._on_new_group)
        self.new_group_button.setStyleSheet("""
            QPushButton {
                background: #2c5f8d;
                color: #e8e8e8;
                border: 1px solid #1a3a5a;
                border-radius: 2px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a7db8;
                border-color: #2c5f8d;
            }
        """)
        header_layout.addWidget(self.new_group_button)
        
        # Saved queries button
        self.saved_queries_button = QPushButton("📋 Saved")
        self.saved_queries_button.setToolTip("Manage saved query presets")
        self.saved_queries_button.clicked.connect(self._open_saved_queries)
        self.saved_queries_button.setStyleSheet("""
            QPushButton {
                background: #4d5a2c;
                color: #e8e8e8;
                border: 1px solid #3a451f;
                border-radius: 2px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #6d7a3c;
                border-color: #4d5a2c;
            }
        """)
        header_layout.addWidget(self.saved_queries_button)
        
        # Advanced query toggle (renamed from 'Advanced' dialog button)
        self.advanced_query_button = QPushButton("Query Mode")
        self.advanced_query_button.setCheckable(True)
        self.advanced_query_button.setToolTip("Toggle advanced boolean query editor")
        self.advanced_query_button.toggled.connect(self._toggle_advanced_mode)
        # Style as a toggle button
        self.advanced_query_button.setStyleSheet("""
            QPushButton {
                padding: 2px 8px;
                background: #333;
                color: #ccc;
                border: 1px solid #555;
                font-size: 9px;
                border-radius: 2px;
            }
            QPushButton:checked {
                background: #d68a00;
                color: #111;
                border: 1px solid #ffa000;
                font-weight: bold;
            }
            QPushButton:hover { background: #444; }
            QPushButton:checked:hover { background: #e69a10; }
        """)
        header_layout.addWidget(self.advanced_query_button)
        
        # Clear all button
        self.clear_all_button = QPushButton("Clear")
        self.clear_all_button.clicked.connect(self._on_clear_all)
        self.clear_all_button.setStyleSheet("""
            QPushButton {
                background: #6d3030;
                color: #e8e8e8;
                border: 1px solid #4a1f1f;
                border-radius: 2px;
                padding: 2px 6px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #8d4040;
                border-color: #6d3030;
            }
        """)
        header_layout.addWidget(self.clear_all_button)
        
        main_layout.addLayout(header_layout)
        
        # --- Advanced Query Section (Hidden by default) ---
        self.advanced_container = QWidget()
        self.advanced_container.setVisible(False)
        advanced_layout = QVBoxLayout(self.advanced_container)
        advanced_layout.setContentsMargins(4, 4, 4, 4)
        advanced_layout.setSpacing(2)
        
        # Add operator palette for drag-and-drop
        self.operator_palette = OperatorPalette(self)
        self.operator_palette.setMaximumHeight(30)
        advanced_layout.addWidget(self.operator_palette)
        
        # Inline advanced query input (tokenized)
        if HAS_TOKENIZED_INPUT:
            try:
                self.tokenized_query = TokenizedQueryInput(self)
                try:
                    self.tokenized_query.setStyleSheet('''
                        QWidget { border: 1px solid #3a7db8; border-radius: 4px; padding: 4px; background: #131417; }
                    ''')
                except Exception:
                    pass
                advanced_layout.addWidget(self.tokenized_query)
                self.tokenized_query.applyQuery.connect(self._on_apply_tokenized_query)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("Failed to create TokenizedQueryInput: %s", e)
                error_msg = QLabel(f"⚠ Advanced query input unavailable: {str(e)}")
                error_msg.setStyleSheet('color: #b66; font-style: italic; font-size: 9px;')
                advanced_layout.addWidget(error_msg)
                self.tokenized_query = None
        else:
            self.tokenized_query = None
            placeholder = QLabel("Advanced query input: not yet implemented")
            placeholder.setStyleSheet('color: #888; font-style: italic; font-size: 9px;')
            advanced_layout.addWidget(placeholder)
            
        # Add "Full Editor Dialog" link
        full_editor_btn = QPushButton("Open Full Screen Editor")
        full_editor_btn.setStyleSheet("text-align: left; padding: 2px; color: #8ab; border: none; font-size: 9px;")
        full_editor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        full_editor_btn.clicked.connect(self._on_open_advanced_query)
        advanced_layout.addWidget(full_editor_btn)

        main_layout.addWidget(self.advanced_container)
        
        # Scrollable area for groups
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for groups
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.setSpacing(2)  # Very tight spacing
        # No stretch at bottom - let groups fill naturally
        
        # Placeholder for empty state
        self.empty_placeholder = QLabel("No active filter groups\nClick '+ Group' or add tags to filter")
        self.empty_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_placeholder.setStyleSheet("color: #666; font-style: italic; margin: 20px;")
        self.groups_layout.addWidget(self.empty_placeholder)
        
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
        
        # Initial placeholder state
        self._update_placeholder_visibility()
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for the filter panel."""
        # Ctrl+N to create new group
        new_group_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_group_shortcut.activated.connect(self._on_new_group)
        
        # Ctrl+Shift+C to clear all (already handled by TagExplorerView, but provide here too)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        clear_shortcut.activated.connect(self._on_clear_all)

    def _toggle_advanced_mode(self, checked: bool):
        """Toggle the visibility of the advanced query section."""
        if hasattr(self, 'advanced_container'):
            self.advanced_container.setVisible(checked)
    
    def _open_saved_queries(self):
        """Open the saved queries dialog."""
        from albumexplore.gui.widgets.saved_query_dialog import SavedQueryDialog
        
        dialog = SavedQueryDialog(self.filter_state, self)
        dialog.querySelected.connect(self._load_saved_query)
        dialog.exec()
    
    def _load_saved_query(self, query):
        """Load a saved query."""
        from albumexplore.tags.filters import SavedQuery
        
        if isinstance(query, SavedQuery):
            self.set_filter_state(query.filter_state)
            self.filtersChanged.emit()

    def _on_open_advanced_query(self):
        """Open the advanced boolean query editor dialog."""
        try:
            from .query_editor import QueryEditorDialog
        except Exception:
            from albumexplore.gui.widgets.query_editor import QueryEditorDialog

        # Create dialog with TagExplorerView as parent so it can access tag_to_album_nodes
        parent_view = self.parent()
        dialog = QueryEditorDialog(parent_view)
        
        # Make the filter panel accessible to the dialog for applying results
        dialog.filter_panel = self
        
        # Prepopulate with simple filters converted to query
        includes = []
        for group in self.filter_state.groups:
            includes.extend(sorted(group.tags))
        excludes = sorted(self.filter_state.exclude_tags)
        from ...search import api as search_api
        q = search_api.simple_filters_to_query(includes, excludes)
        dialog.set_query(q)
        
        # Execute dialog and apply results if accepted
        if dialog.exec():
            # The dialog's on_apply method will handle setting the filter state
            # Just ensure the filters are emitted
            self.filtersChanged.emit()

    def _on_apply_tokenized_query(self, query: str):
        """Apply a tokenized query from the inline editor by converting it to filter state."""
        from ...search import api as search_api
        from PyQt6.QtWidgets import QMessageBox

        try:
            state = search_api.query_to_filter_state(query)
        except Exception as e:
            QMessageBox.warning(self, "Cannot convert query",
                                f"Advanced query cannot be converted to filter groups: {e}\nOpen Advanced dialog to keep as advanced-only.")
            return

        # Apply converted state
        self.set_filter_state(state)
        self.filtersChanged.emit()

    def update_available_tags(self, tags: list):
        """Update available tags for autocomplete across the panel and group widgets.

        This provides a compatibility method used by views that expect the panel
        to expose `update_available_tags`.
        """
        self.available_tags = tags or []
        # Update each group widget's completer/input
        for widget in self.group_widgets.values():
            try:
                widget.update_available_tags(self.available_tags)
            except Exception:
                # Do not fail if a widget cannot be updated
                pass
    
    def _toggle_group_operator(self):
        """Toggle between AND and OR operators for combining groups."""
        if self.filter_state.group_operator == FilterOperator.OR:
            self.filter_state.group_operator = FilterOperator.AND
        else:
            self.filter_state.group_operator = FilterOperator.OR
        
        self._update_group_operator_ui()
        self._update_group_separators()
        self.filtersChanged.emit()

    def _update_group_operator_ui(self):
        """Update the group operator button UI."""
        if self.filter_state.group_operator == FilterOperator.AND:
            self.group_operator_button.setText("ALL Groups")
            self.group_operator_button.setStyleSheet("""
                QPushButton {
                    background: #3a4a5a;
                    color: #d0d8e0;
                    border: 1px solid #2a3a4a;
                    border-radius: 8px;
                    padding: 2px 6px;
                    font-size: 9px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #4a5a6a;
                    border-color: #5a8ab8;
                }
            """)
        else:
            self.group_operator_button.setText("ANY Group")
            self.group_operator_button.setStyleSheet("""
                QPushButton {
                    background: #6d5199;
                    color: #e8e0f0;
                    border: 1px solid #5d4189;
                    border-radius: 8px;
                    padding: 2px 6px;
                    font-size: 9px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #7d61a9;
                    border-color: #9d81c9;
                }
            """)

    def _update_group_separators(self):
        """Update the text and style of separators between groups."""
        separator_text = "AND" if self.filter_state.group_operator == FilterOperator.AND else "OR"
        separator_style = """
            QLabel {
                background: #2196F3;
                color: #fff;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 5px 0px;
            }
        """ if self.filter_state.group_operator == FilterOperator.AND else """
            QLabel {
                background: #FFC107;
                color: #333;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 5px 0px;
            }
        """
        
        for i in range(self.groups_layout.count()):
            item = self.groups_layout.itemAt(i)
            if item and isinstance(item.widget(), QLabel):
                separator = item.widget()
                # Check if it's a separator (not some other label)
                if separator.text() in ("OR", "AND"):
                    separator.setText(separator_text)
                    separator.setStyleSheet(separator_style)

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
        widget.expressionChanged.connect(lambda gid=group.group_id: self._on_expression_changed(gid))
        
        # Add OR separator if not first group
        if len(self.group_widgets) > 0:
            separator_text = "AND" if self.filter_state.group_operator == FilterOperator.AND else "OR"
            separator_style = """
                QLabel {
                    background: #2196F3;
                    color: #fff;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin: 5px 0px;
                }
            """ if self.filter_state.group_operator == FilterOperator.AND else """
                QLabel {
                    background: #FFC107;
                    color: #333;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin: 5px 0px;
                }
            """
            separator = QLabel(separator_text)
            separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            separator.setStyleSheet(separator_style)
            self.groups_layout.addWidget(separator)
        
        # Add widget to end
        self.groups_layout.addWidget(widget)
        
        self.group_widgets[group.group_id] = widget
        self._update_placeholder_visibility()
    
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
                if separator.text() in ("OR", "AND"):
                    self.groups_layout.removeWidget(separator)
                    separator.deleteLater()
        # Or remove OR separator after this group (if this is first group)
        elif widget_index == 0 and self.groups_layout.count() > 2:
            item = self.groups_layout.itemAt(1)
            if item and isinstance(item.widget(), QLabel):
                separator = item.widget()
                if separator.text() in ("OR", "AND"):
                    self.groups_layout.removeWidget(separator)
                    separator.deleteLater()
        
        # Remove widget
        self.groups_layout.removeWidget(widget)
        widget.deleteLater()
        del self.group_widgets[group_id]
        self._update_placeholder_visibility()
    
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

    def _on_active_toggled(self, checked: bool):
        """Handle active checkbox toggled."""
        self.filter_state.active = checked
        self.filtersChanged.emit()

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

    def _on_expression_changed(self, group_id: str):
        """Handle when a group's expression (operators/order) changes."""
        # The group's TagFilterGroup.expression has already been updated by the widget.
        # Ensure summary and filter application are triggered.
        self._update_summary()
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
        # Clear existing UI
        self._on_clear_all()

        # Set new state
        self.filter_state = filter_state

        # Populate from new state
        self._populate_groups()
        self._populate_exclusions()
        self._update_summary()
        self._update_group_operator_ui()
        self.update_active_checkbox()
        self.filtersChanged.emit()

    def update_active_checkbox(self):
        """Ensure active checkbox matches filter state."""
        if hasattr(self, 'active_checkbox'):
            self.active_checkbox.setChecked(self.filter_state.active)

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
