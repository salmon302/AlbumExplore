"""Base test case implementation."""
import unittest
from PyQt6.QtWidgets import QApplication
from albumexplore.database import init_db, get_session

class BaseTestCase(unittest.TestCase):
    """Base test case with PyQt setup."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Initialize application
        cls.app = QApplication([])
        
        # Initialize database in memory for testing
        init_db("sqlite:///:memory:")
        cls.session = get_session()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if hasattr(cls, 'session') and cls.session:
            cls.session.close()
        
        if hasattr(cls, 'app') and cls.app:
            cls.app.quit()
    
    def setUp(self):
        """Set up each test."""
        # Clear any existing data
        self.session.execute("DELETE FROM albums")
        self.session.execute("DELETE FROM tags")
        self.session.commit()
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear test data
        self.session.rollback()