import sys
import logging
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow

def main():
	try:
		logging.basicConfig(level=logging.INFO)
		app = QApplication(sys.argv)
		window = MainWindow()
		window.show()
		sys.exit(app.exec())
	except Exception as e:
		logging.error(f"Error starting GUI: {str(e)}")
		sys.exit(1)

if __name__ == "__main__":
	main()
