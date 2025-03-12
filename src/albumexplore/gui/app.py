"""Main GUI application."""
from PyQt6.QtWidgets import QApplication
import sys
from albumexplore.database import init_db, get_session
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.gui.main_window import MainWindow

def main():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    
    # Initialize database and get session
    init_db()
    session = get_session()
    
    # Create data interface with session
    data_interface = DataInterface(session)
    
    # Create view manager with data interface
    view_manager = ViewManager(data_interface)
    
    # Create and show main window
    window = MainWindow(view_manager)
    window.show()
    
    # Run event loop
    result = app.exec()
    
    # Cleanup
    view_manager.cleanup()
    session.close()
    
    return result

if __name__ == '__main__':
    sys.exit(main())
