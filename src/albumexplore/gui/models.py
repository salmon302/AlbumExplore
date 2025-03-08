"""GUI data models."""

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from typing import List, Any, Optional
from albumexplore.visualization.models import VisualNode

class AlbumTableModel(QAbstractTableModel):
    """Model for displaying album data in a table view."""
    
    HEADERS = ["Artist", "Album", "Year", "Tags"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[VisualNode] = []
        
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        if parent.isValid():
            return 0
        return len(self._data)
        
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        if parent.isValid():
            return 0
        return len(self.HEADERS)
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return the data for a given role and index."""
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            node = self._data[index.row()]
            data = node.data
            
            if index.column() == 0:
                return data.get("artist", "")
            elif index.column() == 1:
                return data.get("title", "")
            elif index.column() == 2:
                return data.get("year", "")
            elif index.column() == 3:
                return ", ".join(data.get("tags", []))
                
        elif role == Qt.ItemDataRole.UserRole:
            return self._data[index.row()].id
            
        return None
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return the header data for a given role."""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None
        
    def setData(self, nodes: List[VisualNode]) -> None:
        """Set the model data."""
        self.beginResetModel()
        self._data = nodes
        self.endResetModel()
        
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable