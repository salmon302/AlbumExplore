# Tag Filter Logic Design: OR vs AND Operations

## Current State

Currently, the tag explorer supports **Include** and **Exclude** filters, but all included tags function with **OR logic** (implicit):
- **Include filters**: An album matches if it has ANY of the included tags
- **Exclude filters**: An album is excluded if it has ANY of the excluded tags

This means if you include tags "Progressive Metal" and "Jazz Fusion", you get albums that have *either* tag.

## Problem Statement

Users need the ability to search for albums that have:
1. **ALL** of certain tags (AND logic)
2. **ANY** of certain tags (OR logic)
3. **Complex combinations** (e.g., (Tag A AND Tag B) OR (Tag C AND Tag D))

For example:
- Albums that are both "Progressive Metal" AND "Instrumental"
- Albums that are "Jazz" OR "Fusion" OR "Jazz Fusion"
- Albums that are ("Metal" AND "Female Vocals") OR ("Rock" AND "Experimental")

## Design Principles

1. **Intuitive UI**: Users should understand the logic without reading documentation
2. **Visual clarity**: The current filter state should be immediately obvious
3. **Flexibility**: Support both simple and complex queries
4. **Backward compatibility**: Don't break existing workflows
5. **Performance**: Maintain fast filtering even with complex logic

## Proposed Solution: Tag Groups with Logic Operators

### Concept Overview

Introduce **Tag Groups** where:
- Each group contains one or more tags
- Tags within a group use **AND logic** (must have all)
- Between groups use **OR logic** (match any group)
- Maintain the existing **Exclude** filters (applied after include logic)

**Filter Logic Formula:**
```
(Group1_Tag1 AND Group1_Tag2 AND ...) OR 
(Group2_Tag1 AND Group2_Tag2 AND ...) OR 
...
AND NOT (Exclude_Tag1 OR Exclude_Tag2 OR ...)
```

### UI Design Options

#### **Option 1: Visual Tag Groups Panel (RECOMMENDED)**

```
┌─ Tag Filter Groups ─────────────────────────────────────┐
│                                                           │
│  [+ New Group]  [Clear All]                              │
│                                                           │
│  ┌─ Group 1 (Match ALL) ────────────────────┐  [×]      │
│  │  • Progressive Metal             [×]      │           │
│  │  • Instrumental                  [×]      │           │
│  │  [+ Add tag to group]                     │           │
│  └───────────────────────────────────────────┘           │
│                         OR                                │
│  ┌─ Group 2 (Match ALL) ────────────────────┐  [×]      │
│  │  • Jazz                          [×]      │           │
│  │  • Fusion                        [×]      │           │
│  │  [+ Add tag to group]                     │           │
│  └───────────────────────────────────────────┘           │
│                                                           │
│  ┌─ Exclude Tags ───────────────────────────┐           │
│  │  • Live                          [×]      │           │
│  │  • Compilation                   [×]      │           │
│  │  [+ Add exclusion]                        │           │
│  └───────────────────────────────────────────┘           │
│                                                           │
│  Results: 47 albums match                                │
└───────────────────────────────────────────────────────────┘
```

**Features:**
- Drag and drop tags between groups
- Visual "OR" separators between groups
- Each group shows "Match ALL" indicator
- Inline tag removal with [×] buttons
- Add tags via dropdown or search
- Collapsible groups for complex queries

#### **Option 2: Tag Table with Group Column**

Extend the existing tag table to include a "Group" column:

```
┌─ Tags ─────────────────────────────────────────────────┐
│ Tag Name          │ Count │ Match │ Group    │ Action  │
├───────────────────┼───────┼───────┼──────────┼─────────┤
│ Progressive Metal │  234  │  47   │ Group 1  │ [Menu▼]│
│ Instrumental      │  156  │  47   │ Group 1  │ [Menu▼]│
│ Jazz              │  89   │  23   │ Group 2  │ [Menu▼]│
│ Fusion            │  67   │  23   │ Group 2  │ [Menu▼]│
│ Live              │  45   │  0    │ Exclude  │ [Menu▼]│
└────────────────────────────────────────────────────────┘

Context Menu:
  • Add to Group 1 (AND)
  • Add to Group 2 (AND)  
  • Add to Group 3 (AND)
  • Create New Group
  ───────────────────
  • Exclude
  • Clear Filter
```

**Features:**
- Maintains familiar table interface
- Group assignment via dropdown or context menu
- Color coding by group
- Groups can be renamed
- Shows match count per filter state

#### **Option 3: Query Builder Interface**

```
┌─ Filter Query Builder ──────────────────────────────────┐
│                                                           │
│  Build your filter:                                      │
│                                                           │
│  ( [Progressive Metal▼] AND [Instrumental▼] )            │
│                                                           │
│  OR                                                       │
│                                                           │
│  ( [Jazz▼] AND [Fusion▼] )                               │
│                                                           │
│  [+ Add AND Group]  [+ Add OR Group]                     │
│                                                           │
│  ─────────────────────────────────────────────           │
│  Exclude: [Live▼] [Compilation▼]                         │
│                                                           │
│  Results: 47 albums                                      │
│                                                           │
│  [Save Query]  [Load Query]  [Clear]  [Apply]           │
└───────────────────────────────────────────────────────────┘
```

