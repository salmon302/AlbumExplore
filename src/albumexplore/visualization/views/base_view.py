from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QPainter, QPalette, QColor
from typing import List, Dict, Any, Set
from albumexplore.gui.gui_logging import (
	gui_logger, graphics_logger, performance_logger,
	log_graphics_event, log_performance_metric, log_interaction
)
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
		self.view_name = self.__class__.__name__
		graphics_logger.info(f"Initializing {self.view_name}")
		
		# Set proper widget attributes for clean rendering
		self.setAutoFillBackground(True)
		
		 # Ensure consistent background color
		palette = self.palette()
		palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
		palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
		self.setPalette(palette)
		
		# Set size policy to expand in both directions
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.setMinimumSize(100, 100)
		
		# Initialize state
		self.nodes: List[VisualNode] = []
		self.edges: List[VisualEdge] = []
		self.selected_ids: Set[str] = set()
		self.transition_animator = TransitionAnimator()
		self.view_state = None
		self.performance_debugger = PerformanceDebugger()
		
		 # Setup efficient update scheduling
		self._update_timer = QTimer(self)
		self._update_timer.setSingleShot(True)
		self._update_timer.timeout.connect(self._handle_update)
		self._last_update_time = 0
		self._min_update_interval = 16  # ~60 FPS
		
		# Monitor buffer state
		graphics_logger.debug(f"{self.view_name} view initialized with size {self.size()}")

		# State tracking
		self._is_updating = False
		self._update_pending = False
		self._cleanup_scheduled = False

		# Performance tracking
		self._frame_times = []
		self._max_frame_samples = 60

		# Cleanup timer
		self._cleanup_timer = QTimer()
		self._cleanup_timer.setSingleShot(True)
		self._cleanup_timer.timeout.connect(self._cleanup_resources)

	def update(self) -> None:
		"""Schedule update with rate limiting."""
		current_time = time.time() * 1000
		if current_time - self._last_update_time >= self._min_update_interval:
			self._last_update_time = current_time
			log_graphics_event("Update", f"{self.view_name} scheduled update")
			super().update()
		else:
			# Schedule deferred update
			if not self._update_timer.isActive():
				remaining_time = self._min_update_interval - (current_time - self._last_update_time)
				self._update_timer.start(int(remaining_time))

	def _handle_update(self) -> None:
		"""Handle scheduled update."""
		if self._is_updating:
			return

		log_graphics_event("Update", f"{self.view_name} handling update")
		start_time = time.time()

		self._is_updating = True
		try:
			self.setUpdatesEnabled(False)
			super().update()
		finally:
			self.setUpdatesEnabled(True)
			self._is_updating = False

		update_time = (time.time() - start_time) * 1000
		self._frame_times.append(update_time)
		if len(self._frame_times) > self._max_frame_samples:
			self._frame_times.pop(0)

		log_performance_metric(self.view_name, "update_time", f"{update_time:.2f}ms")

	def hideEvent(self, event) -> None:
		"""Handle cleanup when view is hidden."""
		log_graphics_event("Visibility", f"{self.view_name} hidden")
		super().hideEvent(event)
		self._schedule_cleanup()
		self.transition_animator.cancel_animations()

	def showEvent(self, event) -> None:
		"""Handle setup when view is shown."""
		log_graphics_event("Visibility", f"{self.view_name} shown")
		super().showEvent(event)
		
		# Ensure proper size when shown
		if self.parent():
			self.resize(self.parent().size())
		
		self.update()

	def update_data(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> None:
		"""Update visualization data with stability."""
		if self._is_updating:
			self._update_pending = True
			return

		self._is_updating = True
		try:
			start_time = time.time()
			graphics_logger.info(f"Updating data in {self.view_name}: {len(nodes)} nodes, {len(edges)} edges")
			
			self.setUpdatesEnabled(False)
			self.nodes = nodes
			self.edges = edges
			self.setUpdatesEnabled(True)
			
			update_time = (time.time() - start_time) * 1000
			log_performance_metric(self.view_name, "data_update_time", f"{update_time:.2f}ms")
			self.update()
		finally:
			self._is_updating = False
			if self._update_pending:
				self._update_pending = False
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
		"""Handle paint events with proper background."""
		start_time = time.time()
		log_graphics_event("Paint", f"{self.view_name} paint event started")
		
		painter = QPainter(self)
		try:
			# Fill background with solid white and enable antialiasing
			painter.setRenderHint(QPainter.RenderHint.Antialiasing)
			painter.fillRect(self.rect(), QColor(255, 255, 255))
			
			# Let subclasses paint their content
			self._paint_content(painter)
			
		finally:
			painter.end()
			paint_time = (time.time() - start_time) * 1000
			log_performance_metric(self.view_name, "paint_time", f"{paint_time:.2f}ms")

	def _paint_content(self, painter: QPainter) -> None:
		"""Paint view-specific content. To be overridden by subclasses."""
		pass

	def resizeEvent(self, event) -> None:
		"""Handle resize events."""
		super().resizeEvent(event)
		log_graphics_event("Resize", f"{self.view_name} resized to {event.size()}")
		
		if self.parent():
			# Ensure view fills parent while maintaining aspect ratio if needed
			self.setGeometry(0, 0, self.parent().width(), self.parent().height())
		
		# Update viewport in view state if available
		if self.view_state:
			self.view_state.update_viewport(self.width(), self.height())
		
		self.update()

	def update_selection(self, selected_ids: Set[str]) -> None:
		"""Update selected nodes."""
		log_interaction(self.view_name, f"Selection changed: {len(selected_ids)} items")
		self.selected_ids = selected_ids
		self.selectionChanged.emit(selected_ids)
		self.update()

	def _schedule_cleanup(self) -> None:
		"""Schedule resource cleanup to avoid immediate buffer destruction during transitions."""
		if not self._cleanup_scheduled:
			self._cleanup_scheduled = True
			self._cleanup_timer.start(200)  # Wait 200ms before cleanup

	def _cleanup_resources(self) -> None:
		"""Clean up buffers and resources."""
		graphics_logger.debug(f"Cleaning up {self.view_name} resources")
		self._cleanup_scheduled = False
		
		# Reset state
		self._is_updating = False
		self._update_pending = False
		self._frame_times.clear()
		
		# Derived classes should override to clean up their specific resources