"""
Tag filter state management for grouped AND/OR filtering.

This module provides the core data structures for managing complex tag filters
with support for AND/OR logic through tag groups.
"""

from typing import Set, List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime


class GroupOperator(Enum):
    """Operators for combining tags within a group."""
    AND = "AND"  # All tags in group must match
    OR = "OR"    # Any tag in group must match (future extension)


class FilterOperator(Enum):
    """Operators for combining groups."""
    OR = "OR"    # Any group must match
    AND = "AND"  # All groups must match (future extension)


@dataclass
class TagFilterGroup:
    """
    Represents a group of tags with a specific operator.
    
    By default, tags within a group use AND logic (album must have ALL tags).
    Groups are combined with OR logic (album matches if ANY group matches).
    """
    
    group_id: str
    name: str = ""
    tags: Set[str] = field(default_factory=set)
    operator: GroupOperator = GroupOperator.AND
    color: Optional[str] = None  # Visual color for UI (e.g., "#FFE0E0")
    enabled: bool = True  # Allow temporarily disabling groups
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.name:
            self.name = f"Group {self.group_id}"
        if isinstance(self.tags, list):
            self.tags = set(self.tags)
    
    def matches(self, album_tags: Set[str]) -> bool:
        """
        Check if an album's tags match this group's criteria.
        
        Args:
            album_tags: Set of tags associated with an album
            
        Returns:
            True if album matches this group's filter criteria
        """
        if not self.enabled or not self.tags:
            return True  # Empty or disabled group matches everything
        
        if self.operator == GroupOperator.AND:
            # All tags in group must be present in album
            return self.tags.issubset(album_tags)
        elif self.operator == GroupOperator.OR:
            # At least one tag in group must be present
            return bool(self.tags.intersection(album_tags))
        
        return False
    
    def add_tag(self, tag: str) -> bool:
        """
        Add a tag to this group.
        
        Args:
            tag: Tag to add
            
        Returns:
            True if tag was added, False if already present
        """
        if tag not in self.tags:
            self.tags.add(tag)
            return True
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from this group.
        
        Args:
            tag: Tag to remove
            
        Returns:
            True if tag was removed, False if not present
        """
        if tag in self.tags:
            self.tags.discard(tag)
            return True
        return False
    
    def has_tag(self, tag: str) -> bool:
        """Check if tag is in this group."""
        return tag in self.tags
    
    def is_empty(self) -> bool:
        """Check if group has no tags."""
        return len(self.tags) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'group_id': self.group_id,
            'name': self.name,
            'tags': list(self.tags),
            'operator': self.operator.value,
            'color': self.color,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TagFilterGroup':
        """Create from dictionary."""
        operator = GroupOperator(data.get('operator', 'AND'))
        return cls(
            group_id=data['group_id'],
            name=data.get('name', ''),
            tags=set(data.get('tags', [])),
            operator=operator,
            color=data.get('color'),
            enabled=data.get('enabled', True)
        )


@dataclass
class TagFilterState:
    """
    Complete state of tag filters including groups and exclusions.
    
    Filter Logic:
        (Group1 matches) OR (Group2 matches) OR ... 
        AND NOT (any exclude tag matches)
    
    Each group uses AND logic internally (must have ALL tags in group).
    Groups are combined with OR logic (match ANY group).
    Exclusions are applied after group matching.
    """
    
    groups: List[TagFilterGroup] = field(default_factory=list)
    exclude_tags: Set[str] = field(default_factory=set)
    group_operator: FilterOperator = FilterOperator.OR
    active: bool = True
    version: str = "2.0"  # For future compatibility
    
    def __post_init__(self):
        """Initialize default values."""
        if isinstance(self.exclude_tags, list):
            self.exclude_tags = set(self.exclude_tags)
    
    def matches(self, album_tags: Set[str]) -> bool:
        """
        Check if an album matches the complete filter state.
        
        Args:
            album_tags: Set of tags associated with an album
            
        Returns:
            True if album matches all filter criteria
        """
        if not self.active:
            return True
        
        # Check exclusions first (faster to eliminate)
        if self.exclude_tags and self.exclude_tags.intersection(album_tags):
            return False
        
        # Get enabled groups
        enabled_groups = [g for g in self.groups if g.enabled and not g.is_empty()]
        
        # If no include groups, accept all (that aren't excluded)
        if not enabled_groups:
            return True
        
        # Check group matching based on operator
        if self.group_operator == FilterOperator.OR:
            # Match if ANY group matches (default behavior)
            return any(group.matches(album_tags) for group in enabled_groups)
        elif self.group_operator == FilterOperator.AND:
            # Match if ALL groups match (future extension)
            return all(group.matches(album_tags) for group in enabled_groups)
        
        return False
    
    def add_group(self, group: Optional[TagFilterGroup] = None) -> TagFilterGroup:
        """
        Add a new filter group.
        
        Args:
            group: Optional pre-configured group. If None, creates empty group.
            
        Returns:
            The added group
        """
        if group is None:
            # Generate unique ID
            group_id = self._generate_group_id()
            group = TagFilterGroup(group_id=group_id)
        
        self.groups.append(group)
        return group
    
    def remove_group(self, group_id: str) -> bool:
        """
        Remove a group by ID.
        
        Args:
            group_id: ID of group to remove
            
        Returns:
            True if group was removed, False if not found
        """
        for i, group in enumerate(self.groups):
            if group.group_id == group_id:
                self.groups.pop(i)
                return True
        return False
    
    def get_group(self, group_id: str) -> Optional[TagFilterGroup]:
        """Get a group by ID."""
        for group in self.groups:
            if group.group_id == group_id:
                return group
        return None
    
    def add_exclusion(self, tag: str) -> bool:
        """
        Add a tag to the exclusion list.
        
        Args:
            tag: Tag to exclude
            
        Returns:
            True if tag was added, False if already present
        """
        if tag not in self.exclude_tags:
            self.exclude_tags.add(tag)
            return True
        return False
    
    def remove_exclusion(self, tag: str) -> bool:
        """
        Remove a tag from the exclusion list.
        
        Args:
            tag: Tag to remove from exclusions
            
        Returns:
            True if tag was removed, False if not present
        """
        if tag in self.exclude_tags:
            self.exclude_tags.discard(tag)
            return True
        return False
    
    def clear_all(self):
        """Clear all filters (groups and exclusions)."""
        self.groups.clear()
        self.exclude_tags.clear()
    
    def clear_groups(self):
        """Clear all groups but keep exclusions."""
        self.groups.clear()
    
    def clear_exclusions(self):
        """Clear all exclusions but keep groups."""
        self.exclude_tags.clear()
    
    def is_empty(self) -> bool:
        """Check if there are no active filters."""
        return len(self.groups) == 0 and len(self.exclude_tags) == 0
    
    def get_tag_locations(self, tag: str) -> Dict[str, List[str]]:
        """
        Find all locations where a tag is used.
        
        Returns:
            Dict with keys 'groups' (list of group IDs) and 'excluded' (bool)
        """
        locations = {
            'groups': [],
            'excluded': tag in self.exclude_tags
        }
        
        for group in self.groups:
            if group.has_tag(tag):
                locations['groups'].append(group.group_id)
        
        return locations
    
    def move_tag(self, tag: str, from_group_id: str, to_group_id: str) -> bool:
        """
        Move a tag from one group to another.
        
        Args:
            tag: Tag to move
            from_group_id: Source group ID
            to_group_id: Destination group ID
            
        Returns:
            True if successful, False otherwise
        """
        from_group = self.get_group(from_group_id)
        to_group = self.get_group(to_group_id)
        
        if from_group and to_group and from_group.has_tag(tag):
            from_group.remove_tag(tag)
            to_group.add_tag(tag)
            return True
        
        return False
    
    def get_filter_summary(self) -> str:
        """
        Get a human-readable summary of the current filters.
        
        Returns:
            String describing the active filters
        """
        parts = []
        
        if self.groups:
            group_summaries = []
            for group in self.groups:
                if group.enabled and not group.is_empty():
                    tags_str = " AND ".join(sorted(group.tags))
                    group_summaries.append(f"({tags_str})")
            
            if group_summaries:
                connector = " OR " if self.group_operator == FilterOperator.OR else " AND "
                parts.append(connector.join(group_summaries))
        
        if self.exclude_tags:
            exclude_str = ", ".join(sorted(self.exclude_tags))
            parts.append(f"Excluding: {exclude_str}")
        
        return " | ".join(parts) if parts else "No filters active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'version': self.version,
            'filter_type': 'grouped',
            'groups': [g.to_dict() for g in self.groups],
            'exclude_tags': list(self.exclude_tags),
            'group_operator': self.group_operator.value,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TagFilterState':
        """Create from dictionary."""
        groups = [TagFilterGroup.from_dict(g) for g in data.get('groups', [])]
        group_operator = FilterOperator(data.get('group_operator', 'OR'))
        
        return cls(
            groups=groups,
            exclude_tags=set(data.get('exclude_tags', [])),
            group_operator=group_operator,
            active=data.get('active', True),
            version=data.get('version', '2.0')
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TagFilterState':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def _generate_group_id(self) -> str:
        """Generate a unique group ID."""
        if not self.groups:
            return "1"
        
        # Get max numeric ID
        max_id = 0
        for group in self.groups:
            try:
                num_id = int(group.group_id)
                max_id = max(max_id, num_id)
            except ValueError:
                pass
        
        return str(max_id + 1)
    
    @classmethod
    def from_legacy_filters(cls, include_tags: Set[str], exclude_tags: Set[str]) -> 'TagFilterState':
        """
        Create TagFilterState from legacy include/exclude tag sets.
        
        By default, creates separate groups for each include tag (OR behavior).
        
        Args:
            include_tags: Set of tags that were marked as "include"
            exclude_tags: Set of tags that were marked as "exclude"
            
        Returns:
            New TagFilterState instance
        """
        state = cls(exclude_tags=exclude_tags.copy())
        
        # Each include tag becomes its own group (OR behavior)
        for i, tag in enumerate(sorted(include_tags), start=1):
            group = TagFilterGroup(
                group_id=str(i),
                name=f"Group {i}",
                tags={tag}
            )
            state.groups.append(group)
        
        return state
    
    @classmethod
    def from_legacy_filters_as_and(cls, include_tags: Set[str], exclude_tags: Set[str]) -> 'TagFilterState':
        """
        Create TagFilterState from legacy filters with all includes in one AND group.
        
        Args:
            include_tags: Set of tags that were marked as "include"
            exclude_tags: Set of tags that were marked as "exclude"
            
        Returns:
            New TagFilterState instance with single AND group
        """
        state = cls(exclude_tags=exclude_tags.copy())
        
        if include_tags:
            group = TagFilterGroup(
                group_id="1",
                name="Group 1",
                tags=include_tags.copy()
            )
            state.groups.append(group)
        
        return state


@dataclass
class SavedQuery:
    """Saved filter configuration for quick reuse."""
    
    name: str
    filter_state: TagFilterState
    description: str = ""
    created: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'filter_state': self.filter_state.to_dict(),
            'description': self.description,
            'created': self.created.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'use_count': self.use_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SavedQuery':
        """Create from dictionary."""
        filter_state = TagFilterState.from_dict(data['filter_state'])
        created = datetime.fromisoformat(data['created'])
        last_used = datetime.fromisoformat(data['last_used']) if data.get('last_used') else None
        
        return cls(
            name=data['name'],
            filter_state=filter_state,
            description=data.get('description', ''),
            created=created,
            last_used=last_used,
            use_count=data.get('use_count', 0)
        )
