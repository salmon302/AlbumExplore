# Tag Management System

This document describes the enhanced tag management system implemented for AlbumExplore, which provides comprehensive tag normalization, validation, consolidation, and hierarchy management.

## Overview

The tag management system consists of three main components:

1. **Tag Migration & Consolidation** - One-time migration to consolidate existing duplicate tags
2. **Tag Validation** - Validation system to catch edge cases during import
3. **Tag Hierarchy** - Support for genre relationships and hierarchical organization

## Features

### 1. Enhanced Tag Normalization

The system now uses an advanced normalization pipeline that:

- **Standardizes formatting**: Converts case, fixes spacing, standardizes hyphenation
- **Expands abbreviations**: `prog` → `progressive`, `alt` → `alternative`
- **Consolidates variants**: `Alt-metal`, `Alt Metal`, `Alternative Metal` → `alternative metal`
- **Handles compound terms**: Properly formats compound genres like `post-metal`, `avant-garde`
- **Fixes misspellings**: Corrects common typos and spelling variations

### 2. Tag Validation

Comprehensive validation system that catches:

- **Invalid patterns**: Empty tags, special characters only, profanity
- **Format strings**: `LP`, `EP`, `CD` (warns these aren't genres)
- **Date patterns**: `2023`, `Jan 1` (warns these aren't genres)
- **Non-genre terms**: `music`, `album`, `good` (warns about relevance)
- **Encoding issues**: Special characters, multiple spaces, formatting problems
- **Length constraints**: Too short/long tags

### 3. Tag Hierarchy

Hierarchical organization supporting:

- **Genre hierarchies**: `metal` → `black metal` → `atmospheric black metal`
- **Parent-child relationships**: Automatic hierarchy creation and management
- **Circular dependency prevention**: Prevents invalid hierarchy loops
- **Related tag discovery**: Find siblings, cousins, ancestors, descendants

## Usage

### Command Line Interface

Use the comprehensive management script:

```bash
# Show help
python scripts/manage_tags.py --help

# Run migration (dry-run first to see what would happen)
python scripts/manage_tags.py migrate --dry-run
python scripts/manage_tags.py migrate

# Initialize tag hierarchies
python scripts/manage_tags.py init-hierarchies

# Validate all existing tags
python scripts/manage_tags.py validate-all

# Show statistics
python scripts/manage_tags.py stats

# Run everything
python scripts/manage_tags.py all --dry-run
python scripts/manage_tags.py all
```

### Programmatic Usage

```python
from albumexplore.database.tag_migration import run_tag_migration
from albumexplore.database.tag_hierarchy import initialize_tag_hierarchies
from albumexplore.database.tag_validator import TagValidator, TagValidationFilter
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer

# Run migration
stats = run_tag_migration(dry_run=False)

# Initialize hierarchies
initialize_tag_hierarchies(overwrite_existing=False)

# Use validation
validator = TagValidator()
results = validator.validate_tag("Progressive Metal")

# Use normalization
normalizer = TagNormalizer()
normalized = normalizer.normalize("Prog Metal")  # → "progressive metal"
```

## Migration Process

### What the Migration Does

1. **Analyzes current state**: Identifies duplicate tags and potential issues
2. **Updates normalized names**: Ensures all tags have proper normalized forms
3. **Consolidates duplicates**: Merges tags with identical normalized names
4. **Creates variants**: Preserves original tag names as variants of canonical forms
5. **Updates frequencies**: Recalculates album counts for all tags
6. **Logs changes**: Records all changes in update history

### Before Migration

```
Tags in database:
- "Progressive Metal" (15 albums)
- "prog metal" (8 albums)  
- "Prog-Metal" (3 albums)
- "progressive-metal" (1 album)
```

### After Migration

```
Tags in database:
- "progressive metal" (27 albums) [canonical]

Tag variants:
- "Progressive Metal" → "progressive metal"
- "prog metal" → "progressive metal"
- "Prog-Metal" → "progressive metal"
- "progressive-metal" → "progressive metal"
```

## Validation Examples

### Valid Tags
```
✅ "progressive metal"
✅ "atmospheric black metal"
✅ "post-rock"
```

### Warning Tags
```
⚠️ "LP" - appears to be format descriptor
⚠️ "2023" - appears to be date
⚠️ "music" - too general, not specific genre
```

### Error Tags
```
❌ "" - empty tag
❌ "---" - invalid pattern
❌ "123" - only numbers
```

## Hierarchy Structure

Example hierarchies created:

```
metal
├── black metal
│   ├── atmospheric black metal
│   ├── depressive black metal
│   └── folk black metal
├── death metal
│   ├── technical death metal
│   ├── melodic death metal
│   └── brutal death metal
└── doom metal
    ├── funeral doom metal
    ├── sludge metal
    └── drone metal

rock
├── progressive rock
│   ├── art rock
│   └── symphonic rock
├── alternative rock
│   ├── grunge
│   ├── britpop
│   └── indie rock
└── punk rock
    ├── hardcore punk
    ├── pop punk
    └── post-punk
```

## Configuration

### Validation Settings

```python
# TagValidator configuration
MAX_TAG_LENGTH = 100
MIN_TAG_LENGTH = 1
MAX_TAGS_PER_ALBUM = 20

# ValidationFilter modes
strict_mode = False  # Allow warnings, block only errors
strict_mode = True   # Block both warnings and errors
```

### Normalization Rules

The system includes extensive rules for:

- **Compound terms**: `post metal` → `post-metal`
- **Misspellings**: `pyschedelic` → `psychedelic`
- **Abbreviations**: `prog` → `progressive`
- **Hyphenation**: Standardizes compound genre formatting

## Integration with Import

The enhanced system is automatically used during data import:

1. **Tags are validated** before processing
2. **Invalid tags are rejected** or fixed based on severity
3. **Valid tags are normalized** using advanced rules
4. **Duplicates are prevented** during the import process
5. **Consolidation runs** after import to clean up any remaining duplicates

## Performance Considerations

- **Caching**: Normalization results are cached for performance
- **Batch processing**: Migration processes tags in batches
- **Dry-run mode**: Always test migrations before applying changes
- **Logging**: Comprehensive logging for monitoring and debugging

## Maintenance

### Regular Tasks

1. **Run validation** periodically to check for new issues
2. **Update hierarchies** as new genres emerge
3. **Review rejected tags** to improve validation rules
4. **Monitor statistics** to identify trending tags

### Monitoring

```bash
# Check current status
python scripts/manage_tags.py stats

# Validate recent imports
python scripts/manage_tags.py validate-all

# Review hierarchy completeness
python scripts/manage_tags.py init-hierarchies --dry-run
```

## Troubleshooting

### Common Issues

1. **Migration fails**: Check database constraints, run in dry-run mode first
2. **Validation too strict**: Adjust strict_mode setting
3. **Missing hierarchies**: Re-run hierarchy initialization
4. **Performance slow**: Check for large tag datasets, consider batch processing

### Recovery

```bash
# Reset and re-run
python scripts/manage_tags.py migrate --dry-run  # Check what would happen
python scripts/manage_tags.py all              # Full reset and rebuild
```

## Examples

See `examples/tag_management_example.py` for comprehensive usage examples demonstrating all features. 