**Features:**
- Explicit boolean operators
- Save/load complex queries
- More technical but very powerful
- Clear visual hierarchy

### Recommendation: **Option 1** (Visual Tag Groups Panel)

**Rationale:**
- **Most intuitive** for non-technical users
- **Visual clarity** - groups are obvious, OR logic is explicit
- **Flexible** - easy to create simple or complex queries
- **Drag-and-drop** makes it fun and interactive
- **Scales well** - groups can be collapsed
- **Familiar pattern** - similar to shopping cart or playlist organization

## Implementation Details

### Data Structure

```python
class TagFilterGroup:
    """Represents a group of tags with AND logic"""
    def __init__(self, group_id: str, name: str = ""):
        self.group_id = group_id
        self.name = name or f"Group {group_id}"
        self.tags: Set[str] = set()  # Tags in this group (AND logic)
    
    def matches(self, album_tags: Set[str]) -> bool:
        """Check if album matches this group (has ALL tags)"""
        return self.tags.issubset(album_tags)

class TagFilterState:
    """Manages the complete filter state"""
    def __init__(self):
        self.groups: List[TagFilterGroup] = []  # OR logic between groups
        self.exclude_tags: Set[str] = set()
        self.active = True
    
    def matches(self, album_tags: Set[str]) -> bool:
        """Check if album matches the filter"""
        # Check exclusions first (faster to eliminate)
        if self.exclude_tags.intersection(album_tags):
            return False
        
        # If no include groups, accept all (not excluded)
        if not self.groups:
            return True
        
        # Check if ANY group matches (OR logic)
        return any(group.matches(album_tags) for group in self.groups)
```

### UI Component Structure

```python
class TagGroupWidget(QWidget):
    """Widget representing a single tag group"""
    tagRemoved = pyqtSignal(str)  # Emitted when tag removed from group
    groupDeleted = pyqtSignal()   # Emitted when group is deleted
    
    def __init__(self, group: TagFilterGroup):
        self.group = group
        self.tag_chips = []  # Visual tag chips with [×] buttons
        self.setup_ui()
    
    def add_tag(self, tag: str):
        """Add a tag to this group"""
        pass
    
    def remove_tag(self, tag: str):
        """Remove a tag from this group"""
        pass

class TagFilterPanel(QWidget):
    """Main panel managing all tag groups"""
    filtersChanged = pyqtSignal()  # Emitted when any filter changes
    
    def __init__(self):
        self.filter_state = TagFilterState()
        self.group_widgets = []
        self.setup_ui()
    
    def create_new_group(self) -> TagGroupWidget:
        """Create a new AND group"""
        pass
    
    def delete_group(self, group_widget: TagGroupWidget):
        """Delete a group"""
        pass
    
    def add_exclusion(self, tag: str):
        """Add a tag to exclusion list"""
        pass
```

### Modified Filter Logic

```python
def apply_tag_filters(self):
    """Apply filters with AND/OR support"""
    self.setUpdatesEnabled(False)
    
    filter_state = self.filter_state  # TagFilterState instance
    
    self.filtered_albums.clear()
    self.matching_counts.clear()
    
    for node in self.album_nodes_original:
        # Get processed tags for this album
        album_tags = self._get_album_tags(node)
        
        # Apply filter logic
        if filter_state.matches(album_tags):
            self.filtered_albums.append(node)
            for tag in album_tags:
                self.matching_counts[tag] += 1
    
    self._update_views()
    self.setUpdatesEnabled(True)
```

## User Workflows

### Workflow 1: Simple AND Query
**Goal**: Find albums that are both "Progressive Metal" AND "Instrumental"

1. Click "New Group" button
2. Click on "Progressive Metal" in tag table (or search for it)
3. Click on "Instrumental" in tag table
4. Both tags appear in Group 1
5. Results update automatically

### Workflow 2: OR Query
**Goal**: Find albums that are "Jazz" OR "Fusion"

1. Click "New Group" button
2. Add "Jazz" to Group 1
3. Click "New Group" button again
4. Add "Fusion" to Group 2
5. See visual "OR" separator between groups
6. Results show albums matching either tag

### Workflow 3: Complex Query
**Goal**: (Progressive Metal AND Instrumental) OR (Jazz AND Experimental)

1. Create Group 1 with "Progressive Metal" and "Instrumental"
2. Create Group 2 with "Jazz" and "Experimental"
3. Visual display shows both groups with OR between them
4. Results update to show albums matching either combination

### Workflow 4: Migration from Current System
**Current**: User has multiple tags marked as "Include"

**Migration Strategy**:
- On first launch with new system, show migration dialog:
  ```
  You have 3 tags currently included: Jazz, Metal, Rock
  
  How would you like to filter?
  ○ Match ANY of these tags (OR) - current behavior
  ○ Match ALL of these tags (AND) - new feature
  ○ Let me configure groups manually
  
  [Continue]
  ```
