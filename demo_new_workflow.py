#!/usr/bin/env python3
"""
Demo script showing the new lazy loading workflow for AlbumExplore.

This demonstrates how the application now starts quickly and allows
users to select which data to load after the GUI is running.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    print("=== AlbumExplore New Workflow Demo ===")
    print()
    print("🚀 Starting GUI with lazy loading...")
    print("   - GUI loads instantly (no CSV processing)")
    print("   - User can select specific files to process")
    print("   - Debug output is filtered and manageable")
    print()
    
    try:
        # Import and run the GUI
        from albumexplore.gui.app import main as gui_main
        
        print("✅ GUI starting now...")
        print("   Use File > Load Data to select CSV files")
        print("   Choose your debug level (ERROR/WARNING/INFO/DEBUG)")
        print("   Process only the files you need for development")
        print()
        
        # Start the GUI
        return gui_main()
        
    except ImportError as e:
        print(f"❌ Error importing GUI: {e}")
        print("   Make sure PyQt6 is installed: pip install PyQt6")
        return 1
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 