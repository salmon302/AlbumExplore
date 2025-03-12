"""Spatial indexing for efficient node lookup."""
from typing import List, Dict, Set
from PyQt6.QtCore import QRectF
from .models import VisualNode

class SpatialGrid:
    """Simple spatial grid for optimized collision detection."""
    
    def __init__(self, width: float, height: float, cell_size: float):
        self.cell_size = cell_size
        self.width = width
        self.height = height
        self.cols = int(width / cell_size) + 1
        self.rows = int(height / cell_size) + 1
        self.cells: Dict[int, List[VisualNode]] = {}
    
    def _get_cell_key(self, x: float, y: float) -> int:
        """Get cell index from coordinates."""
        col = int(x / self.cell_size)
        row = int(y / self.cell_size)
        return row * self.cols + col
    
    def insert(self, node: VisualNode) -> None:
        """Insert node into spatial grid."""
        x = node.data.get('x', 0)
        y = node.data.get('y', 0)
        cell_key = self._get_cell_key(x, y)
        
        if cell_key not in self.cells:
            self.cells[cell_key] = []
        self.cells[cell_key].append(node)
    
    def query(self, rect: QRectF) -> List[VisualNode]:
        """Query nodes within rectangle."""
        start_col = max(0, int(rect.left() / self.cell_size))
        start_row = max(0, int(rect.top() / self.cell_size))
        end_col = min(self.cols - 1, int(rect.right() / self.cell_size))
        end_row = min(self.rows - 1, int(rect.bottom() / self.cell_size))
        
        result = []
        seen = set()
        
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell_key = row * self.cols + col
                if cell_key in self.cells:
                    for node in self.cells[cell_key]:
                        if node.id not in seen:
                            seen.add(node.id)
                            result.append(node)
        
        return result