- Default option maintains current behavior (separate groups)
- User can change later

## Additional Features

### 1. Quick Actions on Tag Table
Right-click on tag in table:
```
• Add to Current Group (AND)
• Add to New Group (OR)
• Add to Group 1
• Add to Group 2
  ───────────────
• Exclude
• Clear Filter
```

### 2. Visual Indicators
- **Group colors**: Each group gets a distinct pastel color
- **Tag chips**: Pills/badges for tags with group color
- **Match count**: Show how many albums match each group
- **Highlight**: Matching tags in album table are highlighted with group color

### 3. Saved Queries
```python
class SavedQuery:
    """Saved filter configuration"""
    name: str
    filter_state: TagFilterState
    created: datetime
    description: str
    
# UI for managing saved queries
┌─ Saved Queries ──────────────────┐
│ • Metal Instrumentals    [Load]  │
│ • Jazz Fusion Albums     [Load]  │
│ • 2023 Discoveries       [Load]  │
│                                   │
│ [Save Current]  [Delete]  [Edit] │
└───────────────────────────────────┘
```

### 4. Query Summary Display
Always visible summary of current filter:
```
Active Filters: (Progressive Metal AND Instrumental) OR (Jazz AND Experimental)
Excluding: Live, Compilation
Results: 47 albums
```

## Technical Considerations

### Performance Optimization
1. **Lazy evaluation**: Only evaluate groups until first match (OR logic)
2. **Tag indexing**: Pre-build index of album_id -> processed_tags
3. **Caching**: Cache results for unchanged filter states
4. **Batch processing**: Process albums in batches as currently done

### Backward Compatibility
1. **Legacy mode**: Option to revert to simple include/exclude
2. **Import existing filters**: Migrate current tag_filters dict to groups
3. **Export**: Allow exporting as simple include/exclude for other tools

### Storage Format
```json
{
  "version": "2.0",
  "filter_type": "grouped",
  "groups": [
    {
      "id": "group_1",
      "name": "Metal Instrumentals",
      "tags": ["Progressive Metal", "Instrumental"],
      "operator": "AND"
    },
    {
      "id": "group_2", 
      "name": "Jazz Fusion",
      "tags": ["Jazz", "Fusion"],
      "operator": "AND"
    }
  ],
  "exclude_tags": ["Live", "Compilation"],
  "group_operator": "OR"
}
```

## Migration Plan

### Phase 1: Foundation (Week 1)
- Implement `TagFilterGroup` and `TagFilterState` classes
- Update filter logic in `apply_tag_filters()`
- Add unit tests for new filter logic
- Maintain backward compatibility

### Phase 2: Basic UI (Week 2)
- Create `TagGroupWidget` component
- Create `TagFilterPanel` component
- Add "New Group" button
- Add tag chips with remove buttons
- Test basic functionality

### Phase 3: Enhanced UI (Week 3)
- Add drag-and-drop between groups
- Add context menu for quick actions
- Add visual OR separators
- Add group naming and colors
- Polish animations and transitions

### Phase 4: Advanced Features (Week 4)
- Implement saved queries
- Add migration dialog for existing users
- Add query summary display
- Add keyboard shortcuts
- Performance optimization

### Phase 5: Testing & Documentation
- User testing with various query types
- Documentation and tutorials
- Video demo
- Release notes

## Alternative Approaches (Considered but Not Recommended)

### Boolean Expression Input
**Example**: `(Progressive Metal AND Instrumental) OR (Jazz AND Experimental)`

**Pros**: Very flexible, compact
**Cons**: 
- Requires learning syntax
- Error-prone for complex queries
- Not intuitive for casual users
- Difficult to visualize

### Nested Tag Hierarchy
**Example**: Drag tags into tree structure

**Pros**: Familiar tree concept
**Cons**:
- Confusing what AND vs OR means in hierarchy
- Hard to represent multiple OR groups
- Takes more screen space

## Conclusion

The **Visual Tag Groups Panel** (Option 1) provides the best balance of:
- **Intuitiveness**: Clear visual groups with explicit OR separators
- **Power**: Supports arbitrarily complex queries
- **Usability**: Drag-and-drop, visual feedback, easy to learn
- **Scalability**: Groups can be collapsed, named, color-coded

This design maintains the simplicity of the current system for basic use cases while enabling power users to create sophisticated tag-based queries.

## Next Steps

1. **Review this design** with stakeholders
2. **Create UI mockups** with real data
3. **Implement prototype** with basic functionality
4. **User testing** with target users
5. **Iterate** based on feedback
6. **Full implementation** following migration plan

---

**Questions for Discussion:**
1. Should we support nesting (AND within OR within AND)?
2. How many groups should we support by default (limit to prevent complexity)?
3. Should we add a "Match Mode" toggle (ALL vs ANY) per group?
4. Do we need NOT logic (must NOT have tag) separate from Exclude?
5. Should saved queries be shareable/exportable?
