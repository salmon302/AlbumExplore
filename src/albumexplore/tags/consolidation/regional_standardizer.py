#!/usr/bin/env python3
"""Regional and cultural tag standardization."""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class RegionalCategory(Enum):
    """Categories of regional/cultural descriptors."""
    GEOGRAPHIC = "geographic"
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    LINGUISTIC = "linguistic"

@dataclass
class RegionalRule:
    """Rule for standardizing regional/cultural tags."""
    canonical_form: str
    variants: List[str]
    category: RegionalCategory
    priority: int = 1
    description: str = ""

class RegionalStandardizer:
    """Handles standardization of regional and cultural tag elements."""
    
    def __init__(self):
        self.regional_rules = self._initialize_regional_rules()
        self.variant_lookup = self._build_variant_lookup()
    
    def _initialize_regional_rules(self) -> List[RegionalRule]:
        """Initialize regional/cultural standardization rules."""
        return [
            # Nordic/Scandinavian
            RegionalRule(
                canonical_form="scandinavian",
                variants=["scandinavian", "nordic", "norse", "scandinavian-folk", "nordic-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=9,
                description="Scandinavian/Nordic regional descriptor"
            ),
            
            # Celtic
            RegionalRule(
                canonical_form="celtic",
                variants=["celtic", "gaelic", "irish", "scottish", "welsh", "celtic-folk"],
                category=RegionalCategory.CULTURAL,
                priority=9,
                description="Celtic cultural descriptor"
            ),
            
            # Slavic
            RegionalRule(
                canonical_form="slavic",
                variants=["slavic", "slavonic", "eastern-european", "slavic-folk"],
                category=RegionalCategory.CULTURAL,
                priority=8,
                description="Slavic cultural descriptor"
            ),
            
            # Viking
            RegionalRule(
                canonical_form="viking",
                variants=["viking", "viking-metal", "norse-metal"],
                category=RegionalCategory.HISTORICAL,
                priority=8,
                description="Viking historical/cultural descriptor"
            ),
            
            # Medieval/Historical periods
            RegionalRule(
                canonical_form="medieval",
                variants=["medieval", "middle-ages", "dark-ages", "medieval-folk"],
                category=RegionalCategory.HISTORICAL,
                priority=7,
                description="Medieval historical period"
            ),
            
            RegionalRule(
                canonical_form="renaissance",
                variants=["renaissance", "baroque", "early-music"],
                category=RegionalCategory.HISTORICAL,
                priority=7,
                description="Renaissance historical period"
            ),
            
            # Geographic regions
            RegionalRule(
                canonical_form="british",
                variants=["british", "uk", "english", "british-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=7,
                description="British geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="american",
                variants=["american", "usa", "us", "american-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=7,
                description="American geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="german",
                variants=["german", "deutsch", "germanic", "german-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=7,
                description="German geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="japanese",
                variants=["japanese", "japan", "j-rock", "j-pop"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=7,
                description="Japanese geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="brazilian",
                variants=["brazilian", "brazil", "brazilian-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=7,
                description="Brazilian geographic descriptor"
            ),
            
            # Cultural/Traditional descriptors
            RegionalRule(
                canonical_form="traditional",
                variants=["traditional", "trad", "folk-traditional", "classical-traditional"],
                category=RegionalCategory.CULTURAL,
                priority=6,
                description="Traditional cultural descriptor"
            ),
            
            RegionalRule(
                canonical_form="ancient",
                variants=["ancient", "archaic", "prehistoric", "primordial"],
                category=RegionalCategory.HISTORICAL,
                priority=6,
                description="Ancient historical descriptor"
            ),
            
            # World music regions
            RegionalRule(
                canonical_form="middle-eastern",
                variants=["middle-eastern", "arabic", "persian", "middle-east"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=6,
                description="Middle Eastern geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="african",
                variants=["african", "africa", "african-folk"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=6,
                description="African geographic descriptor"
            ),
            
            RegionalRule(
                canonical_form="asian",
                variants=["asian", "asia", "far-eastern", "oriental"],
                category=RegionalCategory.GEOGRAPHIC,
                priority=6,
                description="Asian geographic descriptor"
            ),
            
            # Native/Indigenous
            RegionalRule(
                canonical_form="indigenous",
                variants=["indigenous", "native", "aboriginal", "tribal"],
                category=RegionalCategory.CULTURAL,
                priority=6,
                description="Indigenous cultural descriptor"
            ),
        ]
    
    def _build_variant_lookup(self) -> Dict[str, str]:
        """Build lookup table from variant to canonical form."""
        lookup = {}
        
        for rule in self.regional_rules:
            for variant in rule.variants:
                lookup[variant.lower().strip()] = rule.canonical_form
        
        return lookup
    
    def standardize_regional(self, tag: str) -> Tuple[str, bool]:
        """
        Standardize regional/cultural elements in a tag.
        
        Returns:
            Tuple of (standardized_tag, was_modified)
        """
        original_tag = tag.lower().strip()
        standardized_tag = original_tag
        was_modified = False
        
        # Check for exact matches first
        if original_tag in self.variant_lookup:
            return self.variant_lookup[original_tag], True
        
        # Check for regional elements within compound tags
        words = original_tag.replace('-', ' ').split()
        standardized_words = []
        
        for word in words:
            if word in self.variant_lookup:
                standardized_words.append(self.variant_lookup[word])
                was_modified = True
            else:
                standardized_words.append(word)
        
        if was_modified:
            # Reconstruct the tag maintaining the original format
            if '-' in original_tag:
                standardized_tag = '-'.join(standardized_words)
            else:
                standardized_tag = ' '.join(standardized_words)
        
        return standardized_tag, was_modified
    
    def get_regional_category(self, tag: str) -> Optional[RegionalCategory]:
        """Get the regional category of a tag."""
        standardized, _ = self.standardize_regional(tag)
        
        for rule in self.regional_rules:
            if rule.canonical_form == standardized or standardized in rule.variants:
                return rule.category
        
        return None
    
    def consolidate_by_region(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Dict]:
        """Consolidate tags by standardizing regional elements."""
        consolidated = {}
        
        for tag, frequency in tag_frequency_map.items():
            standardized, was_modified = self.standardize_regional(tag)
            category = self.get_regional_category(tag)
            
            # Use standardized form as the key
            key = standardized
            
            if key not in consolidated:
                consolidated[key] = {
                    'standardized_form': standardized,
                    'regional_category': category.value if category else None,
                    'variants': [],
                    'total_frequency': 0,
                    'was_standardized': False
                }
            
            consolidated[key]['variants'].append({
                'original_tag': tag,
                'frequency': frequency,
                'was_modified': was_modified
            })
            consolidated[key]['total_frequency'] += frequency
            
            if was_modified:
                consolidated[key]['was_standardized'] = True
        
        # Sort variants by frequency within each group
        for group_data in consolidated.values():
            group_data['variants'].sort(key=lambda v: v['frequency'], reverse=True)
        
        # Sort groups by total frequency
        return dict(sorted(consolidated.items(), 
                          key=lambda x: x[1]['total_frequency'], 
                          reverse=True))
    
    def get_standardization_stats(self, tag_frequency_map: Dict[str, int]) -> Dict[str, any]:
        """Get statistics about regional standardization opportunities."""
        standardization_opportunities = []
        category_stats = {}
        
        for tag, frequency in tag_frequency_map.items():
            standardized, was_modified = self.standardize_regional(tag)
            category = self.get_regional_category(tag)
            
            if was_modified:
                standardization_opportunities.append({
                    'original_tag': tag,
                    'standardized_tag': standardized,
                    'frequency': frequency,
                    'category': category.value if category else None
                })
            
            if category:
                cat_name = category.value
                if cat_name not in category_stats:
                    category_stats[cat_name] = {
                        'tag_count': 0,
                        'total_frequency': 0,
                        'examples': []
                    }
                
                category_stats[cat_name]['tag_count'] += 1
                category_stats[cat_name]['total_frequency'] += frequency
                
                if len(category_stats[cat_name]['examples']) < 5:
                    category_stats[cat_name]['examples'].append(
                        f"{tag} → {standardized}" if was_modified else tag
                    )
        
        standardization_opportunities.sort(key=lambda x: x['frequency'], reverse=True)
        
        return {
            'standardization_opportunities': standardization_opportunities[:20],  # Top 20
            'category_breakdown': category_stats,
            'total_opportunities': len(standardization_opportunities)
        }

if __name__ == "__main__":
    # Test regional standardization
    standardizer = RegionalStandardizer()
    
    test_tags = [
        "viking metal", "norse-metal", "scandinavian folk", "nordic-folk",
        "celtic-folk", "irish folk", "german folk", "japanese rock",
        "medieval folk", "ancient metal", "traditional folk"
    ]
    
    print("REGIONAL STANDARDIZATION TEST")
    print("=" * 40)
    
    for tag in test_tags:
        standardized, was_modified = standardizer.standardize_regional(tag)
        category = standardizer.get_regional_category(tag)
        status = "✅ MODIFIED" if was_modified else "→ NO CHANGE"
        
        print(f"{status} '{tag}' → '{standardized}' (category: {category.value if category else 'N/A'})")
