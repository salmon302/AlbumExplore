"""Main GUI application."""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from albumexplore.database import init_db, get_session
from albumexplore.gui.main_window import MainWindow
from albumexplore.gui.gui_logging import gui_logger

class AlbumExplorer(MainWindow):
    """Main application window."""
    
    def __init__(self):
        # Get database session
        session = get_session()
        super().__init__(session)

def main():
    """Application entry point."""
    try:
        # Initialize application
        app = QApplication(sys.argv)
        
        # Initialize database
        init_db()
        
        # Create and show main window
        window = AlbumExplorer()
        window.show()
        
        gui_logger.info("Application started")
        return app.exec()
        
    except Exception as e:
        gui_logger.error(f"Error starting application: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
