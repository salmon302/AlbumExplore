"""Test suite for albumexplore."""
import os
import sys
from pathlib import Path

# Ensure test configuration directory exists
test_data_dir = Path(__file__).parent / 'test_data'
test_data_dir.mkdir(exist_ok=True)

# Test package initialization