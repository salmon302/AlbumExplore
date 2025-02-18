from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QWidget
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Tuple, Optional, Set

class ScreenSize(Enum):
	SMALL = "small"      # < 768px
	MEDIUM = "medium"    # 768px - 1024px
	LARGE = "large"      # > 1024px

class Orientation(Enum):
	PORTRAIT = "portrait"
	LANDSCAPE = "landscape"

@dataclass
class ComponentScale:
	widget: QWidget
	base_size: QSize
	min_scale: float = 0.5
	max_scale: float = 2.0

@dataclass
class LayoutConfig:
	"""Configuration for responsive layout."""
	node_size_scale: float
	label_visibility: bool
	detail_level: str
	controls_position: str
	sidebar_width: int
	edge_thickness_scale: float = 1.0  # Set default to 1.0 to maintain base thickness

class ResponsiveManager:
	"""Manages responsive layout adjustments for visualizations."""
	
	def __init__(self):
		self.current_size: ScreenSize = ScreenSize.LARGE
		self.current_orientation: Orientation = Orientation.LANDSCAPE
		self._layout_configs: Dict[ScreenSize, LayoutConfig] = self._init_configs()
		self._base_window_size: QSize = QSize(1200, 800)
		self._min_window_size: QSize = QSize(800, 600)
		self._max_window_size: QSize = QSize(3840, 2160)
		self._components: Dict[str, ComponentScale] = {}
		self._width_scale: float = 1.0
		self._height_scale: float = 1.0

	def _init_configs(self) -> Dict[ScreenSize, LayoutConfig]:
		"""Initialize layout configurations for different screen sizes."""
		return {
			ScreenSize.SMALL: LayoutConfig(
				node_size_scale=0.7,
				label_visibility=False,
				detail_level="low",
				controls_position="bottom",
				sidebar_width=0,  # Full width in small screens
				edge_thickness_scale=0.7  # Scale down edges for small screens
			),
			ScreenSize.MEDIUM: LayoutConfig(
				node_size_scale=0.85,
				label_visibility=True,
				detail_level="medium",
				controls_position="right",
				sidebar_width=250,
				edge_thickness_scale=1.0  # Keep base thickness
			),
			ScreenSize.LARGE: LayoutConfig(
				node_size_scale=1.0,
				label_visibility=True,
				detail_level="high",
				controls_position="right",
				sidebar_width=300,
				edge_thickness_scale=1.0  # Keep base thickness
			)
		}

	def update_screen_size(self, width: int, height: int) -> Tuple[ScreenSize, LayoutConfig]:
		"""Update current screen size and return appropriate layout config."""
		# Determine orientation
		self.current_orientation = (
			Orientation.PORTRAIT if height > width else Orientation.LANDSCAPE
		)
		
		# Determine screen size
		if width < 768:
			self.current_size = ScreenSize.SMALL
		elif width < 1024:
			self.current_size = ScreenSize.MEDIUM
		else:
			self.current_size = ScreenSize.LARGE
			
		return self.current_size, self._layout_configs[self.current_size]

	def get_layout_adjustments(self, view_type: str) -> Dict[str, Any]:
		"""Get layout adjustments for current screen size and view type."""
		config = self._layout_configs[self.current_size]
		
		adjustments = {
			"node_size_scale": config.node_size_scale,
			"edge_thickness_scale": config.edge_thickness_scale,
			"show_labels": config.label_visibility,
			"detail_level": config.detail_level,
			"controls_position": config.controls_position,
			"sidebar_width": config.sidebar_width
		}
		
		# View-specific adjustments
		if self.current_size == ScreenSize.SMALL:
			if view_type == "table":
				adjustments["columns"] = ["title", "artist"]  # Reduced columns
			elif view_type in ["chord", "arc"]:
				adjustments["node_size_scale"] *= 0.8  # Further reduce size
		
		return adjustments

	def get_optimal_dimensions(self, container_width: int, container_height: int) -> Dict[str, int]:
		"""Calculate optimal dimensions for visualization container."""
		# Update screen size and orientation first
		self.update_screen_size(container_width, container_height)
		config = self._layout_configs[self.current_size]
		
		# In portrait mode, use full container width
		if self.current_orientation == Orientation.PORTRAIT:
			return {
				"width": container_width,
				"height": max(300, container_height),
				"sidebar_width": 0
			}
		
		# For all landscape modes, account for sidebar
		available_width = container_width - config.sidebar_width
		return {
			"width": max(300, available_width),
			"height": max(300, container_height),
			"sidebar_width": config.sidebar_width
		}

	def set_base_window_size(self, size: QSize) -> None:
		"""Set the base window size for scaling calculations."""
		self._base_window_size = size

	def set_min_window_size(self, size: QSize) -> None:
		"""Set the minimum window size."""
		self._min_window_size = size

	def set_max_window_size(self, size: QSize) -> None:
		"""Set the maximum window size."""
		self._max_window_size = size

	def get_base_window_size(self) -> QSize:
		"""Get the base window size."""
		return self._base_window_size

	def register_component(self, widget: QWidget, name: str) -> None:
		"""Register a component for responsive scaling."""
		self._components[name] = ComponentScale(
			widget=widget,
			base_size=widget.size()
		)

	def update_scale_factors(self, width_scale: float, height_scale: float) -> None:
		"""Update scale factors and apply to registered components."""
		self._width_scale = max(0.5, min(width_scale, 2.0))
		self._height_scale = max(0.5, min(height_scale, 2.0))
		
		for component in self._components.values():
			new_width = int(component.base_size.width() * self._width_scale)
			new_height = int(component.base_size.height() * self._height_scale)
			component.widget.resize(new_width, new_height)

	def get_current_scale_factors(self) -> Tuple[float, float]:
		"""Get current width and height scale factors."""
		return self._width_scale, self._height_scale


