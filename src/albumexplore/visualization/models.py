"""Models for visualization system."""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Point:
    """2D point representation."""
    x: float = 0.0
    y: float = 0.0

@dataclass
class Viewport:
    """Viewport configuration."""
    x: float = 0.0
    y: float = 0.0
    width: float = 800.0
    height: float = 600.0
    zoom: float = 1.0

@dataclass
class VisualNode:
    """Visual node representation."""
    id: str
    label: str
    size: float = 10.0
    color: str = "#4287f5"  # Default blue
    shape: str = "circle"
    data: Dict[str, Any] = field(default_factory=dict)
    opacity: float = 1.0
    selected: bool = False
    visible: bool = True
    pos: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})

@dataclass
class VisualEdge:
    """Visual edge representation."""
    source: str
    target: str
    weight: float = 1.0
    thickness: float = 1.0
    color: str = "#cccccc"  # Default gray
    data: Dict[str, Any] = field(default_factory=dict)
    opacity: float = 1.0
    visible: bool = True


