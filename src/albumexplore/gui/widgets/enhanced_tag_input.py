from PyQt6.QtWidgets import (QLineEdit, QCompleter, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QListWidget, 
                           QListWidgetItem, QFrame, QComboBox, QToolTip,
                           QScrollArea, QFlowLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QTimer, QPoint
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QFontMetrics
from typing import List, Dict, Set, Optional
import re

class TagChip(QWidget):
    """A visual tag chip with category coloring and remove functionality."""
    
    removeRequested = pyqtSignal(str)  # Tag name to remove
    
    CATEGORY_COLORS = {
        'genre': '#3498db',      # Blue
        'style_modifier': '#9b59b6',  # Purple  
        'instrument': '#e67e22',      # Orange
        'vocal_style': '#e74c3c',     # Red
        'theme': '#2ecc71',           # Green
        'regional': '#f39c12',        # Yellow-orange
        'era': '#34495e',            # Dark gray
        'other': '#95a5a6'           # Light gray
    }
    
    def __init__(self, tag_name, category=None, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.category = category
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Tag label
        self.label = QLabel(self.tag_name)
        self.label.setFont(QFont("Arial", 9))
        
        # Category-based styling
        color = self.CATEGORY_COLORS.get(self.category, self.CATEGORY_COLORS['other'])
        style = f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                border: 1px solid {color};
            }}
        """
        self.label.setStyleSheet(style)
        layout.addWidget(self.label)
        
        # Remove button
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(16, 16)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.3);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.remove_btn.clicked.connect(self.request_remove)
        layout.addWidget(self.remove_btn)
        
        self.setToolTip(f"Tag: {self.tag_name}\nCategory: {self.category or 'Unknown'}")
        
    def request_remove(self):
        self.removeRequested.emit(self.tag_name)


class FlowLayout(QHBoxLayout):
    """A layout that flows items to new lines when they don't fit."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSpacing(5)


