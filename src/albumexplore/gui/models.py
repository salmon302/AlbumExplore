"""GUI models for data representation."""
from typing import List, Any, Dict
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex

class AlbumTableModel(QAbstractTableModel):
    """Table model for album data."""
    
    COLUMNS = ["Artist", "Album", "Year", "Genre", "Country", "Tags"]
    
    def __init__(self):
        super().__init__()
        self._data: List[Dict[str, Any]] = []
    
    def rowCount(self, parent=None) -> int:
        """Get number of rows."""
        return len(self._data)
    
    def columnCount(self, parent=None) -> int:
        """Get number of columns."""
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole) -> Any:
        """Get data for cell."""
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            row = self._data[index.row()]
            column = self.COLUMNS[index.column()].lower()
            return str(row.get(column, ""))
            
        if role == Qt.ItemDataRole.UserRole:
            return self._data[index.row()].get("id")
            
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole) -> str:
        """Get header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Get item flags."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    
    def set_data(self, data: List[Dict[str, Any]]):
        """Update model data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort table data."""
        self.beginResetModel()
        column_name = self.COLUMNS[column].lower()
        reverse = order == Qt.SortOrder.DescendingOrder
        self._data.sort(key=lambda x: str(x.get(column_name, "")), reverse=reverse)
        self.endResetModel()