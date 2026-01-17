# Tag Filter System - Quick Reference

## Overview

A powerful tag filtering system that supports AND/OR logic through visual tag groups.

## Filter Logic

```
(Group1_Tag1 AND Group1_Tag2) OR (Group2_Tag1 AND Group2_Tag2) OR ...
AND NOT (Exclude_Tag1 OR Exclude_Tag2)
```

**Key Principles**:
- Tags within a group: **AND** (must have ALL)
- Between groups: **OR** (match ANY)
- Exclusions: Applied after group matching

## Quick Start

### Basic Usage

```python
from albumexplore.tags.filters import TagFilterState

# Create filter state
state = TagFilterState()

# Add a group: Progressive Metal AND Instrumental
group = state.add_group()
group.add_tag("Progressive Metal")
group.add_tag("Instrumental")

# Add exclusions
state.add_exclusion("Live")

# Check if album matches
album_tags = {"Progressive Metal", "Instrumental", "Epic"}
if state.matches(album_tags):
    print("Album matches!")

# Get human-readable summary
print(state.get_filter_summary())
# Output: (Instrumental AND Progressive Metal) | Excluding: Live
```

### Multiple Groups (OR Logic)

```python
state = TagFilterState()

# Group 1: Progressive Metal AND Instrumental
group1 = state.add_group()
group1.add_tag("Progressive Metal")
group1.add_tag("Instrumental")

# Group 2: Jazz AND Fusion
group2 = state.add_group()
group2.add_tag("Jazz")
group2.add_tag("Fusion")

# Matches albums that satisfy EITHER group
# ✓ {Progressive Metal, Instrumental}
# ✓ {Jazz, Fusion}
# ✗ {Progressive Metal, Jazz}
```

## Common Patterns

### 1. Simple AND Filter
**Use Case**: Albums that are both X and Y
```python
state = TagFilterState()
group = state.add_group()
group.add_tag("Metal")
group.add_tag("Female Vocals")
```

### 2. Simple OR Filter
**Use Case**: Albums that are X or Y
```python
state = TagFilterState()
group1 = state.add_group()
group1.add_tag("Jazz")
group2 = state.add_group()
group2.add_tag("Fusion")
```

### 3. Complex Query
**Use Case**: (Metal AND Instrumental) OR (Jazz AND Experimental), no Live
```python
state = TagFilterState()

group1 = state.add_group()
group1.add_tag("Metal")
group1.add_tag("Instrumental")

group2 = state.add_group()
group2.add_tag("Jazz")
group2.add_tag("Experimental")

state.add_exclusion("Live")
```

### 4. Exclude Only
**Use Case**: All albums except X and Y
```python
state = TagFilterState()
state.add_exclusion("Live")
state.add_exclusion("Compilation")
# No groups = matches all albums (except excluded)
```

## API Reference

### TagFilterState

```python
class TagFilterState:
    # Group Management
    add_group(group=None) -> TagFilterGroup
    remove_group(group_id: str) -> bool
    get_group(group_id: str) -> Optional[TagFilterGroup]
    clear_groups()
    
    # Exclusion Management
    add_exclusion(tag: str) -> bool
    remove_exclusion(tag: str) -> bool
    clear_exclusions()
    
    # Filtering
    matches(album_tags: Set[str]) -> bool
    
    # Tag Management
    get_tag_locations(tag: str) -> Dict
    move_tag(tag: str, from_group_id: str, to_group_id: str) -> bool
    
    # Utilities
    is_empty() -> bool
    clear_all()
    get_filter_summary() -> str
    
    # Serialization
    to_dict() -> Dict
    to_json() -> str
    from_dict(data: Dict) -> TagFilterState
    from_json(json_str: str) -> TagFilterState
    
    # Migration
    from_legacy_filters(include: Set, exclude: Set) -> TagFilterState
    from_legacy_filters_as_and(include: Set, exclude: Set) -> TagFilterState
```

### TagFilterGroup

```python
class TagFilterGroup:
    # Properties
    group_id: str
    name: str
    tags: Set[str]
    operator: GroupOperator  # AND or OR
    color: Optional[str]
    enabled: bool
    
    # Methods
    add_tag(tag: str) -> bool
    remove_tag(tag: str) -> bool
    has_tag(tag: str) -> bool
    is_empty() -> bool
    matches(album_tags: Set[str]) -> bool
    
    # Serialization
    to_dict() -> Dict
    from_dict(data: Dict) -> TagFilterGroup
```

### SavedQuery

```python
class SavedQuery:
    name: str
    filter_state: TagFilterState
    description: str
    created: datetime
    last_used: Optional[datetime]
    use_count: int
    
    to_dict() -> Dict
    from_dict(data: Dict) -> SavedQuery
```

