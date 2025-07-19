"""
Enhanced Tag Hierarchy System for Minimizing Tag Quantity through Proper Organization

This system implements a comprehensive hierarchy to organize tags into:
- Primary genres (metal, rock, electronic, etc.)
- Subgenres with relationship mapping
- Modifiers (atmospheric, technical, melodic, etc.)
- Style indicators (post-, progressive, avant-garde)
- Regional/Cultural indicators (viking, celtic, japanese)
- Proper prefix separation (post- as distinct modifier)
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from collections import defaultdict

class TagType(Enum):
    PRIMARY_GENRE = "primary_genre"
    SUBGENRE = "subgenre"
    MODIFIER = "modifier"
    STYLE_INDICATOR = "style_indicator"
    REGIONAL_CULTURAL = "regional_cultural"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    VOCAL_STYLE = "vocal_style"
    INSTRUMENTAL = "instrumental"

@dataclass
class TagComponent:
    """Represents a component of a composite tag"""
    value: str
    tag_type: TagType
    weight: float = 1.0

@dataclass
class HierarchicalTag:
    """Represents a tag with its hierarchical information"""
    name: str
    normalized_name: str
    tag_type: TagType
    primary_genre: Optional[str] = None
    components: List[TagComponent] = None
    parent_tags: Set[str] = None
    child_tags: Set[str] = None
    aliases: Set[str] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = []
        if self.parent_tags is None:
            self.parent_tags = set()
        if self.child_tags is None:
            self.child_tags = set()
        if self.aliases is None:
            self.aliases = set()

class EnhancedTagHierarchy:
    """Enhanced tag hierarchy system for comprehensive tag organization"""
    
    def __init__(self):
        # Core hierarchy definitions
        self.primary_genres = {
            'metal': {
                'subgenres': ['black metal', 'death metal', 'doom metal', 'heavy metal', 
                             'power metal', 'thrash metal', 'progressive metal'],
                'core_derivatives': ['metalcore', 'deathcore', 'grindcore']
            },
            'rock': {
                'subgenres': ['hard rock', 'progressive rock', 'psychedelic rock', 
                             'alternative rock', 'indie rock', 'art rock'],
                'punk_derivatives': ['punk rock', 'post-punk', 'hardcore punk']
            },
            'electronic': {
                'subgenres': ['ambient', 'techno', 'house', 'trance', 'drum and bass'],
                'experimental': ['idm', 'glitch', 'noise']
            },
            'jazz': {
                'subgenres': ['bebop', 'cool jazz', 'free jazz', 'fusion'],
                'fusion_types': ['jazz fusion', 'jazz rock', 'nu jazz']
            },
            'classical': {
                'subgenres': ['baroque', 'romantic', 'contemporary classical'],
                'orchestral': ['symphonic', 'chamber music', 'orchestral']
            },
            'folk': {
                'subgenres': ['traditional folk', 'contemporary folk', 'folk rock'],
                'regional': ['celtic', 'nordic', 'slavic']
            }
        }
        
        # Style modifiers that can be applied to any genre
        self.style_modifiers = {
            'atmospheric': {'weight': 0.8, 'applies_to': ['metal', 'rock', 'electronic']},
            'technical': {'weight': 0.7, 'applies_to': ['metal', 'rock', 'jazz']},
            'melodic': {'weight': 0.6, 'applies_to': ['metal', 'rock']},
            'progressive': {'weight': 0.9, 'applies_to': ['metal', 'rock', 'electronic']},
            'experimental': {'weight': 0.8, 'applies_to': ['all']},
            'ambient': {'weight': 0.7, 'applies_to': ['electronic', 'metal', 'rock']},
            'industrial': {'weight': 0.7, 'applies_to': ['metal', 'electronic']},
            'symphonic': {'weight': 0.8, 'applies_to': ['metal', 'rock', 'classical']},
            'acoustic': {'weight': 0.6, 'applies_to': ['rock', 'folk', 'metal']},
            'brutal': {'weight': 0.7, 'applies_to': ['metal']},
            'melodic': {'weight': 0.6, 'applies_to': ['metal', 'rock']},
            'dark': {'weight': 0.5, 'applies_to': ['metal', 'electronic', 'rock']},
            'epic': {'weight': 0.6, 'applies_to': ['metal', 'classical']},
            'minimal': {'weight': 0.6, 'applies_to': ['electronic', 'classical']},
            'maximal': {'weight': 0.6, 'applies_to': ['electronic', 'metal']},
            'raw': {'weight': 0.5, 'applies_to': ['metal', 'punk']}
        }
        
        # Prefixes that should be separated and treated as modifiers
        self.separable_prefixes = {
            'post': {
                'description': 'Genre evolution beyond traditional boundaries',
                'weight': 0.9,
                'examples': ['post-metal', 'post-rock', 'post-punk', 'post-hardcore']
            },
            'neo': {
                'description': 'Modern revival or reinterpretation',
                'weight': 0.7,
                'examples': ['neo-classical', 'neo-folk', 'neo-soul']
            },
            'proto': {
                'description': 'Early or foundational form',
                'weight': 0.7,
                'examples': ['proto-metal', 'proto-punk']
            },
            'avant': {
                'description': 'Experimental and forward-thinking',
                'weight': 0.8,
                'examples': ['avant-garde', 'avant-metal']
            },
            'psycho': {
                'description': 'Psychedelic influence',
                'weight': 0.6,
                'examples': ['psychobilly', 'psycho-rock']
            }
        }
        
        # Regional and cultural indicators
        self.regional_cultural = {
            'geographic': {
                'scandinavian': ['norwegian', 'swedish', 'finnish', 'danish'],
                'british': ['english', 'scottish', 'welsh', 'irish'],
                'european': ['german', 'french', 'italian', 'spanish', 'dutch'],
                'north_american': ['american', 'canadian'],
                'asian': ['japanese', 'chinese', 'korean', 'indian'],
                'other': ['australian', 'brazilian', 'mexican']
            },
            'cultural': {
                'viking': {'regions': ['scandinavian'], 'applies_to': ['metal', 'folk']},
                'celtic': {'regions': ['irish', 'scottish', 'welsh'], 'applies_to': ['folk', 'metal']},
                'slavic': {'regions': ['eastern_european'], 'applies_to': ['folk', 'metal']},
                'mediterranean': {'regions': ['italian', 'spanish', 'greek'], 'applies_to': ['folk']},
                'oriental': {'regions': ['asian'], 'applies_to': ['folk', 'electronic']},
                'tribal': {'regions': ['various'], 'applies_to': ['folk', 'electronic']},
                'medieval': {'historical': True, 'applies_to': ['folk', 'metal', 'classical']},
                'renaissance': {'historical': True, 'applies_to': ['classical', 'folk']},
                'baroque': {'historical': True, 'applies_to': ['classical']},
                'romantic': {'historical': True, 'applies_to': ['classical']}
            }
        }
        
        # Vocal style indicators
        self.vocal_styles = {
            'clean': {'description': 'Clear, melodic vocals', 'applies_to': ['all']},
            'harsh': {'description': 'Aggressive, distorted vocals', 'applies_to': ['metal', 'hardcore']},
            'growl': {'description': 'Deep, guttural vocals', 'applies_to': ['metal']},
            'scream': {'description': 'High-pitched aggressive vocals', 'applies_to': ['metal', 'hardcore']},
            'whisper': {'description': 'Soft, intimate vocals', 'applies_to': ['electronic', 'ambient']},
            'chant': {'description': 'Repetitive, ritualistic vocals', 'applies_to': ['folk', 'classical']},
            'falsetto': {'description': 'High-pitched head voice', 'applies_to': ['pop', 'rock']},
            'spoken': {'description': 'Spoken word style', 'applies_to': ['experimental', 'electronic']}
        }
        
        # Instrumental indicators
        self.instrumental_indicators = {
            'guitar_driven': ['guitar', 'guitars', 'guitar-driven'],
            'keyboard_driven': ['keyboard', 'keys', 'piano', 'synthesizer'],
            'orchestral': ['orchestra', 'symphonic', 'chamber'],
            'electronic': ['electronic', 'digital', 'programmed'],
            'acoustic': ['acoustic', 'unplugged'],
            'instrumental': ['instrumental', 'no vocals']
        }
        
        # Initialize the hierarchy
        self.tag_hierarchy: Dict[str, HierarchicalTag] = {}
        self.component_index: Dict[str, List[str]] = defaultdict(list)
        self._build_hierarchy()
    
    def _build_hierarchy(self):
        """Build the complete tag hierarchy"""
        # Add primary genres
        for genre, data in self.primary_genres.items():
            self._add_hierarchical_tag(genre, TagType.PRIMARY_GENRE)
            
            # Add subgenres
            for subgenre in data.get('subgenres', []):
                self._add_hierarchical_tag(subgenre, TagType.SUBGENRE, primary_genre=genre)
                self._add_parent_child_relationship(genre, subgenre)
            
            # Add derivatives
            for category in ['core_derivatives', 'punk_derivatives', 'experimental', 'fusion_types', 'orchestral', 'regional']:
                for derivative in data.get(category, []):
                    self._add_hierarchical_tag(derivative, TagType.SUBGENRE, primary_genre=genre)
                    self._add_parent_child_relationship(genre, derivative)
        
        # Add modifiers
        for modifier in self.style_modifiers:
            self._add_hierarchical_tag(modifier, TagType.MODIFIER)
        
        # Add prefixes
        for prefix in self.separable_prefixes:
            self._add_hierarchical_tag(prefix, TagType.PREFIX)
        
        # Add regional/cultural tags
        for category, items in self.regional_cultural.items():
            if category == 'geographic':
                for region, countries in items.items():
                    self._add_hierarchical_tag(region, TagType.REGIONAL_CULTURAL)
                    for country in countries:
                        self._add_hierarchical_tag(country, TagType.REGIONAL_CULTURAL)
                        self._add_parent_child_relationship(region, country)
            else:  # cultural
                for culture in items:
                    self._add_hierarchical_tag(culture, TagType.REGIONAL_CULTURAL)
        
        # Add vocal styles
        for vocal_style in self.vocal_styles:
            self._add_hierarchical_tag(vocal_style, TagType.VOCAL_STYLE)
    
    def _add_hierarchical_tag(self, name: str, tag_type: TagType, primary_genre: str = None):
        """Add a tag to the hierarchy"""
        normalized_name = self._normalize_tag_name(name)
        
        if normalized_name not in self.tag_hierarchy:
            self.tag_hierarchy[normalized_name] = HierarchicalTag(
                name=name,
                normalized_name=normalized_name,
                tag_type=tag_type,
                primary_genre=primary_genre
            )
            
            # Add to component index
            self.component_index[tag_type.value].append(normalized_name)
    
    def _add_parent_child_relationship(self, parent: str, child: str):
        """Add parent-child relationship between tags"""
        parent_norm = self._normalize_tag_name(parent)
        child_norm = self._normalize_tag_name(child)
        
        if parent_norm in self.tag_hierarchy:
            self.tag_hierarchy[parent_norm].child_tags.add(child_norm)
        
        if child_norm in self.tag_hierarchy:
            self.tag_hierarchy[child_norm].parent_tags.add(parent_norm)
    
    def _normalize_tag_name(self, name: str) -> str:
        """Normalize tag name for consistent indexing"""
        return name.lower().replace('-', ' ').replace('_', ' ').strip()
    
    def decompose_tag(self, tag_name: str) -> List[TagComponent]:
        """
        Decompose a composite tag into its components
        
        Examples:
        - "atmospheric black metal" -> [atmospheric(modifier), black(modifier), metal(primary)]
        - "post-rock" -> [post(prefix), rock(primary)]
        - "technical death metal" -> [technical(modifier), death(modifier), metal(primary)]
        """
        normalized = self._normalize_tag_name(tag_name)
        words = normalized.split()
        components = []
        
        # Check for prefixes
        for i, word in enumerate(words):
            if word in self.separable_prefixes:
                components.append(TagComponent(word, TagType.PREFIX, 0.9))
                words = words[i+1:]  # Remove processed prefix
                break
        
        # Identify the primary genre (usually the last significant word)
        primary_genre = None
        for genre in self.primary_genres.keys():
            if genre in normalized:
                primary_genre = genre
                break
        
        # Process remaining words
        remaining_words = ' '.join(words) if words else normalized
        
        # Look for style modifiers
        for modifier in self.style_modifiers:
            if modifier in remaining_words:
                weight = self.style_modifiers[modifier]['weight']
                components.append(TagComponent(modifier, TagType.MODIFIER, weight))
                remaining_words = remaining_words.replace(modifier, '').strip()
        
        # Look for regional/cultural indicators
        for category_data in self.regional_cultural.values():
            if isinstance(category_data, dict):
                for item in category_data:
                    if item in remaining_words:
                        components.append(TagComponent(item, TagType.REGIONAL_CULTURAL, 0.7))
                        remaining_words = remaining_words.replace(item, '').strip()
        
        # Look for vocal styles
        for vocal_style in self.vocal_styles:
            if vocal_style in remaining_words:
                components.append(TagComponent(vocal_style, TagType.VOCAL_STYLE, 0.6))
                remaining_words = remaining_words.replace(vocal_style, '').strip()
        
        # What remains should be the core genre
        if remaining_words:
            # Check if it's a known subgenre
            found_subgenre = False
            for genre_data in self.primary_genres.values():
                for subgenre in genre_data.get('subgenres', []):
                    if self._normalize_tag_name(subgenre) == remaining_words:
                        components.append(TagComponent(remaining_words, TagType.SUBGENRE, 1.0))
                        found_subgenre = True
                        break
                if found_subgenre:
                    break
            
            if not found_subgenre:
                # Check if it's a primary genre
                if remaining_words in [self._normalize_tag_name(g) for g in self.primary_genres.keys()]:
                    components.append(TagComponent(remaining_words, TagType.PRIMARY_GENRE, 1.0))
                else:
                    # Unknown component - might be a new subgenre
                    components.append(TagComponent(remaining_words, TagType.SUBGENRE, 0.8))
        
        return components
    
    def suggest_consolidation(self, tag_name: str) -> Dict[str, Any]:
        """
        Suggest how a tag should be consolidated based on hierarchy
        
        Returns consolidation suggestions including:
        - Canonical form
        - Component breakdown
        - Hierarchical relationships
        - Consolidation opportunities
        """
        components = self.decompose_tag(tag_name)
        
        # Build canonical form
        canonical_parts = []
        prefix_parts = []
        modifier_parts = []
        core_parts = []
        
        for component in components:
            if component.tag_type == TagType.PREFIX:
                prefix_parts.append(component.value)
            elif component.tag_type == TagType.MODIFIER:
                modifier_parts.append(component.value)
            elif component.tag_type in [TagType.PRIMARY_GENRE, TagType.SUBGENRE]:
                core_parts.append(component.value)
            else:
                modifier_parts.append(component.value)
        
        # Reconstruct canonical form
        if prefix_parts:
            canonical_parts.extend([f"{p}-" for p in prefix_parts])
        
        canonical_parts.extend(modifier_parts)
        canonical_parts.extend(core_parts)
        
        canonical_form = ''.join(canonical_parts) if prefix_parts else ' '.join(canonical_parts)
        
        # Find primary genre
        primary_genre = None
        for component in components:
            if component.tag_type == TagType.PRIMARY_GENRE:
                primary_genre = component.value
                break
        
        if not primary_genre:
            # Infer from subgenre
            for component in components:
                if component.tag_type == TagType.SUBGENRE:
                    for genre, data in self.primary_genres.items():
                        if component.value in [self._normalize_tag_name(sg) for sg in data.get('subgenres', [])]:
                            primary_genre = genre
                            break
                    if primary_genre:
                        break
        
        # Find hierarchical relationships
        parent_tags = set()
        child_tags = set()
        related_tags = set()
        
        if primary_genre:
            parent_tags.add(primary_genre)
            # Add related genres
            related_tags.update(self.primary_genres[primary_genre].get('subgenres', []))
        
        # Suggest consolidation opportunities
        consolidation_suggestions = []
        
        # Check if components could be consolidated
        if len(components) > 2:
            # Suggest removing redundant modifiers
            redundant_modifiers = self._find_redundant_modifiers(components)
            if redundant_modifiers:
                consolidation_suggestions.append({
                    'type': 'remove_redundant_modifiers',
                    'modifiers': redundant_modifiers,
                    'reason': 'These modifiers are redundant or implied by the core genre'
                })
        
        # Check for prefix separation opportunities
        for prefix in self.separable_prefixes:
            if prefix in tag_name.lower() and not any(c.value == prefix for c in components):
                consolidation_suggestions.append({
                    'type': 'separate_prefix',
                    'prefix': prefix,
                    'canonical_form': f"{prefix}-{' '.join(core_parts)}",
                    'reason': f'Prefix "{prefix}" should be separated for better organization'
                })
        
        return {
            'original_tag': tag_name,
            'canonical_form': canonical_form,
            'components': [{'value': c.value, 'type': c.tag_type.value, 'weight': c.weight} for c in components],
            'primary_genre': primary_genre,
            'parent_tags': list(parent_tags),
            'child_tags': list(child_tags),
            'related_tags': list(related_tags),
            'consolidation_suggestions': consolidation_suggestions
        }
    
    def _find_redundant_modifiers(self, components: List[TagComponent]) -> List[str]:
        """Find modifiers that are redundant given the core genre"""
        redundant = []
        
        core_genres = [c.value for c in components if c.tag_type in [TagType.PRIMARY_GENRE, TagType.SUBGENRE]]
        modifiers = [c.value for c in components if c.tag_type == TagType.MODIFIER]
        
        for modifier in modifiers:
            # Check if modifier is implied by core genre
            for core in core_genres:
                if self._is_modifier_implied_by_genre(modifier, core):
                    redundant.append(modifier)
        
        return redundant
    
    def _is_modifier_implied_by_genre(self, modifier: str, genre: str) -> bool:
        """Check if a modifier is already implied by the core genre"""
        implications = {
            'progressive metal': ['progressive', 'technical'],
            'death metal': ['heavy', 'brutal'],
            'black metal': ['dark', 'atmospheric'],
            'ambient': ['atmospheric', 'ambient'],
            'jazz fusion': ['fusion', 'experimental']
        }
        
        return modifier in implications.get(genre, [])
    
    def get_consolidation_rules(self) -> List[Dict[str, Any]]:
        """Generate consolidation rules based on hierarchy"""
        rules = []
        
        # Primary genre consolidation rules
        for genre in self.primary_genres:
            rules.append({
                'pattern': f'heavy {genre}',
                'replacement': genre,
                'reason': f'Heavy is redundant for {genre}',
                'confidence': 0.9
            })
        
        # Prefix separation rules
        for prefix, data in self.separable_prefixes.items():
            for example in data['examples']:
                base_genre = example.replace(f'{prefix}-', '')
                rules.append({
                    'pattern': example.replace('-', ''),  # "postmetal"
                    'replacement': example,  # "post-metal"
                    'reason': f'Separate {prefix} prefix for better organization',
                    'confidence': 0.95
                })
        
        # Modifier consolidation rules
        redundant_patterns = [
            ('progressive prog', 'progressive'),
            ('technical tech', 'technical'),
            ('melodic melody', 'melodic'),
            ('atmospheric ambient', 'atmospheric'),
        ]
        
        for pattern, replacement in redundant_patterns:
            rules.append({
                'pattern': pattern,
                'replacement': replacement,
                'reason': 'Remove redundant modifier',
                'confidence': 0.8
            })
        
        return rules
    
    def analyze_tag_collection(self, tags: List[str]) -> Dict[str, Any]:
        """
        Analyze a collection of tags and provide comprehensive consolidation analysis
        """
        analysis = {
            'total_tags': len(tags),
            'primary_genres': defaultdict(int),
            'modifiers': defaultdict(int),
            'prefixes': defaultdict(int),
            'regional_cultural': defaultdict(int),
            'consolidation_opportunities': [],
            'hierarchy_stats': {},
            'redundancy_analysis': {}
        }
        
        # Analyze each tag
        tag_decompositions = {}
        for tag in tags:
            decomposition = self.decompose_tag(tag)
            tag_decompositions[tag] = decomposition
            
            for component in decomposition:
                if component.tag_type == TagType.PRIMARY_GENRE:
                    analysis['primary_genres'][component.value] += 1
                elif component.tag_type == TagType.MODIFIER:
                    analysis['modifiers'][component.value] += 1
                elif component.tag_type == TagType.PREFIX:
                    analysis['prefixes'][component.value] += 1
                elif component.tag_type == TagType.REGIONAL_CULTURAL:
                    analysis['regional_cultural'][component.value] += 1
        
        # Find consolidation opportunities
        consolidation_groups = defaultdict(list)
        for tag in tags:
            suggestion = self.suggest_consolidation(tag)
            canonical = suggestion['canonical_form']
            consolidation_groups[canonical].append(tag)
        
        # Identify groups with multiple variants
        for canonical, variants in consolidation_groups.items():
            if len(variants) > 1:
                analysis['consolidation_opportunities'].append({
                    'canonical_form': canonical,
                    'variants': variants,
                    'reduction_count': len(variants) - 1
                })
        
        # Calculate potential reduction
        total_reduction = sum(len(group['variants']) - 1 for group in analysis['consolidation_opportunities'])
        analysis['potential_reduction'] = {
            'current_count': len(tags),
            'potential_count': len(tags) - total_reduction,
            'reduction_percentage': (total_reduction / len(tags)) * 100 if tags else 0
        }
        
        return analysis
    
    def get_hierarchy_visualization(self) -> Dict[str, Any]:
        """Generate data for visualizing the tag hierarchy"""
        visualization = {
            'nodes': [],
            'edges': [],
            'clusters': {}
        }
        
        # Add nodes
        for tag_name, tag in self.tag_hierarchy.items():
            node = {
                'id': tag_name,
                'label': tag.name,
                'type': tag.tag_type.value,
                'primary_genre': tag.primary_genre,
                'size': len(tag.child_tags) + 1  # Size based on children count
            }
            visualization['nodes'].append(node)
        
        # Add edges
        for tag_name, tag in self.tag_hierarchy.items():
            for child in tag.child_tags:
                edge = {
                    'source': tag_name,
                    'target': child,
                    'type': 'hierarchy'
                }
                visualization['edges'].append(edge)
        
        # Create clusters by primary genre
        for genre in self.primary_genres:
            visualization['clusters'][genre] = [
                tag_name for tag_name, tag in self.tag_hierarchy.items()
                if tag.primary_genre == genre or tag.normalized_name == genre
            ]
        
        return visualization
