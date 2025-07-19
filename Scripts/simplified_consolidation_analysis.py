#!/usr/bin/env python3
"""Simplified advanced tag consolidation analysis."""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

def load_tag_data(file_path: str) -> Dict[str, int]:
    """Load tag frequency data from CSV."""
    try:
        df = pd.read_csv(file_path)
        
        # Handle different CSV formats
        if 'Normalized Tag' in df.columns and 'Total Count' in df.columns:
            return dict(zip(df['Normalized Tag'], df['Total Count']))
        elif 'normalized_tag' in df.columns and 'total_count' in df.columns:
            return dict(zip(df['normalized_tag'], df['total_count']))
        elif 'Raw Tag' in df.columns and 'Count' in df.columns:
            return dict(zip(df['Raw Tag'], df['Count']))
        else:
            # Try first two columns
            return dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
            
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return {}

def analyze_semantic_consolidation(tag_frequency_map: Dict[str, int]) -> Dict[str, Any]:
    """Analyze semantic consolidation opportunities."""
    
    # Semantic mapping rules
    semantic_mappings = {
        # Progressive synonyms
        'prog metal': 'progressive-metal',
        'prog-metal': 'progressive-metal', 
        'progressive metal': 'progressive-metal',
        'prog rock': 'prog-rock',
        'progressive rock': 'prog-rock',
        
        # Technical synonyms
        'tech death': 'technical-death-metal',
        'tech-death': 'technical-death-metal',
        'technical death metal': 'technical-death-metal',
        
        # Alternative synonyms
        'alt rock': 'alternative-rock',
        'alt-rock': 'alternative-rock',
        'alternative rock': 'alternative-rock',
        'alt metal': 'alternative-metal',
        'alt-metal': 'alternative-metal',
        'alternative metal': 'alternative-metal',
        
        # Core genre synonyms
        'metal core': 'metalcore',
        'metal-core': 'metalcore',
        'death core': 'deathcore',
        'death-core': 'deathcore',
        'grind core': 'grindcore',
        'grind-core': 'grindcore',
        
        # Pop synonyms
        'indie pop': 'indie-pop',
        'dream pop': 'dream-pop',
        'art pop': 'art-pop',
        
        # Rock synonyms
        'indie rock': 'indie-rock',
        'hard rock': 'hard-rock',
        'math rock': 'math-rock',
        'noise rock': 'noise-rock',
        'art rock': 'art-rock',
        'folk rock': 'folk-rock',
        'psychedelic rock': 'psychedelic-rock',
        
        # Punk synonyms
        'pop punk': 'pop-punk',
        'hardcore punk': 'hardcore-punk',
        
        # Jazz synonyms
        'jazz fusion': 'jazz-fusion',
        'jazz rock': 'jazz-rock',
        
        # Singer-songwriter
        'singer songwriter': 'singer-songwriter',
        
        # Electronic
        'drum and bass': 'drum-and-bass',
        'drum n bass': 'drum-and-bass',
        
        # New wave
        'new wave': 'new-wave',
        
        # Neo genres
        'neo prog': 'neo-prog',
        'neo classical': 'neo-classical',
        'neoclassical': 'neo-classical',
    }
    
    consolidated = {}
    
    for tag, frequency in tag_frequency_map.items():
        # Check if tag has a semantic mapping
        canonical = semantic_mappings.get(tag.lower(), tag)
        
        if canonical not in consolidated:
            consolidated[canonical] = {
                'canonical_form': canonical,
                'variants': [],
                'total_frequency': 0
            }
        
        consolidated[canonical]['variants'].append({
            'original_tag': tag,
            'frequency': frequency
        })
        consolidated[canonical]['total_frequency'] += frequency
    
    # Find multi-variant groups
    multi_variant_groups = []
    for canonical, data in consolidated.items():
        if len(data['variants']) > 1:
            multi_variant_groups.append({
                'canonical': canonical,
                'variant_count': len(data['variants']),
                'total_frequency': data['total_frequency'],
                'variants': [v['original_tag'] for v in data['variants']]
            })
    
    multi_variant_groups.sort(key=lambda x: x['total_frequency'], reverse=True)
    
    return {
        'original_count': len(tag_frequency_map),
        'consolidated_count': len(consolidated),
        'reduction_count': len(tag_frequency_map) - len(consolidated),
        'reduction_percentage': ((len(tag_frequency_map) - len(consolidated)) / len(tag_frequency_map) * 100) if len(tag_frequency_map) > 0 else 0,
        'multi_variant_groups': multi_variant_groups[:20]
    }

