from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Point:
	x: float
	y: float

@dataclass
class VisualNode:
	id: str
	label: str
	size: float = 1.0
	color: str = "#4287f5"
	shape: str = "circle"
	data: Optional[Dict[str, Any]] = None

@dataclass
class VisualEdge:
	source: str
	target: str
	weight: float = 1.0
	thickness: float = 1.0
	color: str = "#999999"
	data: Optional[Dict[str, Any]] = None


