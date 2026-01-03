# Quick Visual Guide: Relationship Indicators

## What You'll See Now

### 1. Status Indicator (in Advanced Settings)
```
┌─────────────────────────────────────────────────────────┐
│ Developer Tools (Tag Relationships)                     │
│                                                         │
│ ☐ Override with custom mappings (0 relationships)      │  ← Gray, no relationships
│                                                         │
│ ☑ Override with custom mappings (150 relationships loaded) ← Green/bold, active!
│   [━━━━━●━━━━] 0.50                                    │
│   [Load File...] [Validate] [Edit...] [Discover...]   │
└─────────────────────────────────────────────────────────┘
```

### 2. Result Indicators (in similarity table)
```
Similar Albums (20 matches)

Album                                          Similarity    Score
─────────────────────────────────────────────────────────────────
🔗 Dream Theater - Images and Words           ████████████  0.834  ← Used relationships!
   Rush - 2112                                ██████████    0.745  ← Exact match only
🔗 Porcupine Tree - In Absentia               ████████████  0.812  ← Used relationships!
   Tool - Lateralus                           ███████████   0.789  ← Exact match only
🔗 Opeth - Blackwater Park                    ████████████  0.776  ← Used relationships!
```

The 🔗 emoji tells you instantly which results benefited from tag relationships.

### 3. Enhanced Tooltips (hover over any result)

#### WITH Fuzzy Matching:
```
┌─────────────────────────────────────────────────┐
│ Dream Theater - Images and Words                │
│ Overall Similarity: 0.834                       │
│                                                 │
│ 🔗 Fuzzy Tag Match: 0.756                      │ ← Shows relationship score!
│ (Using tag relationships)                       │
│   • prog metal, technical, complex, symphonic  │
│                                                 │
│ Score Breakdown:                                │
│   Tags: 0.588                                   │
│   Genre: 0.150                                  │
│   Year: 0.086                                   │
│   Location: 0.010                               │
│                                                 │
│ ✓ Tag relationships active                     │ ← Confirmation!
│                                                 │
│ Double-click to explore this album              │
└─────────────────────────────────────────────────┘
```

#### WITHOUT Fuzzy Matching:
```
┌─────────────────────────────────────────────────┐
│ Rush - 2112                                     │
│ Overall Similarity: 0.745                       │
│                                                 │
│ Tag Match: 8 / 15 exact                        │ ← Simple exact count
│   • progressive rock, instrumental, 70s        │
│                                                 │
│ Score Breakdown:                                │
│   Tags: 0.533                                   │
│   Genre: 0.150                                  │
│   Year: 0.052                                   │
│   Location: 0.010                               │
│                                                 │
│ Double-click to explore this album              │
└─────────────────────────────────────────────────┘
```

## How to Test It

1. **Open your app** (already running)
2. **Select any progressive rock album** (like the Uranium album you have open)
3. **Switch to Similarity view**
4. **Expand Advanced Settings** (click "Advanced Settings ▼")
5. **Look at the status indicator** - should show "(150 relationships loaded)"

### Test Scenario A: See the Difference
1. **Uncheck** "Override with custom mappings"
   - Status turns gray: `(150 relationships loaded)`
   - Note the results (no 🔗 emojis)
   - Hover over results - shows "Tag Match: X / Y exact"

2. **Check** "Override with custom mappings"
   - Status turns green/bold: `(150 relationships loaded)`
   - Results may change
   - Look for 🔗 emojis on some results
   - Hover over results - shows "🔗 Fuzzy Tag Match: 0.XXX"

### Test Scenario B: Load Custom Relationships
1. **Click** "Load File..." button
2. **Select** a relationship file (e.g., `data/tag_relationships_comprehensive.yml`)
3. **Watch** the status update with count
4. **Results** automatically refresh

## What Each Indicator Means

### Status Colors:
- **Gray** = Relationships loaded but not active
- **Green/Bold** = Relationships loaded AND actively being used
- **(0 relationships)** = No relationships file loaded

### Emoji Indicators:
- **🔗** = This specific result used tag relationships to match
- **No emoji** = This result matched with exact tags only

### Tooltip Clues:
- **"Fuzzy Tag Match"** = Using relationships
- **"Tag Match: N / M exact"** = Not using relationships
- **"✓ Tag relationships active"** = Confirmation at bottom of tooltip

## Quick Comparison Test

Try this to see the impact clearly:

1. **Open Similarity view** for your Uranium album
2. **Write down** the top 5 results with relationships OFF
3. **Check** "Override with custom mappings"
4. **Write down** the top 5 results with relationships ON
5. **Look for** the 🔗 emojis - those are the new matches!

## Expected Results

For your Uranium album (death industrial, industrial metal, war metal):
- **Without relationships**: Might find ~10-15 albums with exact tag matches
- **With relationships**: Should find 20+ albums including related genres
- **🔗 albums**: Will include industrial variants (dark ambient, power electronics, harsh noise)

The relationships help discover albums in related subgenres even if tags don't match exactly!

---

**Try it now** - your app is already running! Just navigate to the Similarity view and expand Advanced Settings.
