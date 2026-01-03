# Manual Relationship Impact Indicators

## Problem
Users couldn't tell if manual tag relationships were actually affecting similarity calculations. The UI showed controls but provided no feedback about whether relationships were loaded or how they influenced results.

## Solution
Added comprehensive visual indicators to show when and how manual relationships are impacting similarity calculations.

## New Features

### 1. **Relationship Count Indicator**
**Location**: Next to "Override with custom mappings" checkbox in Advanced Settings

**Displays**:
- `(0 relationships)` - No relationships loaded (gray text)
- `(150 relationships loaded)` - Relationships loaded but inactive (gray text)
- `(150 relationships loaded)` - Relationships loaded AND active (green bold text)

**Auto-updates when**:
- Toggling manual override checkbox
- Loading custom relationship file
- Editing relationships
- Accepting suggestions from auto-discovery

**Implementation**:
```python
self.manual_status_label = QLabel("(0 relationships)")
# Updates via _update_manual_status() method
```

### 2. **Visual Result Indicators**
**Location**: In the similarity results table

**Indicator**: 🔗 emoji prefix on album names

**Meaning**:
- **🔗 Present**: Fuzzy tag matching found related tags contributing to this match
- **No emoji**: Match based on exact tag matching only

**Example**:
```
🔗 Dream Theater - Images and Words     ████████████ 0.834
   Rush - 2112                          ██████████   0.745
🔗 Yes - Close to the Edge              ████████████ 0.812
```

The 🔗 indicates that tag relationships (e.g., "prog" ↔ "progressive rock") contributed to the similarity score.

### 3. **Enhanced Tooltips**
**Location**: Hover over any result in the table

**Shows**:

#### When Fuzzy Matching is Active:
```
Artist - Album Title
Overall Similarity: 0.834

🔗 Fuzzy Tag Match: 0.756
(Using tag relationships)
  • progressive rock, symphonic, 70s, complex, instrumental

Score Breakdown:
  Tags: 0.588
  Genre: 0.150
  Year: 0.086
  Location: 0.010

Genre: ✓ Progressive Rock
Year: 1992 (5 years apart)
Country: USA

✓ Tag relationships active

Double-click to explore this album
```

#### When Exact Matching is Used:
```
Artist - Album Title
Overall Similarity: 0.745

Tag Match: 8 / 15 exact
  • rock, instrumental, 70s, guitar, progressive

Score Breakdown:
  Tags: 0.533
  Genre: 0.150
  Year: 0.052
  Location: 0.010

Genre: ✓ Progressive Rock
Year: 1976 (11 years apart)
Country: Canada

Double-click to explore this album
```

### 4. **Component Breakdown**
The tooltip now clearly shows how each component contributed to the final score:
- **Tags**: Weighted tag similarity (shows fuzzy vs exact)
- **Genre**: Genre match contribution
- **Year**: Release year proximity contribution
- **Location**: Country match contribution

This makes it clear when tag relationships (via fuzzy matching) are making a significant difference vs. exact matches.

## How to Use

### Step 1: Check Relationship Status
1. Open Similarity View
2. Click "Advanced Settings ▲" to expand
3. Look at "Developer Tools (Tag Relationships)" section
4. Status shows: `(150 relationships loaded)` or similar

### Step 2: Enable/Disable to Compare
1. **With relationships**: Check "Override with custom mappings"
   - Status turns green and bold
   - Results may change
   - 🔗 emoji appears on albums using related tags

2. **Without relationships**: Uncheck "Override with custom mappings"
   - Status turns gray
   - Only exact tag matches used
   - No 🔗 emoji indicators

### Step 3: Examine Results
1. Look for 🔗 emoji in results - these albums matched via tag relationships
2. Hover over results to see detailed breakdown
3. Compare "Fuzzy Tag Match" score vs "Tag Match: N / M exact"

### Step 4: Understand Impact
**Green status + 🔗 emojis** = Relationships are actively working
**No 🔗 emojis** = Current results don't benefit from relationships (either disabled or no related tags found)

## Example Scenarios

