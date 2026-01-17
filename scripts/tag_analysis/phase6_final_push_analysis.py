#!/usr/bin/env python3
"""
Phase 6 Final Push Analysis - Get to <600 tags with ultra-aggressive optimization
Current: 675 tags, Target: <600 tags, Gap: 75+ tags to eliminate
"""

import pandas as pd
import json
from pathlib import Path
from collections import Counter
import re

def analyze_phase6_opportunities():
    """Analyze current 675 tags for final push to <600."""
    
    print("=== Phase 6 Final Push Analysis ===")
    print("Current: 675 tags | Target: <600 tags | Gap: 75+ tags")
    
    # Load current CSV
    df = pd.read_csv('../atomic_tags_export2.csv')
    
    # Focus on tags with low-medium frequency (1-5 count)
    low_freq = df[df['Count'] <= 5].copy()
    medium_freq = df[(df['Count'] >= 6) & (df['Count'] <= 15)].copy()
    high_freq = df[df['Count'] > 15].copy()
    
    print(f"\nFrequency Distribution:")
    print(f"- Singletons (Count=1): {len(df[df['Count'] == 1])}")
    print(f"- Low frequency (Count=2-5): {len(df[(df['Count'] >= 2) & (df['Count'] <= 5)])}")
    print(f"- Medium frequency (Count=6-15): {len(medium_freq)}")
    print(f"- High frequency (Count>15): {len(high_freq)}")
    
    # Identify ultra-aggressive deletion candidates
    print("\n=== ULTRA-AGGRESSIVE DELETION CANDIDATES ===")
    
    # 1. All remaining singletons (except essential music genres)
    singletons = df[df['Count'] == 1]['Tag'].tolist()
    essential_genres = {
        'acoustic', 'ambient', 'blues', 'classical', 'country', 'electronic', 
        'folk', 'funk', 'jazz', 'metal', 'pop', 'punk', 'rock', 'soul'
    }
    
    singleton_deletions = [tag for tag in singletons if tag.lower() not in essential_genres]
    
    print(f"\n1. Singleton Deletions ({len(singleton_deletions)} candidates):")
    print("High-confidence singleton deletions:")
    for tag in sorted(singleton_deletions)[:20]:  # Show first 20
        print(f"   - {tag}")
    if len(singleton_deletions) > 20:
        print(f"   ... and {len(singleton_deletions) - 20} more")
    
    # 2. Low-frequency technical artifacts and over-specific terms
    low_freq_deletions = []
    technical_patterns = [
        r'.*-ish$', r'.*-like$', r'.*-y$', r'.*-esque$',  # Stylistic suffixes
        r'.*core$', r'.*gaze$', r'.*wave$', r'.*step$',   # Genre suffixes that fragment
        r'.*\d+.*', r'.*bit.*', r'.*fi.*',                # Technical terms
        r'.*(house|trance|techno).*', r'.*(beat|hop|rap).*'  # Electronic sub-genres
    ]
    
    for _, row in low_freq.iterrows():
        tag = row['Tag']
        count = row['Count']
        if count <= 3:
            # Check if it matches technical patterns
            if any(re.match(pattern, tag, re.IGNORECASE) for pattern in technical_patterns):
                low_freq_deletions.append(tag)
            # Or if it's overly specific
            elif len(tag.split()) > 2 or '/' in tag or '-' in tag:
                low_freq_deletions.append(tag)
    
    print(f"\n2. Low-Frequency Pattern Deletions ({len(low_freq_deletions)} candidates):")
    for tag in sorted(low_freq_deletions)[:15]:
        count = df[df['Tag'] == tag]['Count'].iloc[0]
        print(f"   - {tag} (count: {count})")
    
    # 3. Geographic and cultural over-specificity
    geographic_deletions = []
    geographic_patterns = [
        'african', 'american', 'british', 'french', 'german', 'italian', 'japanese',
        'korean', 'nordic', 'eastern', 'western', 'southern', 'northern',
        'uk', 'us', 'celtic', 'irish', 'scottish', 'welsh', 'gaelic'
    ]
    
    for _, row in df.iterrows():
        tag = row['Tag'].lower()
        if any(geo in tag for geo in geographic_patterns) and row['Count'] <= 5:
            geographic_deletions.append(row['Tag'])
    
    print(f"\n3. Geographic Over-Specificity ({len(geographic_deletions)} candidates):")
    for tag in sorted(geographic_deletions)[:10]:
        count = df[df['Tag'] == tag]['Count'].iloc[0]
        print(f"   - {tag} (count: {count})")
    
    # 4. Compound tags that should be decomposed
    compound_candidates = []
    for _, row in df.iterrows():
        tag = row['Tag']
        count = row['Count']
        
        # Look for compounds that can be broken down
        if ((' ' in tag and len(tag.split()) >= 2) or 
            ('/' in tag) or 
            ('-' in tag and not tag.startswith('post-') and not tag.startswith('neo-'))):
            
            # Skip if it's a high-frequency essential compound
            if count > 10 and any(essential in tag.lower() for essential in essential_genres):
                continue
                
            compound_candidates.append((tag, count))
    
    # Sort by frequency (prioritize lower frequency)
    compound_candidates.sort(key=lambda x: x[1])
    
    print(f"\n4. Compound Decomposition Candidates ({len(compound_candidates)} total):")
    print("Priority decompositions (frequency < 10):")
    priority_compounds = [tag for tag, count in compound_candidates if count < 10]
    for tag in priority_compounds[:15]:
        count = df[df['Tag'] == tag]['Count'].iloc[0]
        print(f"   - {tag} (count: {count})")
    
    # 5. Fragment consolidation opportunities
    fragment_groups = {}
    for _, row in df.iterrows():
        tag = row['Tag']
        
        # Group similar fragments
        if tag.lower() in ['alt', 'alternative', 'alternitive']:
            fragment_groups.setdefault('alternative_group', []).append(tag)
        elif tag.lower() in ['prog', 'progressive']:
            fragment_groups.setdefault('progressive_group', []).append(tag)
        elif tag.lower() in ['psych', 'psychedelic', 'psychedelia']:
            fragment_groups.setdefault('psychedelic_group', []).append(tag)
        elif tag.lower() in ['avant', 'avant-garde']:
            fragment_groups.setdefault('avant_garde_group', []).append(tag)
    
    print(f"\n5. Fragment Consolidation Opportunities:")
    for group_name, tags in fragment_groups.items():
        if len(tags) > 1:
            print(f"   {group_name}: {tags}")
    
    # Calculate total reduction potential
    total_deletions = len(set(singleton_deletions + low_freq_deletions + geographic_deletions))
    compound_reduction = len(priority_compounds) * 0.6  # Assume 60% net reduction from decomposition
    
    print(f"\n=== REDUCTION POTENTIAL ===")
    print(f"Direct deletions: {total_deletions}")
    print(f"Compound decompositions: ~{compound_reduction:.0f} net reduction")
    print(f"Total estimated reduction: ~{total_deletions + compound_reduction:.0f}")
    print(f"Projected final count: 675 - {total_deletions + compound_reduction:.0f} = {675 - (total_deletions + compound_reduction):.0f}")
    
    target_achieved = (675 - (total_deletions + compound_reduction)) < 600
    print(f"Target <600 achieved: {'✅ YES' if target_achieved else '❌ NO'}")
    
    if not target_achieved:
        additional_needed = (675 - (total_deletions + compound_reduction)) - 600
        print(f"Additional reduction needed: ~{additional_needed:.0f} tags")
        print("💡 Recommendation: Apply ultra-aggressive approach to medium-frequency tags")
    
    # Return candidates for implementation
    return {
        'singleton_deletions': singleton_deletions,
        'low_freq_deletions': low_freq_deletions,
        'geographic_deletions': geographic_deletions,
        'compound_candidates': priority_compounds,
        'total_reduction': total_deletions + compound_reduction
    }

if __name__ == '__main__':
    results = analyze_phase6_opportunities()
    
    print(f"\n🎯 Phase 6 analysis complete!")
    print(f"📋 Ready to generate ultra-aggressive implementation script")
