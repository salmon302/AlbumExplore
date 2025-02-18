"""Album Explorer GUI application entry point."""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from sqlalchemy.orm import sessionmaker
from albumexplore.database.initialize import init_db
from albumexplore.database.csv_loader import load_csv_data
from albumexplore.gui.main_window import MainWindow
from albumexplore.visualization.error_handling import ErrorManager

def setup_logging():
	"""Configure application logging."""
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
	)

def setup_error_handling(app: QApplication):
	"""Setup global error handling."""
	error_manager = ErrorManager()
	
	def handle_exception(exc_type, exc_value, exc_traceback):
		logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
		error_manager.handle_error(exc_value, None)
	
	sys.excepthook = handle_exception
	return error_manager

def setup_high_dpi():
	"""Configure high DPI support."""
	if hasattr(Qt, 'AA_EnableHighDpiScaling'):
		QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
	if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
		QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

def main():
	try:
		# Setup application infrastructure
		setup_logging()
		setup_high_dpi()
		
		# Initialize database and create session
		engine = init_db()
		Session = sessionmaker(bind=engine)
		db_session = Session()
		
		# Create application
		app = QApplication(sys.argv)
		error_manager = setup_error_handling(app)
		
		# Load CSV data
		csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
		try:
			load_csv_data(db_session, csv_dir)
			logging.info("CSV data loaded successfully")
		except Exception as e:
			logging.error(f"Error loading CSV data: {str(e)}")
			db_session.rollback()
			error_manager.handle_error(e, None)
		
		# Create and show main window
		window = MainWindow(db_session)
		window.resize(1200, 800)
		window.show()
		
		return app.exec()
	except Exception as e:
		logging.error(f"Error starting GUI: {str(e)}")
		return 1

def run_gui():
	sys.exit(main())

if __name__ == "__main__":
	run_gui()
