import click
from sqlalchemy.orm import Session
from ..database import get_session, tag_manager
import json

@click.group()
def tags():
    """Tag management tools."""
    pass

@tags.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
def consolidate(dry_run):
    """Consolidate tags by merging variants and normalizing names."""
    session = get_session()
    mgr = tag_manager.TagManager(session)
    
    if dry_run:
        # Analyze and show potential changes
        stats = mgr.analyze_tag_usage()
        click.echo("Tag Analysis:")
        click.echo(f"Total tags: {stats['total_tags']}")
        click.echo(f"Canonical tags: {stats['canonical_tags']}")
        click.echo(f"Variants: {stats['variants']}")
        click.echo(f"Unused tags: {stats['unused_tags']}")
        click.echo("\nMost common tags:")
        for tag in stats['most_common'][:10]:
            click.echo(f"  {tag['name']}: {tag['count']} uses")
        click.echo("\nTags with most variants:")
        for tag, count in sorted(stats['variants_by_tag'].items(), key=lambda x: x[1], reverse=True)[:10]:
            click.echo(f"  {tag}: {count} variants")
    else:
        # Perform consolidation
        stats = mgr.consolidate_tags()
        click.echo("Consolidation complete:")
        click.echo(f"Tags merged: {stats['merged']}")
        click.echo(f"Tags updated: {stats['updated']}")
        if stats['errors'] > 0:
            click.echo(f"Errors encountered: {stats['errors']}")

@tags.command()
@click.argument('output', type=click.Path())
def export_hierarchy(output):
    """Export current tag hierarchy to JSON file."""
    session = get_session()
    mgr = tag_manager.TagManager(session)
    
    hierarchy = mgr.get_tag_hierarchy()
    
    # Convert sets to lists for JSON serialization
    serializable = {k: list(v) for k, v in hierarchy.items()}
    
    with open(output, 'w') as f:
        json.dump(serializable, f, indent=2)
    
    click.echo(f"Tag hierarchy exported to {output}")

@tags.command()
@click.argument('tag1')
@click.argument('tag2')
@click.option('--force', is_flag=True, help='Merge without confirmation')
def merge_tags(tag1, tag2, force):
    """Merge two tags together."""
    session = get_session()
    mgr = tag_manager.TagManager(session)
    
    # Get tag objects
    t1 = session.query(Tag).filter_by(name=tag1).first()
    t2 = session.query(Tag).filter_by(name=tag2).first()
    
    if not t1 or not t2:
        click.echo("One or both tags not found!")
        return
    
    if not force:
        # Show impact
        click.echo(f"This will merge '{tag1}' into '{tag2}'")
        click.echo(f"'{tag1}' appears in {len(t1.albums)} albums")
        click.echo(f"'{tag2}' appears in {len(t2.albums)} albums")
        
        if not click.confirm("Continue with merge?"):
            return
    
    try:
        mgr._merge_tags(t1, t2)
        session.commit()
        click.echo("Tags merged successfully!")
    except Exception as e:
        click.echo(f"Error merging tags: {e}")
        session.rollback()

@tags.command()
@click.option('--min-confidence', type=float, default=0.8, help='Minimum confidence for suggestions')
def suggest_merges(min_confidence):
    """Suggest tags that could potentially be merged."""
    session = get_session()
    mgr = tag_manager.TagManager(session)
    
    suggestions = mgr.suggest_merges()
    
    if not suggestions:
        click.echo("No merge suggestions found.")
        return
        
    click.echo("Suggested tag merges:")
    for tag1, tag2, confidence in suggestions:
        if confidence >= min_confidence:
            click.echo(f"  {tag1} -> {tag2} (confidence: {confidence:.2f})")

if __name__ == '__main__':
    tags()