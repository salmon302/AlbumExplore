#!/usr/bin/env python3
"""Semantic consolidation for synonymous genre terms."""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class SemanticGroup:
    """Group of semantically equivalent genre terms."""
    canonical_form: str
    synonyms: List[str]
    priority: int = 1
    description: str = ""

class SemanticConsolidator:
    """Handles semantic consolidation of synonymous genre terms."""
    
    def __init__(self):
        self.semantic_groups = self._initialize_semantic_groups()
        self.synonym_lookup = self._build_synonym_lookup()
    
    def _initialize_semantic_groups(self) -> List[SemanticGroup]:
        """Initialize groups of semantically equivalent terms."""
        return [
            # Progressive genre synonyms
            SemanticGroup(
                canonical_form="progressive-metal",
                synonyms=["prog-metal", "prog metal", "progressive metal", "progressive-metal"],
                priority=10,
                description="Progressive metal and all variants"
            ),
            
            SemanticGroup(
                canonical_form="prog-rock", 
                synonyms=["prog rock", "progressive rock", "progressive-rock", "prog-rock"],
                priority=10,
                description="Progressive rock and all variants"
            ),
            
            # Alternative genre synonyms
            SemanticGroup(
                canonical_form="alternative-rock",
                synonyms=["alt-rock", "alt rock", "alternative rock", "alternative-rock"],
                priority=9,
                description="Alternative rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="alternative-metal",
                synonyms=["alt-metal", "alt metal", "alternative metal", "alternative-metal"],
                priority=9,
                description="Alternative metal synonyms"
            ),
            
            # Technical genre synonyms
            SemanticGroup(
                canonical_form="technical-death-metal",
                synonyms=["tech-death", "tech death", "technical death metal", "tech-death-metal"],
                priority=8,
                description="Technical death metal synonyms"
            ),
            
            # Atmospheric synonyms
            SemanticGroup(
                canonical_form="atmospheric-black-metal",
                synonyms=["atmospheric black metal", "atmo-black", "atmospheric-black-metal"],
                priority=8,
                description="Atmospheric black metal synonyms"
            ),
            
            SemanticGroup(
                canonical_form="atmospheric-sludge-metal",
                synonyms=["atmospheric sludge metal", "atmospheric sludge", "atmo-sludge"],
                priority=8,
                description="Atmospheric sludge metal synonyms"
            ),
            
            # Core genre synonyms
            SemanticGroup(
                canonical_form="metalcore",
                synonyms=["metal-core", "metal core", "metalcore"],
                priority=8,
                description="Metalcore synonyms"
            ),
            
            SemanticGroup(
                canonical_form="deathcore",
                synonyms=["death-core", "death core", "deathcore"],
                priority=8,
                description="Deathcore synonyms"
            ),
            
            SemanticGroup(
                canonical_form="grindcore",
                synonyms=["grind-core", "grind core", "grindcore"],
                priority=8,
                description="Grindcore synonyms"
            ),
            
            # Singer-songwriter synonyms
            SemanticGroup(
                canonical_form="singer-songwriter",
                synonyms=["singer songwriter", "singer-songwriter", "singersongwriter"],
                priority=7,
                description="Singer-songwriter synonyms"
            ),
            
            # Shoegaze synonyms
            SemanticGroup(
                canonical_form="shoegaze",
                synonyms=["shoe-gaze", "shoe gaze", "shoegaze"],
                priority=7,
                description="Shoegaze synonyms"
            ),
            
            # Electronic music synonyms
            SemanticGroup(
                canonical_form="drum-and-bass",
                synonyms=["drum and bass", "drum n bass", "dnb", "drum-and-bass"],
                priority=7,
                description="Drum and bass synonyms"
            ),
            
            # Jazz synonyms
            SemanticGroup(
                canonical_form="jazz-fusion",
                synonyms=["jazz fusion", "fusion", "jazz-fusion"],
                priority=7,
                description="Jazz fusion synonyms"
            ),
            
            SemanticGroup(
                canonical_form="jazz-rock",
                synonyms=["jazz rock", "jazz-rock"],
                priority=7,
                description="Jazz rock synonyms"
            ),
            
            # Folk synonyms
            SemanticGroup(
                canonical_form="folk-rock",
                synonyms=["folk rock", "folk-rock"],
                priority=7,
                description="Folk rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="indie-folk",
                synonyms=["indie folk", "indie-folk"],
                priority=7,
                description="Indie folk synonyms"
            ),
            
            # Pop synonyms
            SemanticGroup(
                canonical_form="dream-pop",
                synonyms=["dream pop", "dreampop", "dream-pop"],
                priority=7,
                description="Dream pop synonyms"
            ),
            
            SemanticGroup(
                canonical_form="indie-pop",
                synonyms=["indie pop", "indiepop", "indie-pop"],
                priority=7,
                description="Indie pop synonyms"
            ),
            
            SemanticGroup(
                canonical_form="art-pop",
                synonyms=["art pop", "artpop", "art-pop"],
                priority=7,
                description="Art pop synonyms"
            ),
            
            # Rock synonyms
            SemanticGroup(
                canonical_form="hard-rock",
                synonyms=["hard rock", "hardrock", "hard-rock"],
                priority=7,
                description="Hard rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="psychedelic-rock",
                synonyms=["psychedelic rock", "psych rock", "psychedelic-rock"],
                priority=7,
                description="Psychedelic rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="indie-rock",
                synonyms=["indie rock", "indierock", "indie-rock"],
                priority=7,
                description="Indie rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="noise-rock",
                synonyms=["noise rock", "noiserock", "noise-rock"],
                priority=7,
                description="Noise rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="math-rock",
                synonyms=["math rock", "mathrock", "math-rock"],
                priority=7,
                description="Math rock synonyms"
            ),
            
            SemanticGroup(
                canonical_form="art-rock",
                synonyms=["art rock", "artrock", "art-rock"],
                priority=7,
                description="Art rock synonyms"
            ),
            
            # Punk synonyms
            SemanticGroup(
                canonical_form="pop-punk",
                synonyms=["pop punk", "poppunk", "pop-punk"],
                priority=7,
                description="Pop punk synonyms"
            ),
            
            SemanticGroup(
                canonical_form="hardcore-punk",
                synonyms=["hardcore punk", "hardcorepunk", "hardcore-punk"],
                priority=7,
                description="Hardcore punk synonyms"
            ),
            
            # Neo genre synonyms
            SemanticGroup(
                canonical_form="neo-prog",
                synonyms=["neo prog", "neoprog", "neo-prog"],
                priority=6,
                description="Neo progressive synonyms"
            ),
            
            SemanticGroup(
                canonical_form="neo-classical",
                synonyms=["neo classical", "neoclassical", "neo-classical"],
                priority=6,
                description="Neo classical synonyms"
            ),
            
            # Heavy psych synonyms
            SemanticGroup(
                canonical_form="heavy-psych",
                synonyms=["heavy psych", "heavy-psych", "psychedelic heavy"],
                priority=6,
                description="Heavy psych synonyms"
            ),
            
            # New wave synonyms
            SemanticGroup(
                canonical_form="new-wave",
                synonyms=["new wave", "new-wave", "newwave"],
                priority=6,
                description="New wave synonyms"
            ),
        ]
    
    def _build_synonym_lookup(self) -> Dict[str, str]:
        """Build lookup table from synonym to canonical form."""
        lookup = {}
        
        for group in self.semantic_groups:
            for synonym in group.synonyms:
                lookup[synonym.lower().strip()] = group.canonical_form
        
        return lookup
    
    def get_canonical_form(self, genre: str) -> str:
        """Get canonical form of a genre based on semantic equivalence."""
        genre_clean = genre.lower().strip()
        
        return self.synonym_lookup.get(genre_clean, genre)
    
    def consolidate_by_semantics(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Dict]:
        """Consolidate tags by semantic equivalence."""
        consolidated = {}
        
        for tag, frequency in tag_frequency_map.items():
            canonical = self.get_canonical_form(tag)
            
            if canonical not in consolidated:
                consolidated[canonical] = {
                    'canonical_form': canonical,
                    'variants': [],
                    'total_frequency': 0,
                    'semantic_group': self._get_semantic_group_info(canonical)
                }
            
            consolidated[canonical]['variants'].append({
                'original_tag': tag,
                'frequency': frequency
            })
            consolidated[canonical]['total_frequency'] += frequency
        
        # Sort variants by frequency within each group
        for group_data in consolidated.values():
            group_data['variants'].sort(key=lambda v: v['frequency'], reverse=True)
        
        # Sort groups by total frequency
        return dict(sorted(consolidated.items(), 
                          key=lambda x: x[1]['total_frequency'], 
                          reverse=True))
    
    def _get_semantic_group_info(self, canonical_form: str) -> Dict:
        """Get information about the semantic group for a canonical form."""
        for group in self.semantic_groups:
            if group.canonical_form == canonical_form:
                return {
                    'description': group.description,
                    'priority': group.priority,
                    'synonym_count': len(group.synonyms)
                }
        
        return {'description': 'No semantic group', 'priority': 0, 'synonym_count': 0}
    
    def get_consolidation_stats(self, tag_frequency_map: Dict[str, int]) -> Dict[str, any]:
        """Get statistics about semantic consolidation opportunities."""
        original_count = len(tag_frequency_map)
        consolidated = self.consolidate_by_semantics(tag_frequency_map)
        consolidated_count = len(consolidated)
        
        # Find groups with multiple variants
        multi_variant_groups = []
        for canonical, data in consolidated.items():
            if len(data['variants']) > 1:
                multi_variant_groups.append({
                    'canonical': canonical,
                    'variant_count': len(data['variants']),
                    'total_frequency': data['total_frequency'],
                    'variants': [v['original_tag'] for v in data['variants'][:5]]  # Top 5
                })
        
        multi_variant_groups.sort(key=lambda x: x['total_frequency'], reverse=True)
        
        return {
            'original_tag_count': original_count,
            'consolidated_tag_count': consolidated_count,
            'reduction_count': original_count - consolidated_count,
            'reduction_percentage': ((original_count - consolidated_count) / original_count * 100) if original_count > 0 else 0,
            'multi_variant_groups': multi_variant_groups[:20]  # Top 20 consolidation opportunities
        }

if __name__ == "__main__":
    # Test semantic consolidation
    consolidator = SemanticConsolidator()
    
    test_tags = {
        "prog metal": 100,
        "progressive metal": 50,
        "prog-metal": 25,
        "tech death": 75,
        "technical death metal": 30,
        "indie rock": 200,
        "indie-rock": 50,
        "indierock": 10
    }
    
    print("SEMANTIC CONSOLIDATION TEST")
    print("=" * 40)
    
    for tag in test_tags.keys():
        canonical = consolidator.get_canonical_form(tag)
        print(f"'{tag}' → '{canonical}'")
    
    print("\nCONSOLIDATION STATS:")
    stats = consolidator.get_consolidation_stats(test_tags)
    print(f"Original: {stats['original_tag_count']} tags")
    print(f"Consolidated: {stats['consolidated_tag_count']} tags")
    print(f"Reduction: {stats['reduction_count']} tags ({stats['reduction_percentage']:.1f}%)")
