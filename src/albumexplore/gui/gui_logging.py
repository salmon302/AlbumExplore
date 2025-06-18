"""Logging configuration for GUI components."""
import os
import time
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create log directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Custom RotatingFileHandler with recursion protection
class SafeRotatingFileHandler(RotatingFileHandler):
    """A RotatingFileHandler with protection against recursion errors."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recursion_protection = False
    
    def shouldRollover(self, record):
        """Check if rollover should occur with recursion protection."""
        if self._recursion_protection:
            return 0  # Don't roll over if we're already in this method
        
        try:
            self._recursion_protection = True
            result = super().shouldRollover(record)
            return result
        except RecursionError:
            # If recursion occurs, just don't roll over
            return 0
        finally:
            self._recursion_protection = False
    
    def emit(self, record):
        """Emit a record with recursion protection."""
        if self._recursion_protection:
            return  # Skip emission if we're already in this method
        
        try:
            self._recursion_protection = True
            super().emit(record)
        except RecursionError:
            # If recursion occurs, just skip this log
            pass
        except Exception:
            self.handleError(record)
        finally:
            self._recursion_protection = False

# Configure formatters
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# GUI logger
gui_logger = logging.getLogger('albumexplore.gui')
gui_logger.setLevel(logging.DEBUG)

gui_file_handler = SafeRotatingFileHandler(
    log_dir / f"gui_{time.strftime('%Y%m%d')}.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'  # Added encoding
)
gui_file_handler.setFormatter(formatter)
gui_logger.addHandler(gui_file_handler)

# Graphics logger
graphics_logger = logging.getLogger('albumexplore.graphics')
graphics_logger.setLevel(logging.DEBUG)

graphics_file_handler = SafeRotatingFileHandler(
    log_dir / f"graphics_{time.strftime('%Y%m%d')}.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'  # Added encoding
)
graphics_file_handler.setFormatter(formatter)
graphics_logger.addHandler(graphics_file_handler)

# Database logger
db_logger = logging.getLogger('albumexplore.database')
db_logger.setLevel(logging.DEBUG)

db_file_handler = SafeRotatingFileHandler(
    log_dir / f"database_{time.strftime('%Y%m%d')}.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'  # Added encoding
)
db_file_handler.setFormatter(formatter)
db_logger.addHandler(db_file_handler)

# Performance logger
performance_logger = logging.getLogger('albumexplore.performance')
performance_logger.setLevel(logging.DEBUG)

performance_file_handler = SafeRotatingFileHandler(
    log_dir / f"performance_{time.strftime('%Y%m%d')}.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'  # Added encoding
)
performance_file_handler.setFormatter(formatter)
performance_logger.addHandler(performance_file_handler)

# Optionally add console handler for development
if os.getenv('ALBUMEXPLORE_DEBUG'):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    gui_logger.addHandler(console_handler)
    graphics_logger.addHandler(console_handler)
    db_logger.addHandler(console_handler)
    performance_logger.addHandler(console_handler)

# Set recursion limit higher to help prevent recursion errors
sys.setrecursionlimit(2000)  # Default is usually 1000

def log_graphics_event(event_type: str, message: str):
    """Log a graphics-related event."""
    try:
        graphics_logger.debug(f"{event_type}: {message}")
    except RecursionError:
        pass  # Silently ignore recursion errors in logging

def log_performance_metric(component: str, metric: str, value: str):
    """Log a performance metric."""
    try:
        performance_logger.debug(f"{component} - {metric}: {value}")
    except RecursionError:
        pass  # Silently ignore recursion errors in logging

def log_interaction(component: str, message: str):
    """Log a user interaction."""
    try:
        gui_logger.debug(f"{component} - Interaction: {message}")
    except RecursionError:
        pass  # Silently ignore recursion errors in logging