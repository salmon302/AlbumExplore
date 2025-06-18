"""
One-time migration script to consolidate existing tags in the database.
This script should be run after implementing the improved normalization system.
"""

import logging
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag, TagVariant, TagCategory, UpdateHistory
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.gui.gui_logging import db_logger

class TagMigrationManager:
    """Manages the one-time migration and consolidation of existing tags."""
    
    def __init__(self, dry_run: bool = False):
        self.session = get_session()
        self.normalizer = TagNormalizer()
        self.dry_run = dry_run
        self.stats = {
            'tags_processed': 0,
            'tags_merged': 0,
            'tags_updated': 0,
            'tags_created': 0,
            'variants_created': 0,
            'errors': 0
        }
        
    def run_migration(self) -> Dict:
        """Run the complete tag migration process."""
        db_logger.info("=" * 60)
        db_logger.info("STARTING TAG MIGRATION")
        db_logger.info(f"Dry run mode: {self.dry_run}")
        db_logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze current tag state
            self._analyze_current_tags()
            
            # Step 2: Update normalized names for existing tags
            self._update_normalized_names()
            
            # Step 3: Consolidate duplicate tags
            self._consolidate_duplicate_tags()
            
            # Step 4: Create tag variants for merged tags
            self._create_tag_variants()
            
            # Step 5: Update tag frequencies
            self._update_tag_frequencies()
            
            # Step 6: Log migration history
            if not self.dry_run:
                self._log_migration_history()
                self.session.commit()
            else:
                self.session.rollback()
                
        except Exception as e:
            db_logger.error(f"Migration failed: {str(e)}", exc_info=True)
            self.session.rollback()
            self.stats['errors'] += 1
            raise
        finally:
            end_time = datetime.now()
            duration = end_time - start_time
            
            db_logger.info("=" * 60)
            db_logger.info("MIGRATION COMPLETE")
            db_logger.info(f"Duration: {duration.total_seconds():.2f} seconds")
            db_logger.info(f"Stats: {self.stats}")
            db_logger.info("=" * 60)
            
            self.session.close()
            
        return self.stats
    
    def _analyze_current_tags(self):
        """Analyze the current state of tags in the database."""
        db_logger.info("Analyzing current tag state...")
        
        total_tags = self.session.query(Tag).count()
        total_albums = self.session.query(Album).count()
        
        # Find tags without normalized names
        tags_without_normalized = self.session.query(Tag).filter(
            Tag.normalized_name == None
        ).count()
        
        # Find potential duplicates by name similarity
        all_tags = self.session.query(Tag).all()
        potential_duplicates = defaultdict(list)
        
        for tag in all_tags:
            normalized = self.normalizer.normalize(tag.name)
            potential_duplicates[normalized].append(tag)
        
        duplicate_groups = {k: v for k, v in potential_duplicates.items() if len(v) > 1}
        
        db_logger.info(f"Current database state:")
        db_logger.info(f"  Total tags: {total_tags}")
        db_logger.info(f"  Total albums: {total_albums}")
        db_logger.info(f"  Tags without normalized names: {tags_without_normalized}")
        db_logger.info(f"  Potential duplicate groups: {len(duplicate_groups)}")
        db_logger.info(f"  Tags in duplicate groups: {sum(len(v) for v in duplicate_groups.values())}")
        
        # Show top 10 largest duplicate groups
        sorted_groups = sorted(duplicate_groups.items(), key=lambda x: len(x[1]), reverse=True)
        db_logger.info("Top duplicate groups:")
        for normalized, tags in sorted_groups[:10]:
            tag_names = [f"'{t.name}' ({len(t.albums)} albums)" for t in tags]
            db_logger.info(f"  {normalized}: {', '.join(tag_names)}")
    
    def _update_normalized_names(self):
        """Update normalized names for all existing tags."""
        db_logger.info("Updating normalized names for existing tags...")
        
        tags = self.session.query(Tag).all()
        updated_count = 0
        
        for tag in tags:
            normalized = self.normalizer.normalize(tag.name)
            if tag.normalized_name != normalized:
                if not self.dry_run:
                    tag.normalized_name = normalized
                updated_count += 1
                
        self.stats['tags_updated'] = updated_count
        db_logger.info(f"Updated normalized names for {updated_count} tags")
    
    def _consolidate_duplicate_tags(self):
        """Consolidate tags with the same normalized name."""
        db_logger.info("Consolidating duplicate tags...")
        
        # Group tags by normalized name
        duplicate_groups = defaultdict(list)
        all_tags = self.session.query(Tag).all()
        
        for tag in all_tags:
            normalized = tag.normalized_name or self.normalizer.normalize(tag.name)
            duplicate_groups[normalized].append(tag)
        
        # Process groups with duplicates
        merged_count = 0
        for normalized_name, tags in duplicate_groups.items():
            if len(tags) > 1:
                merged_count += self._merge_tag_group(normalized_name, tags)
        
        self.stats['tags_merged'] = merged_count
        db_logger.info(f"Merged {merged_count} duplicate tags")
    
    def _merge_tag_group(self, normalized_name: str, tags: List[Tag]) -> int:
        """Merge a group of duplicate tags into a single canonical tag."""
        # Choose canonical tag (prefer the one with most albums, then alphabetically first name)
        canonical_tag = max(tags, key=lambda t: (len(t.albums), -len(t.name), t.name.lower()))
        other_tags = [t for t in tags if t != canonical_tag]
        
        db_logger.info(f"Merging {len(other_tags)} tags into canonical '{canonical_tag.name}':")
        for tag in other_tags:
            db_logger.info(f"  Merging '{tag.name}' ({len(tag.albums)} albums)")
        
        if not self.dry_run:
            # Update canonical tag properties
            canonical_tag.normalized_name = normalized_name
            canonical_tag.is_canonical = 1
            
            # Store original names as variants
            self.variants_to_create = getattr(self, 'variants_to_create', [])
            
            for tag in other_tags:
                # Store variant information
                self.variants_to_create.append((tag.name, canonical_tag))
                
                # Transfer album associations
                for album in list(tag.albums):  # Use list() to avoid modification during iteration
                    if canonical_tag not in album.tags:
                        album.tags.append(canonical_tag)
                    album.tags.remove(tag)
                
                # Delete the duplicate tag
                self.session.delete(tag)
        
        return len(other_tags)
    
    def _create_tag_variants(self):
        """Create TagVariant records for merged tags."""
        if not hasattr(self, 'variants_to_create'):
            return
            
        db_logger.info("Creating tag variants for merged tags...")
        
        created_count = 0
        for variant_name, canonical_tag in getattr(self, 'variants_to_create', []):
            if not self.dry_run:
                # Check if variant already exists
                existing_variant = self.session.query(TagVariant).filter(
                    TagVariant.variant == variant_name,
                    TagVariant.canonical_tag_id == canonical_tag.id
                ).first()
                
                if not existing_variant:
                    variant = TagVariant(
                        variant=variant_name,
                        canonical_tag_id=canonical_tag.id
                    )
                    self.session.add(variant)
                    created_count += 1
        
        self.stats['variants_created'] = created_count
        db_logger.info(f"Created {created_count} tag variants")
    
    def _update_tag_frequencies(self):
        """Update frequency counts for all tags."""
        db_logger.info("Updating tag frequencies...")
        
        # Get album counts for each tag
        tag_counts = self.session.query(
            Tag.id,
            func.count(Album.id).label('album_count')
        ).join(
            Tag.albums
        ).group_by(Tag.id).all()
        
        updated_count = 0
        for tag_id, count in tag_counts:
            if not self.dry_run:
                tag = self.session.query(Tag).get(tag_id)
                if tag and tag.frequency != count:
                    tag.frequency = count
                    updated_count += 1
        
        db_logger.info(f"Updated frequencies for {updated_count} tags")
    
    def _log_migration_history(self):
        """Log the migration in the update history."""
        if not self.dry_run:
            history_entry = UpdateHistory(
                entity_type='tag',
                entity_id='migration',
                change_type='consolidation',
                changes=str(self.stats)
            )
            self.session.add(history_entry)


def run_tag_migration(dry_run: bool = False) -> Dict:
    """
    Run the tag migration process.
    
    Args:
        dry_run: If True, don't actually make changes to the database
        
    Returns:
        Dictionary with migration statistics
    """
    migration_manager = TagMigrationManager(dry_run=dry_run)
    return migration_manager.run_migration()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tag migration and consolidation")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Run in dry-run mode (don't make actual changes)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    print("Starting tag migration...")
    stats = run_tag_migration(dry_run=args.dry_run)
    print(f"Migration completed. Stats: {stats}") 