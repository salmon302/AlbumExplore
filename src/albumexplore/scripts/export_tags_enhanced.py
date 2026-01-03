"""
Standalone script to export tags from database to CSV with enhanced normalization.

This can be run directly without click/CLI setup.
"""

import sys
import csv
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from sqlalchemy import func
from albumexplore.database import get_session
from albumexplore.database.models import Tag, album_tags
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer


def export_tags_to_csv(output_dir='tagoutput', use_enhanced=True):
    """Export all tags to CSV files with normalization."""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    print("Connecting to database...")
    session = get_session()
    normalizer = TagNormalizer()
    
    # Get all tags with their usage counts
    print("Querying tags...")
    tag_stats = (
        session.query(
            Tag.name,
            func.count(album_tags.c.album_id).label('count')
        )
        .outerjoin(album_tags, Tag.id == album_tags.c.tag_id)
        .group_by(Tag.id, Tag.name)
        .order_by(Tag.name)
        .all()
    )
    
    # Export raw tags with enhanced normalization
    raw_file = output_path / 'raw_tags_export.csv'
    atomic_file = output_path / 'atomic_tags_export.csv'
    
    print(f"\nExporting {len(tag_stats)} tags...")
    print(f"Using {'enhanced' if use_enhanced else 'standard'} normalization")
    
    # Export raw tags
    print(f"\nWriting to {raw_file}...")
    with open(raw_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Tag', 'Count', 'Normalized Form', 'Filter State'])
        
        for tag_name, count in tag_stats:
            if use_enhanced:
                normalized = normalizer.normalize_enhanced(tag_name)
            else:
                normalized = normalizer.normalize(tag_name)
            
            writer.writerow([tag_name, count, normalized, 0])
    
    print(f"✓ Raw tags exported to {raw_file}")
    
    # Export atomic tags (if enabled)
    if normalizer._enable_atomic_tags:
        print(f"\nProcessing atomic decomposition...")
        atomic_tag_counts = {}
        
        for tag_name, count in tag_stats:
            if use_enhanced:
                normalized = normalizer.normalize_enhanced(tag_name)
            else:
                normalized = normalizer.normalize(tag_name)
            
            # Get atomic tags
            atomic_tags = normalizer.get_atomic_tags(normalized)
            
            if atomic_tags:
                for atomic_tag in atomic_tags:
                    atomic_tag_counts[atomic_tag] = atomic_tag_counts.get(atomic_tag, 0) + count
            else:
                # Tag doesn't decompose, count it as-is
                atomic_tag_counts[normalized] = atomic_tag_counts.get(normalized, 0) + count
        
        # Write atomic tags
        print(f"Writing to {atomic_file}...")
        with open(atomic_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Tag', 'Count', 'Matching Count', 'Is Single', 'Filter State'])
            
            for atomic_tag, count in sorted(atomic_tag_counts.items()):
                # Check if this appears as exact match
                matching_count = sum(1 for name, _ in tag_stats if normalizer.normalize_enhanced(name) == atomic_tag)
                is_single = count == 1
                
                writer.writerow([atomic_tag, count, matching_count, is_single, 0])
        
        print(f"✓ Atomic tags exported to {atomic_file}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("EXPORT SUMMARY")
    print("="*60)
    print(f"Total tags in database: {len(tag_stats)}")
    
    if use_enhanced:
        unique_normalized = len(set(normalizer.normalize_enhanced(name) for name, _ in tag_stats))
        reduction_count = len(tag_stats) - unique_normalized
        reduction_pct = (reduction_count / len(tag_stats) * 100) if len(tag_stats) > 0 else 0
        
        print(f"Unique normalized tags: {unique_normalized}")
        print(f"Potential reduction: {reduction_count} tags ({reduction_pct:.1f}%)")
        
        # Count different types of normalization applied
        case_normalized = 0
        multi_tag_split = 0
        hyphen_normalized = 0
        misspelling_fixed = 0
        
        for tag_name, _ in tag_stats:
            normalized = normalizer.normalize_enhanced(tag_name)
            
            if tag_name != tag_name.lower():
                case_normalized += 1
            
            if '/' in tag_name:
                multi_tag_split += 1
            
            if ('-' in tag_name or '-' in normalized) and tag_name.lower().replace('-', ' ') != normalized.replace('-', ' '):
                hyphen_normalized += 1
            
            # Check if it was a misspelling (normalized form different from lowercase)
            if tag_name.lower() != normalized and tag_name.lower().replace('-', ' ') == normalized.replace('-', ' '):
                misspelling_fixed += 1
        
        print(f"\nNormalization breakdown:")
        print(f"  Case variations: {case_normalized} tags")
        print(f"  Multi-tags (with /): {multi_tag_split} tags")
        print(f"  Hyphen/space variants: {hyphen_normalized} tags")
        print(f"  Misspellings fixed: {misspelling_fixed} tags")
        
        # Show some examples of normalization
        print("\nExample normalizations (first 15):")
        examples_shown = 0
        for tag_name, count in tag_stats:
            normalized = normalizer.normalize_enhanced(tag_name)
            if tag_name != normalized:  # Show ANY normalization, not just lowercase differences
                print(f"  '{tag_name}' → '{normalized}' (used {count} times)")
                examples_shown += 1
                if examples_shown >= 15:
                    break
    
    print("\n" + "="*60)
    print("Export complete!")
    print("="*60)
    
    session.close()


if __name__ == '__main__':
    print("="*60)
    print("Tag Export Tool - Enhanced Normalization")
    print("="*60)
    print()
    
    try:
        export_tags_to_csv(output_dir='tagoutput', use_enhanced=True)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
