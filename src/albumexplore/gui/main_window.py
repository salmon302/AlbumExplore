"""Main window for the GUI application."""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QStatusBar, QSplitter, QMenuBar)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from albumexplore.gui.gui_logging import gui_logger
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.views import view_map
from albumexplore.gui.lastfm_loader_dialog import LastFmLoaderDialog
from albumexplore.gui.data_loader_dialog import DataLoaderDialog

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
        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        # CSV Load action (keeps existing CSV loader)
        load_data_action = QAction("Load Data...", self)
        load_data_action.setShortcut("Ctrl+O")
        load_data_action.setStatusTip("Load album data from CSV/TSV files")
        load_data_action.triggered.connect(self._show_data_loader)
        file_menu.addAction(load_data_action)

        # Load Last.fm Data action
        load_lastfm_action = QAction("Load Last.fm Data...", self)
        load_lastfm_action.setStatusTip("Fetch metadata and album art from Last.fm")
        load_lastfm_action.triggered.connect(self._show_lastfm_loader)
        file_menu.addAction(load_lastfm_action)
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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
            
    def _show_lastfm_loader(self):
        """Show the Last.fm data loader dialog."""
        dialog = LastFmLoaderDialog(self)
        dialog.data_changed.connect(self._refresh_data)
        dialog.exec()

    def _show_data_loader(self):
        """Show the CSV/TSV data loader dialog."""
        dialog = DataLoaderDialog(self)
        dialog.data_loaded.connect(self._refresh_data)
        dialog.exec()
        
    def _refresh_data(self):
        """Refresh data in the view manager."""
        gui_logger.info("Refreshing data from database...")
        result = self.view_manager.update_data()
        if result:
            self.table_view.update_data(result)
            self.status_bar.showMessage("Data refreshed successfully", 5000)
    
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