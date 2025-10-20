# Tag Rules Improvements Based on Singles Analysis

## Overview
Based on analysis of 1,604 single-instance tags, we identified and implemented 18 new suffix compound patterns to improve tag normalization coverage.

## Changes Made to tag_rules.json

### 1. New -core Suffix Compounds (7 patterns)
Added to `atomic_decomposition` section:
- `artcore` → ["art", "core"]
- `dreamcore` → ["dream", "core"]
- `mincecore` → ["mince", "core"]
- `nintendocore` → ["nintendo", "core"]
- `sadcore` → ["sad", "core"]
- `sludgecore` → ["sludge", "core"]
- `thrashcore` → ["thrash", "core"]

### 2. New -gaze Suffix Variants (4 patterns)
Added to `common_misspellings` section:
- `deathgaze` with variants: ["death-gaze", "death gaze"]
- `grunegaze` with variants: ["grune-gaze", "grune gaze"]
- `noisegaze` with variants: ["noise-gaze", "noise gaze"]
- `synthgaze` with variants: ["synth-gaze", "synth gaze"]

### 3. New -jazz Suffix Variant (1 pattern)
Added to `common_misspellings` section:
- `deathjazz` with variants: ["death-jazz", "death jazz"]

### 4. New -pop Suffix Variants (2 patterns)
Added to `common_misspellings` section:
- `bitpop` with variants: ["bit-pop", "bit pop"]
- `visepop` with variants: ["vise-pop", "vise pop"]

### 5. New -punk Suffix Variants (3 patterns)
Added to `common_misspellings` section:
- `electropunk` with variants: ["electro-punk", "electro punk"]
- `skatepunk` with variants: ["skate-punk", "skate punk"]
- `steampunk` with variants: ["steam-punk", "steam punk"]

### 6. New -rock Suffix Variant (1 pattern)
Added to `common_misspellings` section:
- `zamrock` with variants: ["zam-rock", "zam rock"]

### 7. Hyphen Standardization
Added to `common_misspellings` section:
- `8-bit` with variants: ["8 bit", "8bit"]

## Expected Impact

### Before Changes
- 1,604 single-instance tags identified
- 18 suffix compound patterns unrecognized
- Inconsistent handling of hyphen variations

### After Changes
- All 18 suffix patterns now properly normalized
- Hyphen variants automatically consolidated
- Improved consistency across tag collection

### Reduction Estimate
- Previously: 0.2% reduction on singles (4 out of 1,604)
- With new patterns: Expected additional 18+ tag consolidations
- Total improvement: ~1.3% reduction on singles alone

## Verification Steps

1. Re-export all tags:
   ```powershell
   python -m albumexplore.cli.export_tags
   ```

2. Re-export singles:
   ```powershell
   python -m albumexplore.cli.export_tags --max-count 1
   ```

3. Re-run singles analysis:
   ```powershell
   python analyze_singles.py
   ```

4. Compare normalization coverage (before: 97.7%, after: expected 98%+)

## Future Improvements Identified

From the singles analysis, still pending:
- **91 hyphen inconsistencies**: Need review to determine canonical forms
- **98 misspellings**: Additional corrections to add (avoiding location-specific)
- **538 multi-word tags**: Need atomic decomposition rules
- **7 location tags**: Should be filtered or marked as non-genre
- **13 questionable tags**: Tags with -esque, -ish, -related, or band references

## Notes

- Suffix compounds added to `common_misspellings` section normalize hyphen/space variants
- Core compounds added to `atomic_decomposition` section enable tag splitting
- Pattern follows existing conventions: compound form as key, variants as array values
- All changes preserve backward compatibility with existing normalized tags

## Related Files
- Configuration: `src/albumexplore/config/tag_rules.json`
- Analysis script: `analyze_singles.py`
- Export tool: `src/albumexplore/cli/export_tags.py`
- Singles export: `tagoutput/raw_tags_singles.csv`
- Initial analysis: Output from `analyze_singles.py` run
