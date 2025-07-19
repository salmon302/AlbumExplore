"""
Enhanced Tag Consolidator using Hierarchical Tag System

This consolidator integrates with the enhanced tag hierarchy to:
1. Minimize tag quantity through proper categorization
2. Separate prefixes (post-, neo-, proto-, etc.)
3. Organize tags into hierarchical structures
4. Apply intelligent consolidation rules
5. Maintain tag relationships and meanings
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import logging
from collections import defaultdict, Counter

from ..hierarchy.enhanced_tag_hierarchy import EnhancedTagHierarchy, TagType, TagComponent, HierarchicalTag
from ..analysis.tag_analyzer import TagAnalyzer

logger = logging.getLogger(__name__)

class ConsolidationStrategy(Enum):
    """Different strategies for tag consolidation"""
    AGGRESSIVE = "aggressive"  # Maximum consolidation, some meaning loss acceptable
    CONSERVATIVE = "conservative"  # Preserve meaning, minimal consolidation
    BALANCED = "balanced"  # Balance between consolidation and meaning preservation
    HIERARCHICAL = "hierarchical"  # Focus on building proper hierarchies

@dataclass
class ConsolidationRule:
    """Enhanced consolidation rule with hierarchy awareness"""
    pattern: str
    replacement: Optional[str] = None
    action: str = "merge"  # merge, split, decompose, filter
    primary_tag: Optional[str] = None
    category: Optional[TagType] = None
    confidence: float = 1.0
    filter_out: bool = False
    preserve_components: bool = True
    reason: str = ""

@dataclass
class ConsolidationResult:
    """Result of tag consolidation analysis"""
    original_tag: str
    canonical_form: str
    action_taken: str
    components: List[TagComponent] = field(default_factory=list)
    merged_with: Set[str] = field(default_factory=set)
    confidence: float = 1.0
    reason: str = ""
    hierarchy_impact: Dict[str, Any] = field(default_factory=dict)

class EnhancedTagConsolidator:
    """Enhanced tag consolidator with hierarchical organization"""
    
    def __init__(self, analyzer: TagAnalyzer, strategy: ConsolidationStrategy = ConsolidationStrategy.BALANCED):
        self.analyzer = analyzer
        self.strategy = strategy
        self.hierarchy = EnhancedTagHierarchy()
        
        # Consolidation tracking
        self.consolidation_rules: List[ConsolidationRule] = []
        self.consolidation_results: Dict[str, ConsolidationResult] = {}
        self.tag_mappings: Dict[str, str] = {}  # original -> canonical
        self.reverse_mappings: Dict[str, Set[str]] = defaultdict(set)  # canonical -> originals
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'consolidated': 0,
            'decomposed': 0,
            'filtered': 0,
            'preserved': 0
        }
        
        self._initialize_consolidation_rules()
    
    def _initialize_consolidation_rules(self):
        """Initialize consolidation rules based on strategy and hierarchy"""
        
        # Core prefix separation rules
        prefix_rules = self._create_prefix_separation_rules()
        self.consolidation_rules.extend(prefix_rules)
        
        # Redundant modifier rules
        redundancy_rules = self._create_redundancy_rules()
        self.consolidation_rules.extend(redundancy_rules)
        
        # Genre consolidation rules
        genre_rules = self._create_genre_consolidation_rules()
        self.consolidation_rules.extend(genre_rules)
        
        # Strategy-specific rules
        if self.strategy == ConsolidationStrategy.AGGRESSIVE:
            self.consolidation_rules.extend(self._create_aggressive_rules())
        elif self.strategy == ConsolidationStrategy.CONSERVATIVE:
            self.consolidation_rules.extend(self._create_conservative_rules())
        elif self.strategy == ConsolidationStrategy.HIERARCHICAL:
            self.consolidation_rules.extend(self._create_hierarchical_rules())
        
        logger.info(f"Initialized {len(self.consolidation_rules)} consolidation rules")
    
    def _create_prefix_separation_rules(self) -> List[ConsolidationRule]:
        """Create rules for separating prefixes from compound terms"""
        rules = []
        
        for prefix, data in self.hierarchy.separable_prefixes.items():
            for example in data['examples']:
                # Rule for compound form (e.g., "postmetal" -> "post-metal")
                compound_form = example.replace('-', '')
                rules.append(ConsolidationRule(
                    pattern=f"^{compound_form}$",
                    replacement=example,
                    action="split",
                    confidence=0.95,
                    reason=f"Separate {prefix} prefix for better hierarchy"
                ))
                
                # Rule for space-separated form (e.g., "post metal" -> "post-metal")
                space_form = example.replace('-', ' ')
                rules.append(ConsolidationRule(
                    pattern=f"^{re.escape(space_form)}$",
                    replacement=example,
                    action="merge",
                    confidence=0.90,
                    reason=f"Standardize {prefix} prefix format"
                ))
        
        return rules
    
    def _create_redundancy_rules(self) -> List[ConsolidationRule]:
        """Create rules for removing redundant modifiers"""
        rules = []
        
        # Common redundancies
        redundant_patterns = [
            # Progressive variations
            (r"\\bprog\\b.*\\bprogressive\\b", "progressive", "Remove redundant 'prog' when 'progressive' is present"),
            (r"\\bprogressive\\b.*\\bprog\\b", "progressive", "Remove redundant 'prog' when 'progressive' is present"),
            
            # Technical variations
            (r"\\btech\\b.*\\btechnical\\b", "technical", "Remove redundant 'tech' when 'technical' is present"),
            (r"\\btechnical\\b.*\\btech\\b", "technical", "Remove redundant 'tech' when 'technical' is present"),
            
            # Metal redundancies
            (r"heavy metal", "metal", "Remove redundant 'heavy' modifier"),
            (r"metal music", "metal", "Remove redundant 'music' suffix"),
            
            # Rock redundancies
            (r"rock music", "rock", "Remove redundant 'music' suffix"),
            
            # Double modifiers
            (r"atmospheric ambient", "atmospheric", "Remove redundant double atmospheric modifier"),
            (r"melodic melody", "melodic", "Remove redundant double melodic modifier"),
        ]
        
        for pattern, replacement, reason in redundant_patterns:
            rules.append(ConsolidationRule(
                pattern=pattern,
                replacement=replacement,
                action="merge",
                confidence=0.8,
                reason=reason
            ))
        
        return rules
    
    def _create_genre_consolidation_rules(self) -> List[ConsolidationRule]:
        """Create rules for genre-specific consolidations"""
        rules = []
        
        # Core genre variations
        genre_variations = {
            'progressive-metal': ['prog-metal', 'progmetal', 'prog metal'],
            'progressive-rock': ['prog-rock', 'progrock', 'prog rock'],
            'death-metal': ['deathmetal', 'death metal'],
            'black-metal': ['blackmetal', 'black metal'],
            'doom-metal': ['doommetal', 'doom metal'],
            'post-metal': ['postmetal', 'post metal'],
            'post-rock': ['postrock', 'post rock'],
            'post-hardcore': ['posthardcore', 'post hardcore'],
            'post-punk': ['postpunk', 'post punk'],
            'metalcore': ['metal-core', 'metal core'],
            'deathcore': ['death-core', 'death core'],
            'mathcore': ['math-core', 'math core'],
            'grindcore': ['grind-core', 'grind core'],
        }
        
        for canonical, variations in genre_variations.items():
            for variation in variations:
                rules.append(ConsolidationRule(
                    pattern=f"^{re.escape(variation)}$",
                    replacement=canonical,
                    action="merge",
                    confidence=0.95,
                    reason=f"Standardize to canonical form: {canonical}"
                ))
        
        return rules
    
    def _create_aggressive_rules(self) -> List[ConsolidationRule]:
        """Create aggressive consolidation rules"""
        rules = []
        
        # Merge similar subgenres into primary genres
        aggressive_merges = {
            'metal': ['heavy metal', 'extreme metal', 'modern metal'],
            'rock': ['hard rock', 'classic rock', 'modern rock'],
            'electronic': ['electronica', 'electronic music'],
            'ambient': ['ambient music', 'ambient electronic'],
        }
        
        for primary, subgenres in aggressive_merges.items():
            for subgenre in subgenres:
                rules.append(ConsolidationRule(
                    pattern=f"^{re.escape(subgenre)}$",
                    replacement=primary,
                    action="merge",
                    confidence=0.7,
                    reason=f"Aggressive merge into primary genre: {primary}"
                ))
        
        return rules
    
    def _create_conservative_rules(self) -> List[ConsolidationRule]:
        """Create conservative consolidation rules"""
        rules = []
        
        # Only fix obvious formatting issues
        conservative_fixes = [
            # Case standardization
            (r"(.+)", lambda m: m.group(1).lower(), "Standardize case"),
            
            # Hyphenation standardization for compound genres only
            (r"post\s+metal", "post-metal", "Standardize post-metal hyphenation"),
            (r"post\s+rock", "post-rock", "Standardize post-rock hyphenation"),
            (r"post\s+punk", "post-punk", "Standardize post-punk hyphenation"),
            (r"post\s+hardcore", "post-hardcore", "Standardize post-hardcore hyphenation"),
        ]
        
        for pattern, replacement, reason in conservative_fixes:
            rules.append(ConsolidationRule(
                pattern=pattern,
                replacement=replacement,
                action="merge",
                confidence=0.9,
                reason=reason
            ))
        
        return rules
    
    def _create_hierarchical_rules(self) -> List[ConsolidationRule]:
        """Create rules focused on building proper hierarchies"""
        rules = []
        
        # Decomposition rules for complex tags
        decomposition_patterns = [
            # Atmospheric + genre combinations
            (r"atmospheric\\s+(black|death|doom)\\s+metal", "atmospheric {1} metal", "Decompose atmospheric subgenre"),
            
            # Technical + genre combinations
            (r"technical\\s+(death|black|doom)\\s+metal", "technical {1} metal", "Decompose technical subgenre"),
            
            # Melodic + genre combinations
            (r"melodic\\s+(death|black|power)\\s+metal", "melodic {1} metal", "Decompose melodic subgenre"),
            
            # Progressive + genre combinations
            (r"progressive\\s+(metal|rock|electronic)", "progressive {1}", "Decompose progressive genre"),
        ]
        
        for pattern, replacement, reason in decomposition_patterns:
            rules.append(ConsolidationRule(
                pattern=pattern,
                replacement=replacement,
                action="decompose",
                confidence=0.85,
                preserve_components=True,
                reason=reason
            ))
        
        return rules
    
    def consolidate_tag(self, tag: str) -> ConsolidationResult:
        """
        Consolidate a single tag using hierarchy-aware rules
        """
        original_tag = tag.strip()
        
        # Get hierarchy analysis
        hierarchy_analysis = self.hierarchy.suggest_consolidation(original_tag)
        
        # Apply consolidation rules
        result = ConsolidationResult(
            original_tag=original_tag,
            canonical_form=hierarchy_analysis['canonical_form'],
            action_taken="analyze",
            components=hierarchy_analysis['components'],
            hierarchy_impact=hierarchy_analysis
        )
        
        # Check each rule
        for rule in self.consolidation_rules:
            if self._rule_matches(rule, original_tag):
                result = self._apply_rule(rule, original_tag, result)
                break
        
        # If no specific rule matched, use hierarchy suggestions
        if result.action_taken == "analyze":
            result = self._apply_hierarchy_suggestions(hierarchy_analysis, result)
        
        # Store result
        self.consolidation_results[original_tag] = result
        self.tag_mappings[original_tag] = result.canonical_form
        self.reverse_mappings[result.canonical_form].add(original_tag)
        
        # Update statistics
        self.stats['total_processed'] += 1
        if result.action_taken in ['merge', 'decompose']:
            self.stats['consolidated'] += 1
        elif result.action_taken == 'filter':
            self.stats['filtered'] += 1
        elif result.action_taken == 'decompose':
            self.stats['decomposed'] += 1
        else:
            self.stats['preserved'] += 1
        
        return result
    
    def _rule_matches(self, rule: ConsolidationRule, tag: str) -> bool:
        """Check if a rule matches a tag"""
        return bool(re.search(rule.pattern, tag, re.IGNORECASE))
    
    def _apply_rule(self, rule: ConsolidationRule, tag: str, result: ConsolidationResult) -> ConsolidationResult:
        """Apply a consolidation rule to a tag"""
        
        if rule.action == "merge" and rule.replacement:
            result.canonical_form = rule.replacement
            result.action_taken = "merge"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "split":
            # For prefix separation
            result.canonical_form = rule.replacement or tag
            result.action_taken = "split"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "decompose":
            # Break down complex tags into components
            components = self.hierarchy.decompose_tag(tag)
            result.components = components
            result.action_taken = "decompose"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "decompose_modifiers":
            # NEW: Decompose modifiers from genres
            components = self._decompose_modifiers(tag)
            result.components = components
            result.canonical_form = self._build_canonical_from_components(components)
            result.action_taken = "decompose_modifiers"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "hierarchy_simplify":
            # NEW: Simplify based on hierarchy rules
            result.canonical_form = re.sub(rule.pattern, rule.replacement or "", tag, flags=re.IGNORECASE)
            result.action_taken = "hierarchy_simplify"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "split_compound":
            # NEW: Split compound tags
            from ..hierarchy.enhanced_tag_hierarchy import TagComponent, TagType
            components = self._split_compound_tag(tag)
            result.components = [TagComponent(comp.strip(), TagType.SUBGENRE, 0.9) for comp in components if comp.strip()]
            result.canonical_form = " + ".join(components) if len(components) > 1 else (components[0] if components else tag)
            result.action_taken = "split_compound"
            result.confidence = rule.confidence
            result.reason = rule.reason
            
        elif rule.action == "filter" or rule.filter_out:
            result.action_taken = "filter"
            result.confidence = rule.confidence
            result.reason = rule.reason or "Tag filtered out by rule"
        
        return result
    
    def _decompose_modifiers(self, tag: str) -> List[TagComponent]:
        """Decompose a tag into its modifier and genre components"""
        from ..hierarchy.enhanced_tag_hierarchy import TagComponent, TagType
        
        tag_lower = tag.lower()
        components = []
        
        # Common modifiers to extract
        modifiers = ['instrumental', 'atmospheric', 'technical', 'progressive', 'melodic', 'experimental']
        
        remaining = tag_lower
        for modifier in modifiers:
            if modifier in remaining:
                components.append(TagComponent(modifier, TagType.MODIFIER, 0.8))
                remaining = remaining.replace(modifier, '').strip()
        
        # What remains should be the genre
        if remaining:
            # Clean up remaining text
            remaining = re.sub(r'\\s+', ' ', remaining).strip()
            components.append(TagComponent(remaining, TagType.SUBGENRE, 1.0))
        
        return components
    
    def _build_canonical_from_components(self, components: List[TagComponent]) -> str:
        """Build canonical form from components"""
        from ..hierarchy.enhanced_tag_hierarchy import TagType
        
        modifiers = [c.value for c in components if c.tag_type == TagType.MODIFIER]
        genres = [c.value for c in components if c.tag_type in [TagType.PRIMARY_GENRE, TagType.SUBGENRE]]
        
        # For decomposed tags, we might want to keep them separate or create a standardized form
        if modifiers and genres:
            return f"{' '.join(modifiers)} {' '.join(genres)}"
        elif modifiers:
            return ' '.join(modifiers)
        elif genres:
            return ' '.join(genres)
        else:
            return "unknown"
    
    def _split_compound_tag(self, tag: str) -> List[str]:
        """Split a compound tag into its constituent parts"""
        
        # Try different splitting patterns
        if '/' in tag:
            return [part.strip() for part in tag.split('/')]
        elif '&' in tag:
            return [part.strip() for part in tag.split('&')]
        elif '+' in tag:
            return [part.strip() for part in tag.split('+')]
        elif ',' in tag and len(tag.split(',')) == 2:  # Only simple two-part splits
            return [part.strip() for part in tag.split(',')]
        elif '[' in tag and ']' in tag:
            # Extract bracketed content
            import re
            brackets = re.findall(r'\\[([^\\]]+)\\]', tag)
            if brackets:
                return brackets
        elif '(' in tag and ')' in tag:
            # Split on parentheses
            base = tag.split('(')[0].strip()
            paren_content = re.findall(r'\\(([^)]+)\\)', tag)
            if paren_content:
                return [base] + paren_content
        
        # If no splitting pattern found, return original
        return [tag]
    
    def _apply_hierarchy_suggestions(self, hierarchy_analysis: Dict[str, Any], result: ConsolidationResult) -> ConsolidationResult:
        """Apply suggestions from hierarchy analysis"""
        
        suggestions = hierarchy_analysis.get('consolidation_suggestions', [])
        
        if not suggestions:
            result.action_taken = "preserve"
            result.reason = "No consolidation needed"
            return result
        
        # Apply the first (highest priority) suggestion
        suggestion = suggestions[0]
        
        if suggestion['type'] == 'remove_redundant_modifiers':
            # Remove redundant modifiers
            result.action_taken = "simplify"
            result.reason = suggestion['reason']
            result.confidence = 0.8
            
        elif suggestion['type'] == 'separate_prefix':
            # Separate prefix
            result.canonical_form = suggestion['canonical_form']
            result.action_taken = "separate_prefix"
            result.reason = suggestion['reason']
            result.confidence = 0.9
        
        return result
    
    def consolidate_tag_collection(self, tags: List[str]) -> Dict[str, Any]:
        """
        Consolidate an entire collection of tags
        """
        logger.info(f"Starting consolidation of {len(tags)} tags using {self.strategy.value} strategy")
        
        # Reset statistics
        self.stats = {
            'total_processed': 0,
            'consolidated': 0,
            'decomposed': 0,
            'filtered': 0,
            'preserved': 0
        }
        
        # Process each tag
        for tag in tags:
            self.consolidate_tag(tag)
        
        # Analyze the collection
        collection_analysis = self.hierarchy.analyze_tag_collection(tags)
        
        # Generate consolidation report
        report = {
            'input_stats': {
                'total_tags': len(tags),
                'unique_tags': len(set(tags))
            },
            'consolidation_stats': self.stats.copy(),
            'mapping_stats': {
                'unique_canonical_forms': len(self.reverse_mappings),
                'total_mappings': len(self.tag_mappings),
                'reduction_count': len(tags) - len(self.reverse_mappings),
                'reduction_percentage': ((len(tags) - len(self.reverse_mappings)) / len(tags) * 100) if tags else 0
            },
            'hierarchy_analysis': collection_analysis,
            'consolidation_groups': self._generate_consolidation_groups(),
            'recommendations': self._generate_recommendations()
        }
        
        logger.info(f"Consolidation complete. Reduced from {len(tags)} to {len(self.reverse_mappings)} unique forms ({report['mapping_stats']['reduction_percentage']:.1f}% reduction)")
        
        return report
    
    def _generate_consolidation_groups(self) -> List[Dict[str, Any]]:
        """Generate groups showing which tags were consolidated together"""
        groups = []
        
        for canonical, originals in self.reverse_mappings.items():
            if len(originals) > 1:
                # Calculate frequency impact
                total_frequency = 0
                original_frequencies = {}
                
                for original in originals:
                    freq = self.analyzer.tag_frequencies.get(original, 0)
                    original_frequencies[original] = freq
                    total_frequency += freq
                
                groups.append({
                    'canonical_form': canonical,
                    'original_tags': list(originals),
                    'consolidation_count': len(originals),
                    'total_frequency': total_frequency,
                    'original_frequencies': original_frequencies,
                    'primary_original': max(original_frequencies.items(), key=lambda x: x[1])[0] if original_frequencies else canonical
                })
        
        # Sort by consolidation impact (frequency * count)
        groups.sort(key=lambda x: x['total_frequency'] * x['consolidation_count'], reverse=True)
        
        return groups
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations for further improvement"""
        recommendations = []
        
        # Analyze consolidation results for patterns
        action_counts = Counter(result.action_taken for result in self.consolidation_results.values())
        
        # Recommend strategy adjustments
        if action_counts.get('preserved', 0) > action_counts.get('consolidated', 0):
            recommendations.append({
                'type': 'strategy_adjustment',
                'suggestion': 'Consider using AGGRESSIVE strategy for more consolidation',
                'current_preserved': action_counts.get('preserved', 0),
                'current_consolidated': action_counts.get('consolidated', 0)
            })
        
        # Recommend manual review for low-confidence consolidations
        low_confidence = [
            result for result in self.consolidation_results.values()
            if result.confidence < 0.7
        ]
        
        if low_confidence:
            recommendations.append({
                'type': 'manual_review',
                'suggestion': f'Review {len(low_confidence)} low-confidence consolidations',
                'tags_to_review': [result.original_tag for result in low_confidence[:10]]  # Show first 10
            })
        
        # Recommend hierarchy improvements
        hierarchy_gaps = self._identify_hierarchy_gaps()
        if hierarchy_gaps:
            recommendations.append({
                'type': 'hierarchy_improvement',
                'suggestion': 'Add missing hierarchy relationships',
                'missing_relationships': hierarchy_gaps[:5]  # Show first 5
            })
        
        return recommendations
    
    def _identify_hierarchy_gaps(self) -> List[Dict[str, str]]:
        """Identify missing relationships in the hierarchy"""
        gaps = []
        
        # Look for tags that could be children of existing tags
        for canonical in self.reverse_mappings.keys():
            components = self.hierarchy.decompose_tag(canonical)
            
            # Check if this could be a child of a simpler tag
            if len(components) > 1:
                # Try to find a parent tag
                core_components = [c for c in components if c.tag_type in [TagType.PRIMARY_GENRE, TagType.SUBGENRE]]
                if len(core_components) == 1:
                    potential_parent = core_components[0].value
                    if potential_parent in self.reverse_mappings and potential_parent != canonical:
                        gaps.append({
                            'child': canonical,
                            'potential_parent': potential_parent,
                            'relationship_type': 'subgenre'
                        })
        
        return gaps
    
    def get_consolidation_mapping(self) -> Dict[str, str]:
        """Get the mapping from original tags to consolidated forms"""
        return self.tag_mappings.copy()
    
    def get_reverse_mapping(self) -> Dict[str, Set[str]]:
        """Get the reverse mapping from consolidated forms to original tags"""
        return {k: v.copy() for k, v in self.reverse_mappings.items()}
    
    def export_consolidation_results(self, format: str = 'csv') -> str:
        """Export consolidation results in specified format"""
        
        if format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Original Tag', 'Canonical Form', 'Action Taken', 'Confidence',
                'Component Count', 'Reason', 'Frequency', 'Primary Genre'
            ])
            
            # Write data
            for original, result in self.consolidation_results.items():
                frequency = self.analyzer.tag_frequencies.get(original, 0)
                primary_genre = result.hierarchy_impact.get('primary_genre', '')
                
                writer.writerow([
                    original,
                    result.canonical_form,
                    result.action_taken,
                    result.confidence,
                    len(result.components),
                    result.reason,
                    frequency,
                    primary_genre
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

def create_enhanced_consolidator(analyzer: TagAnalyzer, strategy: str = "balanced") -> EnhancedTagConsolidator:
    """Factory function to create an enhanced consolidator"""
    strategy_enum = ConsolidationStrategy(strategy.lower())
    return EnhancedTagConsolidator(analyzer, strategy_enum)
