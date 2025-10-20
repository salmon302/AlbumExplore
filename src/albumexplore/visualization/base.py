from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..database import models
from .models import VisualNode, VisualEdge

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
					"artist": album.pa_artist_name_on_album,
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