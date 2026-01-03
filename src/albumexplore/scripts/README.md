# Ad-hoc Analysis and Maintenance Scripts

This directory contains various scripts used for:
- Analyzing data quality and tag distributions (`analyze_*.py`)
- Checking database state and integrity (`check_*.py`)
- Debugging specific issues (`debug_*.py`)
- Validating configurations and optimizations (`validate_*.py`)
- Performing one-off data operations like backfills or exports (`backfill_*.py`, `export_*.py`)
- Quick testing of specific features (`simple_*.py`, `quick_*.py`)

## Usage

These scripts are designed to be run as modules from the project root to ensure imports work correctly.

Example:
```bash
python -m albumexplore.scripts.analyze_tag_relationships
```

## Note

These scripts are often created for specific tasks and may not be maintained as part of the core application. Use them with understanding of their original purpose.
