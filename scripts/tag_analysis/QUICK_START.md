# Quick Start Guide

## Running the Complete Workflow

The simplest way to expand decomposition rules:

```cmd
cd tag_analysis
python decomposition_workflow.py --auto-apply --min-count 5
```

## Step-by-Step Process

### 1. Analyze Current Tags
```cmd
python analyze_current_tags.py --min-count 10
```
This generates `tag_analysis_report_[timestamp].md` with decomposition candidates.

### 2. Generate New Rules
```cmd
python generate_decomposition_rules.py --min-count 10 --min-confidence 0.6
```
This creates `generated_decomposition_rules.json` with new rules.

### 3. Validate Rules (Dry Run)
```cmd
python apply_decomposition_rules.py --dry-run
```
This shows what would be applied without making changes.

### 4. Apply Rules
```cmd
python apply_decomposition_rules.py
```
This updates the `tag_rules.json` configuration.

### 5. Monitor Impact
After re-exporting tags, compare the results:
```cmd
python monitor_decomposition_impact.py --before-file old_export.csv --after-file new_export.csv
```

## Configuration Options

- `--min-count N`: Only consider tags with at least N instances
- `--min-confidence X`: Only generate rules with confidence ≥ X (0.0-1.0)
- `--dry-run`: Test without making changes
- `--auto-apply`: Automatically apply generated rules

## File Outputs

All scripts generate timestamped files to avoid conflicts:
- `tag_analysis_report_YYYYMMDD_HHMMSS.md`
- `generated_rules_YYYYMMDD_HHMMSS.json`
- `rule_application_report_YYYYMMDD_HHMMSS.md`
- `impact_analysis_YYYYMMDD_HHMMSS.md`
