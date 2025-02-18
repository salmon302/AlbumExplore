from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

from ..state import ViewState, ViewType
from .base_view import BaseView
from .network_view import NetworkView
from .chord_view import ChordView
from .arc_view import ArcView
from .table_view import TableView

# Export view_map for use in ViewManager
view_map = {
	ViewType.TABLE: TableView,
	ViewType.NETWORK: NetworkView,  # Use NetworkView from visualization
	ViewType.CHORD: ChordView,
	ViewType.ARC: ArcView,
}

def create_view(view_type: ViewType, parent: Optional[QWidget] = None) -> BaseView:
	"""Create a view instance with proper initialization."""
	print(f"Creating view of type: {view_type}")
	
	view_class = view_map.get(view_type)
	if not view_class:
		raise ValueError(f"Unsupported view type: {view_type}")
	
	# Create view instance
	view = view_class(parent)
	print(f"Created view instance: {type(view).__name__}")
	
	# Ensure view state is properly initialized
	view.view_state = ViewState(view_type)
	
	# Set up view attributes for proper rendering
	view.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
	view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
	view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
	view.setAutoFillBackground(True)
	
	# Initialize buffer management if supported
	if hasattr(view, '_paint_buffer'):
		view._paint_buffer = None
		view._buffer_dirty = True
	
	return view