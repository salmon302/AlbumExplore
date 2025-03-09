import sys
import logging
from PyQt6.QtWidgets import QApplication
from albumexplore.gui.main_window import MainWindow
from albumexplore.database import init_db, get_session

def main():
    try:
        # Initialize database
        init_db()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        
        # Create application
        app = QApplication(sys.argv)
        
        # Create and show window with database session
        session = get_session()
        window = MainWindow(session)
        window.show()
        
        return app.exec()
    except Exception as e:
        logging.error(f"Error starting GUI: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
