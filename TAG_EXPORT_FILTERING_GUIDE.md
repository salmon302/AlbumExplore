# Tag Export Filtering Guide

## Overview
The tag export tool now supports filtering tags by occurrence count, making it easy to export specific subsets of tags for analysis and improvement.

## Usage

### Export All Tags (Default)
```bash
python -m albumexplore.cli.export_tags
```

### Export Single-Instance Tags Only
```bash
python -m albumexplore.cli.export_tags --max-count 1
```
Output files: `raw_tags_singles.csv`, `atomic_tags_singles.csv`

### Export Rare Tags (5 or fewer occurrences)
```bash
python -m albumexplore.cli.export_tags --max-count 5
```
Output files: `raw_tags_max5.csv`, `atomic_tags_max5.csv`

### Export Common Tags (10 or more occurrences)
```bash
python -m albumexplore.cli.export_tags --min-count 10
```
Output files: `raw_tags_min10.csv`, `atomic_tags_min10.csv`

### Export Tags in a Range (5-50 occurrences)
```bash
python -m albumexplore.cli.export_tags --min-count 5 --max-count 50
```
Output files: `raw_tags_export.csv`, `atomic_tags_export.csv`

### Custom Output Directory
```bash
python -m albumexplore.cli.export_tags --max-count 1 --output-dir ./analysis
```

### Disable Enhanced Normalization
```bash
python -m albumexplore.cli.export_tags --max-count 1 --use-enhanced=false
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output-dir`, `-o` | Path | `tagoutput` | Directory for output CSV files |
| `--use-enhanced` | Flag | `True` | Use enhanced normalization (case, hyphen, misspellings) |
| `--max-count` | Integer | None | Only export tags with count ≤ this value |
| `--min-count` | Integer | None | Only export tags with count ≥ this value |

## Use Cases

### 1. Finding Candidates for Improvement
Export single-instance tags to identify:
- Potential misspellings
- Tags that could be merged
- Location-specific tags (cities, countries)
- Overly specific tags

```bash
python -m albumexplore.cli.export_tags --max-count 1
# Review: tagoutput/raw_tags_singles.csv
```

### 2. Analyzing Rare Tags
Export tags with 2-10 occurrences to find:
- Similar tags that could be consolidated
- Variants that should be merged
- Tags needing better categorization

```bash
python -m albumexplore.cli.export_tags --min-count 2 --max-count 10
```

### 3. Reviewing Common Tags
Export frequently used tags to:
- Verify normalization is working correctly
- Check for popular variants that should be consolidated
- Identify core genre/style patterns

```bash
python -m albumexplore.cli.export_tags --min-count 100
```

### 4. Bulk Analysis Workflow
```bash
# 1. Export singles for improvement candidates
python -m albumexplore.cli.export_tags --max-count 1

# 2. Export rare tags (2-5 occurrences)
python -m albumexplore.cli.export_tags --min-count 2 --max-count 5

# 3. Export common tags for verification
python -m albumexplore.cli.export_tags --min-count 50

# 4. Compare normalized forms across different ranges
```

## Output Files

### Raw Tags Export
Contains original tag names with their normalized forms:
- `Tag`: Original tag as it appears in database
- `Count`: Number of albums with this tag
- `Normalized Form`: Result of enhanced normalization
- `Filter State`: Current filter state (0 = neutral)

### Atomic Tags Export
Contains consolidated atomic tags after decomposition:
- `Tag`: Atomic tag component
- `Count`: Total occurrences across all albums
- `Matching Count`: How many original tags exactly match this form
- `Is Single`: Whether this tag appears only once
- `Filter State`: Current filter state (0 = neutral)

## Example Analysis: Finding Singles for Improvement

### Step 1: Export Singles
```bash
python -m albumexplore.cli.export_tags --max-count 1
# Output: 1604 single-instance tags
```

### Step 2: Review for Patterns
Look for:
- **Misspellings**: `american privitsm` → `american primitivism` ✓
- **Case variants**: Tags that differ only in capitalization
- **Hyphen variants**: `afro-funk` vs `afro funk`
- **Multi-tags**: Tags that should be split (e.g., `acoustic doom metal`)
- **Locations**: City/country names that aren't genres
- **Overly specific**: Tags too narrow to be useful

### Step 3: Add to Normalization Rules
Update `tag_rules.json` with new patterns:
```json
{
  "misspellings": {
    "american primitivism": ["american privitsm"]
  },
  "hyphen_compounds": [
    "afro-funk",
    "afro-rock"
  ]
}
```

### Step 4: Re-export and Verify
```bash
python -m albumexplore.cli.export_tags --max-count 1
# Verify corrections applied
```

## Statistics Example

From a real export of singles:
```
Total tags exported: 1604
Filter applied: count <= 1
Unique normalized tags: 1600
Potential reduction: 4 tags (0.2%)

Example normalizations:
  'american privitsm' → 'american primitivism' ✓ (misspelling corrected)
  'atmosheric black metal' → 'atmospheric black metal' ✓ (misspelling corrected)
  'alt pop' → 'alt-pop' ✓ (hyphen added)
  'afro-funk' → 'afro funk' ✓ (hyphen standardized)
```

## Tips

1. **Start with singles**: Most improvement opportunities are in single-instance tags
2. **Look for patterns**: Group similar tags to find normalization rules
3. **Check atomic decomposition**: Ensure multi-word tags are properly split
4. **Review locations**: Consider whether city/country tags should be separate from genres
5. **Test incrementally**: Add rules gradually and re-export to verify

## Next Steps

After exporting filtered tags:
1. Review the CSV files for patterns
2. Identify normalization improvements
3. Update `tag_rules.json` with new rules
4. Re-run exports to verify changes
5. Update atomic decomposition rules if needed
6. Apply changes to the database when satisfied
