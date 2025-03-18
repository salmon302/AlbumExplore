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
        # Create application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = AlbumExplorer()
        window.show()
        
        return app.exec()
        
    except Exception as e:
        gui_logger.error(f"Error starting GUI: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