### Scenario A: Relationships Making a Difference
```
Status: (150 relationships loaded) [GREEN/BOLD]
Checkbox: ☑ Override with custom mappings

Results:
🔗 Pink Floyd - Dark Side of the Moon     0.834  ← Related via "psychedelic rock"
🔗 King Crimson - In the Court           0.812  ← Related via "art rock"
   Genesis - Selling England              0.798  ← Exact tag match
🔗 Camel - Mirage                         0.776  ← Related via "symphonic prog"
```

**Interpretation**: 3 out of 4 results are benefiting from tag relationships

### Scenario B: Relationships Not Helping
```
Status: (150 relationships loaded) [GRAY]
Checkbox: ☐ Override with custom mappings

Results:
   Rush - Moving Pictures                 0.745  ← All exact matches
   Yes - Fragile                          0.732
   Genesis - Foxtrot                      0.718
   ELP - Brain Salad Surgery             0.701
```

**Interpretation**: Relationships disabled, using exact matching only

### Scenario C: Mixed Impact
```
Status: (150 relationships loaded) [GREEN/BOLD]
Checkbox: ☑ Override with custom mappings

Results:
   Metallica - Master of Puppets         0.889  ← Exact matches sufficient
   Megadeth - Rust in Peace              0.876  ← Exact matches
🔗 Opeth - Blackwater Park               0.812  ← Related via "progressive death metal"
   Slayer - Reign in Blood               0.798  ← Exact matches
```

**Interpretation**: Most results match exactly, but relationships help find related albums like Opeth

## Tooltip Interpretation Guide

### "🔗 Fuzzy Tag Match: 0.756"
- **High score (>0.7)**: Many related tags found
- **Medium score (0.4-0.7)**: Some related tags
- **Low score (<0.4)**: Few related tags, mostly exact

### "Tag Match: 8 / 15 exact"
- Shows exact tag overlaps when fuzzy matching is disabled
- Compare numerator/denominator to gauge similarity

### "✓ Tag relationships active"
- Appears when fuzzy matching is ON and found related tags
- Confirms relationships are influencing this specific result

### Score Breakdown Values
Each component shows its weighted contribution:
- Tags score × tag weight = tag contribution
- Genre (1.0 or 0.0) × genre weight = genre contribution
- Year similarity × year weight = year contribution
- Location (1.0 or 0.0) × location weight = location contribution

**Example**:
```
Tags: 0.588     (fuzzy_score: 0.84 × weight: 0.70)
Genre: 0.150    (exact match × weight: 0.15)
Year: 0.086     (similarity: 0.86 × weight: 0.10)
Location: 0.010 (no match × weight: 0.05)
---------
Total: 0.834
```

## Technical Details

### Status Label Updates
The status label automatically updates on:
- Manual toggle: `_on_manual_toggle()`
- File load: `_load_manual_file()`
- Editor save: `_edit_manual_mappings()`
- Suggestions apply: `_open_suggester()`

### Emoji Indicator Logic
```python
if use_fuzzy and breakdown.get('fuzzy_tag_score', 0) > 0:
    album_name = "🔗 " + album_name
```

Only appears when:
1. Fuzzy matching is enabled AND
2. The breakdown contains a non-zero fuzzy_tag_score

### Tooltip Enhancement
Checks `use_fuzzy` flag and displays:
- Fuzzy tag score (if available)
- Component breakdown with actual values
- Active relationship indicator
- Clear labeling of matching mode

## Benefits

1. **Immediate Feedback**: See relationship count at a glance
2. **Result Attribution**: Know which results used relationships (🔗)
3. **Detailed Analysis**: Hover to see exact contribution breakdown
4. **Easy Comparison**: Toggle on/off to see difference
5. **No Guesswork**: Clear visual and numerical indicators

## Future Enhancements

Potential improvements:
- **Per-result relationship list**: Show which specific relationships were used
- **Relationship strength indicator**: Color-code 🔗 by contribution strength
- **Stats summary**: Show "X% of results used relationships"
- **Relationship explorer**: Click 🔗 to see relationship chain
- **Comparison mode**: Side-by-side fuzzy vs exact results

---

**Status**: ✅ Implemented and tested  
**Impact**: Users can now clearly see when manual relationships are affecting their similarity results
