from typing import Dict, Any, Optional, List, Set
import math
import random
import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget
from albumexplore.gui.gui_logging import gui_logger

from .models import VisualNode, VisualEdge
from .state import StateManager, ViewType
from .renderer import create_renderer
from .data_interface import DataInterface
from .layout import ForceDirectedLayout, ForceParams
from .optimizations import ViewOptimizer, Viewport
from .responsive import ResponsiveManager, ScreenSize
from .view_integration import ViewIntegrationManager, TransitionType
from .transition_animator import TransitionAnimator

class ViewManager:
	"""Manages visualization views and switching between them."""
	
	def __init__(self, data_interface: DataInterface):
		gui_logger.debug("ViewManager initialized")
		self.data_interface = data_interface
		self.state_manager = StateManager()
		self.nodes: List[VisualNode] = []
		self.edges: List[VisualEdge] = []
		self.layout = ForceDirectedLayout()
		self.optimizer = ViewOptimizer()
		self.viewport = Viewport(x=0, y=0, width=800, height=600, zoom=1.0)
		self.responsive_manager = ResponsiveManager()
		self.integration_manager = ViewIntegrationManager()
		self._layout_cache = {}
		self.transition_animator = TransitionAnimator()
		self._data_cache = {}
		self._current_page = 0
		self._total_items = 0
		self._loading = False
		self._current_view = None
		self._previous_view = None
		self._transition_in_progress = False
		self._update_queued = False
		self._transition_delay = 50
		self._cleanup_timer = QTimer()
		self._cleanup_timer.setSingleShot(True)
		self._cleanup_timer.timeout.connect(self._cleanup_old_view)
		self._setup_sync_handlers()
		self.state_manager.switch_view(ViewType.TABLE)

		
	def _initialize_view(self, view_type: ViewType, transition_data: Optional[Dict] = None) -> None:
		"""Initialize view with proper cleanup."""
		if self._transition_in_progress:
			return

		self._transition_in_progress = True
		gui_logger.debug(f"Initializing view: {view_type}")
		
		try:
			# Store old view
			self._previous_view = self._current_view
			
			# Create new view
			view_class = self.get_view_class(view_type)
			if view_class:
				view = view_class()
				view.setUpdatesEnabled(False)
				view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
				view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
				view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
				view.setAutoFillBackground(True)
				
				# Update view with data
				view.update_data(self.nodes, self.edges)
				
				# Apply transition
				if transition_data:
					view.apply_transition(transition_data)
				
				# Hide old view
				if self._previous_view:
					self._previous_view.hide()
				
				# Show new view
				view.show()
				view.setUpdatesEnabled(True)
				self._current_view = view
				
				# Schedule cleanup of old view
				self._cleanup_timer.start(100)  # 100ms delay for cleanup
				
		except Exception as e:
			gui_logger.error(f"Error initializing view: {str(e)}")
		finally:
			self._transition_in_progress = False

		
	def get_view_class(self, view_type: ViewType):
		"""Get the view class for a given view type."""
		from ..visualization.views import view_map
		return view_map.get(view_type)
		
	def _setup_sync_handlers(self) -> None:
		"""Setup handlers for view synchronization."""
		for view_type in ViewType:
			self.integration_manager.register_sync_handler(
				view_type,
				lambda ids: self._handle_sync_selection(ids, view_type)
			)
	
	def _handle_sync_selection(self, selected_ids: Set[str], source_type: ViewType) -> None:
		"""Handle selection sync from other views with optimized performance."""
		if source_type == self.state_manager.current_view.view_type:
			return
			
		if self.state_manager.current_view.selected_ids == selected_ids:
			return
			
		self.state_manager.select_nodes(selected_ids, add=False)
		self.render_current_view()
	
	def _cleanup_old_view(self):
		"""Clean up old view safely."""
		if self._previous_view:
			self._previous_view.setParent(None)
			self._previous_view.deleteLater()
			self._previous_view = None

	def switch_view(self, view_type: ViewType) -> Dict[str, Any]:
		"""Switch view with proper cleanup."""
		if self._transition_in_progress:
			return {}
			
		# Cancel any ongoing animations
		self.transition_animator.cancel_animations()
		
		# Switch view state
		self.state_manager.switch_view(view_type)
		
		# Prepare transition data
		transition_data = self.integration_manager.prepare_transition(
			self.nodes, self.edges,
			self.state_manager.current_view,
			view_type
		)
		
		# Initialize new view
		self._initialize_view(view_type, transition_data)
		
		result = self.render_current_view()
		result.update({
			'transition': transition_data,
			'shared_state': self.integration_manager.get_shared_state()
		})
		return result

	@property
	def current_view(self):
		return self._current_view

	@current_view.setter 
	def current_view(self, view):
		self._current_view = view




	def update_viewport(self, viewport: Dict[str, float]) -> Dict[str, Any]:
		"""Update viewport parameters and re-render."""
		self.viewport = Viewport(
			x=viewport.get('x', self.viewport.x),
			y=viewport.get('y', self.viewport.y),
			width=viewport.get('width', self.viewport.width),
			height=viewport.get('height', self.viewport.height),
			zoom=viewport.get('zoom', self.viewport.zoom)
		)
		return self.render_current_view()

	def _apply_layout(self) -> None:
		"""Apply force-directed layout to nodes."""
		if self.state_manager.current_view.view_type != ViewType.TABLE:
			try:
				# Use adaptive parameters based on graph size
				params = ForceParams.adaptive(len(self.nodes))
				self.layout = ForceDirectedLayout(params)
				
				# Initialize positions if not already set
				for node in self.nodes:
					if 'x' not in node.data or 'y' not in node.data:
						x = random.uniform(0, self.viewport.width)
						y = random.uniform(0, self.viewport.height)
						self._update_node_position(node, x, y)

				
				positions = self.layout.layout(
					self.nodes, self.edges, 
					self.viewport.width, self.viewport.height
				)
				
				# Update node positions
				for node in self.nodes:
					if node.id in positions:
						pos = positions[node.id]
						self._update_node_position(node, pos.x, pos.y)

			except Exception as e:
				print(f"Layout error: {e}")
				# Fallback to random positions if layout fails
				for node in self.nodes:
					x = random.uniform(0, self.viewport.width)
					y = random.uniform(0, self.viewport.height)
					self._update_node_position(node, x, y)

	
	def update_data(self, filters: Optional[Dict[str, Any]] = None) -> None:
		"""Update visualization data with transition protection."""
		if self._view_transition_in_progress:
			self._update_queued = True
			return
			
		gui_logger.debug("Updating data from data interface")
		try:
			# Reset pagination when filters change
			if filters:
				self._current_page = 0
				self._data_cache.clear()
			
			# Get filtered data with pagination
			cache_key = str(filters) if filters else "default"
			if cache_key not in self._data_cache:
				self._data_cache[cache_key] = []
			
			# Load current page if not in cache
			if self._current_page >= len(self._data_cache[cache_key]):
				albums, total = self.data_interface._get_albums_impl(self._current_page, filters)
				self._total_items = total
				if albums:
					self._data_cache[cache_key].extend(albums)
			
			# Clear existing data
			self.nodes.clear()
			self.edges.clear()
			
			# Process all cached data
			albums = self._data_cache[cache_key]
			
			# Process data according to current view type
			if self.state_manager.current_view.view_type == ViewType.TABLE:
				self._create_table_nodes(albums)
			else:
				self._create_graph_nodes(albums)
				self._create_edges(albums)
				self._apply_layout()
			
			print(f"Created {len(self.nodes)} nodes from {len(albums)} albums")
		except Exception as e:
			gui_logger.error(f"Error updating data: {str(e)}")
			raise

	def _create_table_nodes(self, albums: List[Any]) -> None:
		"""Create nodes for table view."""
		for album in albums:
			node = VisualNode(
				id=album.id,
				label=album.title,
				size=1,
				color="#808080",
				shape="row",
				data={
					"type": "row",
					"artist": album.artist,
					"title": album.title,
					"year": album.release_year,
					"tags": [t.name for t in album.tags] if album.tags else []
				}
			)
			self.nodes.append(node)
		# Apply current sort if any
		self._sort_table_nodes()

	def _create_graph_nodes(self, albums: List[Any]) -> None:
		"""Create nodes for graph-based views."""
		for album in albums:
			# Set size directly to number of tags
			size = len(album.tags)
			
			# Extract album data with safe defaults
			node_data = {
				"type": "album",
				"album": album,
				"artist": album.artist,
				"title": album.title,
				"year": album.release_year,
				"genre": getattr(album, 'genre', ''),  # Safe access to genre
				"tags": [t.name for t in album.tags] if album.tags else [],
				"length": album.length,
				"label": f"{album.artist} - {album.title}"
			}
			
			node = VisualNode(
				id=album.id,
				label=f"{album.artist} - {album.title}",
				size=size,
				color="#4a90e2",
				shape="circle" if album.length == "LP" else "square",
				data=node_data
			)
			self.nodes.append(node)




	def _create_edges(self, albums: List[Any]) -> None:
		"""Create edges with enhanced visibility based on shared tags."""
		self.edges.clear()
		edge_map = {}  # Map to store strongest edge between each pair
		
		# Get album IDs and connections
		album_ids = [a.id for a in albums]
		connections = self.data_interface.get_album_connections(album_ids)
		
		# Process shared tag connections
		for conn in connections:
			if not all(k in conn for k in ['source', 'target', 'weight', 'shared_tags']):
				continue
				
			edge_key = tuple(sorted([conn["source"], conn["target"]]))
			
			if edge_key not in edge_map or conn["weight"] > edge_map[edge_key].weight:
				edge_map[edge_key] = VisualEdge(
					source=conn["source"],
					target=conn["target"],
					weight=conn["weight"],  # Use original weight directly
					color="#333333",
					thickness=max(4.0, conn["weight"] * 2.0),
					data={
						"shared_tags": conn["shared_tags"],
						"weight": conn["weight"],
						"thickness": max(4.0, conn["weight"] * 2.0),
						"base_weight": conn["weight"]
					}
				)

		
		# Process tag relationships
		tag_relationships = self.data_interface.get_tag_relationships(min_strength=0.5)
		album_tag_map = {album.id: {tag.id for tag in album.tags} for album in albums}
		
		for rel in tag_relationships:
			for source_id, source_tags in album_tag_map.items():
				for target_id, target_tags in album_tag_map.items():
					if source_id >= target_id:
						continue
						
					if (rel.tag1_id in source_tags and rel.tag2_id in target_tags) or \
					   (rel.tag2_id in source_tags and rel.tag1_id in target_tags):
						edge_key = tuple(sorted([source_id, target_id]))
						weight = rel.strength * 2.0
						
						if edge_key not in edge_map or weight > edge_map[edge_key].weight:
							edge_map[edge_key] = VisualEdge(
								source=source_id,
								target=target_id,
								weight=weight,
								color="#333333",
								thickness=max(4.0, rel.strength * 4.0),
								data={
									"shared_tags": [rel.tag1_id, rel.tag2_id],
									"weight": weight,
									"thickness": max(4.0, rel.strength * 4.0),
									"base_weight": rel.strength
								}
							)
		
		# Add all edges from the map to the final edges list
		self.edges.extend(edge_map.values())


	
	def _update_node_position(self, node: VisualNode, x: float, y: float) -> None:
		"""Update node position consistently across all position representations."""
		if not isinstance(node.data, dict):
			node.data = {}
		if not hasattr(node, 'pos'):
			node.pos = {}
		
		# Update all position representations
		node.data['x'] = x
		node.data['y'] = y
		node.data['pos'] = {'x': x, 'y': y}
		node.pos['x'] = x
		node.pos['y'] = y

	def render_current_view(self) -> Dict[str, Any]:
		"""Render current view with improved stability."""
		view_type = self.state_manager.current_view.view_type
		
		# Get responsive adjustments once
		adjustments = self.responsive_manager.get_layout_adjustments(str(view_type))
		
		if view_type == ViewType.TABLE:
			renderer = create_renderer(view_type)
			result = renderer.render(self.nodes, self.edges, self.state_manager.current_view)
			result.update({
				"layout_adjustments": adjustments,
				"columns": adjustments.get("columns", [])
			})
			return result
		
		# Cache viewport for repeated use
		viewport = self.viewport
		
		# Use stable sorting for consistent node order
		sorted_nodes = sorted(self.nodes, key=lambda n: n.id)
		
		# Pre-calculate view bounds once
		view_bounds = {
			'x': viewport.x - 100,  # Add margin for smoother rendering
			'y': viewport.y - 100,
			'width': viewport.width + 200,
			'height': viewport.height + 200,
			'zoom': viewport.zoom
		}
		
		# Optimize visibility checks
		visible_nodes = set()
		optimized_nodes = []
		for node in sorted_nodes:
			if self.optimizer.is_node_visible(node, view_bounds):
				optimized_nodes.append(node)
				visible_nodes.add(node.id)
		
		# Only process edges connected to visible nodes
		optimized_edges = [
			edge for edge in self.edges
			if edge.source in visible_nodes and edge.target in visible_nodes
		]
		
		renderer = create_renderer(view_type)
		result = renderer.render(optimized_nodes, optimized_edges, self.state_manager.current_view)
		
		# Add layout information
		result.update({
			"layout_adjustments": adjustments,
			"container_dimensions": {
				"width": viewport.width,
				"height": viewport.height,
				"sidebar_width": adjustments.get("sidebar_width", 0)
			}
		})
		
		return result
	
	def update_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
		"""Update filters and re-render view."""
		self.state_manager.update_filters(filters)
		self.update_data(filters)
		return self.render_current_view()
	
	def update_dimensions(self, width: int, height: int) -> Dict[str, Any]:
		"""Update dimensions with caching for better performance."""
		cache_key = f"{width}_{height}_{self.state_manager.current_view.view_type}"
		
		if cache_key in self._layout_cache:
			cached_data = self._layout_cache[cache_key]
			self.viewport = cached_data["viewport"]
			return cached_data["result"]
		
		screen_size, layout_config = self.responsive_manager.update_screen_size(width, height)
		dimensions = self.responsive_manager.get_optimal_dimensions(width, height)
		
		# Use original width for viewport
		self.viewport = Viewport(
			x=self.viewport.x,
			y=self.viewport.y,
			width=width,  # Use original width instead of adjusted width
			height=dimensions["height"],
			zoom=self.viewport.zoom
		)
		
		self._apply_responsive_layout(layout_config)
		result = self.render_current_view()
		
		# Add container dimensions to result
		result["container_dimensions"] = dimensions
		
		# Cache the result
		self._layout_cache[cache_key] = {
			"viewport": self.viewport,
			"result": result
		}
		
		# Limit cache size
		if len(self._layout_cache) > 100:
			self._layout_cache.pop(next(iter(self._layout_cache)))
		
		return result
	
	def _apply_responsive_layout(self, layout_config) -> None:
		"""Apply responsive layout adjustments with optimizations."""
		show_labels = layout_config.label_visibility
		node_scale = layout_config.node_size_scale

		# Update labels and scale node sizes
		for node in self.nodes:
			# Store original size if not already stored
			if not hasattr(node, '_original_size'):
				node._original_size = 10  # Default size for test nodes
				if 'data' in node.__dict__ and 'album' in node.data:
					node._original_size = len(node.data['album'].tags)

			# Scale node size from original size
			node.size = node._original_size * node_scale

			# Handle labels
			if show_labels:
				if 'data' in node.__dict__ and 'album' in node.data:
					node.label = f"{node.data['album'].artist} - {node.data['album'].title}"
				elif 'type' in node.data and node.data['type'] == 'row':
					node.label = node.data['title']
				else:
					node.label = "Test Node"
			else:
				node.label = ""

		# Reset edges to their initial thickness
		for edge in self.edges:
			if edge.data and 'initial_thickness' in edge.data:
				edge.thickness = edge.data['initial_thickness']

	
	def set_table_sort(self, column: str, direction: Optional[str] = None) -> Dict[str, Any]:
		"""Set table sorting and re-render view."""
		if self.state_manager.current_view.view_type != ViewType.TABLE:
			return self.render_current_view()
		
		# Validate column exists in data
		if not any(node.data.get(column) is not None for node in self.nodes):
			# Invalid column, keep current sort state
			return self.render_current_view()
			
		self.state_manager.set_table_sort(column, direction)
		self._sort_table_nodes()
		return self.render_current_view()

	def load_next_page(self) -> bool:
		"""Load next page of data if available."""
		if self._loading or self._total_items <= len(self.nodes):
			return False
		
		self._loading = True
		try:
			self._current_page += 1
			self.update_data()
			return True
		finally:
			self._loading = False

	def clear_cache(self) -> None:
		"""Clear all data caches."""
		self._data_cache.clear()
		self._layout_cache.clear()
		self.data_interface.clear_caches()
		self._current_page = 0
		self._total_items = 0

	def _sort_table_nodes(self) -> None:
		"""Sort table nodes based on current sort state."""
		if self.state_manager.current_view.view_type != ViewType.TABLE:
			return
			
		sort_info = self.state_manager.get_table_sort()
		if not sort_info["column"]:
			return
			
		def sort_key(node):
			value = node.data.get(sort_info["column"])
			# Always put missing values at the bottom regardless of sort direction
			if value is None or pd.isna(value) or str(value).strip() == '':
				return (1, '') if sort_info["direction"] == "asc" else (1, chr(127))
			return (0, value) if sort_info["direction"] == "asc" else (0, value)
			
		reverse = sort_info["direction"] == "desc"
		self.nodes.sort(key=sort_key, reverse=reverse)


	def select_nodes(self, node_ids: Set[str], add: bool = False) -> Dict[str, Any]:
		"""Select nodes and sync across views with optimized performance."""
		# Quick return if selection hasn't changed
		if not add and self.state_manager.current_view.selected_ids == node_ids:
			return {}
		
		if add and all(node_id in self.state_manager.current_view.selected_ids for node_id in node_ids):
			return {}

		# Update selection state
		self.state_manager.select_nodes(node_ids, add)
		
		# Batch sync selection with other views
		self.integration_manager.sync_selection(
			self.state_manager.current_view.selected_ids,
			self.state_manager.current_view.view_type
		)
		
		# Only render if we have actual changes
		return self.render_current_view()