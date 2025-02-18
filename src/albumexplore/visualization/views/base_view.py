from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QKeyEvent
from typing import List, Dict, Any, Set
from albumexplore.gui.gui_logging import gui_logger
import json
import time
from ..models import VisualNode, VisualEdge
from ..state import ViewType, ViewState
from ..transition_animator import TransitionAnimator
from ..debug import PerformanceDebugger

class BaseView(QWidget):
	"""Base class for all visualization views."""
	selectionChanged = pyqtSignal(set)  # Signal emitted when selection changes

	def __init__(self, parent=None):
		super().__init__(parent)
		gui_logger.debug(f"{self.__class__.__name__} initialized")
		
		# Enable Qt optimizations
		self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
		self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
		self.setAutoFillBackground(True)
		
		# Add base-level buffer management
		self.setProperty("paintOnScreen", False)
		self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)
		
		# Enable key events
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
		
		# Initialize state
		self.nodes: List[VisualNode] = []
		self.edges: List[VisualEdge] = []
		self.selected_ids: Set[str] = set()
		self.transition_animator = TransitionAnimator()
		self.view_state = None
		self.performance_debugger = PerformanceDebugger()
		
		# Add update control with improved timing
		self._update_scheduled = False
		self._update_timer = QTimer(self)
		self._update_timer.setSingleShot(True)
		self._update_timer.timeout.connect(self._handle_update)
		self._last_update_time = 0
		self._min_update_interval = 33  # ~30 FPS max

	def update(self) -> None:
		"""Schedule update with rate limiting."""
		current_time = time.time() * 1000
		if not self._update_scheduled and current_time - self._last_update_time >= self._min_update_interval:
			self._update_scheduled = True
			self._last_update_time = current_time
			self._update_timer.start(self._min_update_interval)

	def _handle_update(self) -> None:
		"""Handle scheduled update with cleanup."""
		self._update_scheduled = False
		if hasattr(self, '_paint_buffer'):
			self._buffer_dirty = True
		super().update()

	def hideEvent(self, event) -> None:
		"""Handle cleanup when view is hidden."""
		super().hideEvent(event)
		self.transition_animator.cancel_animations()
		if hasattr(self, '_cleanup_resources'):
			self._cleanup_resources()

	def showEvent(self, event) -> None:
		"""Handle setup when view is shown."""
		super().showEvent(event)
		if hasattr(self, '_buffer_dirty'):
			self._buffer_dirty = True
		self.update()

	def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
		"""Update visualization data with stability."""
		gui_logger.debug(f"Updating data in {self.__class__.__name__}: {len(nodes)} nodes, {len(edges)} edges")
		self.setUpdatesEnabled(False)
		self.nodes = nodes
		self.edges = edges
		self.setUpdatesEnabled(True)
		self.update()

	def apply_transition(self, transition_config: Dict[str, Any]) -> None:
		"""Apply transition with improved stability."""
		if not transition_config or not self.view_state:
			return
		
		gui_logger.debug(f"Applying transition in {self.__class__.__name__}: {transition_config}")
		self.setUpdatesEnabled(False)
		
		# Cancel ongoing animations
		self.transition_animator.cancel_animations()
		
		# Update state
		if 'position' in transition_config:
			self.view_state.position = transition_config['position']
		if 'zoom' in transition_config:
			self.view_state.zoom_level = transition_config['zoom']
		
		# Handle positions
		if 'preserved_positions' in transition_config:
			self._apply_preserved_positions(transition_config)
		
		# Update selection
		if 'shared_selections' in transition_config:
			self.update_selection(set(transition_config['shared_selections']))
		
		self.setUpdatesEnabled(True)
		self.update()

	def _apply_preserved_positions(self, transition_config: Dict[str, Any]) -> None:
		"""Apply preserved positions atomically."""
		node_positions = {}
		for node in self.nodes:
			if node.id in transition_config['preserved_positions']:
				pos = transition_config['preserved_positions'][node.id]
				if not isinstance(node.data, dict):
					node.data = {}
				if not hasattr(node, 'pos'):
					node.pos = {}
				
				# Update all position references atomically
				node.data.update({
					'x': pos['x'],
					'y': pos['y'],
					'pos': {'x': pos['x'], 'y': pos['y']}
				})
				node.pos.update({
					'x': pos['x'],
					'y': pos['y']
				})
				node_positions[node.id] = node
		
		# Start animation if needed
		if transition_config.get('transition', {}).get('type') in ['morph', 'fade']:
			self.transition_animator.animate_transition(
				node_positions,
				transition_config['preserved_positions'],
				transition_config['transition']['type'],
				transition_config['transition'].get('duration', 300)
			)

	def keyPressEvent(self, event: QKeyEvent) -> None:
		"""Handle key press events including copy."""
		if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
			self.copy_selected_to_clipboard()
		elif event.key() == Qt.Key.Key_P and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
			self.show_performance_report()
		else:
			super().keyPressEvent(event)

	def copy_selected_to_clipboard(self) -> None:
		"""Copy selected nodes data to clipboard."""
		if not self.selected_ids:
			return

		selected_data = []
		for node in self.nodes:
			if node.id in self.selected_ids:
				node_data = {
					'id': node.id,
					'label': node.label,
					'data': node.data
				}
				selected_data.append(node_data)

		if selected_data:
			clipboard = QApplication.clipboard()
			clipboard.setText(json.dumps(selected_data, indent=2))

	def show_performance_report(self) -> None:
		"""Show and copy current performance report."""
		self.performance_debugger.copy_report_to_clipboard()
		report = self.performance_debugger.get_performance_report()
		print("Performance report copied to clipboard:")
		print(report)

	def start_performance_measure(self, name: str) -> None:
		"""Start measuring a performance metric."""
		self.performance_debugger.start_measure(name)

	def end_performance_measure(self, name: str) -> float:
		"""End measuring a performance metric."""
		return self.performance_debugger.end_measure(name)

	def take_performance_snapshot(self, additional_metrics: Dict[str, float] = None) -> None:
		"""Take a performance snapshot with current metrics."""
		metrics = {
			'node_count': len(self.nodes),
			'edge_count': len(self.edges),
			'selected_count': len(self.selected_ids),
		}
		if additional_metrics:
			metrics.update(additional_metrics)
		self.performance_debugger.take_snapshot(metrics)

	def paintEvent(self, event) -> None:
		"""Handle paint events with logging."""
		gui_logger.debug(f"Paint event started in {self.__class__.__name__}")
		super().paintEvent(event)
		gui_logger.debug(f"Paint event finished in {self.__class__.__name__}")

	def update_selection(self, selected_ids: Set[str]) -> None:
		"""Update selected nodes."""
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
		self.update()