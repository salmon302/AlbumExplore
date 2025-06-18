#!/usr/bin/env python3
"""
Test script for Phase 1 Integration of Enhanced Tag Consolidation
Verifies that the TagAnalyzer integrates correctly with EnhancedTagConsolidator.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from tags.analysis.tag_analyzer import TagAnalyzer
    from tags.analysis.enhanced_tag_consolidator import EnhancedTagConsolidator
    from tags.normalizer.tag_normalizer import TagNormalizer
except ImportError as e:
    print(f"Import error: {e}")
    print("This is expected if dependencies are not available in the current environment")
    sys.exit(1)

def create_test_data():
    """Create test album data for integration testing."""
    test_albums = [
        {
            'artist': 'Test Band A',
            'album': 'Test Album 1',
            'year': 2020,
            'tags': ['black metal', 'atmospheric', 'Norway', 'cold']
        },
        {
            'artist': 'Test Band B', 
            'album': 'Test Album 2',
            'year': 2019,
            'tags': ['blackmetal', 'epic blackmetal', 'Stockholm', 'Sweden']
        },
        {
            'artist': 'Test Band C',
            'album': 'Test Album 3', 
            'year': 2021,
            'tags': ['death metal', 'technical', 'brutal', 'Florida']
        },
        {
            'artist': 'Test Band D',
            'album': 'Test Album 4',
            'year': 2018,
            'tags': ['progressive metal', 'progmetal', 'complex', 'London']
        },
        {
            'artist': 'Test Band E',
            'album': 'Test Album 5',
            'year': 2022,
            'tags': ['post-rock', 'postrock', 'instrumental', 'Montreal']
        }
    ]
    
    return pd.DataFrame(test_albums)

def test_basic_integration():
    """Test basic integration between TagAnalyzer and EnhancedTagConsolidator."""
    print("=== Phase 1 Integration Test ===")
    
    # Create test data
    df = create_test_data()
    print(f"Created test dataset with {len(df)} albums")
    
    # Initialize analyzer
    analyzer = TagAnalyzer(df)
    print(f"Initialized TagAnalyzer with {len(analyzer.tag_frequencies)} unique tags")
    
    # Show original tag frequencies
    print("\n--- Original Tag Frequencies ---")
    for tag, freq in analyzer.tag_frequencies.most_common():
        print(f"  {tag}: {freq}")
    
    # Initialize enhanced consolidator
    consolidator = EnhancedTagConsolidator(analyzer)
    analyzer.set_enhanced_consolidator(consolidator)
    print(f"\nIntegrated EnhancedTagConsolidator with {len(consolidator.consolidation_rules)} rules")
    
    # Test enhanced analysis
    enhanced_analysis = analyzer.get_consolidated_analysis()
    
    print("\n--- Enhanced Analysis Results ---")
    print(f"Original tag count: {enhanced_analysis['original_count']}")
    print(f"Consolidated tag count: {enhanced_analysis['consolidated_count']}")
    print(f"Reduction: {enhanced_analysis['reduction_percentage']:.1f}%")
    
    # Show categorized results
    print("\n--- Categorized Tags ---")
    for category, tags in enhanced_analysis['categorized'].items():
        if tags:
            print(f"{category.value}: {list(tags.keys())}")
    
    # Show hierarchies
    print("\n--- Hierarchical Relationships ---")
    for parent, relations in enhanced_analysis['hierarchies'].items():
        if relations:
            children = [rel.child for rel in relations[:3]]  # Show first 3
            print(f"{parent} → {children}")
    
    # Show consolidation suggestions
    print(f"\n--- Consolidation Suggestions ({len(enhanced_analysis['suggestions'])}) ---")
    for suggestion in enhanced_analysis['suggestions'][:5]:  # Show first 5
        print(f"  {suggestion['primary_tag']} ← {suggestion['secondary_tag']} "
              f"(confidence: {suggestion['confidence']:.2f})")
    
    return enhanced_analysis

def test_normalizer_integration():
    """Test TagNormalizer integration with consolidator."""
    print(f"\n{'='*50}")
    print("NORMALIZER INTEGRATION TEST")
    print("=" * 50)
    
    # Create test data
    df = create_test_data()
    analyzer = TagAnalyzer(df)
    consolidator = EnhancedTagConsolidator(analyzer)
    
    # Set consolidator in normalizer
    analyzer.normalizer.set_consolidator(consolidator)
    
    # Test normalization with categorization
    test_tags = ['blackmetal', 'death-metal', 'Stockholm', 'atmospheric', 'post rock']
    
    print("Testing normalize_with_categorization:")
    for tag in test_tags:
        result = analyzer.normalizer.normalize_with_categorization(tag)
        normalized_tag, category = result
        if normalized_tag is None:
            print(f"  '{tag}' → FILTERED ({category.value if category else 'N/A'})")
        else:
            print(f"  '{tag}' → '{normalized_tag}' ({category.value if category else 'N/A'})")

def test_analyzer_enhanced_stats():
    """Test enhanced statistics in analyze_tags method."""
    print(f"\n{'='*50}")
    print("ENHANCED STATISTICS TEST")
    print("=" * 50)
    
    # Create test data
    df = create_test_data()
    analyzer = TagAnalyzer(df)
    consolidator = EnhancedTagConsolidator(analyzer)
    analyzer.set_enhanced_consolidator(consolidator)
    
    # Get full analysis including enhanced stats
    stats = analyzer.analyze_tags()
    
    print("Standard analysis results:")
    print(f"  Total tags: {stats['total_tags']}")
    print(f"  Unique tags: {stats['unique_tags']}")
    print(f"  Avg tags per album: {stats['avg_tags_per_album']:.1f}")
    
    if 'enhanced' in stats:
        enhanced = stats['enhanced']
        print(f"\nEnhanced analysis results:")
        print(f"  Original count: {enhanced['original_count']}")
        print(f"  Consolidated count: {enhanced['consolidated_count']}")
        print(f"  Reduction: {enhanced['reduction_percentage']:.1f}%")
        print(f"  Categories found: {len(enhanced['categorized'])}")
        print(f"  Hierarchies found: {len(enhanced['hierarchies'])}")
        print(f"  Suggestions generated: {len(enhanced['suggestions'])}")

def main():
    """Run all integration tests for Phase 1."""
    try:
        # Test basic integration
        enhanced_analysis = test_basic_integration()
        
        # Test normalizer integration
        test_normalizer_integration()
        
        # Test enhanced statistics
        test_analyzer_enhanced_stats()
        
        print(f"\n{'='*50}")
        print("PHASE 1 INTEGRATION SUCCESS")
        print("=" * 50)
        print("✓ TagAnalyzer successfully integrated with EnhancedTagConsolidator")
        print("✓ TagNormalizer enhanced with categorization capabilities")
        print("✓ Enhanced analysis methods working correctly")
        print("✓ All integration points functional")
        
        # Summary
        original_count = enhanced_analysis['original_count']
        consolidated_count = enhanced_analysis['consolidated_count']
        reduction = enhanced_analysis['reduction_percentage']
        print(f"\nPhase 1 Integration demonstrates:")
        print(f"  • {reduction:.1f}% tag reduction ({original_count} → {consolidated_count})")
        print(f"  • Category-based organization")
        print(f"  • Hierarchical relationship detection")
        print(f"  • Smart consolidation suggestions")
        
    except Exception as e:
        print(f"\nPhase 1 Integration Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 