class EnhancedTagInput(QWidget):
    """Smart tag input with auto-completion, categorization, and validation."""
    
    tagsChanged = pyqtSignal(list)  # List of current tags
    tagAdded = pyqtSignal(str, str)  # Tag name, category
    tagRemoved = pyqtSignal(str)     # Tag name
    
    def __init__(self, enhanced_consolidator=None, parent=None):
        super().__init__(parent)
        self.enhanced_consolidator = enhanced_consolidator
        self.current_tags = []
        self.tag_chips = {}  # tag_name -> TagChip widget
        self.suggestion_cache = {}
        
        self.setup_ui()
        self.setup_completer()
        self.setup_validation_timer()
        
    def setup_ui(self):
        """Setup the main UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Header with instructions
        header_layout = QHBoxLayout()
        
        self.instruction_label = QLabel("Enter tags (comma or Enter to add):")
        self.instruction_label.setFont(QFont("Arial", 9))
        header_layout.addWidget(self.instruction_label)
        
        header_layout.addStretch()
        
        # Category filter for suggestions
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        if self.enhanced_consolidator:
            from ...tags.analysis.enhanced_tag_consolidator import TagCategory
            for category in TagCategory:
                self.category_filter.addItem(category.value.title())
        self.category_filter.currentTextChanged.connect(self.update_suggestions)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.category_filter)
        
        main_layout.addLayout(header_layout)
        
        # Input line with smart features
        input_layout = QHBoxLayout()
        
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Type tag name...")
        self.tag_input.returnPressed.connect(self.add_current_tag)
        self.tag_input.textChanged.connect(self.on_text_changed)
        input_layout.addWidget(self.tag_input)
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_current_tag)
        input_layout.addWidget(self.add_button)
        
        main_layout.addLayout(input_layout)
        
        # Validation and suggestion display
        self.validation_label = QLabel("")
        self.validation_label.setFont(QFont("Arial", 8))
        self.validation_label.setWordWrap(True)
        main_layout.addWidget(self.validation_label)
        
        # Current tags display area
        tags_frame = QFrame()
        tags_frame.setFrameStyle(QFrame.Shape.Box)
        tags_frame.setMinimumHeight(60)
        tags_frame.setMaximumHeight(120)
        
        # Use scroll area for many tags
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidget(tags_frame)
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.tags_container = QWidget()
        self.tags_layout = FlowLayout(self.tags_container)
        
        tags_frame_layout = QVBoxLayout(tags_frame)
        tags_frame_layout.addWidget(self.tags_container)
        tags_frame_layout.addStretch()
        
        main_layout.addWidget(self.tags_scroll)
        
        # Quick action buttons
        action_layout = QHBoxLayout()
        
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self.clear_all_tags)
        action_layout.addWidget(self.clear_all_button)
        
        self.suggest_button = QPushButton("Get Suggestions")
        self.suggest_button.clicked.connect(self.show_smart_suggestions)
        action_layout.addWidget(self.suggest_button)
        
        action_layout.addStretch()
        
        self.tag_count_label = QLabel("Tags: 0")
        self.tag_count_label.setFont(QFont("Arial", 8))
        action_layout.addWidget(self.tag_count_label)
        
        main_layout.addLayout(action_layout)
        
    def setup_completer(self):
        """Setup auto-completion based on enhanced consolidator data."""
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.activated.connect(self.on_completion_selected)
        
        self.tag_input.setCompleter(self.completer)
        
        self.update_completer_data()
        
    def update_completer_data(self):
        """Update the completer with current enhanced data."""
        if not self.enhanced_consolidator:
            return
            
        try:
            # Get all tags from enhanced analysis
            enhanced_analysis = self.enhanced_consolidator.analyzer.get_consolidated_analysis()
            categorized = enhanced_analysis.get('categorized', {})
            
            all_tags = []
            for category, tags in categorized.items():
                all_tags.extend(tags.keys())
            
            # Create string model for completer
            model = QStringListModel(sorted(set(all_tags)))
            self.completer.setModel(model)
            
        except Exception as e:
            # Fallback to basic tag data
            basic_tags = list(self.enhanced_consolidator.analyzer.tag_frequencies.keys())
            model = QStringListModel(sorted(basic_tags))
            self.completer.setModel(model)
    
    def setup_validation_timer(self):
        """Setup timer for real-time validation."""
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate_current_input)
        
    def on_text_changed(self, text):
        """Handle text changes in the input field."""
        # Handle comma-separated input
        if ',' in text:
            parts = text.split(',')
            if len(parts) > 1:
                # Add all complete parts
                for part in parts[:-1]:
                    tag = part.strip()
                    if tag and tag not in self.current_tags:
                        self.add_tag(tag)
                
                # Keep the last part in input
                self.tag_input.setText(parts[-1].strip())
                return
        
        # Start validation timer
        self.validation_timer.start(500)  # 500ms delay
        
    def validate_current_input(self):
        """Validate the current input and show suggestions."""
        text = self.tag_input.text().strip()
        if not text:
            self.validation_label.setText("")
            return
            
        if not self.enhanced_consolidator:
            self.validation_label.setText("Enhanced features not available")
            return
            
        try:
            # Check if tag exists in consolidated data
            enhanced_analysis = self.enhanced_consolidator.analyzer.get_consolidated_analysis()
            categorized = enhanced_analysis.get('categorized', {})
            
            # Find exact matches
            exact_match = None
            category_match = None
            
            for category, tags in categorized.items():
                if text.lower() in [tag.lower() for tag in tags.keys()]:
                    exact_match = text
                    category_match = category
                    break
            
            if exact_match:
                self.validation_label.setText(
                    f"✓ Valid tag: '{exact_match}' (Category: {category_match.value.title()})"
                )
                self.validation_label.setStyleSheet("color: green;")
            else:
                # Look for similar tags
                suggestions = self.find_similar_tags(text)
                if suggestions:
                    suggestion_text = "Suggestions: " + ", ".join(suggestions[:3])
                    self.validation_label.setText(f"⚠ Tag not found. {suggestion_text}")
                    self.validation_label.setStyleSheet("color: orange;")
                else:
                    self.validation_label.setText(f"⚠ New tag: '{text}' will be added as-is")
                    self.validation_label.setStyleSheet("color: blue;")
                    
        except Exception as e:
            self.validation_label.setText("Validation error")
            self.validation_label.setStyleSheet("color: red;")
    
    def find_similar_tags(self, input_tag):
        """Find similar tags using enhanced consolidator."""
        if not self.enhanced_consolidator:
            return []
            
        try:
            # Use the tag similarity system
            similar = self.enhanced_consolidator.analyzer.find_similar_tags(input_tag, threshold=0.3)
            return [tag for tag, _ in similar[:5]]
        except:
            return []
    
    def on_completion_selected(self, text):
        """Handle selection from auto-completion."""
        self.add_tag(text)
        self.tag_input.clear()
        
    def add_current_tag(self):
        """Add the current input as a tag."""
        text = self.tag_input.text().strip()
        if text:
            self.add_tag(text)
            self.tag_input.clear()
            
    def add_tag(self, tag_name):
        """Add a tag with category detection."""
        if not tag_name or tag_name in self.current_tags:
            return
            
        # Detect category if enhanced consolidator available
        category = None
        if self.enhanced_consolidator:
            try:
                enhanced_analysis = self.enhanced_consolidator.analyzer.get_consolidated_analysis()
                categorized = enhanced_analysis.get('categorized', {})
                
                for cat, tags in categorized.items():
                    if tag_name.lower() in [t.lower() for t in tags.keys()]:
                        category = cat.value
                        break
            except:
                category = 'other'
        
        # Create tag chip
        chip = TagChip(tag_name, category, self)
        chip.removeRequested.connect(self.remove_tag)
        
        # Add to layout and tracking
        self.tags_layout.addWidget(chip)
        self.tag_chips[tag_name] = chip
        self.current_tags.append(tag_name)
        
        # Update display
        self.update_tag_count()
        self.validation_label.setText("")
        
        # Emit signals
        self.tagAdded.emit(tag_name, category or 'unknown')
        self.tagsChanged.emit(self.current_tags.copy())
        
    def remove_tag(self, tag_name):
        """Remove a tag."""
        if tag_name not in self.current_tags:
            return
            
        # Remove from tracking
        self.current_tags.remove(tag_name)
        
        # Remove chip widget
        if tag_name in self.tag_chips:
            chip = self.tag_chips[tag_name]
            self.tags_layout.removeWidget(chip)
            chip.deleteLater()
            del self.tag_chips[tag_name]
        
        # Update display
        self.update_tag_count()
        
        # Emit signals
        self.tagRemoved.emit(tag_name)
        self.tagsChanged.emit(self.current_tags.copy())
        
    def clear_all_tags(self):
        """Clear all tags."""
        tags_to_remove = self.current_tags.copy()
        for tag in tags_to_remove:
            self.remove_tag(tag)
            
    def set_tags(self, tag_list):
        """Set the current tags programmatically."""
        self.clear_all_tags()
        for tag in tag_list:
            self.add_tag(tag)
            
    def get_tags(self):
        """Get the current list of tags."""
        return self.current_tags.copy()
        
    def update_tag_count(self):
        """Update the tag count display."""
        count = len(self.current_tags)
        self.tag_count_label.setText(f"Tags: {count}")
        
    def show_smart_suggestions(self):
        """Show smart tag suggestions based on current tags."""
        if not self.enhanced_consolidator or not self.current_tags:
            return
            
        try:
            # Get suggestions for missing tags based on current selection
            suggestions = self.get_smart_suggestions()
            
            if suggestions:
                suggestion_text = "Suggested tags: " + ", ".join(suggestions[:5])
                self.validation_label.setText(suggestion_text)
                self.validation_label.setStyleSheet("color: blue;")
            else:
                self.validation_label.setText("No additional suggestions available")
                self.validation_label.setStyleSheet("color: gray;")
                
        except Exception as e:
            self.validation_label.setText("Error getting suggestions")
            self.validation_label.setStyleSheet("color: red;")
    
    def get_smart_suggestions(self):
        """Get smart tag suggestions based on current tags and patterns."""
        if not self.enhanced_consolidator:
            return []
            
        suggestions = []
        
        try:
            # Get enhanced analysis
            enhanced_analysis = self.enhanced_consolidator.analyzer.get_consolidated_analysis()
            categorized = enhanced_analysis.get('categorized', {})
            hierarchies = enhanced_analysis.get('hierarchies', {})
            
            # Find related tags through hierarchies
            for current_tag in self.current_tags:
                # Look for parent-child relationships
                if current_tag in hierarchies:
                    for relation in hierarchies[current_tag]:
                        if relation.child not in self.current_tags:
                            suggestions.append(relation.child)
                
                # Look for similar tags in same category
                for category, tags in categorized.items():
                    if current_tag.lower() in [t.lower() for t in tags.keys()]:
                        # Suggest other tags from same category
                        for tag in tags.keys():
                            if tag not in self.current_tags and tag.lower() != current_tag.lower():
                                suggestions.append(tag)
                        break
            
            # Remove duplicates and limit
            suggestions = list(dict.fromkeys(suggestions))  # Preserves order
            return suggestions[:10]
            
        except:
            return []
    
    def update_suggestions(self, category_filter):
        """Update suggestions based on category filter."""
        self.update_completer_data()
        
    def set_enhanced_consolidator(self, consolidator):
        """Set the enhanced consolidator for smart features."""
        self.enhanced_consolidator = consolidator
        self.update_completer_data()
        
        # Update category filter
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        
        if consolidator:
            from ...tags.analysis.enhanced_tag_consolidator import TagCategory
            for category in TagCategory:
                self.category_filter.addItem(category.value.title())


class TagInputDialog(QWidget):
    """A dialog-style interface for tag input with enhanced features."""
    
    def __init__(self, initial_tags=None, enhanced_consolidator=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enhanced Tag Input")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Smart Tag Input with Auto-completion")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Enhanced tag input
        self.tag_input = EnhancedTagInput(enhanced_consolidator, self)
        layout.addWidget(self.tag_input)
        
        # Set initial tags
        if initial_tags:
            self.tag_input.set_tags(initial_tags)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def get_tags(self):
        """Get the final list of tags."""
        return self.tag_input.get_tags()
        
    def accept(self):
        """Accept and close."""
        self.close()
        
    def reject(self):
        """Cancel and close."""
        self.close() 