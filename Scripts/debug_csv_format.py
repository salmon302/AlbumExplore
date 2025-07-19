#!/usr/bin/env python3
"""Debug CSV header detection."""

import pandas as pd
from pathlib import Path

def debug_csv_format():
    """Debug the CSV format to understand header structure."""
    
    csv_file = Path("csv/_r_ProgMetal _ Yearly Albums - 2022 Prog-rock.csv")
    
    print(f"🔍 DEBUGGING CSV FORMAT: {csv_file}")
    print("=" * 50)
    
    # Read first 20 lines to understand structure
    with open(csv_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📄 File has {len(lines)} total lines")
    print(f"\n📋 First 20 lines:")
    
    for i, line in enumerate(lines[:20]):
        line_clean = line.strip()
        if line_clean:
            print(f"  {i:2}: {line_clean}")
    
    # Try to find header patterns
    print(f"\n🔍 SEARCHING FOR HEADER PATTERNS:")
    
    for i, line in enumerate(lines[:30]):
        if any(keyword in line for keyword in ['Artist', 'Album', 'Genre']):
            print(f"  Line {i:2}: {line.strip()}")
    
    # Try reading with different skip rows
    print(f"\n📊 TESTING DIFFERENT SKIP ROWS:")
    
    for skip in range(8, 15):
        try:
            df = pd.read_csv(csv_file, skiprows=skip, nrows=3)
            print(f"  Skip {skip:2}: Columns = {list(df.columns)}")
            if len(df) > 0:
                print(f"           First row = {dict(df.iloc[0])}")
        except Exception as e:
            print(f"  Skip {skip:2}: Error - {e}")

if __name__ == "__main__":
    debug_csv_format()
