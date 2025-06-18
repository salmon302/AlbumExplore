#!/usr/bin/env python3
"""
Test script to load CSV data and demonstrate the tag management system.

This script will:
1. Load all CSV files from the csv directory
2. Show initial tag statistics
3. Run tag migration to consolidate duplicates
4. Initialize tag hierarchies
5. Run validation
6. Show final statistics and improvements
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from albumexplore.database import get_session
from albumexplore.database.csv_loader import load_csv_data
from albumexplore.database.tag_migration import run_tag_migration
from albumexplore.database.tag_hierarchy import initialize_tag_hierarchies
from albumexplore.database.tag_validator import TagValidator
from albumexplore.database.models import Tag, Album
from albumexplore.gui.gui_logging import db_logger

def show_tag_statistics(title: str = "Tag Statistics"):
    """Show comprehensive tag statistics."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    
    session = get_session()
    try:
        # Basic counts
        total_tags = session.query(Tag).count()
        total_albums = session.query(Album).count()
        
        print(f"📊 Basic Statistics:")
        print(f"   Total tags: {total_tags:,}")
        print(f"   Total albums: {total_albums:,}")
        
        if total_tags == 0:
            print("   No tags found in database")
            return
        
        # Tag frequency analysis
        tag_album_counts = []
        duplicate_groups = {}
        
        for tag in session.query(Tag).all():
            album_count = len(tag.albums)
            tag_album_counts.append(album_count)
            
            # Group by normalized name to find potential duplicates
            normalized = tag.normalized_name or tag.name.lower()
            if normalized not in duplicate_groups:
                duplicate_groups[normalized] = []
            duplicate_groups[normalized].append((tag.name, album_count))
        
        # Find actual duplicates
        actual_duplicates = {k: v for k, v in duplicate_groups.items() if len(v) > 1}
        
        tag_album_counts.sort(reverse=True)
        
        print(f"\n📈 Tag Distribution:")
        if tag_album_counts:
            print(f"   Most used tag: {tag_album_counts[0]} albums")
            print(f"   Median usage: {tag_album_counts[len(tag_album_counts)//2]} albums")
            print(f"   Average usage: {sum(tag_album_counts)/len(tag_album_counts):.1f} albums")
        
        # Single-use tags
        single_use = sum(1 for count in tag_album_counts if count == 1)
        print(f"   Single-use tags: {single_use:,} ({single_use/total_tags*100:.1f}%)")
        
        # High-frequency tags
        high_freq = sum(1 for count in tag_album_counts if count >= 10)
        print(f"   High-frequency tags (≥10): {high_freq:,}")
        
        # Duplicate analysis
        print(f"\n🔍 Duplicate Analysis:")
        print(f"   Potential duplicate groups: {len(actual_duplicates):,}")
        total_duplicates = sum(len(v) for v in actual_duplicates.values())
        print(f"   Tags in duplicate groups: {total_duplicates:,}")
        
        if actual_duplicates:
            # Show top 10 duplicate groups by impact
            sorted_dupes = sorted(
                actual_duplicates.items(), 
                key=lambda x: sum(count for _, count in x[1]), 
                reverse=True
            )
            
            print(f"\n🔥 Top Duplicate Groups (by total album impact):")
            for i, (normalized, variants) in enumerate(sorted_dupes[:10], 1):
                total_albums = sum(count for _, count in variants)
                variant_list = [f"'{name}' ({count})" for name, count in variants]
                print(f"   {i:2d}. {normalized} → {total_albums} total albums")
                print(f"       Variants: {', '.join(variant_list)}")
        
        # Show top tags
        print(f"\n🏆 Top 10 Most Used Tags:")
        top_tags = sorted(session.query(Tag).all(), key=lambda t: len(t.albums), reverse=True)[:10]
        for i, tag in enumerate(top_tags, 1):
            print(f"   {i:2d}. '{tag.name}': {len(tag.albums):,} albums")
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
    finally:
        session.close()

