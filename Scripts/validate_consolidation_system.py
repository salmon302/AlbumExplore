#!/usr/bin/env python3
"""Validate the complete enhanced tag consolidation system."""

import sys
import os
import pandas as pd
from collections import Counter

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from tags.normalizer.tag_normalizer import TagNormalizer

def test_consolidation_examples():
    """Test key consolidation examples."""
    
    normalizer = TagNormalizer()
    
    test_cases = [
        # Progressive consolidations
        ("prog rock", "prog-rock"),
        ("progressive rock", "prog-rock"), 
        ("prog metal", "progressive-metal"),
        ("progressive metal", "progressive-metal"),
        
        # Alternative consolidations (high impact)
        ("alt rock", "alternative-rock"),
        ("alt-rock", "alternative-rock"),
        ("alternative rock", "alternative-rock"),
        ("alt metal", "alternative-metal"),
        
        # High-frequency rock consolidations
        ("noise rock", "noise-rock"),
        ("hard rock", "hard-rock"),
        ("math rock", "math-rock"),
        ("art rock", "art-rock"),
        
        # Regional consolidations
        ("nordic folk", "scandinavian-folk"),
        ("norse metal", "viking-metal"),
        ("irish folk", "celtic-folk"),
        ("scottish folk", "celtic-folk"),
        
        # Technical subgenres
        ("melodic death metal", "melodic-death-metal"),
        ("atmospheric black metal", "atmospheric-black-metal"),
        ("atmospheric sludge", "atmospheric-sludge-metal"),
        
        # Jazz consolidations
        ("jazz fusion", "jazz-fusion"),
        ("jazz rock", "jazz-rock"),
        
        # Neo genres
        ("neo prog", "neo-prog"),
        ("neoclassical", "neo-classical"),
        ("neofolk", "neo-folk"),
        
        # Pop consolidations
        ("art pop", "art-pop"),
        ("dream pop", "dream-pop"),
        ("indie pop", "indie-pop"),
        
        # Punk consolidations
        ("pop punk", "pop-punk"),
        ("hardcore punk", "hardcore-punk"),
        
        # Electronic
        ("drum n bass", "drum-and-bass"),
        ("drum and bass", "drum-and-bass"),
        ("new wave", "new-wave"),
    ]
    
    print("TESTING CONSOLIDATION EXAMPLES")
    print("=" * 40)
    
    passed = 0
    failed = 0
    
    for input_tag, expected in test_cases:
        result = normalizer.normalize(input_tag)
        if result == expected:
            print(f"✅ '{input_tag}' → '{result}'")
            passed += 1
        else:
            print(f"❌ '{input_tag}' → '{result}' (expected '{expected}')")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def analyze_csv_impact():
    """Analyze the impact on actual CSV data."""
    
    print("\nANALYZING CSV IMPACT")
    print("=" * 25)
    
    normalizer = TagNormalizer()
    
    # Load a sample CSV file
    csv_files = [
        "csv/_r_ProgMetal _ Yearly Albums - 2022 Prog-metal.csv",
        "csv/_r_ProgMetal _ Yearly Albums - 2021 Prog-metal.csv",
        "csv/_r_ProgMetal _ Yearly Albums - 2020 Prog-metal.csv",
    ]
    
    all_tags = []
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                if 'Tags' in df.columns:
                    for tags_str in df['Tags'].dropna():
                        if isinstance(tags_str, str):
                            tags = [tag.strip() for tag in tags_str.split(',')]
                            all_tags.extend(tags)
                print(f"📄 Loaded {csv_file}")
            except Exception as e:
                print(f"⚠️  Error loading {csv_file}: {e}")
    
    if not all_tags:
        print("❌ No tags found in CSV files")
        return
    
    print(f"📊 Found {len(all_tags)} total tag instances")
    
    # Count original tags
    original_counter = Counter(all_tags)
    original_unique = len(original_counter)
    
    # Normalize all tags
    normalized_tags = [normalizer.normalize(tag) for tag in all_tags]
    normalized_counter = Counter(normalized_tags)
    normalized_unique = len(normalized_counter)
    
    # Calculate reduction
    reduction = original_unique - normalized_unique
    reduction_pct = (reduction / original_unique) * 100 if original_unique > 0 else 0
    
    print(f"📈 Original unique tags: {original_unique}")
    print(f"📉 Normalized unique tags: {normalized_unique}")
    print(f"🎯 Reduction: {reduction} tags ({reduction_pct:.1f}%)")
    
    # Show top consolidations
    print(f"\n📋 Top consolidations by frequency:")
    
    consolidations = {}
    for original, normalized in zip(all_tags, normalized_tags):
        if original != normalized:
            if normalized not in consolidations:
                consolidations[normalized] = []
            consolidations[normalized].append(original)
    
    # Sort by impact (number of original tags consolidated)
    for canonical, originals in sorted(consolidations.items(), 
                                     key=lambda x: len(set(x[1])), 
                                     reverse=True)[:10]:
        original_set = set(originals)
        frequency = len(originals)
        print(f"  • '{canonical}' ← {original_set} ({frequency} instances)")

def main():
    """Run complete validation."""
    
    print("ENHANCED TAG CONSOLIDATION VALIDATION")
    print("=" * 45)
    
    # Test consolidation examples
    if test_consolidation_examples():
        print("\n✅ All consolidation examples passed!")
    else:
        print("\n❌ Some consolidation examples failed!")
        return
    
    # Analyze CSV impact
    analyze_csv_impact()
    
    print(f"\n🎉 CONSOLIDATION SYSTEM VALIDATION COMPLETE!")
    print(f"The enhanced tag normalization system is ready for production use.")

if __name__ == "__main__":
    main()
