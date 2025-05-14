"""Main GUI application module."""
import sys
import logging
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication, QStackedWidget
from PyQt6.QtGui import QAction # Added QAction
from .views.network_view import NetworkView
from .views.table_view import TableView
from albumexplore.visualization.views.tag_explorer_view import TagExplorerView # Corrected import
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger # Changed from gui_logger to graphics_logger
from albumexplore.database import init_db, get_session # Added imports
from albumexplore.visualization.data_interface import DataInterface # Added import

class AlbumExplorer(QMainWindow):
    """Main application window."""
    
    def __init__(self, parent=None):
        """Initialize the application window."""
        super().__init__(parent)
        self.setWindowTitle("Album Explorer - Attempting Data Load") # Updated title
        self.setMinimumSize(1200, 800)
        
        try:
            init_db()
            self.session = get_session()
            self.data_interface = DataInterface(self.session)
            self.view_manager = ViewManager(self.data_interface, parent=self)
            
            # Initialize views
            self.network_view = NetworkView()
            self.table_view = TableView()
            self.tag_explorer_view = TagExplorerView()

            # Setup Menu Bar for view switching
            self._setup_menu_bar()

            # Connect view_manager signals
            self.view_manager.view_changed.connect(self._update_active_view)

            # Create a stacked widget to hold different views
            self.stacked_widget = QStackedWidget()
            self.stacked_widget.addWidget(self.network_view)
            self.stacked_widget.addWidget(self.table_view)
            self.stacked_widget.addWidget(self.tag_explorer_view) # Add TagExplorerView to stack

            # Set the central widget
            self.setCentralWidget(self.stacked_widget)

            # Initial view setup - this will trigger _update_active_view via signal
            graphics_logger.info("[AlbumExplorer.__init__] Calling self.view_manager.switch_view(ViewType.TABLE)")
            self.view_manager.switch_view(ViewType.TABLE) 
            
            # Data loading and view update are now handled by _update_active_view
            # Remove previous direct calls to self.network_view.update_data here

            graphics_logger.info("Album Explorer initialized. Initial view switch initiated.")
            
        except Exception as e:
            graphics_logger.error(f"Failed to initialize Album Explorer (Data Load stage): {e}", exc_info=True) 
            raise

    def _setup_menu_bar(self):
        """Sets up the main menu bar with view switching actions."""
        menu_bar = self.menuBar()
        view_menu = menu_bar.addMenu("&View")

        table_action = QAction("&Table View", self)
        table_action.triggered.connect(lambda: self._handle_view_switch(ViewType.TABLE))
        view_menu.addAction(table_action)

        network_action = QAction("&Network View", self)
        network_action.triggered.connect(lambda: self._handle_view_switch(ViewType.NETWORK))
        view_menu.addAction(network_action)

        tag_explorer_action = QAction("&Tag Explorer View", self)
        tag_explorer_action.triggered.connect(lambda: self._handle_view_switch(ViewType.TAG_EXPLORER))
        view_menu.addAction(tag_explorer_action)

    def _handle_view_switch(self, view_type: ViewType):
        """Switches the current view in the ViewManager."""
        graphics_logger.info(f"[AlbumExplorer._handle_view_switch] Switching to {view_type.value}")
        self.view_manager.switch_view(view_type)
        # _update_active_view will be called via the view_changed signal from ViewManager

    def _update_active_view(self):
        """Updates the currently displayed view based on ViewManager's state."""
        graphics_logger.info("AlbumExplorer: Updating active view")
        current_view_type = self.view_manager.current_view_type
        render_data = self.view_manager.get_render_data() # Get current render data

        if not render_data:
            graphics_logger.warning("AlbumExplorer: No render data available from get_render_data(). Attempting to force render.")
            # Attempt to render if data is missing, might be initial call
            render_data = self.view_manager._render_view() # Call internal method as a fallback
            if not render_data:
                graphics_logger.error("AlbumExplorer: Still no render data after explicit _render_view call.")
                return
            else:
                graphics_logger.info("AlbumExplorer: Successfully fetched render_data via _render_view fallback.")

        if current_view_type == ViewType.TABLE:
            graphics_logger.info(f"AlbumExplorer: Setting TableView. Data type: {render_data.get('type')}")
            self.table_view.update_data(render_data)
            self.stacked_widget.setCurrentWidget(self.table_view)
        elif current_view_type == ViewType.NETWORK:
            graphics_logger.info(f"AlbumExplorer: Setting NetworkView. Data type: {render_data.get('type')}")
            self.network_view.update_data(render_data)
            self.stacked_widget.setCurrentWidget(self.network_view)
        elif current_view_type == ViewType.TAG_EXPLORER: # Added condition for TagExplorerView
            graphics_logger.info(f"AlbumExplorer: Setting TagExplorerView. Data type: {render_data.get('type')}")
            nodes = render_data.get('nodes', [])
            edges = render_data.get('edges', []) # edges might not be directly used by TagExplorerView but good to pass if available
            self.tag_explorer_view.update_data(nodes, edges)
            self.stacked_widget.setCurrentWidget(self.tag_explorer_view)
        else:
            graphics_logger.warning(f"AlbumExplorer: Unknown view type {current_view_type}")
        
        # Ensure the window is shown and brought to front - REMOVED, handled by main()

    def init_data_and_views(self): # This method seems to be called from main after window.show()
        """Load initial data and trigger the first view update."""
        graphics_logger.info("[AlbumExplorer.init_data_and_views] Called.")
        # Ensure data is loaded by ViewManager if it wasn't already by switch_view
        # The _update_active_view method will fetch the latest render data.
        # self.view_manager.update_data() # This might be redundant if switch_view already prepared data
        self._update_active_view() # This will set the correct widget and update its data
        
        graphics_logger.info("[AlbumExplorer.init_data_and_views] Initial view update triggered.")

