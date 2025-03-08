"""GUI application entry point."""
import sys
import logging
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from albumexplore.database import init_db, get_session
from albumexplore.database.models import Album
from albumexplore.database.csv_loader import load_csv_data
from albumexplore.gui.main_window import MainWindow
from albumexplore.visualization.error_handling import ErrorManager
from albumexplore.gui.gui_logging import (
    gui_logger, graphics_logger, performance_logger, db_logger,  
    setup_logging
)

def initialize_database():
    """Initialize and populate the database."""
    gui_logger.info("Initializing database")
    try:
        session, engine = init_db()
        
        # Check if database is empty
        with get_session() as db:
            album_count = db.query(Album).count()
            gui_logger.debug(f"Current album count: {album_count}")
            
            if album_count == 0:
                gui_logger.info("Database is empty, loading CSV data")
                # Find CSV directory relative to this file
                csv_dir = Path(__file__).parent.parent.parent.parent / 'csv'
                if csv_dir.exists() and any(csv_dir.glob('*.csv')):
                    gui_logger.info(f"Found CSV directory: {csv_dir}")
                    load_csv_data(csv_dir)
                    gui_logger.info("CSV data loaded successfully")
                else:
                    gui_logger.error(f"No CSV files found in directory: {csv_dir}")
            else:
                gui_logger.info(f"Database already contains {album_count} albums")
                
        return session
    except Exception as e:
        gui_logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise

def setup_error_handling(app: QApplication):
    """Setup global error handling."""
    error_manager = ErrorManager()
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        gui_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        error_manager.handle_error(exc_value, None)
    
    sys.excepthook = handle_exception
    return error_manager

def setup_high_dpi():
    """Configure high DPI support."""
    graphics_logger.info("Configuring high DPI support")
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        graphics_logger.debug("High DPI scaling enabled")
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        graphics_logger.debug("High DPI pixmaps enabled")

def setup_memory_monitoring(app: QApplication):
    """Setup memory monitoring and cleanup."""
    def check_memory_usage():
        performance_logger.debug("Performing memory check")
        app.processEvents()  # Process any pending events
    
    memory_check_timer = app.startTimer(30000)  # Check every 30 seconds
    app.timerEvent = lambda event: check_memory_usage() if event.timerId() == memory_check_timer else None
    return memory_check_timer

def cleanup_resources():
    """Perform thorough cleanup of application resources."""
    graphics_logger.info("Cleaning up application resources")

def main():
    """Run the GUI application."""
    start_time = time.time()
    
    # Initialize logging first
    setup_logging()
    gui_logger.info("Starting application")
    
    try:
        # Configure high DPI support before creating QApplication
        setup_high_dpi()
        
        # Create QApplication instance
        gui_logger.info("Creating QApplication instance")
        app = QApplication(sys.argv)
        app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
        
        # Setup error handling and monitoring
        error_manager = setup_error_handling(app)
        setup_memory_monitoring(app)
        
        # Initialize database and load data
        gui_logger.info("Initializing database connection")
        session = initialize_database()
        
        # Create main window
        gui_logger.info("Creating main window")
        window = MainWindow(session)
        
        # Get primary screen geometry
        primary_screen = QGuiApplication.primaryScreen()
        if primary_screen:
            screen_geometry = primary_screen.availableGeometry()
            window_geometry = window.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            window.move(window_geometry.topLeft())
        
        # Show and activate window
        window.show()
        window.raise_()
        window.activateWindow()
        
        # Process events and ensure window is active
        app.processEvents()
        
        # Log initialization time
        init_time = (time.time() - start_time)
        performance_logger.debug(f"Performance - Application - initialization_time: {init_time:.2f}s")
        
        # Register cleanup handler
        app.aboutToQuit.connect(cleanup_resources)
        
        # Start event loop and handle exit
        return_code = app.exec()
        gui_logger.info(f"Application exited with code {return_code}")
        return return_code
        
    except Exception as e:
        gui_logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
