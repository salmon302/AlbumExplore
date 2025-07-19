#!/usr/bin/env python3
"""
Quick Tag Consolidation Script

This script applies the most beneficial, low-risk consolidations identified
by the enhanced tag analysis. It focuses on:

1. Hyphenation standardization (prog-rock vs prog rock)
2. Simple variant consolidation
3. Obvious formatting fixes

Usage:
    python scripts/quick_tag_consolidation.py --dry-run
    python scripts/quick_tag_consolidation.py --apply
"""

import sys
import argparse
from pathlib import Path

# Simple consolidation rules based on analysis results
CONSOLIDATION_RULES = [
    # Progressive variations
    ('prog rock', 'prog-rock'),
    ('prog metal', 'prog-metal'),
    
    # Post- variations  
    ('post metal', 'post-metal'),
    ('post rock', 'post-rock'),
    ('post punk', 'post-punk'),
    ('post hardcore', 'post-hardcore'),
    ('post black metal', 'post-black metal'),
    
    # Alt variations
    ('alt rock', 'alt-rock'),
    ('alt metal', 'alt-metal'),
    
    # Other hyphenation fixes
    ('hard rock', 'hard-rock'),
    ('math rock', 'math-rock'),
    ('art rock', 'art-rock'),
    ('space rock', 'space-rock'),
    ('noise rock', 'noise-rock'),
    ('pop punk', 'pop-punk'),
    ('pop rock', 'pop-rock'),
    ('punk rock', 'punk-rock'),
    
    # Singer-songwriter standardization
    ('singer songwriter', 'singer-songwriter'),
    
    # Jazz fusion
    ('jazz fusion', 'jazz-fusion'),
    
    # Art pop
    ('art pop', 'art-pop'),
    
    # Neo variations
    ('neo prog', 'neo-prog'),
    
    # Remove atmospheric prefixes from specific compound tags
    ('atmospheric post-rock', 'post-rock'),
    ('atmospheric post-metal', 'post-metal'),
    ('atmospheric post-black metal', 'post-black metal'),
    ('orchestral post-rock', 'post-rock'),
    ('instrumental post-rock', 'post-rock'),
    ('progressive post-hardcore', 'post-hardcore'),
    ('electronic avant-garde', 'avant-garde'),
]

def print_consolidation_preview():
    """Print what the consolidation would do"""
    print("QUICK TAG CONSOLIDATION PREVIEW")
    print("=" * 50)
    print(f"Total rules: {len(CONSOLIDATION_RULES)}")
    print()
    
    print("CONSOLIDATION RULES:")
    for original, canonical in CONSOLIDATION_RULES:
        print(f"  '{original}' → '{canonical}'")
    
    print()
    print("IMPACT CATEGORIES:")
    
    hyphenation = [rule for rule in CONSOLIDATION_RULES if rule[0].replace(' ', '-') == rule[1]]
    prefix_cleanup = [rule for rule in CONSOLIDATION_RULES if any(prefix in rule[0] for prefix in ['atmospheric', 'orchestral', 'instrumental', 'progressive', 'electronic'])]
    other = [rule for rule in CONSOLIDATION_RULES if rule not in hyphenation and rule not in prefix_cleanup]
    
    print(f"  Hyphenation standardization: {len(hyphenation)} rules")
    print(f"  Prefix cleanup: {len(prefix_cleanup)} rules") 
    print(f"  Other consolidations: {len(other)} rules")
    
    print()
    print("EXPECTED BENEFITS:")
    print("  • Consistent hyphenation across all compound genres")
    print("  • Cleaner tag hierarchy with reduced redundancy")
    print("  • Better searchability and navigation")
    print("  • Foundation for future hierarchical organization")

def apply_consolidation_to_csv_files(csv_dir: str, dry_run: bool = True):
    """Apply consolidation rules to CSV files"""
    import pandas as pd
    import os
    
    csv_path = Path(csv_dir)
    if not csv_path.exists():
        print(f"CSV directory not found: {csv_dir}")
        return
    
    csv_files = list(csv_path.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in: {csv_dir}")
        return
    
    print(f"{'DRY RUN: ' if dry_run else ''}Processing {len(csv_files)} CSV files...")
    
    total_changes = 0
    
    for csv_file in csv_files:
        print(f"\\n{'DRY RUN: ' if dry_run else ''}Processing {csv_file.name}...")
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Check if it has a tags column or genre column
            tag_columns = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['tag', 'genre', 'subgenre']):
                    tag_columns.append(col)
            
            if not tag_columns:
                print(f"  No tag/genre columns found in {csv_file.name}")
                continue
            
            file_changes = 0
            
            # Apply consolidation rules to each tag column
            for col in tag_columns:
                for original, canonical in CONSOLIDATION_RULES:
                    # Count matches before replacement
                    if col in df.columns and df[col].dtype == 'object':
                        matches = df[col].str.contains(original, case=False, na=False).sum()
                        if matches > 0:
                            print(f"    {col}: '{original}' → '{canonical}' ({matches} matches)")
                            file_changes += matches
                            
                            if not dry_run:
                                # Apply the replacement
                                df[col] = df[col].str.replace(original, canonical, case=False, regex=False)
            
            if file_changes > 0:
                total_changes += file_changes
                print(f"  Total changes in {csv_file.name}: {file_changes}")
                
                if not dry_run:
                    # Save the updated file
                    df.to_csv(csv_file, index=False)
                    print(f"  ✅ Updated {csv_file.name}")
            else:
                print(f"  No changes needed in {csv_file.name}")
        
        except Exception as e:
            print(f"  ❌ Error processing {csv_file.name}: {e}")
    
    print(f"\\n{'DRY RUN ' if dry_run else ''}SUMMARY:")
    print(f"  Total files processed: {len(csv_files)}")
    print(f"  Total changes: {total_changes}")
    
    if dry_run:
        print("\\n  Use --apply to implement these changes")
    else:
        print("\\n  ✅ All changes applied successfully!")

def main():
    parser = argparse.ArgumentParser(description="Quick Tag Consolidation")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to CSV files")
    parser.add_argument("--csv-dir", default="./csv", help="Directory containing CSV files")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        # Default to preview mode
        print_consolidation_preview()
        print()
        print("Use --dry-run to see what changes would be made to your CSV files")
        print("Use --apply to actually implement the changes")
        return
    
    if args.dry_run or args.apply:
        # Apply to CSV files
        try:
            apply_consolidation_to_csv_files(args.csv_dir, dry_run=args.dry_run)
        except ImportError:
            print("Error: pandas is required for CSV processing")
            print("Install with: pip install pandas")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
