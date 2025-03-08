import logging
from typing import Optional, Dict, Any
from albumexplore.gui.gui_logging import gui_logger
from .graphics_debug import init_graphics_debugging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QComboBox, QStatusBar, QSizePolicy, QFrame,
                           QDockWidget)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPalette, QColor, QResizeEvent
from albumexplore.database import get_session
from albumexplore.visualization.views import create_view
from albumexplore.visualization.state import ViewType, ViewState
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.error_handling import ErrorManager, ErrorCategory, ErrorContext
from albumexplore.visualization.responsive import ResponsiveManager
from albumexplore.visualization.view_manager import ViewManager

class MainWindow(QMainWindow):
    def __init__(self, db_session):
        super().__init__()
        gui_logger.debug("MainWindow initialized")
        
        # Store database session
        self._db_session = db_session
        
        # Initialize graphics debugging
        self.graphics_debug = init_graphics_debugging(self)
        
        # Initialize managers
        self.error_manager = ErrorManager()
        self.responsive_manager = ResponsiveManager()
        
        # Basic window setup
        self.setWindowTitle("Album Explorer")
        self.setMinimumSize(1200, 800)
        
        # Create central widget as a container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout for central widget
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create and setup the visualization container first
        self._setup_visualization_container()
        
        # Initialize data interface and view manager
        self.data_interface = DataInterface(self._db_session)
        self.view_manager = ViewManager(
            self.data_interface,
            self.visualization_container,
            graphics_debug=self.graphics_debug
        )
        
        # Create view controls
        self._create_view_controls()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Setup error handling and responsive design
        self._setup_error_handling()
        self._setup_responsive_design()
        
        # Initialize the application AFTER all setup is complete
        QTimer.singleShot(0, self._initialize_application)
    
    def _setup_visualization_container(self):
        """Setup the visualization container and layout."""
        # Create main visualization container
        self.visualization_container = QFrame()
        self.visualization_container.setObjectName("visualizationContainer")
        self.visualization_container.setFrameStyle(QFrame.Shape.StyledPanel)
        self.visualization_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        self.visualization_container.setMinimumSize(800, 600)
        
        # Create layout for visualization container
        self.view_layout = QVBoxLayout(self.visualization_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)
        
        # Add visualization container to main layout
        self.main_layout.addWidget(self.visualization_container, stretch=1)
        
        # Force immediate layout update
        self.visualization_container.updateGeometry()
        
        gui_logger.debug("Visualization container setup complete")
    
    def _initialize_application(self):
        """Initialize application data and view."""
        try:
            gui_logger.debug("Starting application initialization")
            
            # Log initial widget hierarchy
            self._log_widget_hierarchy()
            
            # Update data first
            gui_logger.debug("Loading initial data")
            self.view_manager.update_data()
            gui_logger.info(f"Loaded {len(self.view_manager.nodes)} nodes")
            
            # Switch to initial view
            gui_logger.debug("Switching to initial view")
            result = self.view_manager.switch_view(ViewType.TABLE)
            if not result["success"]:
                raise RuntimeError(f"Failed to initialize view: {result['message']}")
                
            if self.view_manager.current_view:
                # Force immediate geometry update for table
                self.view_manager.current_view.setGeometry(self.visualization_container.rect())
                if hasattr(self.view_manager.current_view, 'table'):
                    self.view_manager.current_view.table.setGeometry(
                        self.view_manager.current_view.rect()
                    )
                    self.view_manager.current_view.table.show()
                    self.view_manager.current_view.table.raise_()
            
            # Log final widget hierarchy
            self._log_widget_hierarchy()
            
            # Show success message
            self.status_bar.showMessage("Application initialized successfully")
            gui_logger.debug("Application initialization complete")
            
            # Ensure window is active and visible
            self.show()
            self.raise_()
            self.activateWindow()
            
        except Exception as e:
            gui_logger.error(f"Error during initialization: {str(e)}", exc_info=True)
            self.status_bar.showMessage(f"Error during initialization: {str(e)}")
            self.error_manager.handle_error(e, ErrorContext(
                view_type="initialization",
                operation="application_init",
                data={}
            ))
    
    def _log_widget_hierarchy(self):
        """Log the complete widget hierarchy for debugging."""
        def _log_widget(widget, level=0):
            indent = "  " * level
            gui_logger.debug(f"{indent}{widget.__class__.__name__}: {widget.objectName()}")
            if hasattr(widget, 'children'):
                for child in widget.children():
                    _log_widget(child, level + 1)
        
        gui_logger.debug("Widget hierarchy:")
        _log_widget(self)
    
    def _handle_view_change(self, view_type_str: str):
        """Handle view type changes."""
        try:
            view_type = ViewType(view_type_str)
            result = self.view_manager.switch_view(view_type)
            
            if not result["success"]:
                self.error_manager.handle_error(
                    Exception(result["message"]),
                    ErrorContext(
                        view_type=view_type_str,
                        operation="view_change",
                        data={"previous_view": str(self.view_manager.previous_view_type)}
                    )
                )
                self.status_bar.showMessage(f"Error changing view: {result['message']}")
            else:
                self.status_bar.showMessage(f"Switched to {view_type_str} view")
                
        except Exception as e:
            gui_logger.error(f"Error changing view: {str(e)}", exc_info=True)
            self.error_manager.handle_error(e, ErrorContext(
                view_type=view_type_str,
                operation="view_change",
                data={}
            ))
    
    def _setup_error_handling(self):
        """Setup error handlers for the main window."""
        def handle_view_error(error: Exception, context: ErrorContext):
            gui_logger.error(f"View error: {str(error)}", exc_info=True)
            self.status_bar.showMessage(f"Error in {context.view_type} view: {str(error)}")
        
        def handle_data_error(error: Exception, context: ErrorContext):
            gui_logger.error(f"Data error: {str(error)}", exc_info=True)
            self.status_bar.showMessage(f"Data error: {str(error)}")
        
        # Register error handlers using existing categories
        self.error_manager.register_handler(ErrorCategory.RENDERING, handle_view_error)
        self.error_manager.register_handler(ErrorCategory.DATA, handle_data_error)
    
    def _setup_responsive_design(self):
        """Setup responsive design handlers."""
        def handle_resize(event: QResizeEvent):
            new_size = event.size()
            gui_logger.debug(f"Window resized to {new_size.width()}x{new_size.height()}")
            
            # Update responsive manager with new screen dimensions
            if hasattr(self, 'responsive_manager'):
                self.responsive_manager.update_screen_size(new_size.width(), new_size.height())
            
            # Update visualization container
            if self.visualization_container:
                self.visualization_container.setGeometry(0, 0, new_size.width(), new_size.height())
            
            # Update current view
            if self.view_manager and self.view_manager.current_view:
                self.view_manager.current_view.resize(new_size)
            
            # Accept the resize event
            event.accept()
        
        # Set the resize event handler directly
        self.resizeEvent = handle_resize
    
    def _create_view_controls(self):
        """Create view selection and control widgets."""
        # Create view controls container
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        # Add view type selector
        view_label = QLabel("View Type:")
        self.view_selector = QComboBox()
        self.view_selector.addItems([vt.value for vt in ViewType])
        self.view_selector.currentTextChanged.connect(self._handle_view_change)
        
        controls_layout.addWidget(view_label)
        controls_layout.addWidget(self.view_selector)
        controls_layout.addStretch()
        
        # Add controls above visualization container
        self.main_layout.insertWidget(0, controls_container)
        gui_logger.debug("View controls setup complete")
    
    def closeEvent(self, event):
        """Handle application shutdown."""
        try:
            # Close database session
            if self._db_session:
                self._db_session.close()
            
            # Clean up view manager
            if hasattr(self, 'view_manager'):
                self.view_manager.cleanup()
            
            gui_logger.info("Application shutdown complete")
            event.accept()
            
        except Exception as e:
            gui_logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
            event.accept()  # Accept anyway to ensure application closes