# Tag Filter System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              TagFilterPanel (QWidget)                     │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  [+ New Group]  [Clear All]   [Filter Summary]     │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─ TagGroupWidget ─────────────────────────────┐        │  │
│  │  │  Group 1: Metal Instrumentals       [×]      │        │  │
│  │  │  • Progressive Metal           [×]           │        │  │
│  │  │  • Instrumental                [×]           │        │  │
│  │  │  [+ Add tag]                                 │        │  │
│  │  └──────────────────────────────────────────────┘        │  │
│  │                      OR                                   │  │
│  │  ┌─ TagGroupWidget ─────────────────────────────┐        │  │
│  │  │  Group 2: Jazz Fusion              [×]       │        │  │
│  │  │  • Jazz                    [×]               │        │  │
│  │  │  • Fusion                  [×]               │        │  │
│  │  │  [+ Add tag]                                 │        │  │
│  │  └──────────────────────────────────────────────┘        │  │
│  │                                                            │  │
│  │  ┌─ Exclusions ───────────────────────────────┐          │  │
│  │  │  • Live                    [×]              │          │  │
│  │  │  • Compilation             [×]              │          │  │
│  │  │  [+ Add exclusion]                          │          │  │
│  │  └─────────────────────────────────────────────┘          │  │
│  │                                                            │  │
│  │  Results: 47 albums match                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            TagExplorerView (existing)                     │  │
│  │  ┌───────────────┬──────┬──────┬──────────┬───────────┐  │  │
│  │  │ Tag           │Count │Match │ Category │ Actions   │  │  │
│  │  ├───────────────┼──────┼──────┼──────────┼───────────┤  │  │
│  │  │ Prog Metal    │ 234  │  47  │ Style    │ [Menu▼]  │  │  │
│  │  │ Instrumental  │ 156  │  47  │ Vocal    │ [Menu▼]  │  │  │
│  │  │ Jazz          │  89  │  23  │ Style    │ [Menu▼]  │  │  │
│  │  └───────────────┴──────┴──────┴──────────┴───────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ filtersChanged signal
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Filter Logic                           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              TagFilterState                             │    │
│  │  • groups: List[TagFilterGroup]                        │    │
│  │  • exclude_tags: Set[str]                              │    │
│  │  • matches(album_tags) -> bool                         │    │
│  │  • add_group() -> TagFilterGroup                       │    │
│  │  • add_exclusion(tag)                                  │    │
│  │  • get_filter_summary() -> str                         │    │
│  │  • to_json() / from_json()                             │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              │ contains 0..N                     │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              TagFilterGroup                             │    │
│  │  • group_id: str                                       │    │
│  │  • name: str                                           │    │
│  │  • tags: Set[str]                                      │    │
│  │  • operator: GroupOperator (AND/OR)                    │    │
│  │  • color: Optional[str]                                │    │
│  │  • enabled: bool                                       │    │
│  │  • matches(album_tags) -> bool                         │    │
│  │  • add_tag(tag) / remove_tag(tag)                      │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ filtering
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Album Data                               │
│                                                                   │
│  Album 1: {Progressive Metal, Instrumental, Epic}               │
│  Album 2: {Jazz, Fusion, Smooth}                                │
│  Album 3: {Death Metal, Technical, Live}                        │
│  ...                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Filter Creation
```
User Action → TagFilterPanel → TagFilterState → TagFilterGroup
                                    ↓
                              filtersChanged signal
                                    ↓
                            TagExplorerView.apply_tag_filters()
```

### 2. Album Filtering
```
Album Data → TagFilterState.matches(album_tags)
                    ↓
            Check each group (OR logic)
                    ↓
            Group.matches(album_tags) (AND logic)
                    ↓
            Check exclusions
                    ↓
            Return True/False
```

### 3. Filter Summary
```
TagFilterState → get_filter_summary()
        ↓
"(Prog Metal AND Instrumental) OR (Jazz AND Fusion) | Excluding: Live"
        ↓
Display in UI
```

## Component Responsibilities

### TagFilterState (Core Logic)
- **Responsibility**: Manage complete filter state
- **Dependencies**: TagFilterGroup
- **Used by**: UI components, serialization
- **Location**: `src/albumexplore/tags/filters/tag_filter_state.py`