def main():
    """Run the GUI application."""
    try:
        graphics_logger.info("[main] Creating QApplication...") # Changed to graphics_logger
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        graphics_logger.info("[main] QApplication created.") # Changed to graphics_logger

        graphics_logger.info("[main] Creating AlbumExplorer window...") # Changed to graphics_logger
        window = AlbumExplorer()
        graphics_logger.info("[main] AlbumExplorer window created.") # Changed to graphics_logger

        # Call init_data_and_views after the window is created but before it's shown,
        # or rely on __init__ to set up the initial view.
        # For now, __init__ calls switch_view which triggers _update_active_view.
        # If init_data_and_views is meant to be the primary data loading point,
        # then the call in __init__ might need adjustment.
        # window.init_data_and_views() # Let's see if __init__ handles it first.

        graphics_logger.info("[main] Calling window.show()...") # Changed to graphics_logger
        window.show() # This should now show the view set by _update_active_view
        graphics_logger.info("[main] window.show() called.") # Changed to graphics_logger
        
        # If init_data_and_views is essential for a post-show update or delayed load:
        # window.init_data_and_views() 

        graphics_logger.info("[main] Calling app.exec()...") # Changed to graphics_logger
        exit_code = app.exec()
        graphics_logger.info(f"[main] app.exec() returned with exit code: {exit_code}") # Changed to graphics_logger
        return exit_code

    except Exception as e:
        graphics_logger.error(f"[main] Error starting GUI: {str(e)}", exc_info=True) # Changed to graphics_logger
        return 1

if __name__ == "__main__":
    effective_exit_code = main()
    
    # Using print for this final message as logging might be shut down
    # or if the issue is with logging itself.
    print(f"[app.py __main__] Script completing. main() returned: {effective_exit_code}. Exiting with sys.exit({effective_exit_code}).", flush=True)
    sys.exit(effective_exit_code)
