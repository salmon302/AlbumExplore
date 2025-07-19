#!/usr/bin/env python3
"""Advanced tag consolidation analysis using all strategies."""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from albumexplore.tags.consolidation.prefix_separator import PrefixSeparator
from albumexplore.tags.consolidation.genre_hierarchy import GenreHierarchy
from albumexplore.tags.consolidation.semantic_consolidator import SemanticConsolidator
from albumexplore.tags.consolidation.regional_standardizer import RegionalStandardizer

class AdvancedTagConsolidator:
    """Combines all consolidation strategies for maximum tag reduction."""
    
    def __init__(self):
        self.prefix_separator = PrefixSeparator()
        self.genre_hierarchy = GenreHierarchy()
        self.semantic_consolidator = SemanticConsolidator()
        self.regional_standardizer = RegionalStandardizer()
    
    def apply_all_strategies(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Any]:
        """Apply all consolidation strategies in sequence."""
        
        print("🔧 Applying advanced consolidation strategies...")
        
        # Step 1: Semantic consolidation (most aggressive)
        print("   1. Semantic consolidation...")
        semantic_result = self.semantic_consolidator.consolidate_by_semantics(tag_frequency_map)
        semantic_tags = {item['canonical_form']: item['total_frequency'] 
                        for item in semantic_result.values()}
        
        # Step 2: Regional standardization
        print("   2. Regional standardization...")
        regional_result = self.regional_standardizer.consolidate_by_region(semantic_tags)
        regional_tags = {item['standardized_form']: item['total_frequency'] 
                        for item in regional_result.values()}
        
        # Step 3: Genre hierarchy consolidation
        print("   3. Genre hierarchy consolidation...")
        hierarchy_result = self.genre_hierarchy.consolidate_by_hierarchy(regional_tags)
        hierarchy_tags = {item['canonical_form']: item['total_frequency'] 
                         for item in hierarchy_result.values()}
        
        # Step 4: Prefix separation (applied to analyze structure)
        print("   4. Prefix separation analysis...")
        prefix_result = self.prefix_separator.consolidate_by_prefix(hierarchy_tags)
        
        return {
            'original_count': len(tag_frequency_map),
            'semantic_result': semantic_result,
            'semantic_count': len(semantic_tags),
            'regional_result': regional_result,
            'regional_count': len(regional_tags),
            'hierarchy_result': hierarchy_result,
            'hierarchy_count': len(hierarchy_tags),
            'prefix_result': prefix_result,
            'final_count': len(hierarchy_tags),
            'total_reduction': len(tag_frequency_map) - len(hierarchy_tags),
            'reduction_percentage': ((len(tag_frequency_map) - len(hierarchy_tags)) / len(tag_frequency_map) * 100) if len(tag_frequency_map) > 0 else 0
        }
    
    def analyze_consolidation_impact(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Any]:
        """Analyze the impact of each consolidation strategy."""
        
        # Get individual strategy stats
        semantic_stats = self.semantic_consolidator.get_consolidation_stats(tag_frequency_map)
        regional_stats = self.regional_standardizer.get_standardization_stats(tag_frequency_map)
        hierarchy_stats = self.genre_hierarchy.get_hierarchy_stats(tag_frequency_map)
        prefix_stats = self.prefix_separator.get_prefix_statistics(list(tag_frequency_map.keys()))
        
        return {
            'semantic_consolidation': semantic_stats,
            'regional_standardization': regional_stats,
            'hierarchy_categorization': hierarchy_stats,
            'prefix_analysis': prefix_stats
        }

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

