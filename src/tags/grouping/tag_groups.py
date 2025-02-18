from typing import Dict, List, Set
from ..normalizer import TagNormalizer
from ..relationships import TagRelationships

class TagGroups:
    """Manages tag grouping and categorization."""
    
    PRIMARY_GENRES = {
        'metal', 'rock', 'punk', 'folk', 'electronic',
        'ambient', 'industrial', 'classical', 'jazz'
    }
    
    STYLE_MODIFIERS = {
        'atmospheric', 'technical', 'melodic', 'experimental',
        'avant-garde', 'progressive', 'symphonic', 'brutal',
        'raw', 'epic', 'psychedelic'
    }
    
    FUSION_INDICATORS = {
        'post', 'neo', 'blackened', 'cyber', 'grind',
        'death', 'black', 'doom', 'gothic'
    }
    
    REGIONAL_TAGS = {
        'nordic', 'celtic', 'oriental', 'viking',
        'medieval', 'eastern', 'western'
    }
    
    def __init__(self):
        self.normalizer = TagNormalizer()
        self.relationships = TagRelationships()
        self.tag_categories: Dict[str, Set[str]] = {
            'primary': set(),
            'subgenres': set(),
            'modifiers': set(),
            'fusion': set(),
            'regional': set(),
            'other': set()
        }
    
    def categorize_tag(self, tag: str) -> str:
        """Categorize a single tag into its appropriate group."""
        normalized = self.normalizer.normalize(tag)
        words = normalized.split()
        
        # Check regional tags first
        if any(word in self.REGIONAL_TAGS for word in words):
            return 'regional'
        
        # Check fusion indicators
        if '-' in normalized:
            parts = normalized.split('-')
            if parts[0] in self.FUSION_INDICATORS:
                return 'fusion'
        elif any(normalized.startswith(f"{indicator} ") for indicator in self.FUSION_INDICATORS):
            return 'fusion'
        
        # Check primary genres
        if normalized in self.PRIMARY_GENRES:
            return 'primary'
        
        # Check style modifiers
        if normalized in self.STYLE_MODIFIERS:
            return 'modifiers'
        
        # Check if it's a subgenre (contains a primary genre)
        if any(genre in normalized for genre in self.PRIMARY_GENRES):
            return 'subgenres'
        
        return 'other'
    
    def group_tags(self, tags: List[str]) -> Dict[str, Set[str]]:
        """Group a list of tags into their respective categories."""
        # Reset categories
        self.tag_categories = {
            'primary': set(),
            'subgenres': set(),
            'modifiers': set(),
            'fusion': set(),
            'regional': set(),
            'other': set()
        }
        
        # Categorize each tag
        for tag in tags:
            category = self.categorize_tag(tag)
            self.tag_categories[category].add(tag)
        
        return self.tag_categories
    
    def get_related_subgenres(self, primary_genre: str) -> List[str]:
        """Get subgenres related to a primary genre."""
        if primary_genre not in self.PRIMARY_GENRES:
            return []
        
        subgenres = []
        for tag in self.tag_categories['subgenres']:
            if primary_genre in self.normalizer.normalize(tag):
                subgenres.append(tag)
        return sorted(subgenres)
    
    def get_style_combinations(self, tag: str) -> List[str]:
        """Get possible style combinations for a tag."""
        combinations = []
        normalized_tag = self.normalizer.normalize(tag)
        
        # Add existing combinations from our dataset
        for subgenre in self.tag_categories['subgenres']:
            normalized_subgenre = self.normalizer.normalize(subgenre)
            if normalized_tag in normalized_subgenre:
                for modifier in self.STYLE_MODIFIERS:
                    if modifier in normalized_subgenre:
                        combinations.append(subgenre)
        
        # Add potential combinations
        for modifier in self.STYLE_MODIFIERS:
            combined = f"{modifier} {normalized_tag}"
            if combined not in combinations:
                combinations.append(combined)
        
        return sorted(set(combinations))
    
    def get_category_hierarchy(self) -> Dict[str, Dict[str, List[str]]]:
        """Get hierarchical organization of tag categories."""
        hierarchy = {}
        
        for primary in self.tag_categories['primary']:
            subgenres = self.get_related_subgenres(primary)
            modifiers = set()
            fusion_tags = set()
            
            # Find modifiers used with this genre
            for subgenre in subgenres:
                normalized_subgenre = self.normalizer.normalize(subgenre)
                for modifier in self.STYLE_MODIFIERS:
                    if modifier in normalized_subgenre:
                        modifiers.add(modifier)
            
            # Find fusion tags related to this genre
            for tag in self.tag_categories['fusion']:
                normalized_tag = self.normalizer.normalize(tag)
                if primary in normalized_tag or any(
                    subgenre in normalized_tag for subgenre in subgenres
                ):
                    fusion_tags.add(tag)
            
            hierarchy[primary] = {
                'subgenres': sorted(subgenres),
                'modifiers': sorted(list(modifiers)),
                'fusion': sorted(list(fusion_tags))
            }
        
        return hierarchy
