from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
							QVBoxLayout, QSizePolicy, QScrollBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from typing import Dict, Any, Set

from .base_view import BaseView
from ..state import ViewType, ViewState

class TableView(BaseView):
	"""Table visualization view."""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.view_state = ViewState(ViewType.TABLE)
		self._setup_table()
		self._setup_scroll_handling()
		
		# Add update batching
		self._update_timer = QTimer(self)
		self._update_timer.setSingleShot(True)
		self._update_timer.timeout.connect(self._process_updates)
		self._pending_updates = []
		
		# Add selection batching
		self._selection_timer = QTimer(self)
		self._selection_timer.setSingleShot(True)
		self._selection_timer.timeout.connect(self._process_selection)
		self._pending_selection = set()
		
	def _setup_table(self):
		"""Setup table widget and properties."""
		self.table = QTableWidget(self)
		self.table.setColumnCount(4)
		self.table.setHorizontalHeaderLabels(["Artist", "Album", "Year", "Tags"])
		
		header = self.table.horizontalHeader()
		header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
		header.setStretchLastSection(True)
		header.setSortIndicatorShown(True)
		header.sectionClicked.connect(self._handle_sort)
		
		self.table.setShowGrid(True)
		self.table.setAlternatingRowColors(True)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
		self.table.verticalHeader().setVisible(False)
		
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		
		self.table.itemSelectionChanged.connect(self._handle_selection_change)
		
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self.table)
		
	def _setup_scroll_handling(self):
		"""Setup scroll event handling for infinite scroll."""
		self._scroll_timer = QTimer(self)
		self._scroll_timer.setSingleShot(True)
		self._scroll_timer.timeout.connect(self._check_scroll_position)
		
		scrollbar = self.table.verticalScrollBar()
		scrollbar.valueChanged.connect(self._handle_scroll)
		
	def _handle_scroll(self):
		"""Handle scroll events with debouncing."""
		self._scroll_timer.start(150)  # Debounce scroll events
		
	def _check_scroll_position(self):
		"""Check if we need to load more data."""
		scrollbar = self.table.verticalScrollBar()
		if scrollbar.value() >= scrollbar.maximum() * 0.8:  # Load more when 80% scrolled
			if hasattr(self.parent(), 'view_manager'):
				self.parent().view_manager.load_next_page()
	
	def update_data(self, nodes, edges):
		"""Update table with batched updates."""
		super().update_data(nodes, edges)
		
		self.table.setUpdatesEnabled(False)
		current_row = self.table.rowCount()
		self.table.setRowCount(len(nodes))
		
		# Batch updates in chunks
		chunk_size = 50
		for i in range(current_row, len(nodes), chunk_size):
			chunk = nodes[i:i + chunk_size]
			self._pending_updates.append((i, chunk))
		
		if self._pending_updates and not self._update_timer.isActive():
			self._update_timer.start(16)  # Process chunks every 16ms
		
		if current_row == 0:
			self.table.resizeColumnsToContents()
		self.table.setUpdatesEnabled(True)

	def _process_updates(self):
		"""Process pending updates in chunks."""
		if not self._pending_updates:
			return
			
		start_row, nodes = self._pending_updates.pop(0)
		
		self.table.setUpdatesEnabled(False)
		try:
			for i, node in enumerate(nodes, start=start_row):
				data = node.data
				
				for col, key in enumerate(['artist', 'title', 'year']):
					item = QTableWidgetItem(str(data.get(key, '')))
					item.setData(Qt.ItemDataRole.UserRole, node.id)
					if node.id in self.selected_ids:
						item.setBackground(QColor(200, 200, 255))
					self.table.setItem(i, col, item)
				
				# Handle tags column separately
				tags_item = QTableWidgetItem(', '.join(str(tag) for tag in data.get('tags', [])))
				tags_item.setData(Qt.ItemDataRole.UserRole, node.id)
				if node.id in self.selected_ids:
					tags_item.setBackground(QColor(200, 200, 255))
				self.table.setItem(i, 3, tags_item)
		finally:
			self.table.setUpdatesEnabled(True)
		
		if self._pending_updates:
			self._update_timer.start(16)
	
	def _handle_sort(self, column_index):
		"""Handle column sorting."""
		header = self.table.horizontalHeader()
		direction = "asc" if header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder else "desc"
		
		# Update sort state
		self.view_state.set_view_specific("sort", {
			"column": column_index,
			"direction": direction
		})
		
		# Sort table
		self.table.sortItems(column_index, 
							Qt.SortOrder.AscendingOrder if direction == "asc" 
							else Qt.SortOrder.DescendingOrder)
	
	def _handle_selection_change(self):
		"""Batch selection changes."""
		selected_ids = set()
		for item in self.table.selectedItems():
			node_id = item.data(Qt.ItemDataRole.UserRole)
			if node_id is not None:
				selected_ids.add(node_id)
		
		self._pending_selection = selected_ids
		if not self._selection_timer.isActive():
			self._selection_timer.start(50)  # Process selection every 50ms

	def _process_selection(self):
		"""Process pending selection changes."""
		if self._pending_selection != self.selected_ids:
			self.update_selection(self._pending_selection)