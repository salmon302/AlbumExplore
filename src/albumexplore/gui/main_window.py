"""Main window for the GUI application."""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QStatusBar, QSplitter)
from PyQt6.QtCore import Qt
from albumexplore.gui.gui_logging import gui_logger
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.views import view_map

class MainWindow(QMainWindow):
    """Main window for the application."""
    
    def __init__(self, view_manager: ViewManager, parent=None):
        super().__init__(parent)
        self.view_manager = view_manager
        
        self.setWindowTitle('Album Explorer')
        self._setup_ui()
        gui_logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create visualization container
        self.viz_container = QWidget()
        self.viz_layout = QVBoxLayout(self.viz_container)
        self.viz_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.viz_container)
        
        # Create and add table view
        gui_logger.debug(f"Creating view for type: {ViewType.TABLE}")
        TableViewClass = view_map[ViewType.TABLE]
        self.table_view = TableViewClass()
        self.viz_layout.addWidget(self.table_view)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initial state
        self.resize(1350, 800)
        
        # Update data
        result = self.view_manager.update_data()
        if result:
            self.table_view.update_data(result)
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Update view manager with new dimensions
        result = self.view_manager.update_dimensions(
            self.viz_container.width(),
            self.viz_container.height()
        )
        if result:
            self.table_view.update_data(result)