"""Main GUI application module."""
import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow
from albumexplore.database import init_db, get_session
from albumexplore.database.db_utils import log_update
from albumexplore.gui.views import NetworkViewWidget
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import gui_logger

class AlbumExplorer(QMainWindow):
    """Main application window."""
    
    def __init__(self, parent=None):
        """Initialize the application window."""
        super().__init__(parent)
        self.setWindowTitle("Album Explorer")
        self.setMinimumSize(1200, 800)
        
        # Initialize database
        try:
            init_db()
            self.session = get_session()
            self.data_interface = DataInterface(self.session)
            self.view_manager = ViewManager(self.data_interface, parent=self)
            
            # Set up main network view
            self.network_view = NetworkViewWidget(self)
            self.setCentralWidget(self.network_view)
            
            # Load initial data
            self.view_manager.switch_view(ViewType.NETWORK)
            self.view_manager.update_data()
            
            gui_logger.info("Album Explorer initialized successfully")
            
        except Exception as e:
            gui_logger.error(f"Failed to initialize Album Explorer: {e}")
            raise

def main():
    """Run the GUI application."""
    try:
        gui_logger.info("[main] Creating QApplication...")
        app = QApplication(sys.argv)
        gui_logger.info("[main] QApplication created.")

        gui_logger.info("[main] Creating AlbumExplorer window...")
        window = AlbumExplorer() # This logs "Album Explorer initialized successfully" from its __init__
        gui_logger.info("[main] AlbumExplorer window created.") # This log will be new, after __init__ completes

        gui_logger.info("[main] Calling window.show()...")
        window.show()
        gui_logger.info("[main] window.show() called.")

        gui_logger.info("[main] Calling app.exec()...")
        exit_code = app.exec()
        gui_logger.info(f"[main] app.exec() returned with exit code: {exit_code}")
        return exit_code

    except Exception as e:
        gui_logger.error(f"[main] Error starting GUI: {str(e)}", exc_info=True)
        return 1 # Ensure non-zero exit code for errors in main

if __name__ == "__main__":
    effective_exit_code = main()
    
    # Using print for this final message as logging might be shut down
    # or if the issue is with logging itself.
    print(f"[app.py __main__] Script completing. main() returned: {effective_exit_code}. Exiting with sys.exit({effective_exit_code}).", flush=True)
    sys.exit(effective_exit_code)
