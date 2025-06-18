#!/usr/bin/env python3
"""
Test script for the Enhanced Tag Consolidation System
Demonstrates improvements in tag organization and consolidation.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tags.analysis.tag_analyzer import TagAnalyzer
from tags.analysis.enhanced_tag_consolidator import EnhancedTagConsolidator
from tags.normalizer.tag_normalizer import TagNormalizer

def create_sample_data():
    """Create sample album data with diverse tags for testing."""
    sample_albums = [
        {
            'artist': 'Band A',
            'album': 'Album 1',
            'year': 2020,
            'tags': ['black metal', 'atmospheric', 'Norway', 'cold', 'dark']
        },
        {
            'artist': 'Band B', 
            'album': 'Album 2',
            'year': 2019,
            'tags': ['blackmetal', 'epic blackmetal', 'Stockholm', 'Sweden', 'melodic']
        },
        {
            'artist': 'Band C',
            'album': 'Album 3', 
            'year': 2021,
            'tags': ['death metal', 'technical', 'brutal', 'Florida', 'USA']
        },
        {
            'artist': 'Band D',
            'album': 'Album 4',
            'year': 2018,
            'tags': ['deathmetal', 'melodic-deathmetal', 'Gothenburg', 'Sweden', 'harmonic']
        },
        {
            'artist': 'Band E',
            'album': 'Album 5',
            'year': 2022,
            'tags': ['progressive metal', 'progmetal', 'complex', 'London', 'UK']
        },
        {
            'artist': 'Band F',
            'album': 'Album 6',
            'year': 2020,
            'tags': ['prog-metal', 'atmospheric', 'conceptual', 'Berlin', 'Germany']
        },
        {
            'artist': 'Band G',
            'album': 'Album 7',
            'year': 2019,
            'tags': ['post-rock', 'postrock', 'instrumental', 'cinematic', 'Montreal']
        },
        {
            'artist': 'Band H',
            'album': 'Album 8',
            'year': 2021,
            'tags': ['post rock', 'ambient', 'drone', 'Tokyo', 'Japan']
        },
        {
            'artist': 'Band I',
            'album': 'Album 9',
            'year': 2020,
            'tags': ['folk metal', 'folkmetal', 'viking', 'celtic', 'traditional']
        },
        {
            'artist': 'Band J',
            'album': 'Album 10',
            'year': 2022,
            'tags': ['celtic-metal', 'medieval', 'acoustic', 'Dublin', 'Ireland']
        },
        {
            'artist': 'Band K',
            'album': 'Album 11',
            'year': 2018,
            'tags': ['doom metal', 'doommetal', 'slow', 'heavy', 'Birmingham']
        },
        {
            'artist': 'Band L',
            'album': 'Album 12',
            'year': 2021,
            'tags': ['sludge metal', 'sludgemetal', 'dirty', 'raw', 'New Orleans']
        },
        {
            'artist': 'Band M',
            'album': 'Album 13',
            'year': 2019,
            'tags': ['psychedelic rock', 'psych rock', 'experimental', 'San Francisco']
        },
        {
            'artist': 'Band N',
            'album': 'Album 14',
            'year': 2020,
            'tags': ['pscyhedelic rock', 'space rock', 'cosmic', 'California', 'USA']
        },
        {
            'artist': 'Band O',
            'album': 'Album 15',
            'year': 2022,
            'tags': ['indie rock', 'indierock', 'lo-fi', 'garage', 'Portland']
        },
        {
            'artist': 'Band P',
            'album': 'Album 16',
            'year': 2021,
            'tags': ['alternative rock', 'alt rock', 'grunge', 'Seattle', 'Washington']
        },
        {
            'artist': 'Band Q',
            'album': 'Album 17',
            'year': 2018,
            'tags': ['metalcore', 'metal-core', 'harsh vocals', 'Manchester', 'UK']
        },
        {
            'artist': 'Band R',
            'album': 'Album 18',
            'year': 2020,
            'tags': ['deathcore', 'death-core', 'breakdown', 'Phoenix', 'Arizona']
        },
        {
            'artist': 'Band S',
            'album': 'Album 19',
            'year': 2019,
            'tags': ['jazz fusion', 'jazzfusion', 'experimental jazz', 'New York']
        },
        {
            'artist': 'Band T',
            'album': 'Album 20',
            'year': 2021,
            'tags': ['avant-garde jazz', 'free jazz', 'improvised', 'Chicago']
        }
    ]
    
    return pd.DataFrame(sample_albums)

def analyze_before_consolidation(analyzer):
    """Analyze tags before consolidation."""
    print("=== BEFORE CONSOLIDATION ===")
    print(f"Total unique tags: {len(analyzer.tag_frequencies)}")
    print(f"Total tag instances: {sum(analyzer.tag_frequencies.values())}")
    
    print("\n--- All Tags by Frequency ---")
    for tag, count in analyzer.tag_frequencies.most_common():
        print(f"  {tag}: {count}")
    
    print("\n--- Obvious Duplicates ---")
    duplicates = []
    tag_list = list(analyzer.tag_frequencies.keys())
    for i, tag1 in enumerate(tag_list):
        for tag2 in tag_list[i+1:]:
            # Simple duplicate detection
            if (tag1.replace('-', '').replace(' ', '') == tag2.replace('-', '').replace(' ', '') or
                tag1.lower() == tag2.lower() or
                abs(len(tag1) - len(tag2)) <= 2 and 
                any(word in tag1.lower() for word in tag2.lower().split())):
                duplicates.append((tag1, tag2, analyzer.tag_frequencies[tag1], analyzer.tag_frequencies[tag2]))
    
    for tag1, tag2, count1, count2 in duplicates:
        print(f"  '{tag1}' ({count1}) ↔ '{tag2}' ({count2})")

def main():
    """Main function to demonstrate enhanced tag consolidation."""
    print("Enhanced Tag Consolidation System Test")
    print("=" * 50)
    
    # Create sample data
    df = create_sample_data()
    print(f"Created sample dataset with {len(df)} albums")
    
    # Initialize analyzer
    analyzer = TagAnalyzer(df)
    
    # Show before consolidation
    analyze_before_consolidation(analyzer)
    
    # Initialize enhanced consolidator
    print(f"\n{'='*50}")
    print("INITIALIZING ENHANCED CONSOLIDATION SYSTEM")
    print("=" * 50)
    
    consolidator = EnhancedTagConsolidator(analyzer)
    
    # Generate and display consolidation report
    print("\n" + "="*50)
    print("ENHANCED CONSOLIDATION ANALYSIS")
    print("=" * 50)
    
    report = consolidator.generate_consolidation_report()
    print(report)
    
    # Show detailed categorization
    print(f"\n{'='*50}")
    print("DETAILED CATEGORIZATION RESULTS")
    print("=" * 50)
    
    categorized = consolidator.categorize_and_consolidate()
    for category, tags in categorized.items():
        if tags:  # Only show categories with tags
            print(f"\n--- {category.value.upper()} ({len(tags)} tags) ---")
            sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
            for tag, count in sorted_tags:
                print(f"  {tag}: {count}")
    
    # Show hierarchy relationships
    print(f"\n{'='*50}")
    print("HIERARCHICAL RELATIONSHIPS")
    print("=" * 50)
    
    hierarchies = consolidator.build_enhanced_hierarchies()
    for parent, relations in hierarchies.items():
        if relations:
            print(f"\n{parent}:")
            for rel in sorted(relations, key=lambda x: x.strength, reverse=True):
                print(f"  → {rel.child} (strength: {rel.strength:.2f})")
    
    # Show consolidation suggestions
    print(f"\n{'='*50}")
    print("CONSOLIDATION SUGGESTIONS")
    print("=" * 50)
    
    suggestions = consolidator.suggest_consolidations()
    if suggestions:
        print("Top consolidation suggestions:")
        for i, suggestion in enumerate(suggestions[:10], 1):
            print(f"{i:2d}. {suggestion['primary_tag']} ← {suggestion['secondary_tag']}")
            print(f"     Confidence: {suggestion['confidence']:.2f}, Category: {suggestion['category']}")
            print(f"     Frequencies: {suggestion['primary_freq']} ← {suggestion['secondary_freq']}")
            print()
    else:
        print("No consolidation suggestions found with current thresholds.")
    
    # Summary statistics
    print(f"\n{'='*50}")
    print("CONSOLIDATION IMPACT SUMMARY")
    print("=" * 50)
    
    total_original = len(analyzer.tag_frequencies)
    total_after = sum(len(tags) for tags in categorized.values())
    locations_filtered = len([tag for tag, count in analyzer.tag_frequencies.items() 
                             if any(rule.filter_out and 
                                  __import__('re').search(rule.pattern, tag, __import__('re').IGNORECASE)
                                  for rule in consolidator.consolidation_rules)])
    
    print(f"Original tags: {total_original}")
    print(f"After consolidation: {total_after}")
    print(f"Location tags filtered: {locations_filtered}")
    print(f"Net reduction: {total_original - total_after} tags ({((total_original - total_after) / total_original * 100):.1f}%)")
    
    print(f"\nConsolidation suggestions: {len(suggestions)}")
    print(f"Hierarchical relationships: {sum(len(relations) for relations in hierarchies.values())}")
    
    print(f"\n{'='*50}")
    print("RECOMMENDATIONS")
    print("=" * 50)
    
    print("1. Apply location tag filtering to remove geographic tags")
    print("2. Implement the top consolidation suggestions")
    print("3. Use hierarchical relationships for nested tag displays")
    print("4. Add category-based tag grouping in the UI")
    print("5. Implement similarity-based tag merging with user approval")

if __name__ == "__main__":
    main() 