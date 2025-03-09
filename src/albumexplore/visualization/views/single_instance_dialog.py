"""Dialog for managing single-instance tags."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QLabel, QPushButton, QComboBox,
                            QHeaderView, QMessageBox, QCheckBox, QGroupBox,
                            QRadioButton, QButtonGroup, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SingleInstanceDialog(QDialog):
    """Dialog for managing single-instance tags."""
    
    # Signal emitted when changes are applied
    changes_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None, single_instance_handler=None, tag_normalizer=None):
        """Initialize the dialog."""
        super().__init__(parent)
        self.single_instance_handler = single_instance_handler
        self.tag_normalizer = tag_normalizer
        self.suggestions = {}
        self.selected_suggestions = {}
        
        self.setWindowTitle("Single-Instance Tag Management")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_data()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header with stats
        self.stats_label = QLabel("Single-instance tags: 0")
        layout.addWidget(self.stats_label)
        
        # Options panel
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout(options_group)
        
        # Confidence threshold
        confidence_layout = QVBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Threshold:"))
        self.confidence_spinner = QSpinBox()
        self.confidence_spinner.setRange(1, 100)
        self.confidence_spinner.setValue(70)
        self.confidence_spinner.setSuffix("%")
        confidence_layout.addWidget(self.confidence_spinner)
        options_layout.addLayout(confidence_layout)
        
        # Auto-apply options
        apply_options_layout = QVBoxLayout()
        apply_options_layout.addWidget(QLabel("Auto-apply:"))
        self.apply_high_confidence = QCheckBox("High confidence suggestions")
        self.apply_high_confidence.setChecked(True)
        apply_options_layout.addWidget(self.apply_high_confidence)
        self.apply_common_misspellings = QCheckBox("Common misspellings")
        self.apply_common_misspellings.setChecked(True)
        apply_options_layout.addWidget(self.apply_common_misspellings)
        options_layout.addLayout(apply_options_layout)
        
        # Filter options
        filter_options_layout = QVBoxLayout()
        filter_options_layout.addWidget(QLabel("Filter by:"))
        self.filter_all = QRadioButton("All single-instance tags")
        self.filter_all.setChecked(True)
        filter_options_layout.addWidget(self.filter_all)
        self.filter_with_suggestions = QRadioButton("Tags with suggestions")
        filter_options_layout.addWidget(self.filter_with_suggestions)
        self.filter_without_suggestions = QRadioButton("Tags without suggestions")
        filter_options_layout.addWidget(self.filter_without_suggestions)
        
        # Create button group
        self.filter_group = QButtonGroup()
        self.filter_group.addButton(self.filter_all)
        self.filter_group.addButton(self.filter_with_suggestions)
        self.filter_group.addButton(self.filter_without_suggestions)
        self.filter_group.buttonClicked.connect(self._apply_filters)
        
        options_layout.addLayout(filter_options_layout)
        layout.addWidget(options_group)
        
        # Table for single-instance tags
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(4)
        self.tags_table.setHorizontalHeaderLabels(["Tag", "Suggested Normalization", "Confidence", "Apply"])
        
        # Configure headers
        header = self.tags_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.tags_table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.auto_apply_button = QPushButton("Auto-Apply Suggestions")
        self.auto_apply_button.clicked.connect(self._auto_apply_suggestions)
        button_layout.addWidget(self.auto_apply_button)
        
        self.apply_button = QPushButton("Apply Selected")
        self.apply_button.clicked.connect(self._apply_selected)
        button_layout.addWidget(self.apply_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_data)
        button_layout.addWidget(self.refresh_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def _load_data(self):
        """Load single-instance tag data."""
        if not self.single_instance_handler:
            return
            
        # Generate suggestions
        self.suggestions = self.single_instance_handler.generate_consolidation_suggestions()
        
        # Update stats
        single_instance_count = len(self.single_instance_handler.single_instance_tags)
        self.stats_label.setText(f"Single-instance tags: {single_instance_count}")
        
        # Populate table
        self._populate_table()
        
    def _populate_table(self):
        """Populate the table with single-instance tags and suggestions."""
        self.tags_table.setRowCount(0)  # Clear table
        
        if not self.single_instance_handler:
            return
            
        # Get all single-instance tags
        single_instance_tags = self.single_instance_handler.single_instance_tags
        
        # Apply filters
        filtered_tags = set()
        if self.filter_all.isChecked():
            filtered_tags = single_instance_tags
        elif self.filter_with_suggestions.isChecked():
            filtered_tags = {tag for tag in single_instance_tags if tag in self.suggestions}
        elif self.filter_without_suggestions.isChecked():
            filtered_tags = {tag for tag in single_instance_tags if tag not in self.suggestions}
        
        # Sort tags alphabetically
        sorted_tags = sorted(filtered_tags)
        
        # Populate table
        self.tags_table.setRowCount(len(sorted_tags))
        
        for i, tag in enumerate(sorted_tags):
            # Tag column
            tag_item = QTableWidgetItem(tag)
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tags_table.setItem(i, 0, tag_item)
            
            # Suggestion column
            suggestion_combo = QComboBox()
            
            # Add suggestions if available
            if tag in self.suggestions and self.suggestions[tag]:
                for suggested_tag, confidence, reason in self.suggestions[tag]:
                    suggestion_combo.addItem(f"{suggested_tag} ({reason})", suggested_tag)
                
                # Add "Keep as is" option
                suggestion_combo.addItem("Keep as is", "")
                
                # Set default selection
                if tag in self.selected_suggestions:
                    index = suggestion_combo.findData(self.selected_suggestions[tag])
                    if index >= 0:
                        suggestion_combo.setCurrentIndex(index)
            else:
                suggestion_combo.addItem("No suggestions", "")
                
            self.tags_table.setCellWidget(i, 1, suggestion_combo)
            
            # Confidence column
            confidence = 0.0
            if tag in self.suggestions and self.suggestions[tag]:
                confidence = self.suggestions[tag][0][1]  # First suggestion's confidence
                
            confidence_item = QTableWidgetItem(f"{confidence:.0%}")
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Color-code confidence
            if confidence >= 0.8:
                confidence_item.setBackground(QColor(200, 255, 200))  # Light green
            elif confidence >= 0.5:
                confidence_item.setBackground(QColor(255, 255, 200))  # Light yellow
            else:
                confidence_item.setBackground(QColor(255, 200, 200))  # Light red
                
            self.tags_table.setItem(i, 2, confidence_item)
            
            # Apply checkbox
            apply_checkbox = QCheckBox()
            apply_checkbox.setChecked(tag in self.selected_suggestions)
            
            # Center the checkbox
            checkbox_layout = QHBoxLayout()
            checkbox_layout.addWidget(apply_checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            
            checkbox_widget = QWidget()
            checkbox_widget.setLayout(checkbox_layout)
            
            self.tags_table.setCellWidget(i, 3, checkbox_widget)
            
    def _apply_filters(self):
        """Apply filters to the table."""
        self._populate_table()
        
    def _auto_apply_suggestions(self):
        """Automatically apply suggestions based on settings."""
        if not self.single_instance_handler:
            return
            
        threshold = self.confidence_spinner.value() / 100.0
        
        # Apply high confidence suggestions
        if self.apply_high_confidence.isChecked():
            applied = self.single_instance_handler.apply_bulk_suggestions(threshold)
            
            # Update selected suggestions
            self.selected_suggestions.update(applied)
            
            # Show results
            if applied:
                QMessageBox.information(
                    self,
                    "Auto-Apply Results",
                    f"Applied {len(applied)} high-confidence suggestions."
                )
            else:
                QMessageBox.information(
                    self,
                    "Auto-Apply Results",
                    "No high-confidence suggestions found."
                )
                
            # Refresh the table
            self._load_data()
            
    def _apply_selected(self):
        """Apply selected suggestions."""
        if not self.single_instance_handler:
            return
            
        # Collect selected suggestions from the table
        selected_count = 0
        
        for i in range(self.tags_table.rowCount()):
            # Get the tag
            tag_item = self.tags_table.item(i, 0)
            if not tag_item:
                continue
                
            tag = tag_item.text()
            
            # Get the checkbox
            checkbox_widget = self.tags_table.cellWidget(i, 3)
            if not checkbox_widget:
                continue
                
            checkbox = checkbox_widget.findChild(QCheckBox)
            if not checkbox or not checkbox.isChecked():
                continue
                
            # Get the selected suggestion
            suggestion_combo = self.tags_table.cellWidget(i, 1)
            if not suggestion_combo:
                continue
                
            suggested_tag = suggestion_combo.currentData()
            if not suggested_tag:  # "Keep as is" selected
                continue
                
            # Apply the suggestion
            if self.single_instance_handler.apply_suggestion(tag, suggested_tag):
                selected_count += 1
                self.selected_suggestions[tag] = suggested_tag
                
        # Show results
        if selected_count > 0:
            QMessageBox.information(
                self,
                "Apply Results",
                f"Applied {selected_count} selected suggestions."
            )
            
            # Emit signal with applied changes
            self.changes_applied.emit(self.selected_suggestions)
            
            # Refresh the table
            self._load_data()
        else:
            QMessageBox.information(
                self,
                "Apply Results",
                "No suggestions were applied."
            )
            
    def accept(self):
        """Handle dialog acceptance."""
        # Save any pending changes to the normalizer
        if self.tag_normalizer and hasattr(self.tag_normalizer, 'save_config'):
            self.tag_normalizer.save_config()
            
        super().accept()