def save_results(results: Dict[str, Any], output_dir: str, timestamp: str):
    """Save consolidation results to files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save comprehensive results as JSON
    results_file = os.path.join(output_dir, f"advanced_consolidation_results_{timestamp}.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        # Convert non-serializable objects to strings
        serializable_results = json.loads(json.dumps(results, default=str))
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)
    
    # Save summary report
    summary_file = os.path.join(output_dir, f"advanced_consolidation_summary_{timestamp}.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("ADVANCED TAG CONSOLIDATION RESULTS\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis timestamp: {timestamp}\n\n")
        
        # Overall impact
        f.write("OVERALL CONSOLIDATION IMPACT:\n")
        f.write(f"  Original tags: {results['analysis']['original_count']:,}\n")
        f.write(f"  Final tags: {results['analysis']['final_count']:,}\n")
        f.write(f"  Total reduction: {results['analysis']['total_reduction']:,} tags\n")
        f.write(f"  Reduction percentage: {results['analysis']['reduction_percentage']:.1f}%\n\n")
        
        # Strategy breakdown
        f.write("STRATEGY BREAKDOWN:\n")
        f.write(f"  1. Semantic consolidation: {results['analysis']['original_count']} → {results['analysis']['semantic_count']} tags\n")
        f.write(f"  2. Regional standardization: {results['analysis']['semantic_count']} → {results['analysis']['regional_count']} tags\n")
        f.write(f"  3. Genre hierarchy: {results['analysis']['regional_count']} → {results['analysis']['hierarchy_count']} tags\n")
        f.write(f"  4. Prefix separation: Structural analysis (does not reduce count)\n\n")
        
        # Top consolidation opportunities
        if 'impact_analysis' in results and 'semantic_consolidation' in results['impact_analysis']:
            semantic_opportunities = results['impact_analysis']['semantic_consolidation'].get('multi_variant_groups', [])
            if semantic_opportunities:
                f.write("TOP SEMANTIC CONSOLIDATION OPPORTUNITIES:\n")
                for i, group in enumerate(semantic_opportunities[:10], 1):
                    f.write(f"  {i:2d}. {group['canonical']} ({group['variant_count']} variants, {group['total_frequency']} total frequency)\n")
                    f.write(f"      Variants: {', '.join(group['variants'])}\n")
                f.write("\n")
        
        # Regional opportunities
        if 'impact_analysis' in results and 'regional_standardization' in results['impact_analysis']:
            regional_opportunities = results['impact_analysis']['regional_standardization'].get('standardization_opportunities', [])
            if regional_opportunities:
                f.write("TOP REGIONAL STANDARDIZATION OPPORTUNITIES:\n")
                for i, opp in enumerate(regional_opportunities[:10], 1):
                    f.write(f"  {i:2d}. '{opp['original_tag']}' → '{opp['standardized_tag']}' ({opp['frequency']} frequency)\n")
                f.write("\n")
        
        # Prefix analysis
        if 'impact_analysis' in results and 'prefix_analysis' in results['impact_analysis']:
            prefix_analysis = results['impact_analysis']['prefix_analysis']
            if prefix_analysis:
                f.write("PREFIX ANALYSIS:\n")
                for prefix, data in sorted(prefix_analysis.items(), key=lambda x: x[1]['count'], reverse=True):
                    f.write(f"  {prefix}: {data['count']} tags, {len(data['base_genres'])} unique base genres\n")
                    f.write(f"    Examples: {'; '.join(data['examples'][:3])}\n")
                f.write("\n")
    
    print(f"✅ Results saved to {output_dir}")
    return results_file, summary_file

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
    
    # Initialize consolidator
    consolidator = AdvancedTagConsolidator()
    
    # Analyze impact of individual strategies
    print("\n🔍 Analyzing individual strategy impacts...")
    impact_analysis = consolidator.analyze_consolidation_impact(tag_frequency_map)
    
    # Apply all strategies
    print("\n⚡ Applying all consolidation strategies...")
    consolidation_results = consolidator.apply_all_strategies(tag_frequency_map)
    
    # Combine results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {
        'timestamp': timestamp,
        'analysis': consolidation_results,
        'impact_analysis': impact_analysis
    }
    
    # Save results
    output_dir = "advanced_consolidation_analysis"
    results_file, summary_file = save_results(results, output_dir, timestamp)
    
    # Print summary
    print(f"\n🎯 CONSOLIDATION SUMMARY:")
    print(f"   Original tags: {consolidation_results['original_count']:,}")
    print(f"   Final tags: {consolidation_results['final_count']:,}")
    print(f"   Total reduction: {consolidation_results['total_reduction']:,} tags")
    print(f"   Reduction percentage: {consolidation_results['reduction_percentage']:.1f}%")
    print(f"\n✅ Advanced consolidation analysis complete!")
    print(f"   Results saved to: {output_dir}")

if __name__ == "__main__":
    main()
