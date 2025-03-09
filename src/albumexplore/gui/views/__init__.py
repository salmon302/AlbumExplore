"""View factory implementation."""
from typing import Optional, Dict, Type
import logging
import importlib
from .base_view import BaseView
from .network_view import NetworkView
from .table_view import TableView
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import gui_logger

# Import visualization views dynamically to avoid circular imports
def _import_visualization_view(view_name):
    """Dynamically import a view from the visualization module."""
    try:
        # First try to import directly from visualization.views
        try:
            # Import the view map from visualization.views
            from albumexplore.visualization.views import view_map as viz_view_map
            # Check if the view type exists in the visualization view map
            if hasattr(ViewType, view_name) and getattr(ViewType, view_name) in viz_view_map:
                return viz_view_map[getattr(ViewType, view_name)]
        except (ImportError, AttributeError) as e:
            gui_logger.debug(f"Could not import from view_map: {str(e)}")
        
        # If that fails, try to import the specific module
        module_name = f"albumexplore.visualization.views.{view_name.lower()}_view"
        gui_logger.debug(f"Trying to import from module: {module_name}")
        module = importlib.import_module(module_name)
        
        # Look for the view class in the module
        for attr_name in dir(module):
            if attr_name.lower() == f"{view_name.lower()}view":
                return getattr(module, attr_name)
        
        gui_logger.error(f"Could not find view class in module {module_name}")
        return None
    except ImportError as e:
        gui_logger.error(f"Failed to import {view_name} view: {str(e)}")
        return None
    except Exception as e:
        gui_logger.error(f"Unexpected error importing {view_name} view: {str(e)}", exc_info=True)
        return None

def create_view(view_type: ViewType, parent=None) -> BaseView:
    """Create appropriate view based on view type."""
    gui_logger.debug(f"Creating view for type: {view_type}")
    
    # Define view mappings
    views = {
        ViewType.TABLE: TableView,
        ViewType.NETWORK: NetworkView,
    }
    
    # Try to get the view class from the mapping
    view_class = views.get(view_type)
    
    # If not found in the basic mapping, try to import from visualization module
    if not view_class:
        gui_logger.debug(f"View type {view_type} not found in basic mapping, trying visualization module")
        view_name = view_type.name
        view_class = _import_visualization_view(view_name)
        
        if view_class:
            gui_logger.debug(f"Successfully imported {view_name} view from visualization module")
        else:
            gui_logger.error(f"Unsupported view type: {view_type}. Available types: {list(views.keys())}")
            raise ValueError(f"Unsupported view type: {view_type}")
    
    # Create and return the view instance
    return view_class(parent)