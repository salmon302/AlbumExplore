# Quick Start: Tag Relationship Similarity

## What Changed?

Your album similarity system now understands tag relationships:
- **"prog rock" and "progressive rock"** are treated as synonyms
- **"symphonic prog"** is recognized as a type of **"progressive rock"**
- **Rare tags** like "canterbury scene" now carry more weight than common tags like "rock"

## How to Use (GUI)

1. **Launch the app**: `python -m albumexplore.gui.app`
2. **Open Similarity View**: Right-click any album → "Show Similar Albums"
3. **Enable fuzzy matching**: Check ☑ "Use fuzzy tag matching" (ON by default)
4. **Optional - Enable IDF weighting**: Check ☑ "Weight rare tags higher"

That's it! Results will now include albums with related tags.

## Quick Test

```bash
# Test the improvements (compares before/after)
python test_tag_relationship_improvements.py
```

Expected output:
- Fuzzy matching finds MORE similar albums
- Albums with "prog" match albums with "progressive rock"
- Similarity scores reflect semantic relationships

## Discover More Relationships

```bash
# Auto-discover potential tag relationships from your database
python analyze_tag_relationships.py

# Save output to: data/discovered_relationships.yml
# Review and merge useful ones into: data/tag_relationships_comprehensive.yml
```

## Files You Care About

- **`data/tag_relationships_comprehensive.yml`** - Tag relationships (you can edit this!)
- **UI Controls** - In Similarity View, look for new checkboxes
- **Test Script** - `test_tag_relationship_improvements.py`

## Common Scenarios

### Scenario 1: "I want similar prog rock albums"

**Before**: Only albums tagged exactly "progressive rock"  
**After**: Albums tagged "prog rock", "prog", "symphonic prog", "art rock" also match

### Scenario 2: "Canterbury scene albums are too rare"

**Before**: Albums with "canterbury scene" tag matched weakly  
**After**: Enable "Weight rare tags higher" → rare tags get priority

### Scenario 3: "I want to add my own tag relationships"

Edit `data/tag_relationships_comprehensive.yml`:
```yaml
your-tag:
  - tag: related-tag
    type: related
    weight: 0.75
```

Restart app or reload relationships in UI.

## Troubleshooting

**Q: Fuzzy matching seems slower**  
A: First calculation loads relationships (~10-20ms overhead). Subsequent calls are cached.

**Q: I want exact matching back**  
A: Uncheck "Use fuzzy tag matching" in the Similarity View.

**Q: How do I see which relationships are loaded?**  
A: Check app logs or count entries in `tag_relationships_comprehensive.yml` (150+ currently).

**Q: Can I add more relationships?**  
A: Yes! Either edit YAML manually or run `analyze_tag_relationships.py` for suggestions.

## What's Included

✅ **150+ Curated Relationships** - prog, metal, jazz, electronic families  
✅ **Auto-Discovery Tool** - Find more relationships from your data  
✅ **IDF Weighting** - Prioritize rare/distinctive tags  
✅ **UI Integration** - Simple checkboxes to enable features  
✅ **Backward Compatible** - Can disable all enhancements  

---

**Questions?** Check `TAG_RELATIONSHIP_SIMILARITY_ENHANCEMENT.md` for full docs.
