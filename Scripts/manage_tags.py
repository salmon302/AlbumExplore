#!/usr/bin/env python3
"""
Comprehensive tag management script for AlbumExplore.

This script provides utilities for:
1. Running one-time migrations to consolidate existing tags
2. Initializing tag hierarchies
3. Validating and cleaning tag data
4. Generating tag reports and statistics

Usage:
    python scripts/manage_tags.py --help
    python scripts/manage_tags.py migrate --dry-run
    python scripts/manage_tags.py migrate
    python scripts/manage_tags.py init-hierarchies
    python scripts/manage_tags.py validate-all
    python scripts/manage_tags.py stats
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from albumexplore.database import get_session
from albumexplore.database.tag_migration import run_tag_migration
from albumexplore.database.tag_hierarchy import initialize_tag_hierarchies, TagHierarchyManager
from albumexplore.database.tag_validator import TagValidator, TagValidationFilter
from albumexplore.database.models import Tag, Album
from albumexplore.gui.gui_logging import db_logger

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_migration(dry_run: bool = False):
    """Run the tag migration process."""
    print("=" * 60)
    print("RUNNING TAG MIGRATION")
    print(f"Dry run mode: {dry_run}")
    print("=" * 60)
    
    try:
        stats = run_tag_migration(dry_run=dry_run)
        
        print("\nMigration Results:")
        print(f"  Tags processed: {stats.get('tags_processed', 0)}")
        print(f"  Tags merged: {stats.get('tags_merged', 0)}")
        print(f"  Tags updated: {stats.get('tags_updated', 0)}")
        print(f"  Variants created: {stats.get('variants_created', 0)}")
        print(f"  Errors: {stats.get('errors', 0)}")
        
        if dry_run:
            print("\n⚠️  This was a dry run. No changes were made to the database.")
        else:
            print("\n✅ Migration completed successfully!")
            
        return stats
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        return None

def init_hierarchies(overwrite_existing: bool = False):
    """Initialize tag hierarchies."""
    print("=" * 60)
    print("INITIALIZING TAG HIERARCHIES")
    print(f"Overwrite existing: {overwrite_existing}")
    print("=" * 60)
    
    try:
        initialize_tag_hierarchies(overwrite_existing=overwrite_existing)
        print("\n✅ Hierarchy initialization completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Hierarchy initialization failed: {str(e)}")
        return None

def validate_all_tags():
    """Validate all tags in the database."""
    print("=" * 60)
    print("VALIDATING ALL TAGS")
    print("=" * 60)
    
    session = get_session()
    validator = TagValidator()
    
    try:
        all_tags = session.query(Tag).all()
        total_tags = len(all_tags)
        
        print(f"Validating {total_tags} tags...")
        
        validation_results = {
            'valid': [],
            'warnings': [],
            'errors': [],
            'issues_by_category': {}
        }
        
        for i, tag in enumerate(all_tags):
            if i % 100 == 0:
                print(f"  Progress: {i}/{total_tags} ({i/total_tags*100:.1f}%)")
            
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
        print(f"\nValidation Summary:")
        print(f"  Valid tags: {len(validation_results['valid'])}")
        print(f"  Tags with warnings: {len(validation_results['warnings'])}")
        print(f"  Tags with errors: {len(validation_results['errors'])}")
        
        print(f"\nIssues by category:")
        for category, count in sorted(validation_results['issues_by_category'].items()):
            print(f"  {category}: {count}")
        
        return validation_results
        
    finally:
        session.close()

def show_statistics():
    """Show comprehensive tag statistics."""
    print("=" * 60)
    print("TAG STATISTICS")
    print("=" * 60)
    
    session = get_session()
    
    try:
        # Basic counts
        total_tags = session.query(Tag).count()
        total_albums = session.query(Album).count()
        
        print(f"Basic Statistics:")
        print(f"  Total tags: {total_tags}")
        print(f"  Total albums: {total_albums}")
        
        # Show top tags
        print(f"\nTop 10 most used tags:")
        top_tags = sorted(session.query(Tag).all(), key=lambda t: len(t.albums), reverse=True)[:10]
        for i, tag in enumerate(top_tags, 1):
            print(f"  {i:2d}. {tag.name}: {len(tag.albums)} albums")
        
    finally:
        session.close()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive tag management for AlbumExplore")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Migration command
    migrate_parser = subparsers.add_parser("migrate", help="Run tag migration and consolidation")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    
    # Hierarchy initialization command
    hierarchy_parser = subparsers.add_parser("init-hierarchies", help="Initialize tag hierarchies")
    hierarchy_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing relationships")
    
    # Validation command
    validate_parser = subparsers.add_parser("validate-all", help="Validate all tags in database")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show tag statistics")
    
    # All-in-one command
    all_parser = subparsers.add_parser("all", help="Run all operations (migrate, init-hierarchies, validate)")
    all_parser.add_argument("--dry-run", action="store_true", help="Run migration in dry-run mode")
    all_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing hierarchy relationships")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    setup_logging(args.verbose)
    
    start_time = datetime.now()
    
    try:
        if args.command == "migrate":
            run_migration(dry_run=args.dry_run)
        elif args.command == "init-hierarchies":
            init_hierarchies(overwrite_existing=args.overwrite)
        elif args.command == "validate-all":
            validate_all_tags()
        elif args.command == "stats":
            show_statistics()
        elif args.command == "all":
            print("Running comprehensive tag management...")
            print("\n1. Running migration...")
            run_migration(dry_run=args.dry_run)
            if not args.dry_run:  # Only proceed if not in dry-run mode
                print("\n2. Initializing hierarchies...")
                init_hierarchies(overwrite_existing=args.overwrite)
                print("\n3. Validating tags...")
                validate_all_tags()
            print("\n4. Showing statistics...")
            show_statistics()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\nTotal execution time: {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    main() 