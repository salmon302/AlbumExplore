#!/usr/bin/env python3
"""
Enhanced Tag Consolidation Implementation

This script applies the enhanced tag hierarchy and consolidation system to your
actual database, implementing:

1. Prefix separation (post-, neo-, proto-, etc.)
2. Hierarchical organization (primary genres, subgenres, modifiers)
3. Intelligent tag consolidation
4. Component-based tag structure
5. Relationship mapping

Usage:
    python scripts/implement_enhanced_tags.py --help
    python scripts/implement_enhanced_tags.py --dry-run  # Preview changes
    python scripts/implement_enhanced_tags.py --apply    # Apply changes
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from albumexplore.database import get_session
    from albumexplore.database.models import Tag, TagCategory, Album, album_tags
    from albumexplore.tags.hierarchy.enhanced_tag_hierarchy import EnhancedTagHierarchy, TagType
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import EnhancedTagConsolidator, ConsolidationStrategy
    from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
    from albumexplore.database.tag_hierarchy import TagHierarchyManager
    
    from sqlalchemy.orm import Session
    from sqlalchemy import text, func
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseTagAnalyzer:
    """Analyzer that works with actual database data"""
    
    def __init__(self, session: Session):
        self.session = session
        self.normalizer = TagNormalizer()
        self.tag_frequencies = {}
        self._load_tag_frequencies()
    
    def _load_tag_frequencies(self):
        """Load tag frequencies from database"""
        logger.info("Loading tag frequencies from database...")
        
        # Query tag frequencies from database
        query = self.session.query(
            Tag.normalized_name,
            func.count(album_tags.c.album_id).label('frequency')
        ).outerjoin(
            album_tags, Tag.id == album_tags.c.tag_id
        ).group_by(Tag.normalized_name)
        
        for tag_name, frequency in query:
            self.tag_frequencies[tag_name] = frequency or 0
        
        logger.info(f"Loaded {len(self.tag_frequencies)} tags with frequencies")
    
    def find_similar_tags(self, tag: str, threshold: float = 0.3) -> List[tuple]:
        """Find similar tags (simplified implementation)"""
        # For now, return empty list - can be enhanced later
        return []

class EnhancedTagImplementor:
    """Implements enhanced tag system in the database"""
    
    def __init__(self, session: Session, strategy: ConsolidationStrategy = ConsolidationStrategy.BALANCED):
        self.session = session
        self.strategy = strategy
        self.hierarchy = EnhancedTagHierarchy()
        self.analyzer = DatabaseTagAnalyzer(session)
        self.consolidator = EnhancedTagConsolidator(self.analyzer, strategy)
        self.hierarchy_manager = TagHierarchyManager(session)
        
        # Implementation tracking
        self.changes_log = []
        self.new_tags = {}
        self.merged_tags = {}
        self.updated_relationships = []
        
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze the current state of tags in the database"""
        logger.info("Analyzing current database state...")
        
        # Get all tags
        all_tags = self.session.query(Tag).all()
        tag_names = [tag.normalized_name for tag in all_tags]
        
        # Perform consolidation analysis
        consolidation_report = self.consolidator.consolidate_tag_collection(tag_names)
        
        # Analyze hierarchy opportunities
        hierarchy_analysis = self.hierarchy.analyze_tag_collection(tag_names)
        
        # Database-specific analysis
        db_stats = {
            'total_tags': len(all_tags),
            'canonical_tags': self.session.query(Tag).filter(Tag.is_canonical == 1).count(),
            'variant_tags': self.session.query(Tag).filter(Tag.is_canonical == 0).count(),
            'tags_with_albums': self.session.query(Tag.id).join(album_tags).distinct().count(),
            'orphaned_tags': len(all_tags) - self.session.query(Tag.id).join(album_tags).distinct().count(),
        }
        
        return {
            'consolidation_report': consolidation_report,
            'hierarchy_analysis': hierarchy_analysis,
            'database_stats': db_stats,
            'implementation_plan': self._create_implementation_plan(consolidation_report)
        }
    
    def _create_implementation_plan(self, consolidation_report: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan for implementing the enhanced tag system"""
        
        plan = {
            'phases': [],
            'estimated_changes': 0,
            'risk_assessment': 'low'
        }
        
        # Phase 1: Prefix separation
        prefix_separations = []
        for group in consolidation_report.get('consolidation_groups', []):
            canonical = group['canonical_form']
            originals = group['original_tags']
            
            # Check if this involves prefix separation
            for prefix in self.hierarchy.separable_prefixes:
                if canonical.startswith(f'{prefix}-') and any(not orig.startswith(f'{prefix}-') for orig in originals):
                    prefix_separations.append(group)
                    break
        
        if prefix_separations:
            plan['phases'].append({
                'name': 'Prefix Separation',
                'description': 'Separate prefixes (post-, neo-, etc.) for better organization',
                'changes': len(prefix_separations),
                'risk': 'low',
                'examples': [g['canonical_form'] for g in prefix_separations[:5]]
            })
        
        # Phase 2: High-confidence consolidations
        high_confidence = [
            g for g in consolidation_report.get('consolidation_groups', [])
            if len(g['original_tags']) > 1 and g['total_frequency'] > 10
        ]
        
        if high_confidence:
            plan['phases'].append({
                'name': 'High-Confidence Consolidations',
                'description': 'Merge obvious tag variants',
                'changes': len(high_confidence),
                'risk': 'low',
                'examples': [g['canonical_form'] for g in high_confidence[:5]]
            })
        
        # Phase 3: Hierarchy relationships
        plan['phases'].append({
            'name': 'Hierarchy Relationships',
            'description': 'Establish parent-child relationships between tags',
            'changes': 'TBD',
            'risk': 'medium',
            'examples': ['metal -> death metal', 'rock -> progressive rock']
        })
        
        # Phase 4: Component decomposition
        plan['phases'].append({
            'name': 'Component Decomposition',
            'description': 'Break down complex tags into components',
            'changes': 'TBD',
            'risk': 'medium',
            'examples': ['atmospheric black metal -> atmospheric + black metal']
        })
        
        plan['estimated_changes'] = sum(p.get('changes', 0) for p in plan['phases'] if isinstance(p.get('changes'), int))
        
        return plan
    
    def implement_phase_1_prefix_separation(self, dry_run: bool = True) -> Dict[str, Any]:
        """Implement Phase 1: Prefix separation"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Implementing Phase 1: Prefix separation...")
        
        changes = []
        
        # Get consolidation groups that involve prefix separation
        consolidation_report = self.consolidator.consolidate_tag_collection(
            [tag.normalized_name for tag in self.session.query(Tag).all()]
        )
        
        for group in consolidation_report.get('consolidation_groups', []):
            canonical = group['canonical_form']
            originals = group['original_tags']
            
            # Check if this involves prefix separation
            for prefix in self.hierarchy.separable_prefixes:
                if canonical.startswith(f'{prefix}-'):
                    # This is a prefix separation case
                    if not dry_run:
                        self._apply_prefix_separation(canonical, originals, prefix)
                    
                    changes.append({
                        'type': 'prefix_separation',
                        'canonical': canonical,
                        'originals': originals,
                        'prefix': prefix,
                        'frequency_impact': group['total_frequency']
                    })
                    break
        
        result = {
            'phase': 'Prefix Separation',
            'changes_count': len(changes),
            'changes': changes,
            'dry_run': dry_run
        }
        
        if not dry_run:
            self.session.commit()
            logger.info(f"Applied {len(changes)} prefix separations")
        else:
            logger.info(f"Would apply {len(changes)} prefix separations")
        
        return result
    
    def _apply_prefix_separation(self, canonical: str, originals: List[str], prefix: str):
        """Apply prefix separation for a specific group"""
        
        # Find or create the canonical tag
        canonical_tag = self.session.query(Tag).filter(Tag.normalized_name == canonical).first()
        
        if not canonical_tag:
            # Create new canonical tag
            canonical_tag = Tag(
                name=canonical.replace('-', ' ').title(),
                normalized_name=canonical,
                is_canonical=1
            )
            self.session.add(canonical_tag)
            self.session.flush()
        
        # Update all original tags to point to canonical
        for original in originals:
            original_tag = self.session.query(Tag).filter(Tag.normalized_name == original).first()
            if original_tag and original != canonical:
                # Move all album associations to canonical tag
                self._merge_tag_associations(original_tag, canonical_tag)
                
                # Mark original as variant
                original_tag.is_canonical = 0
                original_tag.canonical_tag_id = canonical_tag.id
        
        self.changes_log.append({
            'action': 'prefix_separation',
            'canonical': canonical,
            'originals': originals,
            'timestamp': datetime.now()
        })
    
    def implement_phase_2_consolidations(self, dry_run: bool = True) -> Dict[str, Any]:
        """Implement Phase 2: High-confidence consolidations"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Implementing Phase 2: High-confidence consolidations...")
        
        changes = []
        
        consolidation_report = self.consolidator.consolidate_tag_collection(
            [tag.normalized_name for tag in self.session.query(Tag).all()]
        )
        
        # Apply high-confidence consolidations
        high_confidence_groups = [
            g for g in consolidation_report.get('consolidation_groups', [])
            if len(g['original_tags']) > 1 and g['total_frequency'] > 10
        ]
        
        for group in high_confidence_groups:
            canonical = group['canonical_form']
            originals = group['original_tags']
            
            if not dry_run:
                self._apply_tag_consolidation(canonical, originals)
            
            changes.append({
                'type': 'consolidation',
                'canonical': canonical,
                'originals': originals,
                'frequency_impact': group['total_frequency'],
                'consolidation_count': len(originals)
            })
        
        result = {
            'phase': 'High-Confidence Consolidations',
            'changes_count': len(changes),
            'changes': changes,
            'dry_run': dry_run
        }
        
        if not dry_run:
            self.session.commit()
            logger.info(f"Applied {len(changes)} consolidations")
        else:
            logger.info(f"Would apply {len(changes)} consolidations")
        
        return result
    
    def _apply_tag_consolidation(self, canonical: str, originals: List[str]):
        """Apply tag consolidation for a group"""
        
        # Find or create canonical tag
        canonical_tag = self.session.query(Tag).filter(Tag.normalized_name == canonical).first()
        
        if not canonical_tag:
            # Use the most frequent original as the base
            most_frequent_original = max(originals, key=lambda x: self.analyzer.tag_frequencies.get(x, 0))
            base_tag = self.session.query(Tag).filter(Tag.normalized_name == most_frequent_original).first()
            
            if base_tag:
                # Update base tag to canonical form
                base_tag.normalized_name = canonical
                base_tag.name = canonical.replace('-', ' ').title()
                base_tag.is_canonical = 1
                canonical_tag = base_tag
            else:
                # Create new tag
                canonical_tag = Tag(
                    name=canonical.replace('-', ' ').title(),
                    normalized_name=canonical,
                    is_canonical=1
                )
                self.session.add(canonical_tag)
                self.session.flush()
        
        # Merge all other originals into canonical
        for original in originals:
            if original != canonical:
                original_tag = self.session.query(Tag).filter(Tag.normalized_name == original).first()
                if original_tag:
                    self._merge_tag_associations(original_tag, canonical_tag)
                    
                    # Mark as variant
                    original_tag.is_canonical = 0
                    original_tag.canonical_tag_id = canonical_tag.id
        
        self.changes_log.append({
            'action': 'consolidation',
            'canonical': canonical,
            'originals': originals,
            'timestamp': datetime.now()
        })
    
    def _merge_tag_associations(self, source_tag: Tag, target_tag: Tag):
        """Merge all album associations from source tag to target tag"""
        
        # Get all albums associated with source tag
        source_albums = self.session.query(Album).join(
            album_tags, Album.id == album_tags.c.album_id
        ).filter(album_tags.c.tag_id == source_tag.id).all()
        
        for album in source_albums:
            # Check if album is already associated with target tag
            existing = self.session.query(album_tags).filter(
                album_tags.c.album_id == album.id,
                album_tags.c.tag_id == target_tag.id
            ).first()
            
            if not existing:
                # Add association with target tag
                self.session.execute(
                    album_tags.insert().values(
                        album_id=album.id,
                        tag_id=target_tag.id
                    )
                )
            
            # Remove association with source tag
            self.session.execute(
                album_tags.delete().where(
                    album_tags.c.album_id == album.id,
                    album_tags.c.tag_id == source_tag.id
                )
            )
    
    def implement_phase_3_hierarchies(self, dry_run: bool = True) -> Dict[str, Any]:
        """Implement Phase 3: Hierarchy relationships"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Implementing Phase 3: Hierarchy relationships...")
        
        changes = []
        
        # Get all canonical tags
        canonical_tags = self.session.query(Tag).filter(Tag.is_canonical == 1).all()
        
        for tag in canonical_tags:
            # Analyze tag components
            components = self.hierarchy.decompose_tag(tag.normalized_name)
            
            # Find potential parent relationships
            for component in components:
                if component.tag_type == TagType.SUBGENRE:
                    # Look for primary genre parent
                    for genre in self.hierarchy.primary_genres:
                        if genre in tag.normalized_name or self._is_subgenre_of_genre(component.value, genre):
                            parent_tag = self.session.query(Tag).filter(
                                Tag.normalized_name == genre,
                                Tag.is_canonical == 1
                            ).first()
                            
                            if parent_tag and not dry_run:
                                self.hierarchy_manager.create_hierarchy_relationship(parent_tag, tag)
                            
                            changes.append({
                                'type': 'hierarchy_relationship',
                                'parent': genre,
                                'child': tag.normalized_name,
                                'relationship_type': 'genre_subgenre'
                            })
        
        result = {
            'phase': 'Hierarchy Relationships',
            'changes_count': len(changes),
            'changes': changes,
            'dry_run': dry_run
        }
        
        if not dry_run:
            self.session.commit()
            logger.info(f"Applied {len(changes)} hierarchy relationships")
        else:
            logger.info(f"Would apply {len(changes)} hierarchy relationships")
        
        return result
    
    def _is_subgenre_of_genre(self, subgenre: str, genre: str) -> bool:
        """Check if a subgenre belongs to a genre"""
        genre_data = self.hierarchy.primary_genres.get(genre, {})
        all_subgenres = []
        
        for category in ['subgenres', 'core_derivatives', 'punk_derivatives', 'experimental', 'fusion_types']:
            all_subgenres.extend(genre_data.get(category, []))
        
        return subgenre in [self.hierarchy._normalize_tag_name(sg) for sg in all_subgenres]
    
    def generate_implementation_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive implementation report"""
        
        report = []
        report.append("ENHANCED TAG SYSTEM IMPLEMENTATION REPORT")
        report.append("=" * 50)
        report.append(f"Implementation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Strategy: {self.strategy.value}")
        report.append("")
        
        total_changes = 0
        for result in results:
            phase = result['phase']
            changes_count = result['changes_count']
            total_changes += changes_count
            
            report.append(f"PHASE: {phase}")
            report.append(f"  Changes Applied: {changes_count}")
            report.append(f"  Dry Run: {result['dry_run']}")
            
            # Show examples
            if result['changes']:
                report.append("  Examples:")
                for change in result['changes'][:5]:
                    if change['type'] == 'prefix_separation':
                        report.append(f"    • {change['canonical']} ← {len(change['originals'])} variants")
                    elif change['type'] == 'consolidation':
                        report.append(f"    • {change['canonical']} ← {change['consolidation_count']} variants")
                    elif change['type'] == 'hierarchy_relationship':
                        report.append(f"    • {change['parent']} → {change['child']}")
            
            report.append("")
        
        report.append(f"TOTAL CHANGES: {total_changes}")
        report.append("")
        
        # Add recommendations for next steps
        report.append("NEXT STEPS:")
        report.append("1. Review and validate the changes")
        report.append("2. Update any dependent systems")
        report.append("3. Run tag analysis to verify improvements")
        report.append("4. Consider implementing remaining phases")
        
        return "\\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Implement Enhanced Tag System")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Preview changes without applying them")
    parser.add_argument("--apply", action="store_true",
                       help="Apply changes to the database")
    parser.add_argument("--strategy", choices=["aggressive", "conservative", "balanced", "hierarchical"],
                       default="balanced", help="Consolidation strategy")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                       help="Which phase to implement (1=prefixes, 2=consolidation, 3=hierarchy)")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze current state, don't implement changes")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply and not args.analyze_only:
        parser.error("Must specify either --dry-run, --apply, or --analyze-only")
    
    try:
        # Get database session
        session = get_session()
        
        # Create implementor
        strategy = ConsolidationStrategy(args.strategy.lower())
        implementor = EnhancedTagImplementor(session, strategy)
        
        if args.analyze_only:
            # Only analyze current state
            logger.info("Analyzing current database state...")
            analysis = implementor.analyze_current_state()
            
            print("\\n" + "=" * 60)
            print("CURRENT STATE ANALYSIS")
            print("=" * 60)
            
            db_stats = analysis['database_stats']
            print(f"\\nDatabase Statistics:")
            print(f"  Total tags: {db_stats['total_tags']:,}")
            print(f"  Canonical tags: {db_stats['canonical_tags']:,}")
            print(f"  Variant tags: {db_stats['variant_tags']:,}")
            print(f"  Tags with albums: {db_stats['tags_with_albums']:,}")
            print(f"  Orphaned tags: {db_stats['orphaned_tags']:,}")
            
            consolidation = analysis['consolidation_report']['mapping_stats']
            print(f"\\nConsolidation Potential:")
            print(f"  Potential canonical forms: {consolidation['unique_canonical_forms']:,}")
            print(f"  Potential reduction: {consolidation['reduction_count']:,} tags ({consolidation['reduction_percentage']:.1f}%)")
            
            plan = analysis['implementation_plan']
            print(f"\\nImplementation Plan:")
            for phase in plan['phases']:
                print(f"  {phase['name']}: {phase['changes']} changes (risk: {phase['risk']})")
                print(f"    {phase['description']}")
            
        else:
            # Implement changes
            dry_run = args.dry_run
            results = []
            
            if args.phase in ["1", "all"]:
                result = implementor.implement_phase_1_prefix_separation(dry_run)
                results.append(result)
            
            if args.phase in ["2", "all"]:
                result = implementor.implement_phase_2_consolidations(dry_run)
                results.append(result)
            
            if args.phase in ["3", "all"]:
                result = implementor.implement_phase_3_hierarchies(dry_run)
                results.append(result)
            
            # Generate and display report
            report = implementor.generate_implementation_report(results)
            print("\\n" + report)
            
            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"enhanced_tag_implementation_{timestamp}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            print(f"\\nReport saved to: {report_file}")
            
            if not dry_run:
                logger.info("Enhanced tag system implementation completed!")
            else:
                logger.info("Dry run completed. Use --apply to implement changes.")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error during implementation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