def analyze_prefix_separation(tag_list: List[str]) -> Dict[str, Any]:
    """Analyze prefix separation opportunities."""
    
    prefix_patterns = {
        'post': r'^post[\s-]?(.+)$',
        'neo': r'^neo[\s-]?(.+)$',
        'avant': r'^avant[\s-]?(.+)$',
        'proto': r'^proto[\s-]?(.+)$',
        'anti': r'^anti[\s-]?(.+)$',
        'pre': r'^pre[\s-]?(.+)$',
        'pseudo': r'^pseudo[\s-]?(.+)$',
        'non': r'^non[\s-]?(.+)$'
    }
    
    import re
    
    prefix_stats = {}
    
    for tag in tag_list:
        tag_lower = tag.lower()
        
        for prefix, pattern in prefix_patterns.items():
            match = re.match(pattern, tag_lower, re.IGNORECASE)
            if match:
                base_genre = match.group(1).strip()
                
                if prefix not in prefix_stats:
                    prefix_stats[prefix] = {
                        'count': 0,
                        'examples': [],
                        'base_genres': set()
                    }
                
                prefix_stats[prefix]['count'] += 1
                prefix_stats[prefix]['base_genres'].add(base_genre)
                
                if len(prefix_stats[prefix]['examples']) < 5:
                    prefix_stats[prefix]['examples'].append(f"{tag} → {prefix}-{base_genre}")
                
                break  # Only match first prefix found
    
    # Convert sets to lists for JSON serialization
    for prefix_data in prefix_stats.values():
        prefix_data['base_genres'] = list(prefix_data['base_genres'])
    
    return prefix_stats

def main():
    """Main analysis function."""
    
    print("ADVANCED TAG CONSOLIDATION ANALYSIS")
    print("=" * 50)
    
    # Load normalized tag data
    data_file = "tag_analysis_output/normalized_tags_analysis_20250718_191852.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    print(f"📊 Loading tag data from: {data_file}")
    tag_frequency_map = load_tag_data(data_file)
    
    if not tag_frequency_map:
        print("❌ No tag data loaded")
        return
    
    print(f"   Loaded {len(tag_frequency_map):,} unique tags")
    
    # Analyze semantic consolidation
    print("\n🔍 Analyzing semantic consolidation opportunities...")
    semantic_analysis = analyze_semantic_consolidation(tag_frequency_map)
    
    # Analyze prefix separation
    print("🔍 Analyzing prefix separation opportunities...")
    prefix_analysis = analyze_prefix_separation(list(tag_frequency_map.keys()))
    
    # Create results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {
        'timestamp': timestamp,
        'original_tag_count': len(tag_frequency_map),
        'semantic_analysis': semantic_analysis,
        'prefix_analysis': prefix_analysis
    }
    
    # Save results
    output_dir = "advanced_consolidation_analysis"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save comprehensive results as JSON
    results_file = os.path.join(output_dir, f"simplified_consolidation_results_{timestamp}.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save summary report
    summary_file = os.path.join(output_dir, f"simplified_consolidation_summary_{timestamp}.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("ADVANCED TAG CONSOLIDATION ANALYSIS\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis timestamp: {timestamp}\n\n")
        
        # Semantic consolidation results
        f.write("SEMANTIC CONSOLIDATION RESULTS:\n")
        f.write(f"  Original tags: {semantic_analysis['original_count']:,}\n")
        f.write(f"  After consolidation: {semantic_analysis['consolidated_count']:,}\n")
        f.write(f"  Reduction: {semantic_analysis['reduction_count']:,} tags ({semantic_analysis['reduction_percentage']:.1f}%)\n\n")
        
        if semantic_analysis['multi_variant_groups']:
            f.write("TOP SEMANTIC CONSOLIDATION OPPORTUNITIES:\n")
            for i, group in enumerate(semantic_analysis['multi_variant_groups'][:15], 1):
                f.write(f"  {i:2d}. {group['canonical']} ({group['variant_count']} variants, {group['total_frequency']:,} total frequency)\n")
                f.write(f"      Variants: {', '.join(group['variants'])}\n")
            f.write("\n")
        
        # Prefix analysis results
        if prefix_analysis:
            f.write("PREFIX SEPARATION OPPORTUNITIES:\n")
            for prefix, data in sorted(prefix_analysis.items(), key=lambda x: x[1]['count'], reverse=True):
                f.write(f"  {prefix}: {data['count']} tags, {len(data['base_genres'])} unique base genres\n")
                f.write(f"    Examples: {'; '.join(data['examples'][:3])}\n")
            f.write("\n")
    
    # Print summary
    print(f"\n🎯 CONSOLIDATION SUMMARY:")
    print(f"   Semantic consolidation: {semantic_analysis['original_count']:,} → {semantic_analysis['consolidated_count']:,} tags")
    print(f"   Reduction: {semantic_analysis['reduction_count']:,} tags ({semantic_analysis['reduction_percentage']:.1f}%)")
    
    if prefix_analysis:
        total_prefix_tags = sum(data['count'] for data in prefix_analysis.values())
        print(f"   Prefix opportunities: {len(prefix_analysis)} prefixes affecting {total_prefix_tags} tags")
    
    print(f"\n✅ Advanced consolidation analysis complete!")
    print(f"   Results saved to: {output_dir}")

if __name__ == "__main__":
    main()
