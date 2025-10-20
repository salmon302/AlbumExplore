# Tag Filter UI - Drag-and-Drop Quick Reference

## 🎯 Feature Overview

The enhanced tag filter system now supports **drag-and-drop** operations, allowing you to visually organize tags across filter groups with intuitive mouse interactions.

---

## 🖱️ Drag-and-Drop Usage

### Moving Tags Between Groups

**Method 1: Drag from Tag Chip**
1. Click and hold on any tag chip
2. Drag the chip over another group
3. Group border becomes **dashed** when hovering
4. Release to drop the tag into the new group
5. Tag automatically removed from source group

**Method 2: Context Menu (Right-Click)**
1. Right-click on a tag in the tag table
2. Select "Add to Filter Group" > Choose target group
3. Or select "Add to New Group" to create a new group

**Method 3: Multi-Select Context Menu**
1. Hold Ctrl and click multiple tags in tag table
2. Right-click on selection
3. Select "Add N tags to Group" > Choose target group
4. All selected tags added to the group at once

---

## 🎨 Visual Feedback

### Drag States

**Normal State**
```
┌─ Group 1 (Match ALL) ──────┐
│  Progressive Metal   [×]    │
│  Instrumental        [×]    │
│  [Add tag...         ] [+]  │
└─────────────────────────────┘
```

**Hover State (Dragging Over)**
```
╔═ Group 1 (Match ALL) ══════╗
║  Progressive Metal   [×]    ║  ← Dashed border!
║  Instrumental        [×]    ║
║  [Add tag...         ] [+]  ║
╚═════════════════════════════╝
```

**After Drop**
```
┌─ Group 1 (Match ALL) ──────┐
│  Progressive Metal   [×]    │
│  Instrumental        [×]    │
│  Jazz Fusion         [×]    │  ← New tag added
│  [Add tag...         ] [+]  │
└─────────────────────────────┘
```

---

## 🔄 Common Workflows

### Workflow 1: Reorganize Tags

**Goal:** Move "Technical" from Group 1 to Group 2

```
Before:
  Group 1: Progressive Metal, Technical, Instrumental
  Group 2: Heavy, Aggressive

Steps:
  1. Click and drag "Technical" chip from Group 1
  2. Hover over Group 2 (watch for dashed border)
  3. Release mouse to drop

After:
  Group 1: Progressive Metal, Instrumental
  Group 2: Heavy, Aggressive, Technical
```

### Workflow 2: Create Genre-Based Groups

**Goal:** Organize tags by musical style

```
Steps:
  1. Click "+ New Group" to create Group 1
  2. Right-click "Progressive Metal" in tag table
  3. Select "Add to Filter Group" > "Group 1"
  4. Repeat for related tags (Technical, Complex)
  5. Click "+ New Group" for Group 2
  6. Add "Heavy", "Aggressive" to Group 2
  
Result:
  Group 1: Progressive Metal AND Technical AND Complex
  OR
  Group 2: Heavy AND Aggressive
```

### Workflow 3: Quick Exclusions

**Goal:** Exclude unwanted tags from results

```
Steps:
  1. Right-click "Live" tag in table
  2. Select "➖ Add to Exclusions"
  3. Tag appears in Exclusions section
  4. Results automatically filtered

Alternative:
  1. Ctrl+Click to select multiple tags (Live, Compilation, Demo)
  2. Right-click selection
  3. Select "➖ Add 3 tags to Exclusions"
  4. All added to exclusions instantly
```

---

## ⌨️ Keyboard & Mouse Shortcuts

| Action | Shortcut | Description |
|--------|----------|-------------|
| **Start Drag** | Click + Hold | Click tag chip and hold for 100ms |
| **Move Tag** | Drag + Drop | Drag chip to another group |
| **Cancel Drag** | Esc (planned) | Cancel drag operation |
| **Copy Tag** | Ctrl+Drag (planned) | Copy instead of move |
| **Multi-Select** | Ctrl+Click | Select multiple tags in table |
| **Context Menu** | Right-Click | Show options for selected tag(s) |

---

## 🎯 Drag-and-Drop Rules

### What Happens During Drag

1. **Source Group**: Tag is NOT immediately removed
2. **Visual Feedback**: Dragged tag appears to move with cursor
3. **Target Groups**: Show dashed border when hovered
4. **Drop**: Tag added to target, removed from source
5. **Deduplication**: If tag exists in multiple groups, only kept in target

### Smart Behavior

**Automatic Deduplication:**
- Tags can only exist in ONE group at a time
- Dropping a tag removes it from all other groups
- Prevents logical conflicts in filter logic

**Visual Consistency:**
- Tag color matches its group color
- Border color matches group color during hover
- Immediate UI update on drop

**Error Prevention:**
- Can't drop tag on same group (no-op)
- Invalid drop targets don't accept (cursor changes)
- Groups with same tag prevent duplicates

---

## 🔧 Technical Details

