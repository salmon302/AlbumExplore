#!/usr/bin/env python3
"""
Interactive Review Tool for Tag Normalization Suggestions.

This script allows you to interactively review, accept, edit, or reject 
singleton tag normalization suggestions. It bridges the gap between 
automated analysis and rule implementation.

Features:
- Loads suggestions from singleton_suggestions.json
- Checks target tag frequency in the main export CSV
- Updates src/albumexplore/config/tag_rules.json directly
"""

import json
import pandas as pd
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Ensure we can import from src
sys.path.append(os.path.join(os.getcwd(), 'src'))
from albumexplore.tags.config.tag_rules_config import TagRulesConfig

class InteractiveReviewer:
    def __init__(self, suggestions_path: str, csv_path: str, rules_path: str):
        self.suggestions_path = Path(suggestions_path)
        self.csv_path = Path(csv_path)
        self.rules_path = Path(rules_path)
        self.rules_config = TagRulesConfig()
        
        # Load data
        print(f"Loading suggestions from {self.suggestions_path}...")
        with open(self.suggestions_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
            self.suggestions = self.data.get('suggestions', {})
            
        print(f"Loading tag stats from {self.csv_path}...")
        self.df = pd.read_csv(self.csv_path)
        # Create a quick lookup for counts
        self.tag_counts = self.df.set_index('Tag')['Count'].to_dict()
        
    def get_tag_count(self, tag: str) -> int:
        return self.tag_counts.get(tag, 0)
        
    def save_rule(self, original: str, normalized: str):
        """Save a new rule to single_instance_mappings in tag_rules.json."""
        # Reload config to ensure we have latest state
        self.rules_config._load_config()
        
        config = self.rules_config._config
        if 'single_instance_mappings' not in config:
            config['single_instance_mappings'] = {}
            
        config['single_instance_mappings'][original] = normalized
        self.rules_config.save_changes()
        print(f"  [Saved] '{original}' -> '{normalized}'")

    def run(self):
        print(f"\nFound {len(self.suggestions)} suggestions to review.")
        print("Commands: [y]es, [n]o, [e]dit, [s]kip, [q]uit\n")
        
        reviewed_count = 0
        accepted_count = 0
        
        # Sort suggestions by score if available, otherwise by algorithm confidence/reason
        sorted_keys = sorted(self.suggestions.keys(), 
                           key=lambda x: self.suggestions[x].get('score', 0), 
                           reverse=True)
        
        for original in sorted_keys:
            info = self.suggestions[original]
            suggestion = info['suggestion']
            reason = info['reason']
            score = info.get('score', 'N/A')
            
            # Check if rule already exists (maybe added in previous session)
            existing_normalization = self.rules_config.get_normalized_form(original)
            if existing_normalization == suggestion:
                # print(f"Skipping '{original}' - already mapped to '{suggestion}'")
                continue
            
            # Additional check: if mapped to something ELSE, warn or skip?
            # For now, let's just process it.
                
            orig_count = self.get_tag_count(original)
            sugg_count = self.get_tag_count(suggestion)
            
            print("-" * 60)
            print(f"Original:   '{original}' (Count: {orig_count})")
            print(f"Suggestion: '{suggestion}' (Count: {sugg_count})")
            print(f"Reason:     {reason} | Score: {score}")
            
            if sugg_count > 1:
                print(f"  Note: Target tag exists with {sugg_count} albums! (CONFIDENT MATCH)")
            else:
                print(f"  Warning: Target tag is also a singleton (or new).")
                
            while True:
                choice = input("Action [y/n/e/s/q]: ").lower().strip()
                
                if choice == 'y':
                    self.save_rule(original, suggestion)
                    accepted_count += 1
                    reviewed_count += 1
                    break
                elif choice == 'n':
                    print("  [Rejected]")
                    reviewed_count += 1
                    break
                elif choice == 'e':
                    new_sugg = input(f"Enter custom mapping for '{original}': ").strip()
                    if new_sugg:
                        self.save_rule(original, new_sugg)
                        accepted_count += 1
                        reviewed_count += 1
                    break
                elif choice == 's':
                    print("  [Skipped]")
                    break
                elif choice == 'q':
                    print("\nQuitting...")
                    print(f"Session Summary: Reviewed {reviewed_count}, Accepted {accepted_count}")
                    return
                else:
                    print("Invalid command.")
        
        print("\nReview Complete!")
        print(f"Session Summary: Reviewed {reviewed_count}, Accepted {accepted_count}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Interactive Tag Reviewer')
    parser.add_argument('--suggestions', '-s', default='data/exports/singleton_suggestions.json', help='Path to suggestions JSON')
    parser.add_argument('--csv', '-c', default='data/exports/atomic_tags_export2.csv', help='Path to tags export CSV')
    parser.add_argument('--rules', '-r', default='src/albumexplore/config/tag_rules.json', help='Path to tag_rules.json')
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.suggestions):
        print(f"Error: {args.suggestions} not found. Run analysis first.")
        sys.exit(1)
        
    reviewer = InteractiveReviewer(args.suggestions, args.csv, args.rules)
    reviewer.run()
