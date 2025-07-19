#!/usr/bin/env python3
"""
Enhanced Tag Analysis and Consolidation Script

This script analyzes your current tag data using the new enhanced hierarchy system
and provides recommendations for tag consolidation to minimize quantity while
maintaining meaningful distinctions.
"""

import sys
import os
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from albumexplore.tags.hierarchy.enhanced_tag_hierarchy import EnhancedTagHierarchy, TagType
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import EnhancedTagConsolidator, ConsolidationStrategy
    from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)

class MockAnalyzer:
    """Mock analyzer for testing purposes"""
    def __init__(self, tag_frequencies: Dict[str, int]):
        self.tag_frequencies = tag_frequencies
        self.normalizer = TagNormalizer()
        
    def find_similar_tags(self, tag: str, threshold: float = 0.3):
        # Simple mock implementation
        return []

def generate_tag_analysis_data(base_path: str) -> Dict[str, Any]:
    """Generate fresh tag analysis data from CSV files"""
    
    print("🔍 Scanning CSV files for tag data...")
    
    from tags.normalizer.tag_normalizer import TagNormalizer
    normalizer = TagNormalizer()
    
    csv_dir = Path(base_path) / "csv"
    all_tags = []
    
    if not csv_dir.exists():
        print(f"❌ CSV directory not found: {csv_dir}")
        return {"tags": [], "frequencies": {}}
    
    # Process CSV files
    csv_files = list(csv_dir.glob("*.csv"))
    print(f"📁 Found {len(csv_files)} CSV files")
    
    for csv_file in csv_files:
        try:
            # Read the file and find the header row
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find the header row (look for "Artist,Album" pattern)
            header_row = None
            for i, line in enumerate(lines):
                if 'Artist,Album,Release Date,Length,Genre' in line:
                    header_row = i
                    break
            
            if header_row is None:
                print(f"⚠️  No header found in {csv_file}")
                continue
            
            # Read CSV starting from header row
            df = pd.read_csv(csv_file, skiprows=header_row)
            
            # The genre column is always the 5th column (index 4)
            # Based on format: Artist,Album,Release Date,Length,Genre / Subgenres,Vocal Style,...
            if len(df.columns) < 5:
                print(f"⚠️  Not enough columns in {csv_file} (found {len(df.columns)})")
                continue
            
            genre_column = df.columns[4]  # 5th column (0-indexed)
            print(f"📄 Processing {csv_file} (using column: '{genre_column}')")
            
            # Extract tags
            tags_processed = 0
            for tags_str in df[genre_column].dropna():
                if isinstance(tags_str, str) and tags_str.strip():
                    tags = [tag.strip() for tag in tags_str.split(',')]
                    all_tags.extend(tags)
                    tags_processed += 1
            
            print(f"    Found {tags_processed} rows with genre data")
                    
        except Exception as e:
            print(f"⚠️  Error processing {csv_file}: {e}")
    
    print(f"📊 Found {len(all_tags)} total tag instances")
    
    # Normalize tags and count frequencies
    normalized_tags = [normalizer.normalize(tag) for tag in all_tags]
    
    # Create frequency data
    from collections import Counter
    original_counter = Counter(all_tags)
    normalized_counter = Counter(normalized_tags)
    
    return {
        "tags": list(original_counter.keys()),
        "frequencies": dict(original_counter),
        "normalized_tags": list(normalized_counter.keys()),
        "normalized_frequencies": dict(normalized_counter),
        "tag_frequencies": dict(original_counter),  # For compatibility
        "total_tags": len(original_counter),
        "total_normalized_tags": len(normalized_counter),
        "total_instances": sum(original_counter.values())
    }

def load_tag_analysis_data(base_path: str) -> Dict[str, Any]:
    """Load the existing tag analysis data, or generate it if it doesn't exist"""
    
    # Find the most recent analysis files
    output_dir = Path(base_path) / "tag_analysis_output"
    
    # Look for the most recent files
    csv_files = []
    if output_dir.exists():
        csv_files = list(output_dir.glob("normalized_tags_analysis_*.csv"))
    
    if not csv_files:
        print("📊 No existing analysis files found. Generating fresh analysis...")
        return generate_tag_analysis_data(base_path)
    
    # Use the most recent file
    most_recent = max(csv_files, key=lambda x: x.stat().st_mtime)
    
    print(f"Loading tag data from: {most_recent}")
    
    # Load the CSV data
    df = pd.read_csv(most_recent)
    
    # Extract tag frequencies
    tag_frequencies = {}
    tag_details = {}
    
    for _, row in df.iterrows():
        tag = row['Normalized Tag']
        count = row['Total Count']
        variants = row['Raw Variants']
        
        tag_frequencies[tag] = count
        tag_details[tag] = {
            'variants': variants.split(', ') if isinstance(variants, str) else [],
            'count': count
        }
    
    return {
        "tags": list(tag_frequencies.keys()),
        "frequencies": tag_frequencies,
        "normalized_tags": list(tag_frequencies.keys()),
        "normalized_frequencies": tag_frequencies,
        "tag_frequencies": tag_frequencies,  # For compatibility
        "tag_details": tag_details,
        "total_tags": len(tag_frequencies),
        "total_instances": sum(tag_frequencies.values())
    }
    
    return {
        'tag_frequencies': tag_frequencies,
        'tag_details': tag_details,
        'total_tags': len(tag_frequencies),
        'total_instances': sum(tag_frequencies.values())
    }

def apply_improvement_strategies(consolidator, data: Dict[str, Any]):
    """Apply the four improvement strategies to enhance tag consolidation"""
    
    print("🔧 Strategy 1: Implementing deeper modifier and prefix decomposition...")
    _apply_modifier_decomposition_rules(consolidator)
    
    print("🏗️  Strategy 2: Building multi-level genre hierarchy...")
    _apply_hierarchical_rules(consolidator)
    
    print("🔗 Strategy 3: Adding advanced synonym and relationship mapping...")
    _apply_synonym_mapping_rules(consolidator)
    
    print("✂️  Strategy 4: Implementing robust compound tag splitting...")
    _apply_compound_splitting_rules(consolidator)
    
    return consolidator

