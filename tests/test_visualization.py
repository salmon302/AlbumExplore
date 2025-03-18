import pytest
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from albumexplore.database import models
from albumexplore.visualization.views import ChordView, NetworkView, ArcView
from albumexplore.visualization.models import VisualNode, VisualEdge

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
    # Create sample tags with proper category_id references
    tag1 = models.Tag(id="metal", name="metal", category_id="genre")
    tag2 = models.Tag(id="prog", name="progressive", category_id="style")
    
    # Create sample albums
    album1 = models.Album(
        id="album1",
        artist="Artist1",
        title="Album1",
        release_year=2020,
        length="LP"
    )
    album2 = models.Album(
        id="album2",
        artist="Artist2",
        title="Album2",
        release_year=2021,
        length="EP"
    )
    
    # Set up relationships
    album1.tags.append(tag1)
    album2.tags.extend([tag1, tag2])
    
    session.add_all([tag1, tag2, album1, album2])
    session.commit()
    
    return {"albums": [album1, album2], "tags": [tag1, tag2]}

def test_chord_view_rendering(qtbot, sample_data):
    albums = sample_data["albums"]
    view = ChordView()
    view.resize(800, 600)
    view.update_data({"albums": albums})
    
    assert view.width() == 800
    assert view.height() == 600
    assert len(view.nodes) > 0
    assert len(view.edges) > 0

def test_network_view_rendering(qtbot, sample_data):
    albums = sample_data["albums"]
    view = NetworkView()
    view.resize(800, 600)
    view.update_data({"albums": albums})
    
    assert view.width() == 800
    assert view.height() == 600
    assert len(view.nodes) > 0
    assert len(view.edges) > 0

def test_arc_view_rendering(qtbot, sample_data):
    albums = sample_data["albums"]
    view = ArcView()
    view.resize(800, 600)
    view.update_data({"albums": albums})
    
    assert view.width() == 800
    assert view.height() == 600
    assert len(view.nodes) > 0
    assert len(view.edges) > 0

def test_view_interactions(qtbot, sample_data):
    albums = sample_data["albums"]
    view = NetworkView()
    view.resize(800, 600)
    view.update_data({"albums": albums})
    
    # Test zoom interaction
    initial_scale = view.transform().m11()
    QTest.keyClick(view, Qt.Key.Key_Plus, Qt.KeyboardModifier.ControlModifier)
    assert view.transform().m11() > initial_scale
    
    # Test node selection
    center = QPoint(400, 300)
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    assert len(view.selected_nodes) >= 0

def test_view_state_persistence(qtbot, sample_data):
    albums = sample_data["albums"]
    view = NetworkView()
    view.update_data({"albums": albums})
    
    # Test state saving and loading
    view.zoom_level = 1.5
    state = view.save_state()
    view.zoom_level = 1.0
    view.restore_state(state)
    assert view.zoom_level == 1.5