def load_csv_files():
    """Load all CSV files from the csv directory."""
    print(f"\n{'=' * 60}")
    print("LOADING CSV DATA")
    print(f"{'=' * 60}")
    
    csv_dir = Path("csv")
    if not csv_dir.exists():
        print(f"❌ CSV directory not found: {csv_dir}")
        return False
    
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {csv_dir}")
        return False
    
    print(f"📁 Found {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        size_mb = csv_file.stat().st_size / (1024 * 1024)
        print(f"   📄 {csv_file.name} ({size_mb:.1f} MB)")
    
    print(f"\n🚀 Loading CSV data...")
    start_time = time.time()
    
    try:
        load_csv_data(csv_dir)
        end_time = time.time()
        print(f"✅ CSV data loaded successfully in {end_time - start_time:.1f} seconds")
        return True
    except Exception as e:
        print(f"❌ Error loading CSV data: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_migration_test():
    """Run tag migration and show results."""
    print(f"\n{'=' * 60}")
    print("RUNNING TAG MIGRATION")
    print(f"{'=' * 60}")
    
    # First show what would happen (dry run)
    print("🔍 Running dry-run to analyze potential changes...")
    dry_stats = run_tag_migration(dry_run=True)
    
    if dry_stats and dry_stats.get('tags_merged', 0) > 0:
        print(f"📊 Dry-run Results:")
        print(f"   Would merge: {dry_stats.get('tags_merged', 0):,} duplicate tags")
        print(f"   Would update: {dry_stats.get('tags_updated', 0):,} normalized names")
        print(f"   Would create: {dry_stats.get('variants_created', 0):,} variants")
        
        # Ask for confirmation
        response = input(f"\n❓ Proceed with actual migration? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            print(f"\n🔄 Running actual migration...")
            actual_stats = run_tag_migration(dry_run=False)
            
            print(f"✅ Migration Results:")
            print(f"   Merged: {actual_stats.get('tags_merged', 0):,} duplicate tags")
            print(f"   Updated: {actual_stats.get('tags_updated', 0):,} normalized names")
            print(f"   Created: {actual_stats.get('variants_created', 0):,} variants")
            print(f"   Errors: {actual_stats.get('errors', 0):,}")
            
            return actual_stats
        else:
            print("⚠️ Migration cancelled by user")
            return None
    else:
        print("ℹ️ No duplicate tags found to merge")
        return dry_stats

def run_hierarchy_test():
    """Initialize tag hierarchies."""
    print(f"\n{'=' * 60}")
    print("INITIALIZING TAG HIERARCHIES")
    print(f"{'=' * 60}")
    
    try:
        initialize_tag_hierarchies(overwrite_existing=False)
        print("✅ Tag hierarchies initialized successfully")
        
        # Show some hierarchy examples
        session = get_session()
        try:
            from albumexplore.database.tag_hierarchy import TagHierarchyManager
            hierarchy_manager = TagHierarchyManager(session)
            
            # Look for some common metal/rock tags to show hierarchy
            example_tags = ['metal', 'progressive metal', 'black metal', 'rock', 'progressive rock']
            
            print(f"\n🌳 Hierarchy Examples:")
            for tag_name in example_tags:
                tag = session.query(Tag).filter(Tag.normalized_name == tag_name).first()
                if tag:
                    children = hierarchy_manager.get_child_tags(tag)
                    parents = hierarchy_manager.get_parent_tags(tag)
                    
                    if children or parents:
                        print(f"   📂 '{tag.name}':")
                        if parents:
                            print(f"      ⬆️ Parents: {[p.name for p in parents]}")
                        if children:
                            print(f"      ⬇️ Children: {[c.name for c in children[:5]]}" + 
                                  (f" (+{len(children)-5} more)" if len(children) > 5 else ""))
        
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error initializing hierarchies: {e}")

def run_validation_test():
    """Run tag validation analysis."""
    print(f"\n{'=' * 60}")
    print("TAG VALIDATION ANALYSIS")
    print(f"{'=' * 60}")
    
    session = get_session()
    validator = TagValidator()
    
    try:
        all_tags = session.query(Tag).all()
        if not all_tags:
            print("ℹ️ No tags to validate")
            return
        
        print(f"🔍 Validating {len(all_tags):,} tags...")
        
        validation_results = {
            'valid': [],
            'warnings': [],
            'errors': [],
            'issues_by_category': {}
        }
        
        # Sample validation (don't validate all if there are too many)
        sample_size = min(1000, len(all_tags))
        sample_tags = all_tags[:sample_size]
        
        if sample_size < len(all_tags):
            print(f"ℹ️ Validating sample of {sample_size:,} tags for performance")
        
        for i, tag in enumerate(sample_tags):
            if i % 100 == 0 and i > 0:
                print(f"   Progress: {i:,}/{sample_size:,} ({i/sample_size*100:.1f}%)")
            
            results = validator.validate_tag(tag.name)
            
            has_errors = any(r.severity.value == 'error' for r in results)
            has_warnings = any(r.severity.value == 'warning' for r in results)
            
            if has_errors:
                validation_results['errors'].append((tag, results))
            elif has_warnings:
                validation_results['warnings'].append((tag, results))
            else:
                validation_results['valid'].append(tag)
            
            # Categorize issues
            for result in results:
                category = result.category or 'other'
                if category not in validation_results['issues_by_category']:
                    validation_results['issues_by_category'][category] = 0
                validation_results['issues_by_category'][category] += 1
        
        # Print summary
        print(f"\n📊 Validation Summary:")
        print(f"   ✅ Valid tags: {len(validation_results['valid']):,}")
        print(f"   ⚠️ Tags with warnings: {len(validation_results['warnings']):,}")
        print(f"   ❌ Tags with errors: {len(validation_results['errors']):,}")
        
        if validation_results['issues_by_category']:
            print(f"\n📋 Issues by category:")
            for category, count in sorted(validation_results['issues_by_category'].items()):
                print(f"   {category}: {count:,}")
        
        # Show examples of problematic tags
        if validation_results['errors']:
            print(f"\n❌ Example error tags:")
            for tag, results in validation_results['errors'][:5]:
                issues = [r.message for r in results if r.severity.value == 'error']
                print(f"   '{tag.name}': {', '.join(issues)}")
        
        if validation_results['warnings']:
            print(f"\n⚠️ Example warning tags:")
            for tag, results in validation_results['warnings'][:5]:
                issues = [r.message for r in results if r.severity.value == 'warning']
                print(f"   '{tag.name}': {', '.join(issues)}")
        
    finally:
        session.close()

def main():
    """Run the comprehensive test."""
    print("🎵 AlbumExplore Tag Management System Test")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        # Step 1: Show initial state (should be empty)
        show_tag_statistics("Initial Database State")
        
        # Step 2: Load CSV data
        if not load_csv_files():
            print("❌ Failed to load CSV data. Exiting.")
            return
        
        # Step 3: Show state after loading
        show_tag_statistics("After Loading CSV Data")
        
        # Step 4: Run migration
        migration_stats = run_migration_test()
        
        # Step 5: Show state after migration
        if migration_stats:
            show_tag_statistics("After Tag Migration")
        
        # Step 6: Initialize hierarchies
        run_hierarchy_test()
        
        # Step 7: Run validation
        run_validation_test()
        
        # Step 8: Final statistics
        show_tag_statistics("Final Tag Statistics")
        
        print(f"\n🎉 Test completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"\nTotal execution time: {duration:.1f} seconds")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 