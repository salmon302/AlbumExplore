# Similarity View UI Redesign

## Overview
The similarity view UI has been redesigned to improve usability, reduce visual clutter, and provide better discoverability of features.

## Changes Made

### 1. Better Visual Hierarchy
The controls are now organized into distinct sections:

- **Primary Controls** (always visible)
  - Limit results combo box
  - Similarity threshold slider
  - Back button
  
- **Smart Matching** (highlighted section, always visible)
  - Fuzzy tag matching checkbox
  - IDF weights checkbox
  - Styled with subtle blue background for prominence
  
- **Advanced Settings** (collapsible, hidden by default)
  - Component weights (Tags/Vocals/Location sliders)
  - Developer tools for tag relationships
  - Manual mapping controls

### 2. Visual Improvements

**Styled Sections:**
- Smart Matching section uses a subtle blue background (`rgba(70,130,180,0.15)`) to draw attention to new features
- Advanced settings use neutral gray backgrounds to maintain clean appearance
- Consistent border styling and rounded corners throughout

**Better Labels:**
- "Fuzzy tag matching" instead of "Use fuzzy tag matching" (cleaner)
- More descriptive tooltips with context
- Percentage indicators on weight sliders

**Spacing:**
- Improved spacing between controls (8px gaps)
- Better content margins (10px)
- Reduced visual density while maintaining functionality

### 3. Feature Discoverability

**Advanced Settings Toggle:**
- Advanced Settings button is always visible
- Shows `▼` when collapsed, `▲` when expanded
- Hides complexity until needed

**Grouped Controls:**
- Related controls are visually grouped together
- Component weights in one section
- Developer tools in separate section

**Smart Matching Prominence:**
- New fuzzy matching and IDF features are highlighted
- Positioned prominently near top of controls
- Cannot be hidden, ensuring users discover new capabilities

### 4. Reduced Clutter

**Before:**
- 15+ controls in single horizontal row
- No visual grouping
- Manual mapping controls always visible
- Poor discoverability

**After:**
- Primary controls in clean horizontal layout
- Smart Matching in highlighted section
- Advanced features hidden by default
- Clear visual hierarchy

## UI Structure

```
┌─────────────────────────────────────────────┐
│ PRIMARY CONTROLS                            │
│ [Limit ▼] [Threshold ━━━━●━━] [← Back]    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ SMART MATCHING (highlighted in blue)       │
│ ☑ Fuzzy tag matching                       │
│ ☑ IDF weights                              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Advanced Settings ▼]                       │
└─────────────────────────────────────────────┘
  ↓ (when expanded) ↓
┌─────────────────────────────────────────────┐
│ COMPONENT WEIGHTS                           │
│ Tags [━━━●━━] 70   Vocals [●━━━━━] 0       │
│ Location [━●━━━] 5                          │
│ [Reset] [Per-tag...] [Reset Per-tag]       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ DEVELOPER TOOLS (Tag Relationships)         │
│ ☐ Override with custom mappings [━━●━━] 0.50│
│ [Load File...] [Validate] [Edit...]        │
│ [Discover...]                               │
└─────────────────────────────────────────────┘
```

## Technical Implementation

### Files Modified
- `src/albumexplore/gui/views/similarity_bar_view.py`
  - Redesigned `_setup_ui()` method
  - Added `_toggle_advanced()` method
  - Enhanced `_on_manual_toggle()` to enable/disable related controls

### Key Features
- Collapsible sections using `QWidget.setVisible()`
- Styled sections using inline CSS (`QWidget.setStyleSheet()`)
- Better tooltips for user guidance
- Percentage displays on sliders
- Consistent button styling

### Backward Compatibility
- All existing functionality preserved
- Default values unchanged
- Signal connections maintained
- No breaking changes to API

## User Impact

**Improved Usability:**
- Less overwhelming for new users
- Advanced features discoverable but not intrusive
- Clear visual focus on important controls

**Better Workflow:**
- Common tasks (adjusting limit/threshold) always accessible
- New features (fuzzy matching) prominently displayed
- Advanced tuning (weights, manual mappings) accessible when needed

**Professional Appearance:**
- Cleaner, more organized layout
- Consistent styling throughout
- Better use of visual hierarchy

## Future Enhancements

Potential improvements for future iterations:

1. **Tooltips on Hover:**
   - Add "?" icons with detailed explanations
   - Show examples of fuzzy matching in action

2. **Visual Feedback:**
   - Show number of active manual mappings
   - Display IDF weight impact indicator

3. **Presets:**
   - Quick presets for common use cases
   - Save/load user configurations

4. **Inline Help:**
   - Expandable help text within sections
   - Tutorial mode for first-time users

## Testing

The redesigned UI has been tested for:
- ✅ Import syntax (no errors)
- ✅ Application startup
- ✅ Default state (advanced settings hidden)
- ⏳ Visual appearance (manual testing required)
- ⏳ Toggle functionality (manual testing required)
- ⏳ Control interactions (manual testing required)

## Notes

- PyYAML installation recommended for full tag relationship functionality
- Manual mappings feature now better hidden for typical users
- Smart matching features are now the recommended default
