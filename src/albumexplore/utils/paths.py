"""File path resolution utilities."""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    current_dir = Path(__file__).resolve().parent
    while current_dir.name != "AlbumExplore":
        parent = current_dir.parent
        if parent == current_dir:
            raise RuntimeError("Could not find project root directory")
        current_dir = parent
    return current_dir

def get_data_dir() -> Path:
    """Get the absolute path to the data directory."""
    root = get_project_root()
    data_dir = root / "csv"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
    return data_dir

def get_log_dir() -> Path:
    """Get the absolute path to the log directory."""
    root = get_project_root()
    log_dir = root / "logs"
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    return log_dir

def resolve_input_file(filename: str) -> Optional[Path]:
    """Resolve a data input file path."""
    # Check absolute path first
    path = Path(filename)
    if path.is_absolute() and path.exists():
        return path
    
    # Check in data directory
    data_dir = get_data_dir()
    path = data_dir / filename
    if path.exists():
        return path
    
    # Check in project root
    root = get_project_root()
    path = root / filename
    if path.exists():
        return path
    
    logger.warning(f"Could not resolve input file: {filename}")
    return None