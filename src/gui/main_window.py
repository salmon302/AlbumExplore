import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
						   QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, 
						   QLineEdit, QLabel, QComboBox, QStatusBar, QTextEdit, QMenuBar, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import pandas as pd
from pathlib import Path
from albumexplore.data.parsers.csv_parser import CSVParser
from albumexplore.data.validators.data_validator import DataValidator
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.tags.relationships.tag_relationships import TagRelationships
from albumexplore.visualization.views import create_view
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.state import ViewType
from albumexplore.database import get_db_session
from .data_loader_dialog import DataLoaderDialog

logging.basicConfig(level=logging.INFO)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		logging.info("Initializing Album Explorer main window")
		self.setWindowTitle("Album Explorer")
		self.setMinimumSize(1200, 800)
		
		# Initialize database session and data interface
		self.db_session = get_db_session()
		self.data_interface = DataInterface(self.db_session)
		self.view_manager = ViewManager(self.data_interface)

		# Initialize data
		self.df = None
		self.all_tags = set()
		self.normalizer = TagNormalizer()
		self.relationships = TagRelationships() 
		
		# Create menu bar
		self._create_menu_bar()
		
		# Create central widget and layout
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		layout = QVBoxLayout(central_widget)
		
		# Create tab widget
		self.tabs = QTabWidget()
		layout.addWidget(self.tabs)
		
		# Create tabs
		logging.info("Creating UI tabs")
		self.albums_tab = self._create_albums_tab()
		self.tags_tab = self._create_tags_tab()
		self.relationships_tab = self._create_relationships_tab()
		self.consolidation_tab = self._create_consolidation_tab()
		self.network_tab = self._create_network_tab()
		
		self.tabs.addTab(self.albums_tab, "Albums")
		self.tabs.addTab(self.tags_tab, "Tags")
		self.tabs.addTab(self.relationships_tab, "Relationships")
		self.tabs.addTab(self.consolidation_tab, "Consolidation")
		self.tabs.addTab(self.network_tab, "Network")

		
		# Create status bar
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		self.status_bar.showMessage("Ready - Use File > Load Data to begin")
		
		# Disable tabs until data is loaded
		self._set_tabs_enabled(False)

	def _create_menu_bar(self):
		"""Create the application menu bar."""
		menubar = self.menuBar()
		
		# File menu
		file_menu = menubar.addMenu('File')
		
		load_data_action = QAction('Load Data...', self)
		load_data_action.setShortcut('Ctrl+O')
		load_data_action.triggered.connect(self._show_data_loader)
		file_menu.addAction(load_data_action)
		
		file_menu.addSeparator()
		
		exit_action = QAction('Exit', self)
		exit_action.setShortcut('Ctrl+Q')
		exit_action.triggered.connect(self.close)
		file_menu.addAction(exit_action)
		
		# View menu
		view_menu = menubar.addMenu('View')
		
		refresh_action = QAction('Refresh Data', self)
		refresh_action.setShortcut('F5')
		refresh_action.triggered.connect(self._refresh_data)
		refresh_action.setEnabled(False)  # Disabled until data is loaded
		view_menu.addAction(refresh_action)
		self.refresh_action = refresh_action  # Store reference
		
	def _set_tabs_enabled(self, enabled: bool):
		"""Enable or disable all tabs."""
		for i in range(self.tabs.count()):
			self.tabs.setTabEnabled(i, enabled)
			
	def _show_data_loader(self):
		"""Show the data loader dialog."""
		csv_dir = Path("csv")  # Default CSV directory
		dialog = DataLoaderDialog(self, csv_dir)
		dialog.data_loaded.connect(self._on_data_loaded)
		dialog.exec()
		
	def _on_data_loaded(self, dataframe):
		"""Handle data loaded from the dialog."""
		self.df = dataframe
		self._process_loaded_data()
		
	def _refresh_data(self):
		"""Refresh the current data display."""
		if self.df is not None:
			self._process_loaded_data()

	def _create_albums_tab(self):
		widget = QWidget()
		layout = QVBoxLayout(widget)
		
		# Search controls
		search_layout = QHBoxLayout()
		search_label = QLabel("Search:")
		self.search_input = QLineEdit()
		self.search_type = QComboBox()
		self.search_type.addItems(["Artist", "Album", "Genre", "Country"])
		search_button = QPushButton("Search")
		search_button.clicked.connect(self.search_albums)
		
		search_layout.addWidget(search_label)
		search_layout.addWidget(self.search_input)
		search_layout.addWidget(self.search_type)
		search_layout.addWidget(search_button)
		layout.addLayout(search_layout)
		
		# Results table
		self.albums_table = QTableWidget()
		self.albums_table.setColumnCount(6)
		self.albums_table.setHorizontalHeaderLabels(
			["Artist", "Album", "Release Date", "Genre/Subgenres", "Vocal Style", "Country"]
		)
		layout.addWidget(self.albums_table)
		
		return widget

	def _create_tags_tab(self):
		widget = QWidget()
		layout = QVBoxLayout(widget)
		
		# Tag list
		self.tags_table = QTableWidget()
		self.tags_table.setColumnCount(2)
		self.tags_table.setHorizontalHeaderLabels(["Tag", "Frequency"])
		layout.addWidget(self.tags_table)
		
		return widget

	def _create_relationships_tab(self):
		widget = QWidget()
		layout = QVBoxLayout(widget)
		
		# Tag selection
		select_layout = QHBoxLayout()
		select_label = QLabel("Select Tag:")
		self.tag_select = QComboBox()
		self.tag_select.currentTextChanged.connect(self.update_relationships)
		select_layout.addWidget(select_label)
		select_layout.addWidget(self.tag_select)
		layout.addLayout(select_layout)
		
		# Relationships table
		self.relationships_table = QTableWidget()
		self.relationships_table.setColumnCount(2)
		self.relationships_table.setHorizontalHeaderLabels(["Related Tag", "Strength"])
		layout.addWidget(self.relationships_table)
		
		return widget


	def _process_loaded_data(self):
		"""Process the loaded DataFrame and update the UI."""
		try:
			if self.df is None or self.df.empty:
				self.status_bar.showMessage("No data to process")
				return

			logging.info(f"Processing {len(self.df)} rows of data")

			# Clear existing tags
			self.all_tags.clear()
			
			# Extract tags
			logging.info("Extracting tags...")
			for tags in self.df['tags']:
				if isinstance(tags, list):
					self.all_tags.update(tags)

			# Clear and update tag comboboxes
			self.tag_select.clear()
			self.consolidation_tag_select.clear()
			
			sorted_tags = sorted(self.all_tags)
			self.tag_select.addItems(sorted_tags)
			self.consolidation_tag_select.addItems(sorted_tags)

			# Create network data
			nodes = []
			edges = []
			tag_ids = {tag: f"tag_{i}" for i, tag in enumerate(self.all_tags)}

			for tag in self.all_tags:
				nodes.append(VisualNode(
					id=tag_ids[tag],
					label=tag,
					size=10,
					color="#4a90e2",
					shape="circle",
					data={"type": "tag"}
				))

			# Create edges based on tag co-occurrence
			for tags in self.df['tags']:
				if isinstance(tags, list) and len(tags) > 1:
					for i in range(len(tags)):
						for j in range(i + 1, len(tags)):
							edges.append(VisualEdge(
								source=tag_ids[tags[i]],
								target=tag_ids[tags[j]],
								weight=1,
								color="#999999",
								thickness=1
							))

			# Update network view with proper data update
			if hasattr(self, 'network_view'):
				self.network_view.update_data(nodes, edges)
				self.network_view.adjust_viewport_to_content()
				self.network_view.start_layout()

			# Update tables
			logging.info("Updating tables...")
			self.update_albums_table()
			self.update_tags_table()
			self.update_consolidation_table()

			# Enable tabs and refresh action
			self._set_tabs_enabled(True)
			if hasattr(self, 'refresh_action'):
				self.refresh_action.setEnabled(True)

			msg = f"Loaded {len(self.df)} albums with {len(self.all_tags)} unique tags"
			logging.info(msg)
			self.status_bar.showMessage(msg)

		except Exception as e:
			msg = f"Error processing data: {str(e)}"
			logging.error(msg, exc_info=True)
			self.status_bar.showMessage(msg)

	def search_albums(self):
		search_text = self.search_input.text().lower()
		search_type = self.search_type.currentText()
		
		if search_text:
			if search_type == "Genre":
				matches = self.df[self.df['tags'].apply(
					lambda x: any(search_text in tag.lower() for tag in x)
				)]
			else:
				column = search_type if search_type != "Genre" else "Genre / Subgenres"
				matches = self.df[
					self.df[column].str.lower().str.contains(search_text, na=False)
				]
			
			self.update_albums_table(matches)
			self.status_bar.showMessage(f"Found {len(matches)} matching albums")
		else:
			self.update_albums_table()

	def update_albums_table(self, data=None):
		df = data if data is not None else self.df
		self.albums_table.setRowCount(len(df))
		
		for i, (_, row) in enumerate(df.iterrows()):
			self.albums_table.setItem(i, 0, QTableWidgetItem(str(row['Artist'])))
			self.albums_table.setItem(i, 1, QTableWidgetItem(str(row['Album'])))
			self.albums_table.setItem(i, 2, QTableWidgetItem(str(row['Release Date'])))
			self.albums_table.setItem(i, 3, QTableWidgetItem(str(row['Genre / Subgenres'])))
			self.albums_table.setItem(i, 4, QTableWidgetItem(str(row['Vocal Style'])))
			self.albums_table.setItem(i, 5, QTableWidgetItem(str(row['Country / State'])))

	def update_tags_table(self):
		tag_counts = {}
		for tags in self.df['tags']:
			if isinstance(tags, list):
				for tag in tags:
					tag_counts[tag] = tag_counts.get(tag, 0) + 1
		
		self.tags_table.setRowCount(len(tag_counts))
		for i, (tag, count) in enumerate(sorted(tag_counts.items())):
			self.tags_table.setItem(i, 0, QTableWidgetItem(tag))
			self.tags_table.setItem(i, 1, QTableWidgetItem(str(count)))

	def _create_consolidation_tab(self):
		widget = QWidget()
		layout = QVBoxLayout(widget)
		
		# Tag selection area
		select_layout = QHBoxLayout()
		primary_label = QLabel("Primary Tag:")
		self.consolidation_tag_select = QComboBox()
		select_layout.addWidget(primary_label)
		select_layout.addWidget(self.consolidation_tag_select)
		layout.addLayout(select_layout)
		
		# Tags table for selection
		self.consolidation_table = QTableWidget()
		self.consolidation_table.setColumnCount(2)
		self.consolidation_table.setHorizontalHeaderLabels(["Tag", "Merge"])
		self.consolidation_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
		layout.addWidget(self.consolidation_table)
		
		# Buttons
		button_layout = QHBoxLayout()
		self.preview_merge_button = QPushButton("Preview Merge")
		self.execute_merge_button = QPushButton("Execute Merge")
		self.preview_merge_button.clicked.connect(self.preview_tag_merge)
		self.execute_merge_button.clicked.connect(self.execute_tag_merge)
		button_layout.addWidget(self.preview_merge_button)
		button_layout.addWidget(self.execute_merge_button)
		layout.addLayout(button_layout)
		
		# Results text area
		self.merge_results = QTextEdit()
		self.merge_results.setReadOnly(True)
		layout.addWidget(self.merge_results)
		
		return widget
		
	def preview_tag_merge(self):
		primary_tag = self.consolidation_tag_select.currentText()
		if not primary_tag:
			self.merge_results.setText("Please select a primary tag")
			return
			
		selected_items = self.consolidation_table.selectedItems()
		tags_to_merge = {item.text() for item in selected_items if item.column() == 0}
		
		if not tags_to_merge:
			self.merge_results.setText("Please select tags to merge")
			return
			
		# Preview the merge using TagConsolidator
		preview = self.relationships.preview_merge(primary_tag, tags_to_merge)
		self.merge_results.setText(f"Preview of merge into '{primary_tag}':\n"
								 f"Tags to merge: {', '.join(tags_to_merge)}\n"
								 f"Affected entries: {preview.affected_count}")
		
	def execute_tag_merge(self):
		primary_tag = self.consolidation_tag_select.currentText()
		if not primary_tag:
			self.merge_results.setText("Please select a primary tag")
			return
			
		selected_items = self.consolidation_table.selectedItems()
		tags_to_merge = {item.text() for item in selected_items if item.column() == 0}
		
		if not tags_to_merge:
			self.merge_results.setText("Please select tags to merge")
			return
			
		try:
			# Execute the merge using TagConsolidator
			self.relationships.merge_tags(primary_tag, tags_to_merge)
			self.merge_results.setText(f"Successfully merged tags into '{primary_tag}'")
			# Refresh the UI
			self.update_tags_table()
			self.update_consolidation_table()
		except Exception as e:
			self.merge_results.setText(f"Error during merge: {str(e)}")
			
	def update_consolidation_table(self):
		self.consolidation_table.setRowCount(len(self.all_tags))
		for i, tag in enumerate(sorted(self.all_tags)):
			self.consolidation_table.setItem(i, 0, QTableWidgetItem(tag))
			self.consolidation_table.setItem(i, 1, QTableWidgetItem(""))

	def _create_network_tab(self):
		widget = QWidget()
		layout = QVBoxLayout(widget)
		
		# Create network view using create_view
		self.network_view = create_view(ViewType.NETWORK)
		layout.addWidget(self.network_view)
		
		return widget


	def update_relationships(self, tag):
		if not tag:
			return
			
		normalized = self.normalizer.normalize(tag)
		related = self.relationships.get_related_tags(normalized)
		
		self.relationships_table.setRowCount(len(related))
		for i, (related_tag, weight) in enumerate(related):
			self.relationships_table.setItem(i, 0, QTableWidgetItem(related_tag))
			self.relationships_table.setItem(i, 1, QTableWidgetItem(f"{weight:.2f}"))