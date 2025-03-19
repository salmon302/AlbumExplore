"""Tests for the Table View component."""

import sys
import pytest
from PyQt6.QtWidgets import QApplication, QAbstractItemView
from PyQt6.QtCore import Qt, QModelIndex

from albumexplore.gui.views.table_view import TableView


@pytest.fixture(scope="module")
def app():
    """Create a Qt application."""
    return QApplication(sys.argv)


@pytest.fixture
def table_view(app):
    """Create a table view widget."""
    view = TableView()
    yield view
    view.deleteLater()


def test_table_view_creation(table_view):
    """Test that the table view can be created."""
    assert table_view is not None
    # Check that table widget exists and has expected properties
    assert hasattr(table_view, 'table')
    assert table_view.table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
    assert table_view.table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    assert table_view.table.horizontalHeader().sectionsClickable() is True


def test_update_data_table(table_view):
    """Test that the table view can update with data."""
    # Sample test data with some albums
    test_data = {
        'rows': [
            {
                'id': '1', 
                'artist': 'Artist 1', 
                'album': 'Album 1',
                'year': 2023,
                'genre': 'Progressive Rock',
                'country': 'USA',
                'tags': ['rock', 'prog']
            },
            {
                'id': '2', 
                'artist': 'Artist 2', 
                'album': 'Album 2',
                'year': 2024,
                'genre': 'Progressive Metal',
                'country': 'Sweden',
                'tags': ['metal', 'prog']
            }
        ]
    }
    
    # Update the view with test data
    table_view.update_data(test_data)
    
    # Verify the table was updated
    assert table_view.table.rowCount() == 2
    assert table_view.table.columnCount() == 6
    
    # Check cell data
    assert table_view.table.item(0, 0).text() == 'Artist 1'
    assert table_view.table.item(0, 1).text() == 'Album 1'
    assert table_view.table.item(0, 2).text() == '2023'
    assert table_view.table.item(0, 3).text() == 'Progressive Rock'
    assert table_view.table.item(0, 4).text() == 'USA'
    assert table_view.table.item(0, 5).text() == 'rock, prog'
    
    assert table_view.table.item(1, 0).text() == 'Artist 2'
    assert table_view.table.item(1, 1).text() == 'Album 2'
    
    # Check ID storage in user role
    assert table_view.table.item(0, 0).data(Qt.ItemDataRole.UserRole) == '1'
    assert table_view.table.item(1, 0).data(Qt.ItemDataRole.UserRole) == '2'


def test_selection(table_view):
    """Test selection functionality in table view."""
    # First update with data
    test_data = {
        'rows': [
            {
                'id': '1', 
                'artist': 'Artist 1', 
                'album': 'Album 1',
                'year': 2023,
            },
            {
                'id': '2', 
                'artist': 'Artist 2', 
                'album': 'Album 2',
                'year': 2024,
            },
            {
                'id': '3', 
                'artist': 'Artist 3', 
                'album': 'Album 3',
                'year': 2025,
            }
        ],
        'selected_ids': set(['2'])  # Select the second row
    }
    
    # Clear any previous selection
    table_view.table.clearSelection()
    table_view.update_data(test_data)
    
    # Check if the correct row is selected (row with id='2', index 1)
    assert table_view.table.item(1, 0).isSelected() is True
    assert table_view.table.item(0, 0).isSelected() is False
    assert table_view.table.item(2, 0).isSelected() is False