"""
Demo application for the Tag Filter Panel UI.

This demonstrates the new tag filter UI without requiring the full AlbumExplore app.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QSplitter
from PyQt6.QtCore import Qt

from albumexplore.tags.filters import TagFilterState
from albumexplore.gui.widgets.tag_filter_panel import TagFilterPanel


class FilterDemoWindow(QMainWindow):
    """Demo window showing the tag filter panel."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tag Filter Panel Demo")
        self.setMinimumSize(900, 700)
        
        # Create sample data
        self.available_tags = [
            "Progressive Metal",
            "Death Metal",
            "Black Metal",
            "Heavy Metal",
            "Thrash Metal",
            "Jazz",
            "Fusion",
            "Jazz Fusion",
            "Experimental",
            "Instrumental",
            "Female Vocals",
            "Male Vocals",
            "Clean Vocals",
            "Harsh Vocals",
            "Technical",
            "Atmospheric",
            "Symphonic",
            "Epic",
            "Live",
            "Compilation",
            "Acoustic",
            "Electronic",
            "Ambient",
            "Post-Rock",
            "Math Rock",
        ]
        
        # Sample albums for testing
        self.sample_albums = [
            {"name": "Dream Theater - Images and Words", "tags": {"Progressive Metal", "Technical", "Male Vocals"}},
            {"name": "Opeth - Blackwater Park", "tags": {"Progressive Metal", "Death Metal", "Atmospheric"}},
            {"name": "Animals as Leaders - Joy of Motion", "tags": {"Progressive Metal", "Instrumental", "Technical"}},
            {"name": "Nightwish - Once", "tags": {"Symphonic", "Metal", "Female Vocals", "Epic"}},
            {"name": "Tigran Hamasyan - Mockroot", "tags": {"Jazz", "Fusion", "Experimental", "Instrumental"}},
            {"name": "Meshuggah - ObZen", "tags": {"Progressive Metal", "Technical", "Harsh Vocals"}},
            {"name": "Metallica - Master of Puppets", "tags": {"Thrash Metal", "Heavy Metal", "Male Vocals"}},
            {"name": "Death - The Sound of Perseverance", "tags": {"Death Metal", "Technical", "Progressive"}},
            {"name": "Weather Report - Heavy Weather", "tags": {"Jazz", "Fusion", "Instrumental"}},
            {"name": "Tool - Lateralus", "tags": {"Progressive Metal", "Atmospheric", "Male Vocals"}},
            {"name": "Metallica - Live Shit", "tags": {"Thrash Metal", "Live", "Male Vocals"}},
            {"name": "Various Artists - Metal Compilation", "tags": {"Metal", "Compilation"}},
        ]
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Filter panel
        self.filter_panel = TagFilterPanel(available_tags=self.available_tags)
        self.filter_panel.filtersChanged.connect(self._on_filters_changed)
        splitter.addWidget(self.filter_panel)
        
        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("Filtered albums will appear here...")
        splitter.addWidget(self.results_display)
        
        # Set initial splitter sizes
        splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter)
        
        # Initial filter update
        self._on_filters_changed()
    
    def _on_filters_changed(self):
        """Handle filter changes - update results display."""
        filter_state = self.filter_panel.get_filter_state()
        
        # Filter albums
        matching_albums = []
        for album in self.sample_albums:
            if filter_state.matches(album["tags"]):
                matching_albums.append(album)
        
        # Update results count
        self.filter_panel.set_results_count(len(matching_albums))
        
        # Display results
        if not matching_albums:
            if filter_state.is_empty():
                text = "<h3>No filters active - showing all albums</h3>"
                for album in self.sample_albums:
                    tags_str = ", ".join(sorted(album["tags"]))
                    text += f"<p><b>{album['name']}</b><br><i>Tags: {tags_str}</i></p>"
            else:
                text = "<h3>No albums match the current filters</h3>"
                text += "<p>Try adjusting your filter criteria.</p>"
        else:
            text = f"<h3>Found {len(matching_albums)} matching album(s)</h3>"
            for album in matching_albums:
                tags_str = ", ".join(sorted(album["tags"]))
                text += f"<p><b>{album['name']}</b><br><i>Tags: {tags_str}</i></p>"
        
        self.results_display.setHtml(text)


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = FilterDemoWindow()
    window.show()
    
    # Add some example filters to start
    filter_state = window.filter_panel.get_filter_state()
    
    # Example: Progressive Metal AND Instrumental
    group1 = filter_state.add_group()
    group1.name = "Prog Instrumentals"
    window.filter_panel._add_group_widget(group1)
    window.filter_panel.add_tag_to_group("Progressive Metal", group1.group_id)
    window.filter_panel.add_tag_to_group("Instrumental", group1.group_id)
    
    # Example exclusion
    window.filter_panel.add_exclusion("Live")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