def _apply_modifier_decomposition_rules(consolidator):
    """Apply Strategy 1: Deeper modifier and prefix decomposition"""
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import ConsolidationRule
    from albumexplore.tags.hierarchy.enhanced_tag_hierarchy import TagType
    
    # Enhanced modifier decomposition rules
    modifier_decomposition_rules = [
        # Instrumental + Genre combinations -> separate modifiers
        ConsolidationRule(
            pattern=r"instrumental\\s+(post-rock|post-metal|black-metal|death-metal|doom-metal)",
            replacement=None,  # Will be handled by decomposition
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'instrumental' modifier from base genre for flexible querying"
        ),
        
        # Atmospheric + Genre combinations
        ConsolidationRule(
            pattern=r"atmospheric\\s+(post-metal|black-metal|doom-metal|sludge)",
            replacement=None,
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'atmospheric' modifier from base genre"
        ),
        
        # Technical + Genre combinations
        ConsolidationRule(
            pattern=r"technical\\s+(death-metal|black-metal|thrash-metal)",
            replacement=None,
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'technical' modifier from base genre"
        ),
        
        # Progressive + Genre combinations
        ConsolidationRule(
            pattern=r"progressive\\s+(post-hardcore|metalcore|deathcore)",
            replacement=None,
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'progressive' modifier from base genre"
        ),
        
        # Melodic + Genre combinations
        ConsolidationRule(
            pattern=r"melodic\\s+(death-metal|black-metal|hardcore)",
            replacement=None,
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'melodic' modifier from base genre"
        ),
        
        # Experimental + Genre combinations
        ConsolidationRule(
            pattern=r"experimental\\s+(rock|metal|electronic|hip-hop)",
            replacement=None,
            action="decompose_modifiers",
            confidence=0.9,
            preserve_components=True,
            reason="Separate 'experimental' modifier from base genre"
        ),
    ]
    
    consolidator.consolidation_rules.extend(modifier_decomposition_rules)

def _apply_hierarchical_rules(consolidator):
    """Apply Strategy 2: Multi-level genre hierarchy implementation"""
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import ConsolidationRule
    
    # Define hierarchical relationships for redundancy elimination
    hierarchy_rules = [
        # Metal hierarchy - if specific subgenre is present, remove generic "metal"
        ConsolidationRule(
            pattern=r"(.*(death|black|doom|power|thrash|progressive|symphonic|folk|viking)-metal.*)(,\\s*|\\s+)metal\\b",
            replacement=r"\\1",  # Keep only the specific subgenre
            action="hierarchy_simplify",
            confidence=0.85,
            reason="Remove redundant 'metal' when specific metal subgenre is present"
        ),
        
        # Rock hierarchy - similar for rock subgenres
        ConsolidationRule(
            pattern=r"(.*(progressive|psychedelic|alternative|indie|hard|folk)-rock.*)(,\\s*|\\s+)rock\\b",
            replacement=r"\\1",
            action="hierarchy_simplify",
            confidence=0.85,
            reason="Remove redundant 'rock' when specific rock subgenre is present"
        ),
        
        # Progressive hierarchy - if prog-metal is present, remove generic "progressive"
        ConsolidationRule(
            pattern=r"(.*prog(ressive)?-(metal|rock).*)(,\\s*|\\s+)progressive\\b",
            replacement=r"\\1",
            action="hierarchy_simplify",
            confidence=0.85,
            reason="Remove redundant 'progressive' when specific prog subgenre is present"
        ),
        
        # Post- hierarchy
        ConsolidationRule(
            pattern=r"(.*post-(metal|rock|punk|hardcore).*)(,\\s*|\\s+)(metal|rock|punk|hardcore)\\b",
            replacement=r"\\1",
            action="hierarchy_simplify",
            confidence=0.85,
            reason="Remove redundant base genre when post- variant is present"
        ),
    ]
    
    consolidator.consolidation_rules.extend(hierarchy_rules)

def _apply_synonym_mapping_rules(consolidator):
    """Apply Strategy 3: Advanced synonym and relationship mapping"""
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import ConsolidationRule
    
    # Manually curated synonym mappings based on analysis feedback
    synonym_rules = [
        # Avant-prog and Zeuhl relationship
        ConsolidationRule(
            pattern=r"^zeuhl$",
            replacement="avant-prog",
            action="merge",
            confidence=0.8,
            reason="Zeuhl is a specialized form of avant-garde progressive rock"
        ),
        
        # Heavy-psych relationships
        ConsolidationRule(
            pattern=r"^heavy-psych$",
            replacement="psychedelic-rock",  # Can also add stoner-rock as secondary
            action="merge",
            confidence=0.7,
            reason="Heavy-psych is closely related to psychedelic rock with stoner elements"
        ),
        
        # Drone and ambient relationships
        ConsolidationRule(
            pattern=r"^drone-metal$",
            replacement="atmospheric-metal",
            action="merge",
            confidence=0.6,
            reason="Drone metal shares atmospheric qualities"
        ),
        
        # Shoegaze relationships
        ConsolidationRule(
            pattern=r"^shoegaze$",
            replacement="dream-pop",
            action="merge",
            confidence=0.7,
            reason="Shoegaze and dream-pop are closely related subgenres"
        ),
        
        # Krautrock relationships
        ConsolidationRule(
            pattern=r"^krautrock$",
            replacement="experimental-rock",
            action="merge",
            confidence=0.7,
            reason="Krautrock is a form of experimental rock"
        ),
        
        # Math-rock relationships
        ConsolidationRule(
            pattern=r"^math-rock$",
            replacement="experimental-rock",
            action="merge", 
            confidence=0.6,
            reason="Math-rock can be considered experimental rock with complex time signatures"
        ),
        
        # Singer-songwriter implications
        ConsolidationRule(
            pattern=r"^singer-songwriter$",
            replacement="folk",  # Primary mapping, but could imply acoustic too
            action="merge",
            confidence=0.6,
            reason="Singer-songwriter often implies folk elements and acoustic performance"
        ),
        
        # Industrial relationships
        ConsolidationRule(
            pattern=r"^industrial-metal$",
            replacement="industrial",  # Keep as industrial, metal is implied
            action="merge",
            confidence=0.8,
            reason="Industrial-metal can be simplified to industrial in most contexts"
        ),
        
        # Crust punk relationships
        ConsolidationRule(
            pattern=r"^crust-punk$",
            replacement="hardcore-punk",
            action="merge",
            confidence=0.7,
            reason="Crust punk is a variant of hardcore punk"
        ),
        
        # Space rock relationships
        ConsolidationRule(
            pattern=r"^space-rock$",
            replacement="psychedelic-rock",
            action="merge",
            confidence=0.7,
            reason="Space rock is a variant of psychedelic rock"
        ),
    ]
    
    consolidator.consolidation_rules.extend(synonym_rules)

