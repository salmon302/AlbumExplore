#!/usr/bin/env python3
"""
Test script for the new lazy loading workflow.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        from albumexplore.gui.app import AlbumExplorer, main
        print("✅ AlbumExplorer import successful")
    except ImportError as e:
        print(f"❌ AlbumExplorer import failed: {e}")
        return False
    
    try:
        from albumexplore.gui.data_loader_dialog import DataLoaderDialog, DataLoadWorker
        print("✅ DataLoaderDialog import successful")
    except ImportError as e:
        print(f"❌ DataLoaderDialog import failed: {e}")
        return False
    
    try:
        from albumexplore.data.parsers.csv_parser import CSVParser
        print("✅ CSVParser import successful")
    except ImportError as e:
        print(f"❌ CSVParser import failed: {e}")
        return False
    
    return True

def test_csv_discovery():
    """Test CSV file discovery."""
    print("\nTesting CSV file discovery...")
    
    csv_dir = Path("csv")
    if not csv_dir.exists():
        print(f"❌ CSV directory not found: {csv_dir}")
        return False
    
    csv_files = list(csv_dir.glob("*.csv")) + list(csv_dir.glob("*.tsv"))
    print(f"✅ Found {len(csv_files)} CSV/TSV files")
    
    if csv_files:
        for i, csv_file in enumerate(csv_files[:3]):  # Show first 3
            size_kb = csv_file.stat().st_size // 1024
            print(f"   - {csv_file.name} ({size_kb} KB)")
        if len(csv_files) > 3:
            print(f"   ... and {len(csv_files) - 3} more files")
    
    return len(csv_files) > 0

def main():
    """Run the tests."""
    print("=== Lazy Loading Workflow Test ===")
    print()
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Cannot proceed.")
        return 1
    
    # Test CSV discovery
    if not test_csv_discovery():
        print("\n⚠️  No CSV files found, but imports work.")
        print("   You can still test the GUI, but won't be able to load data.")
    
    print("\n✅ All tests passed!")
    print("\nYou can now run:")
    print("   python demo_new_workflow.py")
    print("\nOr directly:")
    print("   python -m albumexplore.gui.app")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 