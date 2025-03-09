"""Tag cloud visualization widget."""
from collections import Counter
import math
import random

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath, QPainterPath, QMouseEvent


class CloudTag:
    """Represents a single tag in the cloud with position and rendering information."""
    
    def __init__(self, text, weight, x=0, y=0):
        self.text = text
        self.weight = weight  # Raw tag count
        self.size_factor = 0  # Calculated size factor (0-1)
        self.x = x
        self.y = y
        self.width = 0
        self.height = 0
        self.hovered = False
        self.color = QColor(0, 0, 0)
        self.filter_state = 0  # 0: neutral, 1: included, 2: excluded
        
    def contains(self, x, y):
        """Check if the point is inside this tag."""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
                
    def get_bounds(self):
        """Get tag bounding rectangle."""
        return QRectF(self.x, self.y, self.width, self.height)


class TagCloudWidget(QWidget):
    """Widget that displays tags in a cloud layout with size proportional to frequency."""
    
    # Signal emitted when a tag is clicked
    tagClicked = pyqtSignal(str)
    
    # Constants for rendering
    MIN_FONT_SIZE = 9
    MAX_FONT_SIZE = 24
    TAG_SPACING = 8
    ANIMATION_DURATION = 300
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMouseTracking(True)
        
        # Tag data
        self.tags = {}  # Maps tag text to CloudTag objects
        self.layout_valid = False
        self.hover_tag = None
        
        # Color scheme
        self.neutral_colors = [QColor(70, 130, 180), QColor(30, 144, 255), 
                              QColor(0, 119, 190), QColor(47, 79, 79),
                              QColor(25, 25, 112)]
        self.include_color = QColor(50, 170, 50)
        self.exclude_color = QColor(170, 50, 50)
        
    def update_tags(self, tag_counts):
        """Update the tag cloud with new tag data."""
        if not tag_counts:
            self.tags = {}
            self.layout_valid = False
            self.update()
            return
        
        # Find min and max counts for scaling
        max_count = max(tag_counts.values())
        min_count = min(tag_counts.values())
        count_range = max(1, max_count - min_count)
        
        # Create or update tag objects
        new_tags = {}
        for tag_text, count in tag_counts.items():
            # Calculate size factor (0-1 range)
            size_factor = (count - min_count) / count_range
            
            if tag_text in self.tags:
                # Update existing tag
                tag = self.tags[tag_text]
                tag.weight = count
                tag.size_factor = size_factor
            else:
                # Create new tag
                tag = CloudTag(tag_text, count)
                tag.size_factor = size_factor
                tag.color = random.choice(self.neutral_colors)
            
            new_tags[tag_text] = tag
        
        self.tags = new_tags
        self.layout_valid = False
        self.update()
        
    def update_filter_states(self, tag_filters):
        """Update the filter states of tags."""
        for tag_text, state in tag_filters.items():
            if tag_text in self.tags:
                self.tags[tag_text].filter_state = state
                
                # Update color based on filter state
                if state == 1:  # Include
                    self.tags[tag_text].color = self.include_color
                elif state == 2:  # Exclude
                    self.tags[tag_text].color = self.exclude_color
                else:  # Neutral
                    self.tags[tag_text].color = random.choice(self.neutral_colors)
        
        self.update()
    
    def resizeEvent(self, event):
        """Handle resize events by invalidating layout."""
        super().resizeEvent(event)
        self.layout_valid = False
        
    def paintEvent(self, event):
        """Paint the tag cloud."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        # Recompute layout if needed
        if not self.layout_valid:
            self._compute_layout()
            self.layout_valid = True
        
        # Paint each tag
        for tag in self.tags.values():
            self._paint_tag(painter, tag)
    
    def _compute_layout(self):
        """Compute tag positions using a spiral layout algorithm."""
        if not self.tags:
            return
            
        # Sort tags by weight for layout (highest weight first)
        sorted_tags = sorted(self.tags.values(), key=lambda t: t.weight, reverse=True)
        
        # Calculate font sizes and measure text
        for tag in sorted_tags:
            font_size = self.MIN_FONT_SIZE + tag.size_factor * (self.MAX_FONT_SIZE - self.MIN_FONT_SIZE)
            font = QFont()
            font.setPointSizeF(font_size)
            
            # Measure text with this font
            metrics = self.fontMetrics()
            tag.width = metrics.horizontalAdvance(tag.text) + self.TAG_SPACING * 2
            tag.height = metrics.height() + self.TAG_SPACING
        
        # Place tags using a spiral layout
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Start with the largest tag in the center
        sorted_tags[0].x = center_x - sorted_tags[0].width // 2
        sorted_tags[0].y = center_y - sorted_tags[0].height // 2
        
        # Place the rest using spiral layout
        angle = 0.0
        radius = 0.0
        step = 0.3  # Controls the spiral tightness
        
        for i in range(1, len(sorted_tags)):
            tag = sorted_tags[i]
            placed = False
            
            # Keep trying positions along the spiral until we find a non-overlapping one
            while not placed:
                # Calculate position on spiral
                x = center_x + radius * math.cos(angle) - tag.width // 2
                y = center_y + radius * math.sin(angle) - tag.height // 2
                
                # Check if this position overlaps with any placed tag
                if self._check_position(tag, x, y, sorted_tags[:i]):
                    tag.x = x
                    tag.y = y
                    placed = True
                else:
                    # Move to next position on spiral
                    angle += step
                    radius += step / (2 * math.pi)
    
    def _check_position(self, tag, x, y, placed_tags):
        """Check if the tag at position (x,y) overlaps with any placed tags."""
        # Ensure tag is within widget bounds
        if x < 0 or y < 0 or x + tag.width > self.width() or y + tag.height > self.height():
            return False
            
        # Check for overlap with other tags
        tag_rect = QRectF(x, y, tag.width, tag.height)
        for other_tag in placed_tags:
            other_rect = other_tag.get_bounds()
            if tag_rect.intersects(other_rect):
                return False
                
        return True
    
    def _paint_tag(self, painter, tag):
        """Paint a single tag."""
        # Set font size based on tag weight
        font_size = self.MIN_FONT_SIZE + tag.size_factor * (self.MAX_FONT_SIZE - self.MIN_FONT_SIZE)
        font = QFont()
        font.setPointSizeF(font_size)
        painter.setFont(font)
        
        # Determine color based on filter state
        if tag.filter_state == 1:  # Include
            color = self.include_color
        elif tag.filter_state == 2:  # Exclude
            color = self.exclude_color
        else:
            color = tag.color
        
        # Adjust for hover state
        if tag.hovered:
            color = color.lighter(120)
            font.setBold(True)
            painter.setFont(font)
            
        painter.setPen(QPen(color, 1.5 if tag.hovered else 1.0))
        
        # Draw text
        painter.drawText(
            tag.x + self.TAG_SPACING, 
            tag.y + tag.height - self.TAG_SPACING,
            tag.text
        )
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for hover effects."""
        # Reset hover state
        hover_changed = False
        if self.hover_tag:
            self.hover_tag.hovered = False
            hover_changed = True
            self.hover_tag = None
        
        # Check for new hover
        for tag in self.tags.values():
            if tag.contains(event.position().x(), event.position().y()):
                tag.hovered = True
                self.hover_tag = tag
                hover_changed = True
                # Change cursor to indicate clickable
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                break
        else:
            # Not hovering over any tag
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Update if hover state changed
        if hover_changed:
            self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press events to select tags."""
        if event.button() == Qt.MouseButton.LeftButton:
            for tag in self.tags.values():
                if tag.contains(event.position().x(), event.position().y()):
                    self.tagClicked.emit(tag.text)
                    break
                    
    def leaveEvent(self, event):
        """Handle mouse leave events to reset hover states."""
        hover_changed = False
        if self.hover_tag:
            self.hover_tag.hovered = False
            hover_changed = True
            self.hover_tag = None
            
        if hover_changed:
            self.update()
        
        super().leaveEvent(event)