def _apply_compound_splitting_rules(consolidator):
    """Apply Strategy 4: Robust splitting of compound tags"""
    from albumexplore.tags.consolidation.enhanced_tag_consolidator import ConsolidationRule
    
    compound_splitting_rules = [
        # Enhanced slash splitting with better preservation
        ConsolidationRule(
            pattern=r"([^/]+)/([^/]+)/([^/]+)",  # Three-part compounds
            replacement=None,  # Will be handled by split logic
            action="split_compound",
            confidence=0.9,
            preserve_components=True,
            reason="Split three-part compound tag into separate components"
        ),
        
        ConsolidationRule(
            pattern=r"([^/]+)/([^/]+)",  # Two-part compounds
            replacement=None,
            action="split_compound", 
            confidence=0.9,
            preserve_components=True,
            reason="Split two-part compound tag into separate components"
        ),
        
        # Ampersand splitting
        ConsolidationRule(
            pattern=r"([^&]+)\\s*&\\s*([^&]+)",
            replacement=None,
            action="split_compound",
            confidence=0.85,
            preserve_components=True,
            reason="Split ampersand-connected compound tag"
        ),
        
        # Plus sign splitting
        ConsolidationRule(
            pattern=r"([^+]+)\\s*\\+\\s*([^+]+)",
            replacement=None,
            action="split_compound",
            confidence=0.85,
            preserve_components=True,
            reason="Split plus-connected compound tag"
        ),
        
        # Comma splitting (but be careful with natural commas)
        ConsolidationRule(
            pattern=r"^([^,]+),\\s*([^,]+)$",  # Only simple two-part comma splits
            replacement=None,
            action="split_compound",
            confidence=0.7,
            preserve_components=True,
            reason="Split comma-separated compound tag"
        ),
        
        # Bracket-based splitting [genre1][genre2]
        ConsolidationRule(
            pattern=r"\\[([^\\]]+)\\]\\[([^\\]]+)\\]",
            replacement=None,
            action="split_compound",
            confidence=0.9,
            preserve_components=True,
            reason="Split bracket-enclosed compound tags"
        ),
        
        # Parentheses-based alternatives Genre1 (Genre2)
        ConsolidationRule(
            pattern=r"^([^(]+)\\s*\\(([^)]+)\\)$",
            replacement=None,
            action="split_compound",
            confidence=0.8,
            preserve_components=True,
            reason="Split parentheses-indicated alternative genre"
        ),
    ]
    
    consolidator.consolidation_rules.extend(compound_splitting_rules)

