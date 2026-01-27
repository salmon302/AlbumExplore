from typing import List, Dict, Any, Set
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel

class AlbumTableModel(QAbstractTableModel):
    """Table model for album data."""
    
    # Define columns and their indices
    COL_FAV = 0
    COL_ARTIST = 1
    COL_ALBUM = 2
    COL_YEAR = 3
    COL_GENRE = 4
    COL_COUNTRY = 5
    COL_VOCAL = 6
    COL_TAGS = 7
    COL_PLAYS = 8
    COL_LISTENERS = 9
    
    HEADERS = [
        '', 'Artist', 'Album', 'Year', 'Genre', 
        'Country', 'Vocal Style', 'Tags', 'Plays', 'Listeners'
    ]
    
    def __init__(self, favorites_manager=None):
        super().__init__()
        self._data: List[Dict[str, Any]] = []
        self._fav_mgr = favorites_manager
        
    def set_data(self, data: List[Dict[str, Any]]):
        """Update model data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)
        
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row_idx = index.row()
        col_idx = index.column()
        item = self._data[row_idx]
        
        if role == Qt.ItemDataRole.UserRole:
            # Return full item data for UserRole
            return item
        
        if role == Qt.ItemDataRole.UserRole + 1:
            # Return ID
            return item.get('id')

        # Formatting for display
        if role == Qt.ItemDataRole.DisplayRole:
            if col_idx == self.COL_ARTIST:
                return str(item.get('artist', ''))
            elif col_idx == self.COL_ALBUM:
                return str(item.get('album', ''))
            elif col_idx == self.COL_YEAR:
                val = item.get('year')
                return str(val) if val is not None else ""
            elif col_idx == self.COL_GENRE:
                return str(item.get('genre', ''))
            elif col_idx == self.COL_COUNTRY:
                return str(item.get('country', ''))
            elif col_idx == self.COL_VOCAL:
                return str(item.get('vocal_style', ''))
            elif col_idx == self.COL_TAGS:
                tags = item.get('tags', [])
                if isinstance(tags, list):
                    return ", ".join(str(t) for t in tags[:5]) + ("..." if len(tags) > 5 else "")
                return str(tags)
            elif col_idx == self.COL_PLAYS:
                val = item.get('playcount')
                return f"{val:,}" if val is not None else ""
            elif col_idx == self.COL_LISTENERS:
                val = item.get('listeners')
                return f"{val:,}" if val is not None else ""
            elif col_idx == self.COL_FAV:
                # Handled by delegate or decoration role?
                # Using DisplayRole for sorting logic if needed, but usually empty string or special char
                if self._fav_mgr:
                    aid = item.get('id')
                    return "★" if self._fav_mgr.is_favorite(aid) else "☆"
                return ""

        # Raw values for sorting
        if role == Qt.ItemDataRole.EditRole: # Use EditRole for sorting with proxy
            if col_idx == self.COL_PLAYS:
                return item.get('playcount') or 0
            elif col_idx == self.COL_LISTENERS:
                return item.get('listeners') or 0
            elif col_idx == self.COL_YEAR:
                return item.get('year') or 0
            elif col_idx == self.COL_TAGS:
                 tags = item.get('tags', [])
                 return ", ".join(str(t) for t in tags)
            elif col_idx == self.COL_FAV:
                if self._fav_mgr:
                    return self._fav_mgr.is_favorite(item.get('id'))
                return False
            # Fallback to string representation for others
            return self.data(index, Qt.ItemDataRole.DisplayRole)
            
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col_idx in [self.COL_YEAR, self.COL_PLAYS, self.COL_LISTENERS]:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if col_idx == self.COL_FAV:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
        return None

    def get_row_data(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None

class AlbumProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering and sorting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_text = ""
        self.fav_only = False
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    
    def set_filter_text(self, text: str):
        self.filter_text = text.lower()
        self.invalidateFilter()
        
    def set_fav_only(self, enabled: bool):
        self.fav_only = enabled
        self.invalidateFilter()
        
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        # Get source model
        model = self.sourceModel()
        if not model:
            return True
            
        # Check Favorites first (fastest)
        if self.fav_only:
            idx = model.index(source_row, AlbumTableModel.COL_FAV, source_parent)
            is_fav = model.data(idx, Qt.ItemDataRole.EditRole) # boolean
            if not is_fav:
                return False
                
        # Check text filter
        if not self.filter_text:
            return True
            
        # Check main columns
        # We can optimize by checking 'user role' which has the raw dict
        idx = model.index(source_row, 0, source_parent)
        item_data = model.data(idx, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return False
            
        # Searchable text construction
        # This matches the previous logic
        searchable_parts = [
            str(item_data.get('artist', '')),
            str(item_data.get('album', '')),
            str(item_data.get('year', '')),
            str(item_data.get('genre', '')),
            str(item_data.get('country', '')),
            str(item_data.get('vocal_style', '')),
            ', '.join(str(t) for t in item_data.get('tags', []))
        ]
        combined_text = ' '.join(searchable_parts).lower()
        
        # Verify all tokens (AND logic)
        tokens = self.filter_text.split()
        return all(token in combined_text for token in tokens)
        
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        # Use EditRole for proper sorting (numbers vs strings)
        left_data = self.sourceModel().data(left, Qt.ItemDataRole.EditRole)
        right_data = self.sourceModel().data(right, Qt.ItemDataRole.EditRole)
        
        if left_data is None: left_data = ""
        if right_data is None: right_data = ""
        
        try:
            return left_data < right_data
        except TypeError:
            return str(left_data) < str(right_data)
