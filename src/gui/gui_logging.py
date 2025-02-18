import logging
from pathlib import Path

def setup_gui_logging(log_path: str = None):
	"""Setup logging for GUI events."""
	logger = logging.getLogger("GUI")
	logger.setLevel(logging.DEBUG)
	log_path = log_path or str(Path.home() / "albumexplore_gui.log")
	handler = logging.FileHandler(log_path)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	return logger

gui_logger = setup_gui_logging()