### TagFilterGroup (Group Logic)
- **Responsibility**: Manage single group of tags with AND logic
- **Dependencies**: None (pure data structure)
- **Used by**: TagFilterState
- **Location**: `src/albumexplore/tags/filters/tag_filter_state.py`

### TagFilterPanel (UI - Phase 2)
- **Responsibility**: Visual container for filter groups
- **Dependencies**: TagFilterState, TagGroupWidget
- **Signals**: `filtersChanged()`
- **Location**: TBD `src/albumexplore/gui/widgets/tag_filter_panel.py`

### TagGroupWidget (UI - Phase 2)
- **Responsibility**: Visual representation of one group
- **Dependencies**: TagFilterGroup
- **Signals**: `tagAdded(str)`, `tagRemoved(str)`, `groupDeleted()`
- **Location**: TBD `src/albumexplore/gui/widgets/tag_group_widget.py`

### TagExplorerView (Existing - Integration)
- **Responsibility**: Main tag exploration interface
- **Integration**: Use TagFilterState instead of dict
- **Location**: `src/albumexplore/visualization/views/tag_explorer_view.py`

## Filter Logic Pseudocode

```python
def matches(album_tags: Set[str]) -> bool:
    # Step 1: Check exclusions (fast reject)
    if any_exclude_tag_in(album_tags):
        return False
    
    # Step 2: If no include groups, accept all
    if no_groups:
        return True
    
    # Step 3: Check if ANY group matches (OR logic)
    for group in groups:
        if group.matches(album_tags):  # ALL tags in group (AND logic)
            return True
    
    return False
```

## Example Filter Evaluation

**Filter**: `(Prog Metal AND Instrumental) OR (Jazz AND Fusion)` excluding `Live`

**Album A**: `{Progressive Metal, Instrumental, Epic}`
1. Not in exclude list ✓
2. Check Group 1: Has both "Prog Metal" and "Instrumental" ✓
3. **Result**: MATCH ✓

**Album B**: `{Jazz, Smooth}`
1. Not in exclude list ✓
2. Check Group 1: Missing "Prog Metal" and "Instrumental" ✗
3. Check Group 2: Has "Jazz" but missing "Fusion" ✗
4. **Result**: NO MATCH ✗

**Album C**: `{Jazz, Fusion, Live}`
1. In exclude list ("Live") ✗
2. **Result**: NO MATCH ✗ (excluded before checking groups)

## State Transitions

```
┌─────────────┐
│   Empty     │ No filters active, all albums shown
└──────┬──────┘
       │ add_group()
       ▼
┌─────────────┐
│ Has Groups  │ Only albums matching groups shown
└──────┬──────┘
       │ add_exclusion()
       ▼
┌─────────────┐
│ Groups +    │ Albums match groups AND not excluded
│ Exclusions  │
└──────┬──────┘
       │ clear_all()
       ▼
┌─────────────┐
│   Empty     │ Back to showing all albums
└─────────────┘
```

## Serialization Format

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
    }
  ],
  "exclude_tags": ["Live", "Compilation"],
  "group_operator": "OR",
  "active": true
}
```

## Integration Points

### Existing Code Integration
1. **Replace** `tag_filters: Dict[str, int]` with `filter_state: TagFilterState`
2. **Update** `apply_tag_filters()` to use `filter_state.matches()`
3. **Add** `TagFilterPanel` to UI layout
4. **Connect** filter panel signals to refresh logic

### Backward Compatibility
```python
# Old code
tag_filters = {"Metal": FILTER_INCLUDE, "Jazz": FILTER_INCLUDE}

# Migration
filter_state = TagFilterState.from_legacy_filters(
    include_tags={"Metal", "Jazz"},
    exclude_tags=set()
)
```

## Performance Considerations

1. **Set Operations**: O(1) membership testing
2. **Early Exit**: Exclusions checked first
3. **Lazy OR**: Stop at first matching group
4. **Batch Processing**: Compatible with existing batch logic
5. **Memory**: Minimal overhead (sets are efficient)

## Testing Strategy

### Unit Tests (✅ Complete)
- 29 tests covering all logic paths
- Edge cases (empty groups, disabled groups)
- Complex scenarios (real-world queries)
- Serialization round-trips

### Integration Tests (Phase 2)
- UI component creation
- Signal connections
- Filter state updates
- Visual feedback

### End-to-End Tests (Phase 3)
- User workflows
- Filter persistence
- Performance with large datasets
- Migration from legacy system
