from typing import Optional, Dict, Type
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from ..state import ViewState, ViewType
from .base_view import BaseView
from .enhanced_network_view import EnhancedNetworkView
from .chord_view import ChordView
from .arc_view import ArcView
from .table_view import TableView
from .tag_explorer_view import TagExplorerView
from .tag_graph_view import TagGraphView
from albumexplore.gui.gui_logging import gui_logger
from albumexplore.gui.views import TableViewWidget  # Import the correct table implementation

# Export view_map for use in ViewManager
view_map: Dict[ViewType, Type[BaseView]] = {
    ViewType.TABLE: TableViewWidget,  # Use the correct table widget implementation
    ViewType.NETWORK: EnhancedNetworkView,
    ViewType.CHORD: ChordView,
    ViewType.ARC: ArcView,
    ViewType.TAG_EXPLORER: TagExplorerView,
    ViewType.TAG_GRAPH: TagGraphView,
}

def create_view(view_type: ViewType, parent: Optional[QWidget] = None) -> BaseView:
    """Create a view instance with proper initialization."""
    gui_logger.debug(f"Creating visualization view: {view_type}")
    view_class = view_map.get(view_type)
    if not view_class:
        raise ValueError(f"Unsupported view type: {view_type}")
    
    # Create view instance first
    view = view_class(parent)
    
    # Set parent explicitly if provided
    if parent and view.parent() is None:
        view.setParent(parent)
        gui_logger.debug(f"Set parent for {view_type} view")
    
    # Ensure view state is properly initialized
    view.view_state = ViewState(view_type)
    
    # Set up view attributes for proper rendering
    view.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
    view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
    view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    view.setAutoFillBackground(True)
    
    # Set size and layout policies
    view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    view.setMinimumSize(100, 100)
    
    # Set initial size if parent exists
    if parent:
        view.resize(parent.size())
        
    # Set background color
    palette = view.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    view.setPalette(palette)
    
    gui_logger.debug(f"View {view_type} created with size {view.size()}")
    return view
