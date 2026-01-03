"""
Saved Query Dialog for managing filter presets.

Allows users to save, load, and manage tag filter configurations as named presets.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
                             QInputDialog, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Optional

from albumexplore.tags.filters import TagFilterState, SavedQuery


class SavedQueryDialog(QDialog):
    """
    Dialog for managing saved filter queries.
    
    Signals:
        querySelected(SavedQuery): Emitted when user selects a query to load
    """
    
    querySelected = pyqtSignal(object)  # SavedQuery
    
    def __init__(self, current_filter_state: TagFilterState = None, parent=None):
        """
        Initialize the saved query dialog.
        
        Args:
            current_filter_state: Current filter state to save as new query
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_filter_state = current_filter_state
        self.saved_queries = []  # List of SavedQuery objects
        self.queries_file = Path.home() / ".albumexplore" / "saved_queries.json"
        
        self.setWindowTitle("Saved Filter Queries")
        self.setMinimumSize(600, 400)
        
        self._setup_ui()
        self._load_queries()
        self._populate_list()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Saved Filter Queries")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - List of queries
        left_layout = QVBoxLayout()
        
        list_label = QLabel("Saved Queries:")
        list_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(list_label)
        
        self.query_list = QListWidget()
        self.query_list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.query_list)
        
        # Buttons for list actions
        list_buttons = QHBoxLayout()
        
        self.new_button = QPushButton("Save Current")
        self.new_button.setToolTip("Save current filter as new query")
        self.new_button.clicked.connect(self._save_new_query)
        self.new_button.setEnabled(self.current_filter_state is not None)
        list_buttons.addWidget(self.new_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Delete selected query")
        self.delete_button.clicked.connect(self._delete_query)
        self.delete_button.setEnabled(False)
        list_buttons.addWidget(self.delete_button)
        
        left_layout.addLayout(list_buttons)
        
        content_layout.addLayout(left_layout, 1)
        
        # Right side - Query details
        right_layout = QVBoxLayout()
        
        details_label = QLabel("Query Details:")
        details_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(details_label)
        
        # Name display
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_display = QLabel("")
        self.name_display.setStyleSheet("font-weight: bold; color: #4a7ba7;")
        name_layout.addWidget(self.name_display)
        name_layout.addStretch()
        right_layout.addLayout(name_layout)
        
        # Description display
        right_layout.addWidget(QLabel("Description:"))
        self.description_display = QTextEdit()
        self.description_display.setReadOnly(True)
        self.description_display.setMaximumHeight(80)
        right_layout.addWidget(self.description_display)
        
        # Stats display
        stats_label = QLabel("Statistics:")
        stats_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(stats_label)
        
        self.stats_display = QLabel("")
        self.stats_display.setWordWrap(True)
        right_layout.addWidget(self.stats_display)
        
        # Filter summary display
        summary_label = QLabel("Filter Summary:")
        summary_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(summary_label)
        
        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        right_layout.addWidget(self.summary_display)
        
        right_layout.addStretch()
        
        content_layout.addLayout(right_layout, 1)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.load_button = QPushButton("Load Selected")
        self.load_button.setToolTip("Load selected query")
        self.load_button.clicked.connect(self._load_selected_query)
        self.load_button.setEnabled(False)
        self.load_button.setStyleSheet("""
            QPushButton {
                background: #2c5f8d;
                color: #e8e8e8;
                border: 1px solid #1a3a5a;
                border-radius: 3px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a7db8;
            }
            QPushButton:disabled {
                background: #2a2d32;
                color: #666;
            }
        """)
        button_layout.addWidget(self.load_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _load_queries(self):
        """Load saved queries from file."""
        if not self.queries_file.exists():
            return
        
        try:
            with open(self.queries_file, 'r') as f:
                data = json.load(f)
                self.saved_queries = [SavedQuery.from_dict(q) for q in data]
        except Exception as e:
            QMessageBox.warning(self, "Load Error", 
                              f"Failed to load saved queries: {e}")
    
    def _save_queries(self):
        """Save queries to file."""
        try:
            # Ensure directory exists
            self.queries_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save queries
            with open(self.queries_file, 'w') as f:
                data = [q.to_dict() for q in self.saved_queries]
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", 
                              f"Failed to save queries: {e}")
    
    def _populate_list(self):
        """Populate the query list."""
        self.query_list.clear()
        
        # Sort by last_used (most recent first), then by name
        sorted_queries = sorted(self.saved_queries, 
                               key=lambda q: (q.last_used or datetime.min, q.name),
                               reverse=True)
        
        for query in sorted_queries:
            item = QListWidgetItem(query.name)
            item.setData(Qt.ItemDataRole.UserRole, query)
            
            # Add tooltip with description and stats
            tooltip = f"{query.description}\n\n"
            tooltip += f"Created: {query.created.strftime('%Y-%m-%d %H:%M')}\n"
            if query.last_used:
                tooltip += f"Last used: {query.last_used.strftime('%Y-%m-%d %H:%M')}\n"
            tooltip += f"Used {query.use_count} times"
            item.setToolTip(tooltip)
            
            self.query_list.addItem(item)
    
    def _on_selection_changed(self, current, previous):
        """Handle selection change in query list."""
        if current is None:
            self.delete_button.setEnabled(False)
            self.load_button.setEnabled(False)
            self._clear_details()
            return
        
        self.delete_button.setEnabled(True)
        self.load_button.setEnabled(True)
        
        # Display query details
        query = current.data(Qt.ItemDataRole.UserRole)
        self._display_query_details(query)
    
    def _display_query_details(self, query: SavedQuery):
        """Display details of selected query."""
        self.name_display.setText(query.name)
        self.description_display.setPlainText(query.description)
        
        # Stats
        stats = f"Created: {query.created.strftime('%Y-%m-%d %H:%M')}\n"
        if query.last_used:
            stats += f"Last used: {query.last_used.strftime('%Y-%m-%d %H:%M')}\n"
        stats += f"Times used: {query.use_count}"
        self.stats_display.setText(stats)
        
        # Filter summary
        summary = query.filter_state.get_filter_summary()
        self.summary_display.setPlainText(summary)
    
    def _clear_details(self):
        """Clear the details display."""
        self.name_display.setText("")
        self.description_display.setPlainText("")
        self.stats_display.setText("")
        self.summary_display.setPlainText("")
    
    def _save_new_query(self):
        """Save current filter state as new query."""
        if self.current_filter_state is None:
            return
        
        # Get name from user
        name, ok = QInputDialog.getText(self, "Save Query", 
                                       "Enter a name for this query:")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        
        # Check for duplicate name
        if any(q.name == name for q in self.saved_queries):
            reply = QMessageBox.question(self, "Duplicate Name",
                                        f"A query named '{name}' already exists. Overwrite?",
                                        QMessageBox.StandardButton.Yes | 
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            
            # Remove existing query with same name
            self.saved_queries = [q for q in self.saved_queries if q.name != name]
        
        # Get description from user
        description, ok = QInputDialog.getMultiLineText(self, "Save Query",
                                                        "Enter a description (optional):",
                                                        "")
        if not ok:
            description = ""
        
        # Create saved query
        query = SavedQuery(
            name=name,
            filter_state=self.current_filter_state,
            description=description.strip(),
            created=datetime.now()
        )
        
        self.saved_queries.append(query)
        self._save_queries()
        self._populate_list()
        
        QMessageBox.information(self, "Query Saved", 
                               f"Query '{name}' has been saved.")
    
    def _delete_query(self):
        """Delete selected query."""
        current = self.query_list.currentItem()
        if current is None:
            return
        
        query = current.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "Delete Query",
                                    f"Delete query '{query.name}'?",
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.saved_queries.remove(query)
            self._save_queries()
            self._populate_list()
    
    def _load_selected_query(self):
        """Load selected query and close dialog."""
        current = self.query_list.currentItem()
        if current is None:
            return
        
        query = current.data(Qt.ItemDataRole.UserRole)
        
        # Update usage stats
        query.last_used = datetime.now()
        query.use_count += 1
        self._save_queries()
        
        # Emit signal and accept dialog
        self.querySelected.emit(query)
        self.accept()
