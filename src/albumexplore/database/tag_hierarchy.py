"""
Tag hierarchy system for managing genre relationships and classifications.
"""

from typing import Dict, List, Set, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from albumexplore.database import get_session
from albumexplore.database.models import Tag, TagCategory, tag_hierarchy
from albumexplore.gui.gui_logging import db_logger

class TagHierarchyManager:
    """Manages tag hierarchies and genre relationships."""
    
    # Predefined genre hierarchies
    GENRE_HIERARCHIES = {
        # Metal hierarchies
        'metal': {
            'black metal': ['atmospheric black metal', 'depressive black metal', 'folk black metal'],
            'death metal': ['technical death metal', 'melodic death metal', 'brutal death metal'],
            'doom metal': ['funeral doom metal', 'sludge metal', 'stoner metal', 'drone metal'],
            'progressive metal': ['djent', 'technical metal', 'math metal'],
            'heavy metal': ['power metal', 'speed metal', 'thrash metal'],
        },
        
        # Rock hierarchies
        'rock': {
            'progressive rock': ['art rock', 'symphonic rock'],
            'alternative rock': ['grunge', 'britpop', 'indie rock'],
            'hard rock': ['arena rock', 'blues rock'],
            'punk rock': ['hardcore punk', 'pop punk', 'post-punk'],
        },
        
        # Electronic hierarchies
        'electronic': {
            'ambient': ['dark ambient', 'drone ambient', 'space ambient'],
            'techno': ['acid techno', 'minimal techno'],
            'house': ['deep house', 'tech house'],
        },
    }
    
    # Style modifiers that can apply to multiple genres
    STYLE_MODIFIERS = {
        'atmospheric', 'progressive', 'technical', 'experimental', 'ambient',
        'acoustic', 'electric', 'instrumental', 'vocal', 'melodic', 'brutal',
        'symphonic', 'orchestral', 'minimal', 'maximal', 'dark', 'light'
    }
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
        self._hierarchy_cache = {}
        self._reverse_hierarchy_cache = {}
        
    def initialize_hierarchies(self, overwrite_existing: bool = False):
        """Initialize the tag hierarchies in the database."""
        db_logger.info("Initializing tag hierarchies...")
        
        created_relationships = 0
        
        try:
            for root_genre, subgenres in self.GENRE_HIERARCHIES.items():
                # Ensure root genre exists
                root_tag = self._get_or_create_tag(root_genre)
                
                for parent_genre, children in subgenres.items():
                    # Ensure parent genre exists
                    parent_tag = self._get_or_create_tag(parent_genre)
                    
                    # Create relationship between root and parent
                    if self._create_hierarchy_relationship(root_tag, parent_tag, overwrite_existing):
                        created_relationships += 1
                    
                    # Create relationships between parent and children
                    for child_genre in children:
                        child_tag = self._get_or_create_tag(child_genre)
                        if self._create_hierarchy_relationship(parent_tag, child_tag, overwrite_existing):
                            created_relationships += 1
            
            self.session.commit()
            db_logger.info(f"Created {created_relationships} hierarchy relationships")
            
        except Exception as e:
            self.session.rollback()
            db_logger.error(f"Error initializing hierarchies: {str(e)}", exc_info=True)
            raise
    
    def get_parent_tags(self, tag: Tag) -> List[Tag]:
        """Get all parent tags for a given tag."""
        return list(tag.parent_tags)
    
    def get_child_tags(self, tag: Tag) -> List[Tag]:
        """Get all direct child tags for a given tag."""
        return list(tag.child_tags)
    
    def get_all_descendants(self, tag: Tag) -> Set[Tag]:
        """Get all descendant tags (children, grandchildren, etc.) for a given tag."""
        descendants = set()
        to_process = [tag]
        
        while to_process:
            current_tag = to_process.pop()
            children = self.get_child_tags(current_tag)
            for child in children:
                if child not in descendants:
                    descendants.add(child)
                    to_process.append(child)
        
        return descendants
    
    def get_all_ancestors(self, tag: Tag) -> Set[Tag]:
        """Get all ancestor tags (parents, grandparents, etc.) for a given tag."""
        ancestors = set()
        to_process = [tag]
        
        while to_process:
            current_tag = to_process.pop()
            parents = self.get_parent_tags(current_tag)
            for parent in parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    to_process.append(parent)
        
        return ancestors
    
    def get_root_genre(self, tag: Tag) -> Optional[Tag]:
        """Get the root genre for a given tag."""
        ancestors = self.get_all_ancestors(tag)
        if not ancestors:
            return tag  # Tag itself is a root
        
        # Find the ancestor with no parents
        for ancestor in ancestors:
            if not self.get_parent_tags(ancestor):
                return ancestor
        
        return None
    
    def is_subgenre_of(self, child_tag: Tag, parent_tag: Tag) -> bool:
        """Check if child_tag is a subgenre of parent_tag."""
        ancestors = self.get_all_ancestors(child_tag)
        return parent_tag in ancestors
    
    def find_related_tags(self, tag: Tag, max_distance: int = 2) -> Dict[str, List[Tag]]:
        """Find tags related to the given tag within a certain hierarchical distance."""
        related = {
            'parents': self.get_parent_tags(tag),
            'children': self.get_child_tags(tag),
            'siblings': [],
            'cousins': []
        }
        
        # Find siblings (tags with same parent)
        for parent in related['parents']:
            siblings = self.get_child_tags(parent)
            for sibling in siblings:
                if sibling != tag and sibling not in related['siblings']:
                    related['siblings'].append(sibling)
        
        # Find cousins (children of siblings of parents)
        if max_distance >= 2:
            for parent in related['parents']:
                grandparents = self.get_parent_tags(parent)
                for grandparent in grandparents:
                    uncles = self.get_child_tags(grandparent)
                    for uncle in uncles:
                        if uncle != parent:
                            cousins = self.get_child_tags(uncle)
                            for cousin in cousins:
                                if cousin not in related['cousins']:
                                    related['cousins'].append(cousin)
        
        return related
    
    def suggest_parent_tags(self, tag_name: str) -> List[Tuple[Tag, float]]:
        """Suggest potential parent tags for a given tag name based on naming patterns."""
        suggestions = []
        
        # Look for compound tags that might indicate hierarchy
        tag_lower = tag_name.lower()
        
        # Check for style modifiers
        for modifier in self.STYLE_MODIFIERS:
            if tag_lower.startswith(modifier + ' '):
                base_genre = tag_lower[len(modifier) + 1:]
                base_tag = self.session.query(Tag).filter(Tag.normalized_name == base_genre).first()
                if base_tag:
                    suggestions.append((base_tag, 0.8))
        
        # Check for known patterns
        patterns = [
            ('black ', 'black metal'),
            ('death ', 'death metal'),
            ('doom ', 'doom metal'),
            ('folk ', 'folk'),
            ('jazz ', 'jazz'),
            (' metal', 'metal'),
            (' rock', 'rock'),
            (' punk', 'punk rock'),
            (' core', 'hardcore')
        ]
        
        for pattern, parent_name in patterns:
            if pattern in tag_lower:
                parent_tag = self.session.query(Tag).filter(Tag.normalized_name == parent_name).first()
                if parent_tag:
                    confidence = 0.7 if tag_lower.endswith(pattern) else 0.5
                    suggestions.append((parent_tag, confidence))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:5]  # Return top 5 suggestions
    
    def create_hierarchy_relationship(self, parent_tag: Tag, child_tag: Tag) -> bool:
        """Create a hierarchy relationship between two tags."""
        return self._create_hierarchy_relationship(parent_tag, child_tag, overwrite_existing=False)
    
    def remove_hierarchy_relationship(self, parent_tag: Tag, child_tag: Tag) -> bool:
        """Remove a hierarchy relationship between two tags."""
        try:
            if child_tag in parent_tag.child_tags:
                parent_tag.child_tags.remove(child_tag)
                self.session.commit()
                db_logger.info(f"Removed hierarchy relationship: {parent_tag.name} -> {child_tag.name}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            db_logger.error(f"Error removing hierarchy relationship: {str(e)}", exc_info=True)
            return False
    
    def get_hierarchy_statistics(self) -> Dict:
        """Get statistics about the current tag hierarchy."""
        stats = {
            'total_tags': self.session.query(Tag).count(),
            'root_tags': 0,
            'leaf_tags': 0,
            'intermediate_tags': 0,
            'total_relationships': 0,
            'max_depth': 0,
            'avg_children_per_parent': 0
        }
        
        all_tags = self.session.query(Tag).all()
        parent_child_counts = []
        
        for tag in all_tags:
            parents = self.get_parent_tags(tag)
            children = self.get_child_tags(tag)
            
            if not parents and not children:
                # Isolated tag
                continue
            elif not parents:
                # Root tag
                stats['root_tags'] += 1
            elif not children:
                # Leaf tag
                stats['leaf_tags'] += 1
            else:
                # Intermediate tag
                stats['intermediate_tags'] += 1
            
            if children:
                parent_child_counts.append(len(children))
            
            stats['total_relationships'] += len(children)
        
        if parent_child_counts:
            stats['avg_children_per_parent'] = sum(parent_child_counts) / len(parent_child_counts)
        
        return stats
    
    def _get_or_create_tag(self, tag_name: str) -> Tag:
        """Get an existing tag or create a new one."""
        tag = self.session.query(Tag).filter(Tag.normalized_name == tag_name.lower()).first()
        
        if not tag:
            import uuid
            tag = Tag(
                id=str(uuid.uuid4()),
                name=tag_name,
                normalized_name=tag_name.lower(),
                is_canonical=1
            )
            self.session.add(tag)
            self.session.flush()
            db_logger.debug(f"Created new tag: {tag_name}")
        
        return tag
    
    def _create_hierarchy_relationship(self, parent_tag: Tag, child_tag: Tag, overwrite_existing: bool = False) -> bool:
        """Create a hierarchy relationship between parent and child tags."""
        try:
            # Check if relationship already exists
            if child_tag in parent_tag.child_tags:
                if not overwrite_existing:
                    return False
            
            # Prevent circular dependencies
            if self.is_subgenre_of(parent_tag, child_tag):
                db_logger.warning(f"Circular dependency detected: {parent_tag.name} -> {child_tag.name}")
                return False
            
            # Create the relationship
            if child_tag not in parent_tag.child_tags:
                parent_tag.child_tags.append(child_tag)
                db_logger.debug(f"Created hierarchy relationship: {parent_tag.name} -> {child_tag.name}")
                return True
            
            return False
            
        except Exception as e:
            db_logger.error(f"Error creating hierarchy relationship: {str(e)}", exc_info=True)
            return False


def initialize_tag_hierarchies(session: Optional[Session] = None, overwrite_existing: bool = False):
    """
    Initialize tag hierarchies in the database.
    
    Args:
        session: Database session to use
        overwrite_existing: Whether to overwrite existing relationships
    """
    manager = TagHierarchyManager(session)
    return manager.initialize_hierarchies(overwrite_existing)


def get_tag_hierarchy_manager(session: Optional[Session] = None) -> TagHierarchyManager:
    """Get a TagHierarchyManager instance."""
    return TagHierarchyManager(session) 