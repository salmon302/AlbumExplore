from typing import Optional, Dict, Type
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from ..state import ViewState, ViewType
from .base_view import BaseView
from .chord_view import ChordView
from .arc_view import ArcView
from .table_view import TableView
from .tag_explorer_view import TagExplorerView
from albumexplore.gui.gui_logging import gui_logger

# Export view_map for use in ViewManager
view_map: Dict[ViewType, Type[BaseView]] = {
    ViewType.TABLE: TableView,
    ViewType.CHORD: ChordView,
    ViewType.ARC: ArcView,
    ViewType.TAG_EXPLORER: TagExplorerView
}

def create_view(view_type: ViewType, parent: Optional[QWidget] = None) -> Optional[BaseView]:
    """Create a view of the specified type."""
    if view_type not in view_map:
        gui_logger.error(f"Unknown view type: {view_type}")
        return None
        
    try:
        view_class = view_map[view_type]
        view = view_class(parent)
        
        # Set default styling
        view.setAutoFillBackground(True)
        palette = view.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        view.setPalette(palette)
        
        # Set size policy
        view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        gui_logger.debug(f"Created view of type: {view_type}")
        return view
    except Exception as e:
        gui_logger.error(f"Error creating view of type {view_type}: {str(e)}", exc_info=True)
        return None