def post_process_consolidation(consolidation_report: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Post-process consolidation results to apply additional improvements"""
    
    print("🔄 Post-processing consolidation results...")
    
    # Strategy 1: Enhanced modifier decomposition tracking
    _track_modifier_decomposition(consolidation_report, data)
    
    # Strategy 2: Hierarchy relationship validation
    _validate_hierarchy_relationships(consolidation_report)
    
    # Strategy 3: Synonym impact analysis
    _analyze_synonym_impact(consolidation_report)
    
    # Strategy 4: Compound splitting effectiveness
    _analyze_compound_splitting(consolidation_report)
    
    # Calculate improvement metrics
    _calculate_improvement_metrics(consolidation_report, data)
    
    return consolidation_report

def _track_modifier_decomposition(consolidation_report: Dict[str, Any], data: Dict[str, Any]):
    """Track the effectiveness of modifier decomposition"""
    
    decomposed_tags = []
    modifier_frequency = {}
    
    # Look for tags that were decomposed into modifiers + genres
    for group in consolidation_report.get('consolidation_groups', []):
        for original_tag in group['original_tags']:
            if any(modifier in original_tag.lower() for modifier in [
                'instrumental', 'atmospheric', 'technical', 'progressive', 'melodic', 'experimental'
            ]):
                base_genre = original_tag.lower()
                # Extract the modifier and base genre
                for modifier in ['instrumental', 'atmospheric', 'technical', 'progressive', 'melodic', 'experimental']:
                    if modifier in base_genre:
                        base_genre = base_genre.replace(modifier, '').strip()
                        if modifier not in modifier_frequency:
                            modifier_frequency[modifier] = 0
                        modifier_frequency[modifier] += data['tag_frequencies'].get(original_tag, 0)
                        
                        decomposed_tags.append({
                            'original': original_tag,
                            'modifier': modifier,
                            'base_genre': base_genre,
                            'frequency': data['tag_frequencies'].get(original_tag, 0)
                        })
                        break
    
    consolidation_report['modifier_decomposition'] = {
        'decomposed_count': len(decomposed_tags),
        'modifier_frequencies': modifier_frequency,
        'examples': decomposed_tags[:10],  # Show top 10 examples
        'total_frequency_affected': sum(modifier_frequency.values())
    }

def _validate_hierarchy_relationships(consolidation_report: Dict[str, Any]):
    """Validate that hierarchy relationships are being properly applied"""
    
    hierarchy_simplifications = []
    
    for group in consolidation_report.get('consolidation_groups', []):
        canonical = group['canonical_form']
        originals = group['original_tags']
        
        # Look for cases where we simplified based on hierarchy
        for original in originals:
            if '-metal' in original and 'metal' in original and original != canonical:
                hierarchy_simplifications.append({
                    'original': original,
                    'canonical': canonical,
                    'type': 'metal_hierarchy',
                    'frequency': group.get('original_frequencies', {}).get(original, 0)
                })
            elif '-rock' in original and 'rock' in original and original != canonical:
                hierarchy_simplifications.append({
                    'original': original,
                    'canonical': canonical,
                    'type': 'rock_hierarchy',
                    'frequency': group.get('original_frequencies', {}).get(original, 0)
                })
    
    consolidation_report['hierarchy_simplifications'] = {
        'count': len(hierarchy_simplifications),
        'examples': hierarchy_simplifications[:10],
        'total_frequency_affected': sum(h['frequency'] for h in hierarchy_simplifications)
    }

def _analyze_synonym_impact(consolidation_report: Dict[str, Any]):
    """Analyze the impact of synonym mapping rules"""
    
    synonym_mappings = []
    
    # Known synonym pairs from our rules
    known_synonyms = {
        'zeuhl': 'avant-prog',
        'heavy-psych': 'psychedelic-rock',
        'drone-metal': 'atmospheric-metal',
        'shoegaze': 'dream-pop',
        'krautrock': 'experimental-rock',
        'math-rock': 'experimental-rock',
        'singer-songwriter': 'folk',
        'industrial-metal': 'industrial',
        'crust-punk': 'hardcore-punk',
        'space-rock': 'psychedelic-rock'
    }
    
    for group in consolidation_report.get('consolidation_groups', []):
        canonical = group['canonical_form']
        originals = group['original_tags']
        
        for original in originals:
            original_lower = original.lower().replace(' ', '-')
            if original_lower in known_synonyms and known_synonyms[original_lower] in canonical:
                synonym_mappings.append({
                    'original': original,
                    'canonical': canonical,
                    'synonym_type': known_synonyms[original_lower],
                    'frequency': group.get('original_frequencies', {}).get(original, 0)
                })
    
    consolidation_report['synonym_mappings'] = {
        'count': len(synonym_mappings),
        'examples': synonym_mappings,
        'total_frequency_affected': sum(s['frequency'] for s in synonym_mappings)
    }

def _analyze_compound_splitting(consolidation_report: Dict[str, Any]):
    """Analyze the effectiveness of compound tag splitting"""
    
    split_compounds = []
    
    for group in consolidation_report.get('consolidation_groups', []):
        for original in group['original_tags']:
            # Check if this was a compound tag that got split
            if any(sep in original for sep in ['/', '&', '+', '[', '(']) and len(group['original_tags']) == 1:
                # This suggests the compound was split rather than merged
                components = []
                
                if '/' in original:
                    components = [c.strip() for c in original.split('/')]
                elif '&' in original:
                    components = [c.strip() for c in original.split('&')]
                elif '+' in original:
                    components = [c.strip() for c in original.split('+')]
                
                if len(components) > 1:
                    split_compounds.append({
                        'original': original,
                        'components': components,
                        'canonical': group['canonical_form'],
                        'frequency': group.get('original_frequencies', {}).get(original, 0)
                    })
    
    consolidation_report['compound_splitting'] = {
        'split_count': len(split_compounds),
        'examples': split_compounds[:10],
        'total_frequency_affected': sum(s['frequency'] for s in split_compounds)
    }

def _calculate_improvement_metrics(consolidation_report: Dict[str, Any], data: Dict[str, Any]):
    """Calculate metrics showing the impact of the four improvement strategies"""
    
    # Calculate metrics for each strategy
    strategy_metrics = {
        'modifier_decomposition': {
            'tags_affected': consolidation_report.get('modifier_decomposition', {}).get('decomposed_count', 0),
            'frequency_affected': consolidation_report.get('modifier_decomposition', {}).get('total_frequency_affected', 0)
        },
        'hierarchy_simplification': {
            'tags_affected': consolidation_report.get('hierarchy_simplifications', {}).get('count', 0),
            'frequency_affected': consolidation_report.get('hierarchy_simplifications', {}).get('total_frequency_affected', 0)
        },
        'synonym_mapping': {
            'tags_affected': consolidation_report.get('synonym_mappings', {}).get('count', 0),
            'frequency_affected': consolidation_report.get('synonym_mappings', {}).get('total_frequency_affected', 0)
        },
        'compound_splitting': {
            'tags_affected': consolidation_report.get('compound_splitting', {}).get('split_count', 0),
            'frequency_affected': consolidation_report.get('compound_splitting', {}).get('total_frequency_affected', 0)
        }
    }
    
    # Calculate total improvement
    total_tags_affected = sum(strategy['tags_affected'] for strategy in strategy_metrics.values())
    total_frequency_affected = sum(strategy['frequency_affected'] for strategy in strategy_metrics.values())
    
    improvement_summary = {
        'strategy_breakdown': strategy_metrics,
        'total_improvement': {
            'tags_affected': total_tags_affected,
            'frequency_affected': total_frequency_affected,
            'percentage_of_tags': (total_tags_affected / data['total_tags']) * 100 if data['total_tags'] > 0 else 0,
            'percentage_of_instances': (total_frequency_affected / data['total_instances']) * 100 if data['total_instances'] > 0 else 0
        }
    }
    
    consolidation_report['improvement_metrics'] = improvement_summary

def analyze_with_enhanced_hierarchy(data: Dict[str, Any], strategy: str = "balanced") -> Dict[str, Any]:
    """Analyze tags using the enhanced hierarchy system with new improvement strategies"""
    
    print(f"\\nAnalyzing {data['total_tags']} unique tags with {strategy} strategy...")
    print("🚀 Applying improved consolidation strategies...")
    
    # Create mock analyzer
    analyzer = MockAnalyzer(data['tag_frequencies'])
    
    # Create enhanced consolidator
    strategy_enum = ConsolidationStrategy(strategy.lower())
    consolidator = EnhancedTagConsolidator(analyzer, strategy_enum)
    
    # Apply new improvement strategies
    consolidator = apply_improvement_strategies(consolidator, data)
    
    # Get list of all tags
    all_tags = list(data['tag_frequencies'].keys())
    
    # Perform consolidation analysis
    consolidation_report = consolidator.consolidate_tag_collection(all_tags)
    
    # Apply post-processing improvements
    consolidation_report = post_process_consolidation(consolidation_report, data)
    
    return consolidation_report

def generate_detailed_analysis(data: Dict[str, Any], consolidation_report: Dict[str, Any]) -> Dict[str, Any]:
    """Generate detailed analysis of the consolidation results with improvement metrics"""
    
    # Create hierarchy system for additional analysis
    hierarchy = EnhancedTagHierarchy()
    
    detailed_analysis = {
        'input_summary': {
            'total_original_tags': data['total_tags'],
            'total_instances': data['total_instances'],
            'average_frequency': data['total_instances'] / data['total_tags'] if data['total_tags'] > 0 else 0
        },
        'consolidation_summary': consolidation_report['mapping_stats'],
        'improvement_strategies': consolidation_report.get('improvement_metrics', {}),
        'hierarchy_breakdown': {},
        'prefix_analysis': {},
        'component_analysis': {},
        'consolidation_examples': [],
        'recommendations': [],
        'strategy_effectiveness': {}
    }
    
    # Analyze by tag type
    type_breakdown = {tag_type.value: {'count': 0, 'frequency': 0} for tag_type in TagType}
    
    consolidator = EnhancedTagConsolidator(MockAnalyzer(data['tag_frequencies']))
    
    for tag, frequency in data['tag_frequencies'].items():
        components = hierarchy.decompose_tag(tag)
        
        for component in components:
            type_breakdown[component.tag_type.value]['count'] += 1
            type_breakdown[component.tag_type.value]['frequency'] += frequency
    
    detailed_analysis['hierarchy_breakdown'] = type_breakdown
    
    # Analyze prefixes (enhanced for better insights)
    prefix_usage = {}
    modifier_usage = {}
    
    for prefix in hierarchy.separable_prefixes:
        prefix_tags = [tag for tag in data['tag_frequencies'] if tag.lower().startswith(prefix.lower())]
        if prefix_tags:
            total_freq = sum(data['tag_frequencies'][tag] for tag in prefix_tags)
            prefix_usage[prefix] = {
                'tags': prefix_tags,
                'count': len(prefix_tags),
                'total_frequency': total_freq,
                'examples': prefix_tags[:5],
                'avg_frequency': total_freq / len(prefix_tags)
            }
    
    # Analyze modifiers separately
    common_modifiers = ['atmospheric', 'technical', 'progressive', 'melodic', 'experimental', 'instrumental']
    for modifier in common_modifiers:
        modifier_tags = [tag for tag in data['tag_frequencies'] if modifier.lower() in tag.lower()]
        if modifier_tags:
            total_freq = sum(data['tag_frequencies'][tag] for tag in modifier_tags)
            modifier_usage[modifier] = {
                'tags': modifier_tags,
                'count': len(modifier_tags),
                'total_frequency': total_freq,
                'examples': modifier_tags[:5],
                'avg_frequency': total_freq / len(modifier_tags)
            }
    
    detailed_analysis['prefix_analysis'] = prefix_usage
    detailed_analysis['modifier_analysis'] = modifier_usage
    
    # Generate specific examples
    consolidation_groups = consolidation_report.get('consolidation_groups', [])
    detailed_analysis['consolidation_examples'] = consolidation_groups[:20]  # Top 20 examples
    
    # Enhanced recommendations based on new strategies
    recommendations = _generate_enhanced_recommendations(
        consolidation_report, data, prefix_usage, modifier_usage
    )
    detailed_analysis['recommendations'] = recommendations
    
    # Strategy effectiveness analysis
    if 'improvement_metrics' in consolidation_report:
        detailed_analysis['strategy_effectiveness'] = _analyze_strategy_effectiveness(
            consolidation_report['improvement_metrics'], data
        )
    
    return detailed_analysis

def _generate_enhanced_recommendations(consolidation_report: Dict[str, Any], data: Dict[str, Any], 
                                     prefix_usage: Dict, modifier_usage: Dict) -> List[Dict[str, Any]]:
    """Generate enhanced recommendations based on the four improvement strategies"""
    
    recommendations = []
    
    # Strategy 1: Modifier Decomposition Recommendations
    if modifier_usage:
        total_modifier_tags = sum(m['count'] for m in modifier_usage.values())
        total_modifier_freq = sum(m['total_frequency'] for m in modifier_usage.values())
        
        recommendations.append({
            'type': 'modifier_decomposition',
            'strategy_number': 1,
            'description': f"Implement modifier decomposition for {total_modifier_tags} tags with modifiers",
            'impact': f"Could create atomic tags from {total_modifier_freq:,} tag instances",
            'benefit': "Enables flexible querying (e.g., all 'atmospheric' music across genres)",
            'examples': {k: v['examples'][:3] for k, v in modifier_usage.items()},
            'implementation': "Separate modifiers like 'atmospheric', 'technical' from base genres"
        })
    
    # Strategy 2: Hierarchy Implementation Recommendations
    hierarchy_opportunities = consolidation_report.get('hierarchy_simplifications', {})
    if hierarchy_opportunities.get('count', 0) > 0:
        recommendations.append({
            'type': 'hierarchy_implementation', 
            'strategy_number': 2,
            'description': f"Apply hierarchical relationships to {hierarchy_opportunities['count']} tags",
            'impact': f"Affects {hierarchy_opportunities.get('total_frequency_affected', 0):,} tag instances",
            'benefit': "Reduces redundancy while maintaining browsability (metal → death-metal → technical-death-metal)",
            'examples': hierarchy_opportunities.get('examples', [])[:3],
            'implementation': "Remove redundant parent tags when specific child tags are present"
        })
    
    # Strategy 3: Synonym Mapping Recommendations
    synonym_opportunities = consolidation_report.get('synonym_mappings', {})
    if synonym_opportunities.get('count', 0) > 0:
        recommendations.append({
            'type': 'synonym_mapping',
            'strategy_number': 3,
            'description': f"Map {synonym_opportunities['count']} conceptually related tags",
            'impact': f"Consolidates {synonym_opportunities.get('total_frequency_affected', 0):,} tag instances",
            'benefit': "Groups related but lexically different tags (e.g., zeuhl → avant-prog)",
            'examples': synonym_opportunities.get('examples', [])[:3],
            'implementation': "Create curated mappings for semantically related tags"
        })
    
    # Strategy 4: Compound Splitting Recommendations  
    compound_opportunities = consolidation_report.get('compound_splitting', {})
    if compound_opportunities.get('split_count', 0) > 0:
        recommendations.append({
            'type': 'compound_splitting',
            'strategy_number': 4,
            'description': f"Split {compound_opportunities['split_count']} compound tags",
            'impact': f"Affects {compound_opportunities.get('total_frequency_affected', 0):,} tag instances",
            'benefit': "Preserves all genre information instead of losing it to broad categories",
            'examples': compound_opportunities.get('examples', [])[:3],
            'implementation': "Always split tags containing '/', '&', '+' into separate components"
        })
    
    # Overall Strategy Recommendations
    improvement_metrics = consolidation_report.get('improvement_metrics', {})
    if improvement_metrics:
        total_improvement = improvement_metrics.get('total_improvement', {})
        recommendations.append({
            'type': 'overall_strategy',
            'strategy_number': 'summary',
            'description': f"Combined strategies affect {total_improvement.get('tags_affected', 0)} unique tags",
            'impact': f"{total_improvement.get('percentage_of_instances', 0):.1f}% of all tag instances improved",
            'benefit': "Creates more atomic, flexible, and organized tag system",
            'next_steps': [
                "Implement modifier separation for flexible querying",
                "Apply hierarchical organization to reduce redundancy", 
                "Add semantic relationships between related tags",
                "Split compound tags to preserve all information"
            ]
        })
    
    # High-impact consolidations (existing logic)
    consolidation_groups = consolidation_report.get('consolidation_groups', [])
    high_impact = [g for g in consolidation_groups if g['consolidation_count'] > 3 or g['total_frequency'] > 100]
    if high_impact:
        recommendations.append({
            'type': 'high_impact_consolidation',
            'description': f"Found {len(high_impact)} high-impact consolidation opportunities",
            'examples': [{'canonical': g['canonical_form'], 'variants': g['original_tags'][:3]} for g in high_impact[:5]]
        })
    
    # Prefix separation recommendations (enhanced)
    if prefix_usage:
        total_prefix_freq = sum(p['total_frequency'] for p in prefix_usage.values())
        recommendations.append({
            'type': 'prefix_separation',
            'description': f"Found {len(prefix_usage)} prefixes that can be systematically separated",
            'impact': f"Could organize {sum(p['count'] for p in prefix_usage.values())} tags with {total_prefix_freq:,} total instances",
            'benefit': "Better organization and more consistent tag structure",
            'examples': {k: {'count': v['count'], 'examples': v['examples'][:2]} for k, v in prefix_usage.items()},
            'priority': 'high' if total_prefix_freq > 1000 else 'medium'
        })
    
    return recommendations

def _analyze_strategy_effectiveness(improvement_metrics: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze how effective each of the four strategies was"""
    
    total_tags = data['total_tags']
    total_instances = data['total_instances']
    
    strategy_analysis = {}
    
    for strategy_name, metrics in improvement_metrics.get('strategy_breakdown', {}).items():
        effectiveness_score = 0
        
        tags_affected = metrics.get('tags_affected', 0)
        freq_affected = metrics.get('frequency_affected', 0)
        
        # Calculate effectiveness based on coverage and frequency impact
        tag_coverage = (tags_affected / total_tags) * 100 if total_tags > 0 else 0
        freq_coverage = (freq_affected / total_instances) * 100 if total_instances > 0 else 0
        
        # Effectiveness score combines coverage and impact
        effectiveness_score = (tag_coverage + freq_coverage) / 2
        
        strategy_analysis[strategy_name] = {
            'tags_affected': tags_affected,
            'frequency_affected': freq_affected,
            'tag_coverage_percent': tag_coverage,
            'frequency_coverage_percent': freq_coverage,
            'effectiveness_score': effectiveness_score,
            'priority': 'high' if effectiveness_score > 5 else ('medium' if effectiveness_score > 1 else 'low')
        }
    
    # Rank strategies by effectiveness
    ranked_strategies = sorted(
        strategy_analysis.items(), 
        key=lambda x: x[1]['effectiveness_score'], 
        reverse=True
    )
    
    return {
        'individual_strategies': strategy_analysis,
        'ranking': [{'strategy': name, 'score': data['effectiveness_score']} for name, data in ranked_strategies],
        'most_effective': ranked_strategies[0][0] if ranked_strategies else None,
        'total_improvement': improvement_metrics.get('total_improvement', {})
    }

def save_analysis_results(results: Dict[str, Any], output_dir: str):
    """Save analysis results to files"""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed JSON report
    json_file = output_path / f"enhanced_tag_analysis_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Detailed analysis saved to: {json_file}")
    
    # Save consolidation groups CSV
    if 'consolidation_report' in results and 'consolidation_groups' in results['consolidation_report']:
        csv_file = output_path / f"consolidation_groups_{timestamp}.csv"
        groups_df = pd.DataFrame(results['consolidation_report']['consolidation_groups'])
        if not groups_df.empty:
            groups_df.to_csv(csv_file, index=False)
            print(f"Consolidation groups saved to: {csv_file}")
    
    # Save summary report
    summary_file = output_path / f"consolidation_summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        write_summary_report(results, f)
    
    print(f"Summary report saved to: {summary_file}")

