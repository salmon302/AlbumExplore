"""Album header widget for displaying selected album details."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from albumexplore.database.models import Album


class AlbumHeaderWidget(QWidget):
    """Widget to display details of the currently selected/focused album."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Create a frame for better visual separation
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        
        # Album cover placeholder (for future implementation)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(80, 80)
        self.cover_label.setStyleSheet("background-color: #444; border: 1px solid #666;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setText("♫")
        font = self.cover_label.font()
        font.setPointSize(24)
        self.cover_label.setFont(font)
        frame_layout.addWidget(self.cover_label)
        
        # Album details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(5)
        
        # Title label
        self.title_label = QLabel("No album selected")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        details_layout.addWidget(self.title_label)
        
        # Metadata label (year, genre, country)
        self.metadata_label = QLabel("")
        metadata_font = QFont()
        metadata_font.setPointSize(10)
        self.metadata_label.setFont(metadata_font)
        self.metadata_label.setStyleSheet("color: #888;")
        details_layout.addWidget(self.metadata_label)
        
        # Tags label
        self.tags_label = QLabel("")
        tags_font = QFont()
        tags_font.setPointSize(9)
        self.tags_label.setFont(tags_font)
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("color: #666;")
        details_layout.addWidget(self.tags_label)
        
        details_layout.addStretch()
        frame_layout.addLayout(details_layout, 1)
        
        layout.addWidget(frame)
        
    def set_album(self, album: Album):
        """Update the widget to display the given album."""
        if not album:
            self.title_label.setText("No album selected")
            self.metadata_label.setText("")
            self.tags_label.setText("")
            return
        
        # Set title (artist - album)
        artist_name = album.pa_artist_name_on_album or "Unknown Artist"
        title = f"{artist_name} - {album.title}"
        self.title_label.setText(title)
        
        # Set metadata
        metadata_parts = []
        if album.release_year:
            metadata_parts.append(str(album.release_year))
        if album.genre:
            metadata_parts.append(album.genre)
        if album.country:
            metadata_parts.append(album.country)
        
        metadata_text = " | ".join(metadata_parts) if metadata_parts else "No metadata"
        self.metadata_label.setText(metadata_text)
        
        # Set tags (limit to first 10 for display)
        if album.tags:
            tag_names = [tag.name for tag in album.tags[:10]]
            tags_text = "Tags: " + ", ".join(tag_names)
            if len(album.tags) > 10:
                tags_text += f" (+{len(album.tags) - 10} more)"
        else:
            tags_text = "Tags: None"
        
        self.tags_label.setText(tags_text)
    
    def clear(self):
        """Clear the album display."""
        self.set_album(None)
