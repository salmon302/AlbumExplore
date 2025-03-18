"""Integration tests for the GUI components."""
import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from albumexplore.gui.app import AlbumExplorer
from albumexplore.gui.models import AlbumTableModel
from albumexplore.database import Base, models, set_test_session, clear_test_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def categories(session):
    # Create tag categories
    genre = models.TagCategory(id="genre", name="Genre")
    style = models.TagCategory(id="style", name="Style")
    session.add_all([genre, style])
    session.commit()
    return {"genre": genre, "style": style}

@pytest.fixture
def sample_data(session, categories):
    # Create sample tags with proper category references
    tag1 = models.Tag(id="metal", name="Metal", category_id="genre")
    tag2 = models.Tag(id="progressive", name="Progressive", category_id="style")
    
    # Create sample albums
    album1 = models.Album(
        id="album1",
        artist="Dream Theater",
        title="Images and Words",
        release_year=1992,
        vocal_style="clean"
    )
    album2 = models.Album(
        id="album2",
        artist="Tool",
        title="Lateralus",
        release_year=2001,
        vocal_style="mixed"
    )
    
    # Set up relationships
    album1.tags.extend([tag1, tag2])
    album2.tags.extend([tag1])
    
    session.add_all([tag1, tag2, album1, album2])
    session.commit()
    return {"tags": [tag1, tag2], "albums": [album1, album2]}

@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication(sys.argv)

@pytest.fixture
def main_window(app, session, sample_data):
    """Create main application window with test session."""
    # Set the test session before creating the window
    set_test_session(session)
    window = AlbumExplorer()
    yield window
    # Clean up
    clear_test_session()
    window.close()

def test_table_view(main_window):
    """Test that table view displays data correctly."""
    table = main_window.table_view
    model = table.model()
    
    assert isinstance(model, AlbumTableModel)
    assert model.rowCount() == 2  # Two albums in sample data
    
    # Check table contents
    assert model.data(model.index(0, model.fieldColumn('artist'))) == "Dream Theater"
    assert model.data(model.index(1, model.fieldColumn('artist'))) == "Tool"

def test_tag_explorer(main_window):
    """Test that tag explorer loads and displays tags."""
    explorer = main_window.tag_explorer
    assert explorer is not None
    
    # Check tag categories are displayed
    category_items = explorer.findItems("Genre", Qt.MatchFlag.MatchExactly)
    assert len(category_items) == 1
    
    # Check tags are displayed under categories
    genre_item = category_items[0]
    assert genre_item.childCount() > 0
    assert any(genre_item.child(i).text(0) == "Metal" 
              for i in range(genre_item.childCount()))

def test_filter_panel(main_window):
    """Test filter panel functionality."""
    filter_panel = main_window.filter_panel
    assert filter_panel is not None
    
    # Check year filter
    year_filter = filter_panel.year_filter
    assert year_filter.minimum() <= 1992  # Should include earliest album
    assert year_filter.maximum() >= 2001  # Should include latest album
    
    # Check tag filter
    tag_filter = filter_panel.tag_filter
    assert "Metal" in [tag_filter.itemText(i) 
                      for i in range(tag_filter.count())]
    
def test_view_integration(main_window):
    """Test integration between different views."""
    # Select a tag in explorer
    explorer = main_window.tag_explorer
    metal_items = explorer.findItems("Metal", Qt.MatchFlag.MatchExactly | 
                                          Qt.MatchFlag.MatchRecursive)
    assert len(metal_items) == 1
    
    explorer.setCurrentItem(metal_items[0])
    
    # Check table view updates
    table = main_window.table_view
    model = table.model()
    assert model.rowCount() == 2  # Both albums have Metal tag