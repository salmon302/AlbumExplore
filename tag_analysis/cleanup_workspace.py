#!/usr/bin/env python3
"""
Cleanup obsolete scripts and documentation after Phase 5 strategic optimization
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def cleanup_obsolete_files():
    """Remove obsolete files and organize the workspace."""
    
    print("=== AlbumExplore Workspace Cleanup ===")
    print("Removing obsolete scripts and documentation files...")
    
    # Files to remove from main directory
    main_dir_obsolete = [
        'advanced_tag_analysis.py',
        'analyze_and_expand_rules.py', 
        'check_double_rules.py',
        'double_tag_analyzer.py',
        'final_impact_summary.py',
        'fragment_cleanup.py',
        'high_impact_rules.py',
        'low_frequency_analyzer.py',
        'normalization_summary.py',
        'rule_application_report.md',
        'singleton_analyzer.py'
    ]
    
    # Files to remove from tag_analysis directory
    tag_analysis_obsolete = [
        # Phase 1 files
        'analyze_current_tags.py',
        'analyze_singletons.py',
        'apply_improvements.py',
        'generate_decomposition_rules.py',
        'current_tag_analysis.md',
        'decomposition_workflow.py',
        'optimization_opportunities.md',
        'rule_generation_report.md',
        'singleton_analysis.md',
        'singleton_analysis_report.md',
        'TAG_OPTIMIZATION_COMPLETE.md',
        'TAG_OPTIMIZATION_SUMMARY.md',
        
        # Phase 2 files
        'find_additional_opportunities.py',
        'apply_additional_optimizations.py',
        'phase2_analysis.py',
        'apply_phase2_optimizations.py',
        'PHASE2_OPTIMIZATION_COMPLETE.md',
        'phase2_optimization_report.md',
        'post_optimization_analysis.md',
        
        # Phase 3 files
        'phase3_singleton_analysis.py',
        'apply_phase3_cleanup.py',
        'validate_phase3.py',
        'phase3_singleton_focus_report.md',
        
        # Phase 4 files
        'phase4_aggressive_analysis.py',
        'apply_phase4_cleanup.py',
        'phase4_aggressive_plan.md',
        
        # Early Phase 5 files (superseded by strategic approach)
        'phase5_deep_analysis.py',
        'phase5_deep_analysis_plan.md',
        'phase5_ultra_aggressive_analysis.py',
        'phase5_ultra_aggressive_plan.md',
        
        # Intermediate files and reports
        'advanced_pattern_analysis.py',
        'apply_decomposition_rules.py',
        'monitor_decomposition_impact.py',
        'double_tag_analysis.md',
        'low_frequency_analysis.md',
        'rule_application_report.md',
        
        # JSON rule files (now consolidated into main config)
        'double_tag_rules.json',
        'double_tag_rules_cleaned.json',
        'low_frequency_rules.json',
        'new_decomposition_rules.json',
        'singleton_rules.json'
    ]
    
    # Files to keep in tag_analysis
    keep_files = [
        'apply_phase5_strategic.py',  # Final optimization script
        'README.md',                  # Documentation
        'QUICK_START.md',            # User guide
        'COMPLETE_PROGRESS_REPORT.md' # Final report
    ]
    
    # Keep backup files (important for rollback)
    backup_pattern = 'tag_rules_backup_'
    
    removed_count = 0
    
    # Clean main directory
    print("\n--- Cleaning main directory ---")
    for filename in main_dir_obsolete:
        filepath = Path(f'../{filename}')
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"✓ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {filename}: {e}")
        else:
            print(f"- Already gone: {filename}")
    
    # Clean tag_analysis directory
    print("\n--- Cleaning tag_analysis directory ---")
    tag_analysis_dir = Path('.')
    
    for filename in tag_analysis_obsolete:
        filepath = tag_analysis_dir / filename
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"✓ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {filename}: {e}")
        else:
            print(f"- Already gone: {filename}")
    
    # List remaining files
    print("\n--- Files retained in tag_analysis ---")
    remaining_files = []
    for item in sorted(tag_analysis_dir.iterdir()):
        if item.is_file():
            remaining_files.append(item.name)
    
    for filename in remaining_files:
        if filename in keep_files:
            print(f"✓ Kept (essential): {filename}")
        elif filename.startswith(backup_pattern):
            print(f"✓ Kept (backup): {filename}")
        else:
            print(f"? Kept (review): {filename}")
    
    print(f"\n=== Cleanup Summary ===")
    print(f"Files removed: {removed_count}")
    print(f"Files retained: {len(remaining_files)}")
    print(f"Backup files preserved: {len([f for f in remaining_files if f.startswith(backup_pattern)])}")
    
    # Update README to reflect current state
    update_readme()
    
    print("\n✅ Workspace cleanup complete!")
    print("🔄 Ready for continued optimization work")
    
    return removed_count

def update_readme():
    """Update README to reflect post-cleanup state."""
    
    readme_content = """# Tag Analysis Scripts

This directory contains the final tag optimization tools for AlbumExplore.

## Current Status (Post-Phase 5)
- **Target achieved**: Reduced from 1,010 to ~597 unique tags (40.9% reduction)
- **Final approach**: Strategic ultra-aggressive optimization with high-confidence rules
- **All changes**: Backed up and reversible via tag_rules_backup_* files

## Essential Files

### Active Scripts
- `apply_phase5_strategic.py` - Final strategic optimization implementation

### Documentation  
- `COMPLETE_PROGRESS_REPORT.md` - Comprehensive progress summary
- `QUICK_START.md` - Quick reference for tag optimization
- `README.md` - This file

### Backups
- `tag_rules_backup_phase3_*.json` - Phase 3 backup
- `tag_rules_backup_phase4_*.json` - Phase 4 backup  
- `tag_rules_backup_phase5_*.json` - Phase 5 backup (current state)

## Next Steps
1. Export and validate new tag counts
2. Test music discovery functionality  
3. Apply additional optimizations if needed
4. Monitor tag usage in production

## Rollback Instructions
To rollback to any previous phase:
```bash
cp tag_rules_backup_[phase]_[timestamp].json ../src/albumexplore/config/tag_rules.json
```

## Historical Context
This workspace has been cleaned of obsolete scripts from Phases 1-4 and early Phase 5 analysis.
All critical functionality is preserved in the final strategic optimization script.
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✓ Updated README.md")

if __name__ == '__main__':
    cleanup_obsolete_files()
