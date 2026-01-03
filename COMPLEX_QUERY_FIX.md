# Complex Query Implementation - Bug Fixes

## Problem Summary

The complex query implementations (TagFilterPanel, QueryEditorDialog, and TokenizedQueryInput) were present in the codebase but **not properly connected** to the Tag Explorer View, making them inaccessible and non-functional.

## Issues Identified

### 1. Filter Panel Signal Not Connected
**File:** `src/albumexplore/visualization/views/tag_explorer_view.py` (line ~547)

**Issue:** The `TagFilterPanel` was created and added to the UI, but its `filtersChanged` signal was never connected to the `apply_tag_filters()` method.

**Impact:** Any changes made in the filter panel (adding groups, adding exclusions, etc.) would not actually filter the albums displayed.

**Fix:** Added signal connection:
```python
self.filter_panel.filtersChanged.connect(self.apply_tag_filters)
```

### 2. **CRITICAL: Filter Panel Constructor Called Incorrectly**
**File:** `src/albumexplore/visualization/views/tag_explorer_view.py` (line ~375)

**Issue:** The TagFilterPanel was being instantiated as `TagFilterPanel(self)`, which passed the TagExplorerView instance as the `filter_state` parameter (first positional arg) instead of as the `parent` parameter (third positional arg).

**Impact:** This would cause the filter panel to fail to initialize properly, potentially treating the view object as a filter state, leading to AttributeErrors or silent failures.

**Fix:** Changed to explicit keyword argument:
```python
self.filter_panel = TagFilterPanel(parent=self)
```

### 3. Query Editor Dialog Not Applying Results
**File:** `src/albumexplore/gui/widgets/tag_filter_panel.py` (line ~268)

**Issue:** The `_on_open_advanced_query()` method opened the `QueryEditorDialog` but didn't handle the dialog result or apply the query back to the filter panel.

**Impact:** Users could enter boolean queries in the advanced editor, but clicking "Apply" wouldn't actually apply the query to the filters.

**Fix:** 
- Made the filter panel accessible to the dialog via `dialog.filter_panel = self`
- Added proper result handling after `dialog.exec()`
- Ensured `filtersChanged` signal is emitted after applying query results

### 4. Query Editor Apply Logic Issue
**File:** `src/albumexplore/gui/widgets/query_editor.py` (line ~91)

**Issue:** The `on_apply()` method tried to find the filter panel through the parent view hierarchy, but the parent relationship wasn't set up correctly for the new dialog creation pattern.

**Impact:** Even when users clicked "Apply" in the query editor, it might not find the filter panel to apply the query to.

**Fix:** Added a direct `filter_panel` attribute check first before falling back to the parent view lookup pattern.

### 5. Visibility and Debugging Enhancements
**File:** `src/albumexplore/visualization/views/tag_explorer_view.py`

**Improvements:**
- Increased minimum height of filter panel container from 120px to 180px for better visibility
- Added distinctive border styling to make the panel more visible
- Added comprehensive logging at each step of filter panel creation
- Added error labels to display filter panel construction errors to users
- Added logging of visibility and height after panel is added

## Features Now Accessible

With these fixes, users can now access and use:

### 1. Advanced Filter Panel
- **Location:** Below the tag search bar in the Tag Explorer view
- **Features:**
  - Create multiple filter groups with OR logic between them
  - Add tags to groups for AND logic within groups
  - Add exclusion tags (NOT logic)
  - Visual representation of complex queries

### 2. Advanced Query Editor (Boolean Syntax)
- **Access:** Click the "Advanced" button in the filter panel
- **Features:**
  - Boolean query syntax with AND, OR, NOT operators
  - Parentheses for grouping
  - Query validation with parse error reporting
  - Explain feature showing match counts for sub-expressions
  - Converts queries to filter groups when possible

### 3. Inline Tokenized Query Input
- **Location:** Below the filter panel header
- **Features:**
  - Quick inline boolean query entry
  - Converts and applies queries directly to filter state
  - Visual tokenization of query components

## Testing Recommendations

1. **Basic Filter Panel:**
   - Open Tag Explorer view
   - Click "+ Group" to create a filter group
   - Add tags to the group
   - Verify albums are filtered correctly
   - Add exclusion tags and verify they work

2. **Advanced Query Editor:**
   - Click the "Advanced" button
   - Enter a query like: `progressive AND (symphonic OR neo-prog)`
   - Click "Validate" to see explain tree
   - Click "Apply" to apply the query
   - Verify the query is converted to filter groups
   - Verify albums are filtered correctly

3. **Tokenized Query Input:**
   - Type a simple query in the inline input
   - Press Enter or click apply
   - Verify the query is converted and applied

## Implementation Notes

- The filter panel and query implementations use a conversion strategy: complex boolean queries are converted to filter group representations (if possible)
- Some very complex queries (e.g., nested ORs with NOTs) cannot be converted to the simple group representation and will show a warning
- The `apply_tag_filters()` method now properly combines both legacy tag table filters AND filter panel groups
- Exclusions from both sources are combined for the final filter logic

## Future Enhancements

Consider these potential improvements:

1. Add a "query mode" that skips conversion and evaluates boolean queries directly
2. Show query syntax hints in the tokenized input field
3. Add query history/saved queries feature
4. Improve error messages for complex queries that cannot be converted
5. Add visual feedback when filters are active (e.g., colored border on filter panel)
