"""
Export tags to CSV with enhanced normalization.

This script exports all tags from the database to CSV files with proper normalization applied.
"""

import click
import csv
from pathlib import Path
from sqlalchemy import func, select
from ..database import get_session
from ..database.models import Tag, album_tags
from ..tags.normalizer.tag_normalizer import TagNormalizer


@click.command()
@click.option('--output-dir', '-o', type=click.Path(), default='tagoutput',
              help='Output directory for CSV files')
@click.option('--use-enhanced', is_flag=True, default=True,
              help='Use enhanced normalization (recommended)')
@click.option('--max-count', type=int, default=None,
              help='Only export tags with count <= this value (e.g., 1 for singles)')
@click.option('--min-count', type=int, default=None,
              help='Only export tags with count >= this value')
def export_tags(output_dir, use_enhanced, max_count, min_count):
    """Export all tags to CSV files with normalization."""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    session = get_session()
    normalizer = TagNormalizer()
    
    # Get all tags with their usage counts
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
    
    # Apply count filters if specified
    if max_count is not None or min_count is not None:
        filtered_stats = []
        for tag_name, count in tag_stats:
            if max_count is not None and count > max_count:
                continue
            if min_count is not None and count < min_count:
                continue
            filtered_stats.append((tag_name, count))
        tag_stats = filtered_stats
    
    # Generate appropriate filename based on filters
    if max_count is not None and max_count == 1:
        raw_file = output_path / 'raw_tags_singles.csv'
        atomic_file = output_path / 'atomic_tags_singles.csv'
    elif max_count is not None:
        raw_file = output_path / f'raw_tags_max{max_count}.csv'
        atomic_file = output_path / f'atomic_tags_max{max_count}.csv'
    elif min_count is not None:
        raw_file = output_path / f'raw_tags_min{min_count}.csv'
        atomic_file = output_path / f'atomic_tags_min{min_count}.csv'
    else:
        raw_file = output_path / 'raw_tags_export.csv'
        atomic_file = output_path / 'atomic_tags_export.csv'
    
    # Display filter info
    filter_info = []
    if min_count is not None:
        filter_info.append(f"count >= {min_count}")
    if max_count is not None:
        filter_info.append(f"count <= {max_count}")
    filter_text = f" (filtered: {', '.join(filter_info)})" if filter_info else ""
    
    click.echo(f"Exporting {len(tag_stats)} tags{filter_text}...")
    click.echo(f"Using {'enhanced' if use_enhanced else 'standard'} normalization")
    
    # Export raw tags
    with open(raw_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Tag', 'Count', 'Normalized Form', 'Filter State'])
        
        for tag_name, count in tag_stats:
            if use_enhanced:
                normalized = normalizer.normalize_enhanced(tag_name)
            else:
                normalized = normalizer.normalize(tag_name)
            
            writer.writerow([tag_name, count, normalized, 0])
    
    click.echo(f"✓ Raw tags exported to {raw_file}")
    
    # Export atomic tags (if enabled)
    if normalizer._enable_atomic_tags:
        atomic_tag_counts = {}
        
        for tag_name, count in tag_stats:
            if use_enhanced:
                normalized = normalizer.normalize_enhanced(tag_name)
            else:
                normalized = normalizer.normalize(tag_name)
            
            # Get atomic tags using normalize_to_atomic
            atomic_tags = normalizer.normalize_to_atomic(tag_name)
            
            if atomic_tags:
                for atomic_tag in atomic_tags:
                    atomic_tag_counts[atomic_tag] = atomic_tag_counts.get(atomic_tag, 0) + count
            else:
                # Tag doesn't decompose, count it as-is
                atomic_tag_counts[normalized] = atomic_tag_counts.get(normalized, 0) + count
        
        # Write atomic tags
        with open(atomic_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Tag', 'Count', 'Matching Count', 'Is Single', 'Filter State'])
            
            for atomic_tag, count in sorted(atomic_tag_counts.items()):
                # Check if this appears as exact match
                matching_count = sum(1 for name, _ in tag_stats if normalizer.normalize_enhanced(name) == atomic_tag)
                is_single = count == 1
                
                writer.writerow([atomic_tag, count, matching_count, is_single, 0])
        
        click.echo(f"✓ Atomic tags exported to {atomic_file}")
    
    # Print summary statistics
    click.echo("\nExport Summary:")
    click.echo(f"  Total tags exported: {len(tag_stats)}")
    
    if filter_info:
        click.echo(f"  Filter applied: {', '.join(filter_info)}")
    
    if use_enhanced:
        unique_normalized = len(set(normalizer.normalize_enhanced(name) for name, _ in tag_stats))
        click.echo(f"  Unique normalized tags: {unique_normalized}")
        if len(tag_stats) > 0:
            click.echo(f"  Potential reduction: {len(tag_stats) - unique_normalized} tags ({(len(tag_stats) - unique_normalized)/len(tag_stats)*100:.1f}%)")
        
        # Show some examples of normalization
        click.echo("\nExample normalizations:")
        examples_shown = 0
        for tag_name, count in tag_stats:
            normalized = normalizer.normalize_enhanced(tag_name)
            if tag_name.lower() != normalized:
                click.echo(f"  '{tag_name}' → '{normalized}' (count: {count})")
                examples_shown += 1
                if examples_shown >= 10:
                    break


if __name__ == '__main__':
    export_tags()
