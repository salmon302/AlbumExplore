from typing import Optional, Dict
import logging
from albumexplore.gui.gui_logging import gui_logger
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
						   QLabel, QComboBox, QStatusBar, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QResizeEvent
from albumexplore.visualization.views import create_view
from albumexplore.visualization.state import ViewType, ViewState
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.error_handling import ErrorManager, ErrorCategory, ErrorContext
from albumexplore.visualization.responsive import ResponsiveManager
from albumexplore.visualization.view_manager import ViewManager



class MainWindow(QMainWindow):
	def __init__(self, db_session):
		super().__init__()
		gui_logger.debug("MainWindow initialized")
		
		# Set window properties
		self.setWindowTitle("Album Explorer")
		self.setMinimumSize(1200, 800)
		
		# Enable Qt's widget double buffering
		self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
		self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
		
		# Create central widget and layout
		central_widget = QWidget()
		central_widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
		self.setCentralWidget(central_widget)
		self.main_layout = QVBoxLayout(central_widget)
		self.main_layout.setContentsMargins(10, 10, 10, 10)
		self.main_layout.setSpacing(10)
		
		# Create view container with improved rendering
		self.view_container = QWidget()
		self.view_container.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
		self.view_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.view_layout = QVBoxLayout(self.view_container)
		self.view_layout.setContentsMargins(0, 0, 0, 0)
		self.view_layout.setSpacing(0)
		
		# Initialize managers
		self.data_interface = DataInterface(db_session)
		self.view_manager = ViewManager(self.data_interface)
		self.error_manager = ErrorManager()
		self.responsive_manager = ResponsiveManager()
		
		# Create status bar
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		
		# Setup error handling and responsive design
		self._setup_error_handling()
		self._setup_responsive_design()
		
		# Create view controls at the top
		self._create_view_controls()
		
		# Add view container to main layout
		self.main_layout.addWidget(self.view_container)
		
		# Initialize data and view
		self._initialize_application()

	def _initialize_application(self):
		"""Initialize application data and view."""
		try:
			# Update data first
			self.view_manager.update_data()
			logging.info(f"Loaded {len(self.view_manager.nodes)} nodes")
			
			# Let view manager handle the initial view
			result = self.view_manager.switch_view(ViewType.TABLE)
			
			# Show success message
			self.status_bar.showMessage("Application initialized successfully")
			
		except Exception as e:
			logging.error(f"Error during initialization: {str(e)}")
			self.status_bar.showMessage(f"Error during initialization: {str(e)}")
			self.error_manager.handle_error(e, ErrorContext(
				view_type="initialization",
				operation="application_init",
				data={}
			))


	def _create_view_controls(self):
		"""Create view type selection controls."""
		controls = QHBoxLayout()
		view_label = QLabel("View Type:")
		self.view_selector = QComboBox()
		self.view_selector.addItems([vt.value for vt in ViewType])
		self.view_selector.currentTextChanged.connect(self._handle_view_change)
		controls.addWidget(view_label)
		controls.addWidget(self.view_selector)
		controls.addStretch()
		self.main_layout.addLayout(controls)

	def _initialize_view(self, view_type: ViewType, transition_data: Optional[Dict] = None):
		"""Initialize view with improved rendering stability."""
		gui_logger.debug(f"Initializing view: {view_type}")
		try:
			# Store old view for smooth transition
			old_view = None
			if self.view_layout.count() > 0:
				old_view = self.view_layout.itemAt(0).widget()
				if old_view:
					old_view.setUpdatesEnabled(False)
			
			# Create new view
			view = create_view(view_type, self)
			if view:
				# Configure view
				view.setUpdatesEnabled(False)
				view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
				
				# Update view with data
				print(f"Initializing {view_type} view with {len(self.view_manager.nodes)} nodes and {len(self.view_manager.edges)} edges")
				view.update_data(self.view_manager.nodes, self.view_manager.edges)
				
				# Connect signals
				view.selectionChanged.connect(self._handle_selection_change)
				
				# Add to layout
				self.view_layout.addWidget(view)
				view.hide()  # Hide initially
				
				# Apply transition
				if transition_data:
					view.apply_transition(transition_data)
				
				# Remove old view after new one is ready
				if old_view:
					old_view.hide()
					old_view.deleteLater()
				
				# Show new view
				view.show()
				view.setUpdatesEnabled(True)
				
				# Store reference
				self.current_view = view
				
				logging.info(f"View initialized: {view_type}")
				self.status_bar.showMessage(f"View initialized: {view_type}")
		except Exception as e:
			logging.error(f"Error initializing view: {str(e)}")
			self.status_bar.showMessage(f"Error initializing view: {str(e)}")
			self.error_manager.handle_error(e, ErrorContext(
				view_type=str(view_type),
				operation="view_initialization",
				data={}
			))


	def _handle_view_change(self, view_type_str: str):
		"""Handle view type changes."""
		gui_logger.debug(f"Handling view change: {view_type_str}")
		try:
			view_type = ViewType(view_type_str)
			logging.info(f"Switching to view type: {view_type}")
			
			# Get transition result from view manager
			result = self.view_manager.switch_view(view_type)
			
			# Initialize new view with transition data
			self._initialize_view(view_type, result.get('transition'))
			
			# No need to set current_view here as it's now handled in _initialize_view
			
			self.status_bar.showMessage(f"Switched to {view_type.value} view")
		except Exception as e:
			logging.error(f"Error switching view: {str(e)}")
			self.status_bar.showMessage(f"Error switching view: {str(e)}")
			self.error_manager.handle_error(e, ErrorContext(
				view_type=view_type_str,
				operation="view_switch",
				data={}
			))



	def _handle_selection_change(self, selected_ids: set):
		"""Handle selection changes in the current view."""
		gui_logger.debug(f"Handling selection change: {selected_ids}")
		try:
			self.view_manager.select_nodes(selected_ids)
			self.status_bar.showMessage(f"Selected {len(selected_ids)} items")
		except Exception as e:
			logging.error(f"Error handling selection change: {str(e)}")
			self.status_bar.showMessage(f"Error handling selection: {str(e)}")

	def _setup_error_handling(self):
		def handle_error(error_info):
			self.status_bar.showMessage(f"Error: {error_info.message}", 5000)
		for category in ErrorCategory:
			self.error_manager.register_handler(category, handle_error)

	def _setup_responsive_design(self):
		self.responsive_manager.set_base_window_size(QSize(1200, 800))
		self.responsive_manager.register_component(self.view_container, "view_container")
		self.responsive_manager.register_component(self.status_bar, "status_bar")

	def load_data(self):
		gui_logger.debug("Loading data...")
		try:
			self.view_manager.update_data()
			if hasattr(self, 'current_view'):
				self.current_view.update_data(
					self.view_manager.nodes,
					self.view_manager.edges
				)
			msg = "Data loaded successfully"
			logging.info(msg)
			self.status_bar.showMessage(msg)
		except Exception as e:
			msg = f"Error loading data: {str(e)}"
			logging.error(msg)
			self.status_bar.showMessage(msg)

	def resizeEvent(self, event: QResizeEvent):
		"""Handle resize with improved stability."""
		gui_logger.debug(f"Resize event: {event.size()}")
		if hasattr(self, 'current_view'):
			self.current_view.setUpdatesEnabled(False)
			
		super().resizeEvent(event)
		
		if hasattr(self, 'current_view'):
			result = self.view_manager.update_dimensions(
				event.size().width(),
				event.size().height()
			)
			self.current_view.update_data(
				self.view_manager.nodes,
				self.view_manager.edges
			)
			self.current_view.setUpdatesEnabled(True)

	def keyPressEvent(self, event):
		"""Handle key press events and forward them to current view."""
		gui_logger.debug(f"Key press event: {event.key()}")
		if hasattr(self, 'current_view'):
			# Forward event to current view
			self.current_view.keyPressEvent(event)
		else:
			super().keyPressEvent(event)