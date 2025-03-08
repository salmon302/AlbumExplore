"""Configure GUI application logging and handlers."""
import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure root logger
logging.basicConfig(level=logging.INFO)

# Configure application loggers
gui_logger = logging.getLogger("albumexplore.gui")
graphics_logger = logging.getLogger("albumexplore.gui.graphics")
performance_logger = logging.getLogger("albumexplore.gui.performance")
db_logger = logging.getLogger("albumexplore.database")

def setup_logging():
    """Set up all logging handlers."""
    # Set log levels
    for logger in [gui_logger, graphics_logger, performance_logger, db_logger]:
        logger.setLevel(logging.DEBUG)
        # Remove any existing handlers
        logger.handlers.clear()
        # Prevent propagation to root logger
        logger.propagate = False

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    current_date = datetime.now().strftime("%Y%m%d")

    # File handlers for each logger
    handlers = {
        gui_logger: logging.FileHandler(os.path.join(log_dir, f'gui_{current_date}.log')),
        graphics_logger: logging.FileHandler(os.path.join(log_dir, f'graphics_{current_date}.log')),
        performance_logger: logging.FileHandler(os.path.join(log_dir, f'performance_{current_date}.log')),
        db_logger: logging.FileHandler(os.path.join(log_dir, f'database_{current_date}.log'))
    }

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - {%(filename)s:%(lineno)d}')

    # Configure and add handlers
    for logger, file_handler in handlers.items():
        # Configure file handler
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        
        # Add console handler to each logger
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    gui_logger.info("Logging system initialized")

# Utility functions
def log_graphics_event(event_type: str, message: str) -> None:
    """Log a graphics-related event."""
    graphics_logger.debug(f"Graphics Event - {event_type}: {message}")

def log_performance_metric(component: str, metric: str, value: str) -> None:
    """Log a performance metric."""
    performance_logger.debug(f"Performance - {component} - {metric}: {value}")

def log_interaction(component: str, message: str) -> None:
    """Log a user interaction."""
    gui_logger.info(f"Interaction - {component}: {message}")