### MIME Types

Drag-and-drop uses two MIME types for compatibility:

```python
# Custom format (preferred)
'application/x-tagchip'  # Binary encoded tag text

# Fallback format
'text/plain'             # Plain text tag name
```

### Signals Emitted

```python
# From TagChip
tagChip.dragStarted.emit(tag_text)

# From TagGroupWidget
groupWidget.tagDraggedOut.emit(tag_text)
groupWidget.tagDroppedIn.emit(tag_text)

# From TagFilterPanel
panel.filtersChanged.emit()  # After drop completes
```

### Drop Acceptance Logic

```python
def dragEnterEvent(event):
    # Accept if:
    if event.mimeData().hasText() or 
       event.mimeData().hasFormat('application/x-tagchip'):
        event.acceptProposedAction()
        # Show visual feedback
    else:
        event.ignore()
```

---

## 🎨 Customization

### Changing Drag Behavior

**Make Tags Non-Draggable:**
```python
chip = TagChip("My Tag", draggable=False)
```

**Custom Drop Behavior:**
```python
def custom_dropEvent(self, event):
    tag_text = event.mimeData().text()
    # Custom logic here
    self.add_tag(tag_text)
    event.acceptProposedAction()
```

### Styling Drag States

**Custom Hover Border:**
```python
self.frame.setStyleSheet(f"""
    QFrame {{
        border: 4px dotted #FF0000;  /* Custom style */
        border-radius: 8px;
        background: white;
    }}
""")
```

---

## 🐛 Troubleshooting

### Issue: Drag Not Starting

**Possible Causes:**
- Tag chip has `draggable=False`
- Mouse moved less than 10 pixels
- Click released too quickly

**Solution:**
- Check chip constructor: `TagChip(text, draggable=True)`
- Hold mouse button and move at least 10 pixels
- Ensure mouse button stays pressed

### Issue: Drop Not Accepted

**Possible Causes:**
- Target doesn't accept drops
- Tag already in target group
- MIME type not recognized

**Solution:**
- Verify `setAcceptDrops(True)` on target
- Check for duplicate tags
- Ensure MIME data is set correctly

### Issue: Visual Feedback Not Showing

**Possible Causes:**
- CSS not applied
- Event not received
- Border color same as background

**Solution:**
- Check `dragEnterEvent` is called
- Verify stylesheet is applied
- Use contrasting colors

---

## 📚 API Reference

### TagChip

```python
class TagChip(QWidget):
    """Visual tag chip with drag support."""
    
    dragStarted = pyqtSignal(str)  # Emits tag text
    
    def __init__(
        self,
        tag_text: str,
        color: str = None,
        removable: bool = True,
        draggable: bool = True,  # New parameter
        parent=None
    )
```

### TagGroupWidget

```python
class TagGroupWidget(QWidget):
    """Filter group with drag-drop support."""
    
    tagDraggedOut = pyqtSignal(str)  # Tag dragged from group
    tagDroppedIn = pyqtSignal(str)   # Tag dropped into group
    
    def dragEnterEvent(self, event: QDragEnterEvent)
    def dragLeaveEvent(self, event)
    def dropEvent(self, event: QDropEvent)
```

### TagFilterPanel

```python
class TagFilterPanel(QWidget):
    """Main filter panel coordinating groups."""
    
    def _on_tag_dragged_out(self, tag: str, source_group_id: str)
    def _on_tag_dropped_in(self, tag: str, target_group_id: str)
```

---

## 🎓 Best Practices

### DO:
✅ Use drag-and-drop for quick reorganization  
✅ Use context menu for bulk operations  
✅ Create logical group names  
✅ Keep groups focused (3-5 tags each)  
✅ Use exclusions for unwanted tags  

### DON'T:
❌ Drag tags too quickly (wait for visual feedback)  
❌ Create too many groups (use OR logic effectively)  
❌ Add same tag to multiple groups (auto-deduplicated anyway)  
❌ Forget to check results count after changes  

---

## 🚀 Coming Soon

**Planned Enhancements:**
- Ctrl+Drag to copy instead of move
- Drag multiple tags at once
- Drag tags from external sources
- Drop zones for quick exclusions
- Visual "ghost" of tag during drag
- Undo/redo for drag operations
- Drag groups to reorder

---

## 📖 Related Documentation

- [Tag Filter Logic Design](TAG_FILTER_LOGIC_DESIGN.md)
- [Tag Filter Architecture](TAG_FILTER_ARCHITECTURE.md)
- [Phase 1 Complete](TAG_FILTER_PHASE1_COMPLETE.md)
- [Phase 2 Complete](TAG_FILTER_PHASE2_COMPLETE.md)
- [Phase 3 Progress](TAG_FILTER_PHASE3_PROGRESS.md)

---

**Last Updated:** October 16, 2025  
**Version:** Phase 3 - Enhanced UI  
**Status:** Drag-and-Drop ✅ Complete
