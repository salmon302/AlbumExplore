"""Main application window."""
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                          QComboBox, QStatusBar, QSplitter)
from PyQt6.QtCore import Qt, QSize
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.state import ViewType
from albumexplore.gui.graphics_debug import GraphicsDebugMonitor, init_graphics_debugging
from albumexplore.gui.gui_logging import gui_logger
from .views import create_view

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, session=None):
        super().__init__()
        self.setWindowTitle("Album Explorer")
        self.resize(QSize(1200, 800))
        
        # Initialize components
        self.debug_monitor = init_graphics_debugging(self)
        self.data_interface = DataInterface(session)
        self.view_manager = ViewManager(self.data_interface, self, self.debug_monitor)
        
        # Add recursion protection flag
        self._is_processing_selection = False
        
        # UI setup
        self._setup_ui()
        self._setup_connections()
        
        # Load initial data
        self.load_data()
        gui_logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Set up UI elements."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        
        # View selector
        self.view_selector = QComboBox()
        for view_type in ViewType:
            self.view_selector.addItem(view_type.value)
        controls_layout.addWidget(self.view_selector)
        controls_layout.addStretch()
        
        layout.addWidget(controls)
        
        # Main content area
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # View container
        self.view_container = QWidget()
        self.view_layout = QVBoxLayout(self.view_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.content_splitter.addWidget(self.view_container)
        
        layout.addWidget(self.content_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initial view
        self.current_view = None
        self._switch_view(ViewType.TABLE)
    
    def _setup_connections(self):
        """Set up signal connections."""
        self.view_selector.currentTextChanged.connect(self._on_view_changed)
    
    def _on_view_changed(self, view_type_str: str):
        """Handle view type changes."""
        try:
            view_type = ViewType(view_type_str)
            self._switch_view(view_type)
            self.status_bar.showMessage(f"Switched to {view_type_str} view")
        except Exception as e:
            gui_logger.error(f"Error switching views: {str(e)}", exc_info=True)
            self.status_bar.showMessage(f"Error switching views: {str(e)}")
    
    def _switch_view(self, view_type: ViewType):
        """Switch to a different view."""
        # Clear old view
        if self.current_view:
            self.current_view.setParent(None)
        
        # Create new view
        self.current_view = create_view(view_type, self)
        
        # Add to layout
        self.view_layout.addWidget(self.current_view)
        
        # Connect selection handling
        self.current_view.selection_changed.connect(self._handle_selection)
        
        # Update view manager
        result = self.view_manager.switch_view(view_type)
        self.current_view.update_data(result)
    
    def __init__(self, session=None):
        super().__init__()
        self.setWindowTitle("Album Explorer")
        self.resize(QSize(1200, 800))
        
        # Initialize components
        self.debug_monitor = init_graphics_debugging(self)
        self.data_interface = DataInterface(session)
        self.view_manager = ViewManager(self.data_interface, self, self.debug_monitor)
        
        # Add recursion protection flag
        self._is_processing_selection = False
        
        # UI setup
        self._setup_ui()
        self._setup_connections()
        
        # Load initial data
        self.load_data()
        gui_logger.info("Main window initialized")

    def _handle_selection(self, selected_ids: set):
        """Handle selection changes."""
        # Use instance variable for recursion protection
        if self._is_processing_selection:
            return
            
        try:
            self._is_processing_selection = True
            result = self.view_manager.select_nodes(selected_ids)
            if self.current_view:
                self.current_view.update_data(result)
        finally:
            self._is_processing_selection = False
    
    def load_data(self):
        """Load/reload data."""
        try:
            result = self.view_manager.update_data()
            if self.current_view:
                self.current_view.update_data(result)
            self.status_bar.showMessage("Data loaded successfully")
        except Exception as e:
            gui_logger.error(f"Error loading data: {str(e)}", exc_info=True)
            self.status_bar.showMessage(f"Error loading data: {str(e)}")
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        if self.current_view:
            result = self.view_manager.update_dimensions(
                self.view_container.width(),
                self.view_container.height()
            )
            self.current_view.update_data(result)
    
    def closeEvent(self, event):
        """Handle window close."""
        self.view_manager.cleanup()
        super().closeEvent(event)