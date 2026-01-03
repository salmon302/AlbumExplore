"""
Tag group widget - visual representation of a single filter group.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QMenu, QLineEdit, QCompleter, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent

from albumexplore.tags.filters import TagFilterGroup, GroupOperator
from albumexplore.gui.widgets.tag_chip_widget import TagChip


class TagGroupWidget(QWidget):
    """
    Visual representation of a TagFilterGroup.
    
    Shows group name, tags as chips, and controls for adding/removing tags.
    
    Signals:
        tagAdded(str): Emitted when a tag is added to the group
        tagRemoved(str): Emitted when a tag is removed from the group
        groupDeleted(): Emitted when the delete button is clicked
        groupNameChanged(str): Emitted when group name is changed
    """
    
    tagAdded = pyqtSignal(str)
    tagRemoved = pyqtSignal(str)
    groupDeleted = pyqtSignal()
    groupNameChanged = pyqtSignal(str)
    tagDraggedOut = pyqtSignal(str)  # Emitted when tag dragged out of group
    tagDroppedIn = pyqtSignal(str)   # Emitted when tag dropped into group
    expressionChanged = pyqtSignal()
    
    # Color palette for groups
    GROUP_COLORS = [
        "#FFE0E0",  # Light red
        "#E0E0FF",  # Light blue
        "#E0FFE0",  # Light green
        "#FFFFE0",  # Light yellow
        "#FFE0FF",  # Light magenta
        "#E0FFFF",  # Light cyan
        "#FFD0C0",  # Light orange
        "#F0E0FF",  # Light purple
    ]
    
    def __init__(self, group: TagFilterGroup, available_tags: list = None, parent=None):
        """
        Initialize the tag group widget.
        
        Args:
            group: The TagFilterGroup to represent
            available_tags: List of all available tags for autocomplete
            parent: Parent widget
        """
        super().__init__(parent)
        self.group = group
        self.available_tags = available_tags or []
        self.tag_chips = {}  # Map tag -> TagChip widget
        
        # Enable drag-and-drop
        self.setAcceptDrops(True)
        
        # Set group color if not already set
        if not self.group.color:
            color_index = int(self.group.group_id) % len(self.GROUP_COLORS)
            self.group.color = self.GROUP_COLORS[color_index]
        
        self._setup_ui()
        self._populate_tags()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        
        # Frame for visual grouping with better visibility
        self.frame = QFrame()
        self.frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.frame.setLineWidth(1)
        # Apply styling for better visibility in dark theme
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #252830;
                border: 1px solid #4a7ba7;
                border-radius: 4px;
            }
        """)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(6, 6, 6, 6)
        frame_layout.setSpacing(5)
        
        # Header with group name and controls
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        # Enabled checkbox
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setChecked(self.group.enabled)
        self.enabled_checkbox.setToolTip("Enable/disable this group")
        self.enabled_checkbox.toggled.connect(self._on_enabled_toggled)
        header_layout.addWidget(self.enabled_checkbox)
        
        # Group name label (editable on double-click)
        self.name_label = QLabel(self.group.name)
        self.name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                color: #e8e8e8;
                padding: 1px 3px;
            }
        """)
        self.name_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_label.setToolTip("Double-click to rename group")
        self.name_label.mouseDoubleClickEvent = self._start_rename_group
        header_layout.addWidget(self.name_label)
        
        # Name editor (hidden until editing)
        self.name_editor = QLineEdit()
        self.name_editor.setVisible(False)
        self.name_editor.setMaxLength(50)
        self.name_editor.returnPressed.connect(self._finish_rename_group)
        self.name_editor.editingFinished.connect(self._cancel_rename_if_focus_lost)
        header_layout.addWidget(self.name_editor)
        
        # Operator indicator (clickable to toggle)
        operator_text = "ALL" if self.group.operator == GroupOperator.AND else "ANY"
        self.operator_label = QPushButton(operator_text)
        self.operator_label.setToolTip("Click to switch between AND/OR logic")
        self.operator_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.operator_label.setFixedHeight(16)
        self.operator_label.clicked.connect(self._toggle_operator)
        self._update_operator_style()
        header_layout.addWidget(self.operator_label)
        
        header_layout.addStretch()
        
        # Delete button
        self.delete_button = QPushButton("×")
        self.delete_button.setFixedSize(16, 16)
        self.delete_button.setToolTip("Delete this group")
        self.delete_button.clicked.connect(self.groupDeleted.emit)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #555;
                border-radius: 8px;
                color: #888;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #4a1f1f;
                color: #d88;
                border-color: #8d4040;
            }
        """)
        header_layout.addWidget(self.delete_button)
        
        frame_layout.addLayout(header_layout)
        
        # Tags container (flow layout)
        self.tags_widget = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch()  # This will be moved as tags are added
        frame_layout.addWidget(self.tags_widget)
        
        # Add tag input and button
        add_layout = QHBoxLayout()
        add_layout.setSpacing(4)
        
        self.add_tag_input = QLineEdit()
        self.add_tag_input.setPlaceholderText("Add tag...")
        self.add_tag_input.setMaximumWidth(150)
        self.add_tag_input.setStyleSheet("""
            QLineEdit {
                background: #1e2127;
                color: #e8e8e8;
                border: 1px solid #3f3f46;
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #4a7ba7;
            }
        """)
        self.add_tag_input.returnPressed.connect(self._on_add_tag)
        
        # Setup autocomplete if available tags provided
        if self.available_tags:
            completer = QCompleter(self.available_tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.add_tag_input.setCompleter(completer)
        
        add_layout.addWidget(self.add_tag_input)
        
        self.add_tag_button = QPushButton("+")
        self.add_tag_button.setFixedSize(18, 18)
        self.add_tag_button.setToolTip("Add tag to group")
        self.add_tag_button.clicked.connect(self._on_add_tag)
        self.add_tag_button.setStyleSheet("""
            QPushButton {
                background: #2d5a3d;
                color: #ddd;
                border: 1px solid #1f3f2a;
                border-radius: 9px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #3d7a4d;
            }
        """)
        add_layout.addWidget(self.add_tag_button)
        add_layout.addStretch()
        
        frame_layout.addLayout(add_layout)
        
        main_layout.addWidget(self.frame)
        
        # Apply group color to frame
        self._update_frame_color()
    
    def _update_frame_color(self):
        """Update frame border color based on group color."""
        if self.group.color:
            self.frame.setStyleSheet(f"""
                QFrame {{
                    border: 1px solid {self.group.color}40;
                    border-radius: 4px;
                    background: #1a1d21;
                    padding: 4px;
                }}
            """)
    
    def _toggle_operator(self):
        """Toggle between AND and OR operators."""
        if self.group.operator == GroupOperator.AND:
            self.group.operator = GroupOperator.OR
        else:
            self.group.operator = GroupOperator.AND
        
        # Update button text and style
        operator_text = "ALL" if self.group.operator == GroupOperator.AND else "ANY"
        self.operator_label.setText(operator_text)
        self._update_operator_style()
        
        # Emit signal so panel knows to update
        self.groupNameChanged.emit(self.group.name)  # Reuse this signal
        # Operator change affects evaluation/expression
        try:
            self.expressionChanged.emit()
        except Exception:
            pass
    
    def _refresh_tag_display(self):
        """Refresh the entire tag display (used after operator changes)."""
        # Save current tags
        current_tags = list(self.tag_chips.keys())
        
        # Clear all widgets except the stretch
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear chip tracking
        self.tag_chips.clear()
        
        # Re-add all tags (which will add operators between them)
        for tag in sorted(current_tags):
            self._add_tag_chip(tag)
    
    def _update_operator_style(self):
        """Update operator button styling based on current operator."""
        if self.group.operator == GroupOperator.AND:
            # AND = Gray/blue theme (stricter, all must match)
            style = """
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
            """
        else:  # OR
            # OR = Purple theme (more flexible, any can match)
            style = """
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
            """
        self.operator_label.setStyleSheet(style)
    
    def _populate_tags(self):
        """Populate the tags from the group."""
        for tag in sorted(self.group.tags):
            self._add_tag_chip(tag)
    
    def _add_tag_chip(self, tag: str):
        """Add a visual tag chip to the display."""
        if tag in self.tag_chips:
            return  # Already exists
        
        chip = TagChip(tag, color=self.group.color, removable=True, draggable=True)
        chip.removeClicked.connect(lambda t=tag: self._on_remove_tag(t))
        chip.dragStarted.connect(lambda t=tag: self.tagDraggedOut.emit(t))
        
        # Insert before the stretch
        insert_index = self.tags_layout.count() - 1
        self.tags_layout.insertWidget(insert_index, chip)
        
        self.tag_chips[tag] = chip
    

    
    def _remove_tag_chip(self, tag: str):
        """Remove a tag chip from the display."""
        if tag not in self.tag_chips:
            return
        
        chip = self.tag_chips[tag]
        self.tags_layout.removeWidget(chip)
        chip.deleteLater()
        del self.tag_chips[tag]
    
    def _on_add_tag(self):
        """Handle adding a new tag."""
        tag = self.add_tag_input.text().strip()
        if not tag:
            return
        
        # Add to group model
        if self.group.add_tag(tag):
            # Add visual chip
            self._add_tag_chip(tag)
            # Update expression
            self._sync_expression()
            # Emit signal
            self.tagAdded.emit(tag)
            # Clear input
            self.add_tag_input.clear()
    
    def _on_remove_tag(self, tag: str):
        """Handle removing a tag."""
        # Remove from group model
        if self.group.remove_tag(tag):
            # Remove visual chip
            self._remove_tag_chip(tag)
            # Update expression
            self._sync_expression()
            # Emit signal
            self.tagRemoved.emit(tag)
    
    def _sync_expression(self):
        """Sync the expression list from the visual layout order."""
        expression = []
        
        # Walk through the layout and build expression
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if widget is None:
                continue
            
            # Check if it's a tag chip
            if isinstance(widget, TagChip):
                expression.append(widget.tag_text)
            # Check if it's an operator
            elif hasattr(widget, 'operator_type'):
                from albumexplore.gui.widgets.operator_widget import OperatorWidget
                if isinstance(widget, OperatorWidget):
                    expression.append(widget.operator_type.value)
        
        old_expr = getattr(self.group, 'expression', None)
        # Update the group's expression
        self.group.expression = expression

        # Debug: print the expression
        if expression:
            print(f"Group {self.group.name} expression: {' '.join(expression)}")

        # Emit signal if expression changed so parent panel can react
        if old_expr != expression:
            try:
                self.expressionChanged.emit()
            except Exception:
                pass
    
    def add_tag(self, tag: str):
        """Programmatically add a tag to this group."""
        if self.group.add_tag(tag):
            self._add_tag_chip(tag)
            self.tagAdded.emit(tag)
            return True
        return False
    
    def remove_tag(self, tag: str):
        """Programmatically remove a tag from this group."""
        if self.group.remove_tag(tag):
            self._remove_tag_chip(tag)
            self.tagRemoved.emit(tag)
            return True
        return False
    
    def get_group(self) -> TagFilterGroup:
        """Get the underlying TagFilterGroup."""
        return self.group
    
    def update_available_tags(self, tags: list):
        """Update the list of available tags for autocomplete."""
        self.available_tags = tags
        if tags:
            completer = QCompleter(tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.add_tag_input.setCompleter(completer)
    
    def is_empty(self) -> bool:
        """Check if this group has no tags."""
        return self.group.is_empty()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this group."""
        self.group.enabled = enabled
        self.enabled_checkbox.setChecked(enabled)
        # The toggled signal will handle the rest
    
    def _on_enabled_toggled(self, checked: bool):
        """Handle enabled checkbox toggled."""
        self.group.enabled = checked
        # Update visual state of other controls
        self.name_label.setEnabled(checked)
        self.operator_label.setEnabled(checked)
        self.tags_widget.setEnabled(checked)
        self.add_tag_input.setEnabled(checked)
        self.add_tag_button.setEnabled(checked)
        
        # Emit signal to update filters
        self.expressionChanged.emit()
    
    def _start_rename_group(self, event):
        """Start renaming the group."""
        # Hide label, show editor
        self.name_label.setVisible(False)
        self.name_editor.setVisible(True)
        self.name_editor.setText(self.group.name)
        self.name_editor.setFocus()
        self.name_editor.selectAll()
    
    def _finish_rename_group(self):
        """Finish renaming the group."""
        new_name = self.name_editor.text().strip()
        
        # Validate name
        if not new_name:
            # Revert to original if empty
            self.name_editor.setText(self.group.name)
            return
        
        # Update group name
        if new_name != self.group.name:
            self.group.name = new_name
            self.name_label.setText(new_name)
            self.groupNameChanged.emit(new_name)
        
        # Hide editor, show label
        self.name_editor.setVisible(False)
        self.name_label.setVisible(True)
    
    def _cancel_rename_if_focus_lost(self):
        """Cancel rename if editor lost focus without pressing Enter."""
        if self.name_editor.isVisible() and not self.name_editor.hasFocus():
            # Check if user didn't press Enter (returnPressed would have been called)
            # Just hide the editor and restore original
            self.name_editor.setVisible(False)
            self.name_label.setVisible(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        # Accept both tags and operators
        if (event.mimeData().hasText() or 
            event.mimeData().hasFormat('application/x-tagchip') or
            event.mimeData().hasFormat('application/x-operator')):
            event.acceptProposedAction()
            # Visual feedback: highlight the group border
            self.frame.setStyleSheet(f"""
                QFrame {{
                    border: 3px dashed #4a7ba7;
                    border-radius: 4px;
                    background-color: #2a2d32;
                }}
            """)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        # Reset visual feedback
        self._update_frame_color()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        # Reset visual feedback
        self._update_frame_color()
        
        # Find the drop position by checking which widget is closest to the drop point
        drop_pos = event.position().toPoint() if hasattr(event.position(), 'toPoint') else event.pos()
        insert_index = self._get_drop_index(drop_pos)
        
        # Check if it's an operator
        if event.mimeData().hasFormat('application/x-operator'):
            operator_text = event.mimeData().data('application/x-operator').data().decode()
            self._add_operator(operator_text, insert_index)
            event.acceptProposedAction()
            return
        
        # Otherwise, handle as tag drop
        tag_text = None
        if event.mimeData().hasFormat('application/x-tagchip'):
            tag_text = event.mimeData().data('application/x-tagchip').data().decode()
        elif event.mimeData().hasText():
            tag_text = event.mimeData().text()
        
        if tag_text and self.add_tag(tag_text):
            self.tagDroppedIn.emit(tag_text)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _get_drop_index(self, drop_pos):
        """Determine the insertion index based on drop position."""
        # Map the position to the tags_widget coordinate space
        local_pos = self.tags_widget.mapFromParent(drop_pos)
        
        # Find which widget the drop is closest to
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if widget is None:
                continue
            
            widget_geometry = widget.geometry()
            
            # If drop is before the center of this widget, insert before it
            if local_pos.x() < widget_geometry.center().x():
                return i
        
        # If we didn't find a position, insert before the stretch (at the end)
        return self.tags_layout.count() - 1
    
    def _add_operator(self, operator_text: str, insert_index: int = None):
        """Add an operator to this group at the specified index."""
        from albumexplore.gui.widgets.operator_widget import OperatorWidget, OperatorType
        
        # Parse operator type
        try:
            op_type = OperatorType(operator_text)
        except ValueError:
            return
        
        # Create operator widget
        operator = OperatorWidget(op_type, draggable=True, parent=self)
        operator.deleteRequested.connect(lambda: self._remove_operator(operator))
        
        # Insert at specified index or before the stretch at the end
        if insert_index is None:
            insert_index = self.tags_layout.count() - 1
        
        self.tags_layout.insertWidget(insert_index, operator)
        
        # Update expression
        self._sync_expression()
    
    def _remove_operator(self, operator_widget):
        """Remove an operator widget from the group."""
        self.tags_layout.removeWidget(operator_widget)
        operator_widget.deleteLater()
        
        # Update expression
        self._sync_expression()
