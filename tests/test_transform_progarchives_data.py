"""
Unit tests for the data transformation module.
"""

import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path to find albumexplore modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from albumexplore.scraping.transform_progarchives_data import (
    clean_text,
    convert_duration_to_seconds,
    process_recording_type,
    parse_subgenres,
    generate_id
)

class TestDataCleaning(unittest.TestCase):
    """Test data cleaning functions."""
    
    def test_clean_text(self):
        """Test HTML cleaning and whitespace normalization."""
        # Test HTML removal
        self.assertEqual(clean_text("<p>Test text</p>"), "Test text")
        
        # Test whitespace normalization
        self.assertEqual(clean_text("  Test \n  text  "), "Test text")
        
        # Test HTML entities
        self.assertEqual(clean_text("Band &amp; Artist"), "Band & Artist")
        
        # Test None/NA handling
        self.assertIsNone(clean_text(None))
        self.assertIsNone(clean_text(pd.NA))
    
    def test_convert_duration_to_seconds(self):
        """Test duration string conversion to seconds."""
        # Test MM:SS format
        self.assertEqual(convert_duration_to_seconds("4:30"), 270)
        
        # Test HH:MM:SS format
        self.assertEqual(convert_duration_to_seconds("1:02:30"), 3750)
        
        # Test seconds only
        self.assertEqual(convert_duration_to_seconds("45"), 45)
        
        # Test None/NA handling
        self.assertIsNone(convert_duration_to_seconds(None))
        self.assertIsNone(convert_duration_to_seconds(pd.NA))
        
        # Test invalid format
        self.assertIsNone(convert_duration_to_seconds("invalid"))
    
    def test_process_recording_type(self):
        """Test recording type standardization."""
        # Test exact matches
        self.assertEqual(process_recording_type("studio album"), "Studio")
        self.assertEqual(process_recording_type("live album"), "Live")
        
        # Test case insensitivity
        self.assertEqual(process_recording_type("STUDIO ALBUM"), "Studio")
        
        # Test partial matches
        self.assertEqual(process_recording_type("This is a studio album from 1975"), "Studio")
        
        # Test fallback
        self.assertEqual(process_recording_type("unknown type"), "Other")
        
        # Test None/NA handling
        self.assertEqual(process_recording_type(None), "Unknown")
        self.assertEqual(process_recording_type(pd.NA), "Unknown")
    
    def test_parse_subgenres(self):
        """Test subgenre string parsing."""
        # Test slash separation
        self.assertEqual(
            parse_subgenres("Progressive Rock/Symphonic Prog"),
            ["Progressive Rock", "Symphonic Prog"]
        )
        
        # Test comma separation
        self.assertEqual(
            parse_subgenres("Jazz Rock, Fusion, Canterbury Scene"),
            ["Jazz Rock", "Fusion", "Canterbury Scene"]
        )
        
        # Test mixed separators
        self.assertEqual(
            parse_subgenres("Progressive Rock/Art Rock, Eclectic Prog"),
            ["Progressive Rock", "Art Rock", "Eclectic Prog"]
        )
        
        # Test None/NA handling
        self.assertEqual(parse_subgenres(None), [])
        self.assertEqual(parse_subgenres(pd.NA), [])
        
        # Test empty string
        self.assertEqual(parse_subgenres(""), [])
    
    def test_generate_id(self):
        """Test ID generation."""
        # Test basic ID generation
        self.assertTrue(isinstance(generate_id(), str))
        
        # Test ID with prefix
        self.assertTrue(generate_id("test_").startswith("test_"))
        
        # Test uniqueness
        ids = [generate_id() for _ in range(100)]
        self.assertEqual(len(ids), len(set(ids)), "Generated IDs should be unique")

if __name__ == "__main__":
    unittest.main()
