#!/usr/bin/env python3
"""
Master Dev Loop Script for Tag Normalization.

Orchestrates the full cycle:
1. Analyze Singletons (Generate Suggestions)
2. Score Suggestions (Add Confidence Metrics)
3. Interactive Review (Human Choice)
4. Validation (Check Results)
"""

import subprocess
import sys
import os
from pathlib import Path

def run_step(description, command):
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    
    # Calculate source directory
    # scripts/tag_analysis/../../src -> src
    # Assuming this script is at scripts/run_tag_loop.py
    # But it is executed from root (cwd).
    
    # Let's trust cwd is project root based on usage
    cwd = Path(os.getcwd())
    src_dir = cwd / 'src'
    
    # Prepare environment
    env = os.environ.copy()
    current_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(src_dir) + os.pathsep + current_pythonpath
    
    try:
        subprocess.check_call([sys.executable] + command, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error executing step '{description}': {e}")
        if input("Continue anyway? [y/n]: ").lower() != 'y':
            sys.exit(1)

def main():
    base_dir = Path(os.getcwd())
    scripts_dir = base_dir / 'scripts' / 'tag_analysis'
    data_dir = base_dir / 'data' / 'exports'

    # Ensure paths exist
    csv_path = data_dir / 'atomic_tags_export2.csv'
    suggestions_json = data_dir / 'singleton_suggestions.json'
    
    if not csv_path.exists():
        print(f"Error: Input CSV not found at {csv_path}")
        sys.exit(1)

    # 1. Analyze
    run_step("Analyze Singletons (Rule-Based + Fuzzy)", [
        str(scripts_dir / 'auto_singleton_mapper.py'),
        str(csv_path),
        str(suggestions_json)
    ])

    # 1.5 Analyze Co-occurrence
    run_step("Analyze Co-occurrence (DB)", [
        str(scripts_dir / 'check_cooccurrence.py')
    ])
    
    # 1.6 Merge Suggestions
    run_step("Merge Suggestions", [
        str(scripts_dir / 'merge_suggestions.py')
    ])
    
    # Use merged file for downstream
    merged_json = data_dir / 'merged_suggestions.json'

    # 2. Score
    run_step("Score Suggestions", [
        str(scripts_dir / 'score_suggestions.py'),
        str(merged_json)
    ])

    # 3. Generate Application Script
    scored_json = data_dir / 'merged_suggestions_scored.json'
    # If scored json doesn't exist (e.g. scoring failed or disabled), fallback to merged
    target_json = scored_json if scored_json.exists() else merged_json
    
    adhoc_dir = base_dir / 'scripts' / 'adhoc'
    
    run_step("Generate Application Script", [
        str(scripts_dir / 'generate_application_script.py'),
        '--suggestions', str(target_json),
        '--output-dir', str(adhoc_dir)
    ])

    # 4. Validation
    validation_json = data_dir / 'normalization_validation.json'
    run_step("Validate Normalization", [
        str(scripts_dir / 'validate_normalization.py'),
        str(csv_path),
        str(validation_json)
    ])

    print("\nLoop Complete!")

if __name__ == "__main__":
    main()