## Migration from Legacy System

### Old System
```python
# Simple dict with include/exclude states
tag_filters = {
    "Metal": FILTER_INCLUDE,
    "Jazz": FILTER_INCLUDE,
    "Live": FILTER_EXCLUDE
}
```

### New System (OR Behavior - Default)
```python
include = {"Metal", "Jazz"}
exclude = {"Live"}
state = TagFilterState.from_legacy_filters(include, exclude)
# Creates 2 groups: (Metal) OR (Jazz)
```

### New System (AND Behavior - Alternative)
```python
include = {"Metal", "Jazz"}
exclude = {"Live"}
state = TagFilterState.from_legacy_filters_as_and(include, exclude)
# Creates 1 group: (Metal AND Jazz)
```

## Real-World Examples

### Example 1: Metal Instrumentals
```python
state = TagFilterState()
group = state.add_group()
group.name = "Metal Instrumentals"
group.add_tag("Metal")
group.add_tag("Instrumental")
state.add_exclusion("Live")
```
**Matches**: Studio instrumental metal albums  
**Excludes**: Live albums

### Example 2: Female-Fronted Metal or Rock
```python
state = TagFilterState()

group1 = state.add_group()
group1.add_tag("Metal")
group1.add_tag("Female Vocals")

group2 = state.add_group()
group2.add_tag("Rock")
group2.add_tag("Female Vocals")
```
**Matches**: Metal OR Rock with female vocals

### Example 3: Progressive Fusion
```python
state = TagFilterState()
group = state.add_group()
group.add_tag("Progressive")
group.add_tag("Fusion")
group.add_tag("Jazz")
```
**Matches**: Albums that are ALL of: Progressive, Fusion, AND Jazz

### Example 4: Experimental Albums (Various Genres)
```python
state = TagFilterState()

# Experimental Metal
group1 = state.add_group()
group1.add_tag("Metal")
group1.add_tag("Experimental")

# Experimental Rock
group2 = state.add_group()
group2.add_tag("Rock")
group2.add_tag("Experimental")

# Experimental Jazz
group3 = state.add_group()
group3.add_tag("Jazz")
group3.add_tag("Experimental")

state.add_exclusion("Compilation")
```
**Matches**: Experimental albums across Metal, Rock, or Jazz  
**Excludes**: Compilations

## Serialization Example

```json
{
  "version": "2.0",
  "filter_type": "grouped",
  "groups": [
    {
      "group_id": "1",
      "name": "Metal Instrumentals",
      "tags": ["Progressive Metal", "Instrumental"],
      "operator": "AND",
      "color": "#FFE0E0",
      "enabled": true
    },
    {
      "group_id": "2",
      "name": "Jazz Fusion",
      "tags": ["Jazz", "Fusion"],
      "operator": "AND",
      "color": "#E0E0FF",
      "enabled": true
    }
  ],
  "exclude_tags": ["Live", "Compilation"],
  "group_operator": "OR",
  "active": true
}
```

## Filter Summary Format

The `get_filter_summary()` method returns human-readable text:

```
Format: (Tag1 AND Tag2) OR (Tag3 AND Tag4) | Excluding: Tag5, Tag6

Examples:
- (Instrumental AND Progressive Metal)
- (Metal AND Female Vocals) OR (Rock AND Female Vocals)
- (Jazz AND Fusion) | Excluding: Live, Compilation
- No filters active
```

## Performance Tips

1. **Order matters**: Most restrictive groups first (faster rejection)
2. **Exclusions**: Cheap to check, very effective
3. **Set operations**: O(1) membership testing
4. **Lazy evaluation**: Stops at first matching group
5. **Empty groups**: Automatically ignored

## Testing

Run tests:
```bash
pytest tests/test_tag_filter_state.py -v
```

Run examples:
```bash
python examples/tag_filter_examples.py
```

## Files

- **Implementation**: `src/albumexplore/tags/filters/tag_filter_state.py`
- **Tests**: `tests/test_tag_filter_state.py`
- **Examples**: `examples/tag_filter_examples.py`
- **Design Doc**: `docs/TAG_FILTER_LOGIC_DESIGN.md`
- **Architecture**: `docs/TAG_FILTER_ARCHITECTURE.md`

## Next Steps

**Phase 2**: Build UI components
- TagGroupWidget (visual group representation)
- TagFilterPanel (container for groups)
- Integration with TagExplorerView

See `docs/TAG_FILTER_LOGIC_DESIGN.md` for full implementation plan.

---

**Status**: ✅ Phase 1 Complete (Core Logic)  
**Test Coverage**: 92%  
**Tests Passing**: 29/29