def write_summary_report(results: Dict[str, Any], file):
    """Write a human-readable summary report with improvement strategy details"""
    
    file.write("ENHANCED TAG ANALYSIS SUMMARY WITH IMPROVEMENT STRATEGIES\\n")
    file.write("=" * 70 + "\\n\\n")
    file.write(f"Analysis timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
    file.write(f"Strategy applied: {results.get('strategy', 'balanced').upper()}\\n\\n")
    
    # Input summary
    input_summary = results['detailed_analysis']['input_summary']
    file.write("INPUT SUMMARY:\\n")
    file.write(f"  Total original tags: {input_summary['total_original_tags']:,}\\n")
    file.write(f"  Total tag instances: {input_summary['total_instances']:,}\\n")
    file.write(f"  Average frequency: {input_summary['average_frequency']:.2f}\\n\\n")
    
    # Consolidation impact
    consolidation = results['detailed_analysis']['consolidation_summary']
    file.write("CONSOLIDATION IMPACT:\\n")
    file.write(f"  Unique canonical forms: {consolidation['unique_canonical_forms']:,}\\n")
    file.write(f"  Reduction count: {consolidation['reduction_count']:,}\\n")
    file.write(f"  Reduction percentage: {consolidation['reduction_percentage']:.1f}%\\n\\n")
    
    # NEW: Improvement Strategies Analysis
    if 'improvement_strategies' in results['detailed_analysis']:
        strategies = results['detailed_analysis']['improvement_strategies']
        file.write("IMPROVEMENT STRATEGIES EFFECTIVENESS:\\n")
        file.write("-" * 50 + "\\n")
        
        strategy_names = {
            'modifier_decomposition': '1. Modifier & Prefix Decomposition',
            'hierarchy_simplification': '2. Multi-level Genre Hierarchy',
            'synonym_mapping': '3. Advanced Synonym Mapping',
            'compound_splitting': '4. Compound Tag Splitting'
        }
        
        if 'strategy_breakdown' in strategies:
            for strategy_key, strategy_data in strategies['strategy_breakdown'].items():
                strategy_name = strategy_names.get(strategy_key, strategy_key.title())
                file.write(f"  {strategy_name}:\\n")
                file.write(f"    Tags affected: {strategy_data['tags_affected']:,}\\n")
                file.write(f"    Instances affected: {strategy_data['frequency_affected']:,}\\n\\n")
        
        if 'total_improvement' in strategies:
            total = strategies['total_improvement']
            file.write(f"  TOTAL IMPROVEMENT ACROSS ALL STRATEGIES:\\n")
            file.write(f"    Total tags affected: {total['tags_affected']:,}\\n")
            file.write(f"    Total instances affected: {total['frequency_affected']:,}\\n")
            file.write(f"    Percentage of tags improved: {total['percentage_of_tags']:.1f}%\\n")
            file.write(f"    Percentage of instances improved: {total['percentage_of_instances']:.1f}%\\n\\n")
    
    # Strategy effectiveness ranking
    if 'strategy_effectiveness' in results['detailed_analysis']:
        effectiveness = results['detailed_analysis']['strategy_effectiveness']
        file.write("STRATEGY EFFECTIVENESS RANKING:\\n")
        file.write("-" * 40 + "\\n")
        
        for i, strategy in enumerate(effectiveness.get('ranking', []), 1):
            file.write(f"  {i}. {strategy['strategy'].replace('_', ' ').title()}: {strategy['score']:.1f} effectiveness score\\n")
        file.write("\\n")
    
    # Hierarchy breakdown
    hierarchy = results['detailed_analysis']['hierarchy_breakdown']
    file.write("HIERARCHY BREAKDOWN:\\n")
    for tag_type, data in hierarchy.items():
        if data['count'] > 0:
            file.write(f"  {tag_type.replace('_', ' ').title()}: {data['count']} components, {data['frequency']:,} instances\\n")
    file.write("\\n")
    
    # Enhanced prefix analysis
    prefixes = results['detailed_analysis']['prefix_analysis']
    if prefixes:
        file.write("PREFIX ANALYSIS:\\n")
        for prefix, data in prefixes.items():
            file.write(f"  {prefix}: {data['count']} tags, {data['total_frequency']:,} instances (avg: {data.get('avg_frequency', 0):.1f})\\n")
            file.write(f"    Examples: {', '.join(data['examples'])}\\n")
        file.write("\\n")
    
    # NEW: Modifier analysis
    modifiers = results['detailed_analysis'].get('modifier_analysis', {})
    if modifiers:
        file.write("MODIFIER ANALYSIS:\\n")
        for modifier, data in modifiers.items():
            file.write(f"  {modifier}: {data['count']} tags, {data['total_frequency']:,} instances (avg: {data.get('avg_frequency', 0):.1f})\\n")
            file.write(f"    Examples: {', '.join(data['examples'][:3])}\\n")
        file.write("\\n")
    
    # Top consolidation examples
    examples = results['detailed_analysis']['consolidation_examples'][:10]
    if examples:
        file.write("TOP CONSOLIDATION OPPORTUNITIES:\\n")
        for i, example in enumerate(examples, 1):
            file.write(f"  {i:2d}. {example['canonical_form']}: {example['total_frequency']:,} total frequency\\n")
            file.write(f"      Consolidates: {', '.join(example['original_tags'][:3])}{'...' if len(example['original_tags']) > 3 else ''}\\n")
        file.write("\\n")
    
    # Enhanced recommendations
    recommendations = results['detailed_analysis']['recommendations']
    if recommendations:
        file.write("IMPLEMENTATION RECOMMENDATIONS:\\n")
        file.write("=" * 40 + "\\n")
        
        # Group recommendations by strategy
        strategy_recs = [r for r in recommendations if 'strategy_number' in r]
        other_recs = [r for r in recommendations if 'strategy_number' not in r]
        
        if strategy_recs:
            file.write("\\nSTRATEGY-BASED RECOMMENDATIONS:\\n")
            for rec in sorted(strategy_recs, key=lambda x: str(x.get('strategy_number', 'z'))):
                if rec.get('strategy_number') != 'summary':
                    file.write(f"\\nStrategy {rec['strategy_number']}: {rec['type'].replace('_', ' ').title()}\\n")
                    file.write(f"  Description: {rec['description']}\\n")
                    file.write(f"  Impact: {rec['impact']}\\n")
                    file.write(f"  Benefit: {rec['benefit']}\\n")
                    file.write(f"  Implementation: {rec['implementation']}\\n")
                else:
                    file.write(f"\\nOVERALL STRATEGY SUMMARY:\\n")
                    file.write(f"  {rec['description']}\\n")
                    file.write(f"  Impact: {rec['impact']}\\n")
                    file.write(f"  Next steps:\\n")
                    for step in rec.get('next_steps', []):
                        file.write(f"    • {step}\\n")
        
        if other_recs:
            file.write(f"\\nADDITIONAL RECOMMENDATIONS:\\n")
            for rec in other_recs:
                file.write(f"  • {rec['type'].replace('_', ' ').title()}: {rec['description']}\\n")
        file.write("\\n")

def print_interactive_summary(results: Dict[str, Any]):
    """Print an enhanced interactive summary to console"""
    
    print("\\n" + "=" * 80)
    print("ENHANCED TAG ANALYSIS RESULTS - WITH IMPROVEMENT STRATEGIES")
    print("=" * 80)
    
    input_summary = results['detailed_analysis']['input_summary']
    consolidation = results['detailed_analysis']['consolidation_summary']
    
    print(f"\\n📊 INPUT ANALYSIS:")
    print(f"   Original tags: {input_summary['total_original_tags']:,}")
    print(f"   Total instances: {input_summary['total_instances']:,}")
    print(f"   Average frequency: {input_summary['average_frequency']:.2f}")
    
    print(f"\\n🔧 CONSOLIDATION IMPACT:")
    print(f"   Reduced to: {consolidation['unique_canonical_forms']:,} canonical forms")
    print(f"   Tags saved: {consolidation['reduction_count']:,}")
    print(f"   Reduction: {consolidation['reduction_percentage']:.1f}%")
    
    # NEW: Show improvement strategies impact
    if 'improvement_strategies' in results['detailed_analysis']:
        strategies = results['detailed_analysis']['improvement_strategies']
        print(f"\\n🚀 IMPROVEMENT STRATEGIES IMPACT:")
        
        if 'total_improvement' in strategies:
            total = strategies['total_improvement']
            print(f"   Total tags enhanced: {total['tags_affected']:,}")
            print(f"   Total instances enhanced: {total['frequency_affected']:,}")
            print(f"   Coverage: {total['percentage_of_instances']:.1f}% of all tag instances")
        
        # Show individual strategy effectiveness
        if 'strategy_breakdown' in strategies:
            print(f"\\n   Strategy breakdown:")
            strategy_names = {
                'modifier_decomposition': 'Modifier Decomposition',
                'hierarchy_simplification': 'Hierarchy Simplification', 
                'synonym_mapping': 'Synonym Mapping',
                'compound_splitting': 'Compound Splitting'
            }
            
            for strategy_key, strategy_data in strategies['strategy_breakdown'].items():
                name = strategy_names.get(strategy_key, strategy_key.title())
                print(f"     {name}: {strategy_data['tags_affected']} tags, {strategy_data['frequency_affected']:,} instances")
    
    # Show strategy effectiveness ranking
    if 'strategy_effectiveness' in results['detailed_analysis']:
        effectiveness = results['detailed_analysis']['strategy_effectiveness']
        if effectiveness.get('ranking'):
            print(f"\\n🏆 MOST EFFECTIVE STRATEGY:")
            top_strategy = effectiveness['ranking'][0]
            print(f"   {top_strategy['strategy'].replace('_', ' ').title()} (score: {top_strategy['score']:.1f})")
    
    # Show hierarchy breakdown
    hierarchy = results['detailed_analysis']['hierarchy_breakdown']
    print(f"\\n🏗️  HIERARCHY BREAKDOWN:")
    for tag_type, data in hierarchy.items():
        if data['count'] > 0:
            print(f"   {tag_type.replace('_', ' ').title()}: {data['count']} components")
    
    # Show modifier opportunities
    modifiers = results['detailed_analysis'].get('modifier_analysis', {})
    if modifiers:
        print(f"\\n🎯 MODIFIER DECOMPOSITION OPPORTUNITIES:")
        for modifier, data in list(modifiers.items())[:5]:
            print(f"   {modifier}: {data['count']} tags ({data['total_frequency']:,} instances)")
    
    # Show prefix analysis
    prefixes = results['detailed_analysis']['prefix_analysis']
    if prefixes:
        print(f"\\n🏷️  PREFIX SEPARATION OPPORTUNITIES:")
        for prefix, data in list(prefixes.items())[:5]:
            print(f"   {prefix}: {data['count']} tags ({data['total_frequency']:,} instances)")
    
    # Show top consolidations
    examples = results['detailed_analysis']['consolidation_examples'][:5]
    if examples:
        print(f"\\n⭐ TOP CONSOLIDATIONS:")
        for example in examples:
            print(f"   {example['canonical_form']} ← {len(example['original_tags'])} variants ({example['total_frequency']:,} total)")
    
    # Show strategy-based recommendations
    strategy_recs = [r for r in results['detailed_analysis']['recommendations'] if 'strategy_number' in r and r.get('strategy_number') != 'summary']
    if strategy_recs:
        print(f"\\n💡 STRATEGY RECOMMENDATIONS:")
        for rec in sorted(strategy_recs, key=lambda x: x.get('strategy_number', 0)):
            print(f"   Strategy {rec['strategy_number']}: {rec['description']}")
    
    print(f"\\n✨ NEXT STEPS:")
    print(f"   1. Review the detailed analysis files for complete insights")
    print(f"   2. Prioritize implementing the most effective strategies first")
    print(f"   3. Consider applying strategies incrementally to validate results")
    print(f"   4. Monitor impact on search and browsing capabilities")

def main():
    parser = argparse.ArgumentParser(description="Enhanced Tag Analysis and Consolidation with Improvement Strategies")
    parser.add_argument("--base-path", default=".", help="Base path to the project directory")
    parser.add_argument("--strategy", choices=["aggressive", "conservative", "balanced", "hierarchical"], 
                       default="balanced", help="Consolidation strategy")
    parser.add_argument("--output-dir", default="./enhanced_tag_analysis", help="Output directory for results")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")
    parser.add_argument("--test-strategies", action="store_true", help="Run a test of improvement strategies on sample data")
    parser.add_argument("--show-examples", action="store_true", help="Show detailed examples of each improvement strategy")
    
    args = parser.parse_args()
    
    try:
        # Test mode for validating strategies
        if args.test_strategies:
            return run_strategy_test()
        
        # Load existing tag analysis data
        print("Loading existing tag analysis data...")
        data = load_tag_analysis_data(args.base_path)
        
        if args.show_examples:
            show_strategy_examples(data)
            return 0
        
        # Analyze with enhanced hierarchy
        consolidation_report = analyze_with_enhanced_hierarchy(data, args.strategy)
        
        # Generate detailed analysis
        detailed_analysis = generate_detailed_analysis(data, consolidation_report)
        
        # Combine results
        results = {
            'strategy': args.strategy,
            'timestamp': datetime.now().isoformat(),
            'input_data': {
                'total_tags': data['total_tags'],
                'total_instances': data['total_instances']
            },
            'consolidation_report': consolidation_report,
            'detailed_analysis': detailed_analysis
        }
        
        # Save results
        save_analysis_results(results, args.output_dir)
        
        # Print summary
        if not args.quiet:
            print_interactive_summary(results)
        
        print(f"\\n✅ Enhanced tag analysis complete!")
        print(f"   Results saved to: {args.output_dir}")
        print(f"   🚀 Applied {len([r for r in detailed_analysis.get('recommendations', []) if 'strategy_number' in r])} improvement strategies")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def run_strategy_test() -> int:
    """Run a test of the improvement strategies on sample data"""
    
    print("🧪 TESTING IMPROVEMENT STRATEGIES")
    print("=" * 50)
    
    # Sample test data representing common tag patterns
    test_data = {
        'tag_frequencies': {
            # Strategy 1: Modifier decomposition examples
            'Instrumental Post-Rock': 45,
            'Atmospheric Black Metal': 67,
            'Technical Death Metal': 89,
            'Progressive Metalcore': 34,
            'Melodic Hardcore': 23,
            'Experimental Electronic': 56,
            
            # Strategy 2: Hierarchy examples  
            'Progressive Metal, Metal': 12,
            'Death Metal, Metal, Heavy Metal': 8,
            'Post-Rock, Rock': 15,
            'Black Metal, Extreme Metal, Metal': 6,
            
            # Strategy 3: Synonym examples
            'Zeuhl': 15,
            'Heavy-Psych': 23,
            'Shoegaze': 34,
            'Krautrock': 18,
            'Math-Rock': 27,
            'Singer-Songwriter': 45,
            
            # Strategy 4: Compound splitting examples
            'Death Metal/Heavy Metal/OSDM': 12,
            'Progressive Rock/Art Rock': 18,
            'Black Metal & Atmospheric': 9,
            'Post-Punk + New Wave': 14,
            'Folk[Acoustic][Singer-Songwriter]': 7,
            'Doom Metal (Stoner)': 11,
        },
        'total_tags': 16,
        'total_instances': 562
    }
    
    print(f"📊 Test data: {test_data['total_tags']} unique tags, {test_data['total_instances']} total instances\\n")
    
    # Test each strategy
    test_results = {}
    
    for strategy in ['conservative', 'balanced', 'aggressive']:
        print(f"Testing {strategy.upper()} strategy...")
        
        # Create mock analyzer
        analyzer = MockAnalyzer(test_data['tag_frequencies'])
        
        # Run consolidation
        from albumexplore.tags.consolidation.enhanced_tag_consolidator import EnhancedTagConsolidator, ConsolidationStrategy
        strategy_enum = ConsolidationStrategy(strategy)
        consolidator = EnhancedTagConsolidator(analyzer, strategy_enum)
        
        # Apply improvements
        consolidator = apply_improvement_strategies(consolidator, test_data)
        
        # Get results
        all_tags = list(test_data['tag_frequencies'].keys())
        report = consolidator.consolidate_tag_collection(all_tags)
        
        test_results[strategy] = report
        
        print(f"  Reduction: {report['mapping_stats']['reduction_percentage']:.1f}%")
        print(f"  Canonical forms: {report['mapping_stats']['unique_canonical_forms']}")
        print()
    
    # Show best strategy
    best_strategy = max(test_results.items(), key=lambda x: x[1]['mapping_stats']['reduction_percentage'])
    print(f"🏆 Best performing strategy: {best_strategy[0].upper()}")
    print(f"   Achieved {best_strategy[1]['mapping_stats']['reduction_percentage']:.1f}% reduction")
    
    print("\\n✅ Strategy testing complete!")
    return 0

def show_strategy_examples(data: Dict[str, Any]) -> None:
    """Show examples of how each improvement strategy would work"""
    
    print("\\n🎯 IMPROVEMENT STRATEGY EXAMPLES")
    print("=" * 60)
    
    # Find examples for each strategy from actual data
    tags = list(data['tag_frequencies'].keys())
    
    # Strategy 1: Modifier decomposition
    print("\\n1️⃣  MODIFIER & PREFIX DECOMPOSITION:")
    print("   Separates descriptive modifiers from base genres for flexible querying")
    print("   Examples from your data:")
    
    modifier_examples = []
    for tag in tags:
        tag_lower = tag.lower()
        if any(mod in tag_lower for mod in ['instrumental', 'atmospheric', 'technical', 'progressive', 'melodic']):
            modifier_examples.append(tag)
            if len(modifier_examples) >= 3:
                break
    
    for example in modifier_examples:
        for modifier in ['instrumental', 'atmospheric', 'technical', 'progressive', 'melodic']:
            if modifier in example.lower():
                base_genre = example.lower().replace(modifier, '').strip()
                print(f"     '{example}' → '{modifier}' + '{base_genre}'")
                break
    
    # Strategy 2: Hierarchy
    print("\\n2️⃣  MULTI-LEVEL GENRE HIERARCHY:")
    print("   Removes redundant parent tags when specific child tags are present")
    print("   Examples from your data:")
    
    hierarchy_examples = []
    for tag in tags:
        if ('metal' in tag.lower() and any(sub in tag.lower() for sub in ['death', 'black', 'doom', 'power', 'progressive'])):
            hierarchy_examples.append(tag)
            if len(hierarchy_examples) >= 3:
                break
    
    for example in hierarchy_examples[:3]:
        if 'death metal' in example.lower() and 'metal' in example.lower():
            print(f"     '{example}' → 'death-metal' (remove redundant 'metal')")
        elif 'progressive metal' in example.lower():
            print(f"     '{example}' → 'progressive-metal' (remove redundant 'metal')")
    
    # Strategy 3: Synonyms
    print("\\n3️⃣  ADVANCED SYNONYM MAPPING:")
    print("   Maps conceptually related but lexically different tags")
    print("   Examples from your data:")
    
    synonym_map = {
        'zeuhl': 'avant-prog',
        'heavy-psych': 'psychedelic-rock', 
        'shoegaze': 'dream-pop',
        'krautrock': 'experimental-rock',
        'math-rock': 'experimental-rock'
    }
    
    for tag in tags:
        tag_lower = tag.lower().replace(' ', '-')
        if tag_lower in synonym_map:
            print(f"     '{tag}' → '{synonym_map[tag_lower]}' (semantic relationship)")
    
    # Strategy 4: Compound splitting
    print("\\n4️⃣  COMPOUND TAG SPLITTING:")
    print("   Splits compound tags to preserve all genre information")
    print("   Examples from your data:")
    
    compound_examples = []
    for tag in tags:
        if any(sep in tag for sep in ['/', '&', '+', '(', '[']):
            compound_examples.append(tag)
            if len(compound_examples) >= 3:
                break
    
    for example in compound_examples:
        if '/' in example:
            parts = [p.strip() for p in example.split('/')]
            print(f"     '{example}' → {parts} (separate tags)")
        elif '&' in example:
            parts = [p.strip() for p in example.split('&')]
            print(f"     '{example}' → {parts} (separate tags)")
    
    print(f"\\n💡 These strategies can be applied to your {data['total_tags']} unique tags")
    print("   Run the full analysis to see complete impact assessment!")

if __name__ == "__main__":
    sys.exit(main())
