import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from albumexplore.database import Base, models
from albumexplore.visualization.data_interface import DataInterface

@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine) -> Session:
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def categories(session):
    metal = models.TagCategory(id="metal", name="Metal")
    rock = models.TagCategory(id="rock", name="Rock")
    session.add_all([metal, rock])
    session.commit()
    return {"metal": metal, "rock": rock}

def test_create_tag(session, categories):
    """Test tag creation through data interface."""
    tag1 = models.Tag(
        id="metal",
        name="metal",
        category_id="metal", 
        normalized_name="metal",
        is_canonical=True
    )
    session.add(tag1)
    session.commit()

    # Verify tag was created
    tag = session.query(models.Tag).filter_by(name="metal").first()
    assert tag is not None
    assert tag.name == "metal" 
    assert tag.category_id == "metal"