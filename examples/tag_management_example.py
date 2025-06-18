#!/usr/bin/env python3
"""
Example script demonstrating the new tag management features.

This example shows how to:
1. Run tag migration to consolidate duplicates
2. Initialize tag hierarchies
3. Validate tags during import
4. Use the enhanced normalization system
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from albumexplore.database import get_session
from albumexplore.database.tag_migration import run_tag_migration
from albumexplore.database.tag_hierarchy import initialize_tag_hierarchies, TagHierarchyManager
from albumexplore.database.tag_validator import TagValidator, TagValidationFilter
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.database.models import Tag, Album

def example_tag_migration():
    """Example: Run tag migration to consolidate duplicates."""
    print("=== TAG MIGRATION EXAMPLE ===")
    
    # Run in dry-run mode first to see what would happen
    print("Running migration in dry-run mode...")
    stats = run_tag_migration(dry_run=True)
    print(f"Migration would merge {stats.get('tags_merged', 0)} duplicate tags")
    
    # Uncomment to actually run the migration
    # print("Running actual migration...")
    # stats = run_tag_migration(dry_run=False)
    # print(f"Successfully merged {stats.get('tags_merged', 0)} duplicate tags")

def example_tag_hierarchies():
    """Example: Initialize and use tag hierarchies."""
    print("\n=== TAG HIERARCHY EXAMPLE ===")
    
    # Initialize hierarchies
    print("Initializing tag hierarchies...")
    initialize_tag_hierarchies(overwrite_existing=False)
    
    # Use hierarchy manager
    session = get_session()
    try:
        hierarchy_manager = TagHierarchyManager(session)
        
        # Find a metal tag and show its hierarchy
        metal_tag = session.query(Tag).filter(Tag.normalized_name == 'black metal').first()
        if metal_tag:
            print(f"\nHierarchy for '{metal_tag.name}':")
            
            parents = hierarchy_manager.get_parent_tags(metal_tag)
            children = hierarchy_manager.get_child_tags(metal_tag)
            
            print(f"  Parents: {[p.name for p in parents]}")
            print(f"  Children: {[c.name for c in children]}")
            
            # Find related tags
            related = hierarchy_manager.find_related_tags(metal_tag)
            print(f"  Siblings: {[s.name for s in related.get('siblings', [])]}")
        
    finally:
        session.close()

def example_tag_validation():
    """Example: Validate tags during processing."""
    print("\n=== TAG VALIDATION EXAMPLE ===")
    
    # Sample problematic tags
    sample_tags = [
        "Progressive Metal",      # Good tag
        "LP",                    # Format string (warning)
        "2023",                  # Date (warning)
        "",                      # Empty (error)
        "---",                   # Invalid pattern (error)
        "  spaced  out  ",       # Spacing issues (info)
        "Experimental Black Metal"  # Good compound tag
    ]
    
    validator = TagValidator()
    validation_filter = TagValidationFilter(strict_mode=False)
    
    print("Validating sample tags...")
    for tag in sample_tags:
        results = validator.validate_tag(tag)
        print(f"\nTag: '{tag}'")
        
        if not results:
            print("  ✅ Valid")
        else:
            for result in results:
                icon = "❌" if result.severity.value == "error" else "⚠️" if result.severity.value == "warning" else "ℹ️"
                print(f"  {icon} {result.message}")
                if result.suggested_fix:
                    print(f"     Suggested fix: '{result.suggested_fix}'")
    
    # Filter tags
    print(f"\nFiltering tags with validation...")
    valid_tags, rejected_tags, validation_info = validation_filter.filter_tags(sample_tags)
    
    print(f"Valid tags: {valid_tags}")
    print(f"Rejected tags: {rejected_tags}")
    print(f"Summary: {validation_info['summary']}")

def example_tag_normalization():
    """Example: Use enhanced tag normalization."""
    print("\n=== TAG NORMALIZATION EXAMPLE ===")
    
    normalizer = TagNormalizer()
    
    # Sample tags with normalization issues
    sample_tags = [
        "Prog Metal",           # Should become "progressive metal"
        "Alt-Rock",            # Should become "alternative rock"
        "Post Metal",          # Should become "post-metal"
        "Black-Metal",         # Should become "black metal"
        "avant garde",         # Should become "avant-garde"
        "DEATH METAL",         # Should become "death metal"
        "  atmospheric   black    metal  "  # Should clean up spacing
    ]
    
    print("Normalizing sample tags...")
    for original in sample_tags:
        normalized = normalizer.normalize(original)
        category = normalizer.get_category(normalized)
        
        print(f"'{original}' → '{normalized}' (category: {category})")

def main():
    """Run all examples."""
    print("Tag Management Features Examples")
    print("=" * 50)
    
    try:
        # Run examples
        example_tag_normalization()
        example_tag_validation()
        example_tag_hierarchies()
        example_tag_migration()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 