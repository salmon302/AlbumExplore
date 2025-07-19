#!/usr/bin/env python3
"""Simple tag analysis demonstration using the enhanced normalization system."""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from tags.normalizer.tag_normalizer import TagNormalizer

def demonstrate_enhanced_consolidation():
    """Demonstrate the enhanced consolidation system with example tags."""
    
    print("🎯 ENHANCED TAG CONSOLIDATION DEMONSTRATION")
    print("=" * 55)
    
    normalizer = TagNormalizer()
    
    # Example tags from our analysis (including variants we expect to see)
    test_tags = [
        # Progressive variants
        "prog rock", "progressive rock", "prog metal", "progressive metal",
        
        # Alternative variants (high frequency)
        "alt rock", "alt-rock", "alternative rock", "alt metal", "alternative metal",
        
        # High-frequency rock variations
        "noise rock", "hard rock", "math rock", "art rock", "folk rock",
        "garage rock", "space rock", "experimental rock",
        
        # Pop variations
        "art pop", "indie pop", "dream pop", "psychedelic pop",
        
        # Punk variations
        "pop punk", "punk rock", "hardcore punk",
        
        # Jazz variations
        "jazz fusion", "jazz rock",
        
        # Regional/cultural
        "nordic folk", "norse metal", "irish folk", "scottish folk",
        "viking metal", "celtic folk", "scandinavian folk",
        
        # Technical subgenres
        "melodic death metal", "technical death metal", "brutal death metal",
        "atmospheric black metal", "melodic black metal",
        "atmospheric sludge metal", "atmospheric sludge",
        
        # Neo genres
        "neo prog", "neo classical", "neoclassical", "neo folk", "neofolk",
        
        # Electronic
        "new wave", "drum n bass", "drum and bass",
        
        # Heavy psych
        "heavy psych", "psych rock", "psychedelic rock", "psychedelic metal",
        
        # Post genres (for testing prefix logic)
        "post metal", "post-metal", "postmetal",
        "post rock", "post-rock", "postrock",
        
        # Core metal genres
        "death metal", "black metal", "doom metal", "thrash metal",
        
        # Common misspellings and variations
        "mathcore", "deathcore", "metalcore", "grindcore",
        "metal-core", "death-core", "grind-core"
    ]
    
    print(f"📊 Testing {len(test_tags)} example tags")
    print("\n🔧 CONSOLIDATION RESULTS:")
    
    # Track consolidations
    consolidations = {}
    original_count = len(set(test_tags))
    
    for tag in test_tags:
        normalized = normalizer.normalize(tag)
        if normalized not in consolidations:
            consolidations[normalized] = []
        consolidations[normalized].append(tag)
    
    consolidated_count = len(consolidations)
    reduction = original_count - consolidated_count
    reduction_pct = (reduction / original_count) * 100 if original_count > 0 else 0
    
    print(f"📈 Original unique tags: {original_count}")
    print(f"📉 Consolidated tags: {consolidated_count}")
    print(f"🎯 Reduction: {reduction} tags ({reduction_pct:.1f}%)")
    
    # Show key consolidations
    print(f"\n📋 KEY CONSOLIDATIONS:")
    
    # Sort by number of variants consolidated
    for canonical, variants in sorted(consolidations.items(), 
                                    key=lambda x: len(set(x[1])), 
                                    reverse=True):
        unique_variants = set(variants)
        if len(unique_variants) > 1:  # Only show actual consolidations
            variants_str = "', '".join(sorted(unique_variants))
            print(f"  • '{canonical}' ← ['{variants_str}']")
    
    # Show some single mappings for validation
    print(f"\n✅ VALIDATION EXAMPLES:")
    key_examples = [
        ("prog rock", "prog-rock"),
        ("alternative rock", "alternative-rock"), 
        ("nordic folk", "scandinavian-folk"),
        ("melodic death metal", "melodic-death-metal"),
        ("neo prog", "neo-prog"),
        ("jazz fusion", "jazz-fusion")
    ]
    
    for input_tag, expected in key_examples:
        result = normalizer.normalize(input_tag)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{input_tag}' → '{result}'")

def analyze_prefix_opportunities():
    """Analyze prefix separation opportunities."""
    
    print(f"\n🔍 PREFIX SEPARATION ANALYSIS:")
    print("=" * 35)
    
    # Test tags with prefix opportunities
    prefix_tags = [
        "post metal", "post rock", "post punk", "post hardcore",
        "neo prog", "neo classical", "neo folk",
        "heavy metal", "heavy psych", "heavy rock",
        "dark metal", "dark ambient", "dark wave",
        "black metal", "black rock", "blackgaze",
        "death metal", "death rock", "deathcore",
    ]
    
    normalizer = TagNormalizer()
    
    # Group by potential prefixes
    prefix_groups = {}
    
    for tag in prefix_tags:
        normalized = normalizer.normalize(tag)
        parts = normalized.split('-')
        if len(parts) >= 2:
            prefix = parts[0]
            suffix = '-'.join(parts[1:])
            
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(normalized)
    
    print(f"📊 Found {len(prefix_groups)} prefix groups:")
    
    for prefix, tags in sorted(prefix_groups.items()):
        if len(tags) > 1:
            tags_str = "', '".join(sorted(set(tags)))
            print(f"  • '{prefix}-*': ['{tags_str}']")
    
    print(f"\n💡 Prefix separation could further reduce tags by grouping")
    print(f"   related genres under common prefixes.")

def main():
    """Run the demonstration."""
    
    demonstrate_enhanced_consolidation()
    analyze_prefix_opportunities()
    
    print(f"\n🎉 ENHANCED CONSOLIDATION SYSTEM ACTIVE!")
    print(f"The tag normalizer now applies advanced consolidation rules")
    print(f"automatically whenever tags are processed through the system.")

if __name__ == "__main__":
    main()
