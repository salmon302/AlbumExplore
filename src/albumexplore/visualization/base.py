from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..database import models
from .models import VisualNode, VisualEdge
from .layout import ForceDirectedLayout, ForceParams

class VisualizationBase(ABC):

	"""Base class for all visualizations."""
	
	def __init__(self):
		self.nodes: List[VisualNode] = []
		self.edges: List[VisualEdge] = []
		self.view_state: Dict[str, Any] = {}
	
	@abstractmethod
	def process_data(self, albums: List[models.Album], tags: List[models.Tag]) -> None:
		"""Process raw data into visualization format."""
		pass
	
	@abstractmethod
	def update_layout(self) -> None:
		"""Update visualization layout."""
		pass
	
	@abstractmethod
	def apply_filters(self, filters: Dict[str, Any]) -> None:
		"""Apply filters to the visualization."""
		pass

class NetworkGraph(VisualizationBase):
	"""Force-directed network graph visualization."""
	
	def __init__(self):
		super().__init__()
		self.layout = ForceDirectedLayout()
		self.width = 800.0
		self.height = 600.0
		self.is_layout_initialized = False
	
	def process_data(self, albums: List[models.Album], tags: List[models.Tag]) -> None:
		# Process albums into nodes
		for album in albums:
			self.nodes.append(VisualNode(
				id=album.id,
				label=f"{album.artist} - {album.title}",
				size=len(album.tags),
				color=self._get_primary_genre_color(album),
				shape="circle" if album.length == "LP" else "square",
				data={"type": "album", "album": album}
			))
		
		# Create edges based on shared tags
		self._create_album_connections(albums)
	
	def update_layout(self) -> None:
		"""Update force-directed layout."""
		if not self.is_layout_initialized:
			self.layout.initialize_positions(self.nodes, self.width, self.height)
			self.is_layout_initialized = True
		
		return self.layout.apply_forces(self.nodes, self.edges)
	
	def apply_filters(self, filters: Dict[str, Any]) -> None:
		# Placeholder for filter implementation
		pass
	
	def _get_primary_genre_color(self, album: models.Album) -> str:
		# Placeholder for genre color mapping
		return "#808080"
	
	def _create_album_connections(self, albums: List[models.Album]) -> None:
		# Create edges between albums based on shared tags
		for i, album1 in enumerate(albums):
			for album2 in albums[i+1:]:
				shared_tags = set(t.id for t in album1.tags) & set(t.id for t in album2.tags)
				if shared_tags:
					self.edges.append(VisualEdge(
						source=album1.id,
						target=album2.id,
						weight=len(shared_tags),
						color="#666666",
						thickness=len(shared_tags) * 0.5,
						data={"shared_tags": list(shared_tags)}
					))

class TableView(VisualizationBase):
	"""Table visualization with sorting capabilities."""
	
	def __init__(self):
		super().__init__()
		self.sort_column = None
		self.sort_direction = "asc"  # "asc" or "desc"
		self.sortable_columns = ["artist", "title", "year"]
	
	def process_data(self, albums: List[models.Album], tags: List[models.Tag]) -> None:
		# Process albums into table rows
		for album in albums:
			self.nodes.append(VisualNode(
				id=album.id,
				label=album.title,
				size=1,
				color="",
				shape="row",
				data={
					"type": "row",
					"artist": album.artist,
					"title": album.title,
					"year": album.release_year,
					"tags": [t.name for t in album.tags]
				}
			))
		# Apply sorting if sort column is set
		if self.sort_column:
			self._sort_nodes()
	
	def set_sort(self, column: str, direction: Optional[str] = None) -> None:
		"""Set sorting column and direction."""
		if column not in self.sortable_columns:
			return
			
		if self.sort_column == column and direction is None:
			# Toggle direction if same column
			self.sort_direction = "desc" if self.sort_direction == "asc" else "asc"
		else:
			self.sort_column = column
			self.sort_direction = direction if direction else "asc"
		
		self._sort_nodes()
	
	def _sort_nodes(self) -> None:
		"""Sort nodes based on current sort column and direction."""
		if not self.sort_column:
			return
			
		reverse = self.sort_direction == "desc"
		self.nodes.sort(
			key=lambda node: node.data.get(self.sort_column, ""),
			reverse=reverse
		)
	
	def update_layout(self) -> None:
		# Table doesn't need layout updates
		pass
	
	def apply_filters(self, filters: Dict[str, Any]) -> None:
		# Placeholder for table filtering
		pass