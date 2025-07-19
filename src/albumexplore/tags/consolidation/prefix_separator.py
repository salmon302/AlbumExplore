#!/usr/bin/env python3
"""Advanced prefix separation for tag consolidation."""

import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass

@dataclass
class PrefixRule:
    """Rule for separating prefixes from base genres."""
    prefix: str
    pattern: str  # Regex pattern to match
    separator: str = "-"  # How to separate prefix from base
    priority: int = 1  # Higher priority rules are applied first
    description: str = ""

class PrefixSeparator:
    """Handles aggressive prefix separation for tag consolidation."""
    
    def __init__(self):
        self.prefix_rules = self._initialize_prefix_rules()
        self.separated_cache: Dict[str, str] = {}
        
    def _initialize_prefix_rules(self) -> List[PrefixRule]:
        """Initialize comprehensive prefix separation rules."""
        return [
            # Post- prefix (highest priority - most common)
            PrefixRule(
                prefix="post", 
                pattern=r"^post[\s-]?(.+)$",
                priority=10,
                description="Post-genre separation (post-metal, post-rock, etc.)"
            ),
            
            # Neo- prefix  
            PrefixRule(
                prefix="neo",
                pattern=r"^neo[\s-]?(.+)$", 
                priority=9,
                description="Neo-genre separation (neo-prog, neo-classical, etc.)"
            ),
            
            # Avant- prefix
            PrefixRule(
                prefix="avant",
                pattern=r"^avant[\s-]?garde[\s-]?(.+)$",
                priority=8,
                description="Avant-garde genre separation"
            ),
            PrefixRule(
                prefix="avant",
                pattern=r"^avant[\s-]?(.+)$",
                priority=7,
                description="Avant- genre separation"
            ),
            
            # Proto- prefix
            PrefixRule(
                prefix="proto",
                pattern=r"^proto[\s-]?(.+)$",
                priority=6,
                description="Proto-genre separation (proto-metal, proto-punk, etc.)"
            ),
            
            # Anti- prefix
            PrefixRule(
                prefix="anti",
                pattern=r"^anti[\s-]?(.+)$",
                priority=5,
                description="Anti-genre separation"
            ),
            
            # Pre- prefix
            PrefixRule(
                prefix="pre",
                pattern=r"^pre[\s-]?(.+)$",
                priority=4,
                description="Pre-genre separation"
            ),
            
            # Pseudo- prefix
            PrefixRule(
                prefix="pseudo",
                pattern=r"^pseudo[\s-]?(.+)$",
                priority=3,
                description="Pseudo-genre separation"
            ),
            
            # Non- prefix
            PrefixRule(
                prefix="non",
                pattern=r"^non[\s-]?(.+)$",
                priority=2,
                description="Non-genre separation"
            ),
            
            # Meta- prefix
            PrefixRule(
                prefix="meta",
                pattern=r"^meta[\s-]?(.+)$",
                priority=1,
                description="Meta-genre separation"
            ),
        ]
    
    def separate_prefix(self, tag: str) -> Tuple[str, str, str]:
        """
        Separate prefix from base genre.
        
        Returns:
            Tuple of (separated_tag, prefix, base_genre)
        """
        if tag in self.separated_cache:
            cached = self.separated_cache[tag]
            parts = cached.split(self.prefix_rules[0].separator, 1)
            if len(parts) == 2:
                return cached, parts[0], parts[1]
            return cached, "", cached
        
        tag_lower = tag.lower().strip()
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.prefix_rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            match = re.match(rule.pattern, tag_lower, re.IGNORECASE)
            if match:
                base_genre = match.group(1).strip()
                if base_genre:  # Ensure we have a valid base genre
                    separated_tag = f"{rule.prefix}{rule.separator}{base_genre}"
                    self.separated_cache[tag] = separated_tag
                    return separated_tag, rule.prefix, base_genre
        
        # No prefix found, return original
        return tag, "", tag
    
    def get_prefix_statistics(self, tags: List[str]) -> Dict[str, Dict]:
        """Analyze prefix distribution in tag list."""
        prefix_stats = {}
        
        for tag in tags:
            separated_tag, prefix, base_genre = self.separate_prefix(tag)
            
            if prefix:
                if prefix not in prefix_stats:
                    prefix_stats[prefix] = {
                        'count': 0,
                        'examples': [],
                        'base_genres': set()
                    }
                
                prefix_stats[prefix]['count'] += 1
                prefix_stats[prefix]['base_genres'].add(base_genre)
                
                if len(prefix_stats[prefix]['examples']) < 5:
                    prefix_stats[prefix]['examples'].append(f"{tag} → {separated_tag}")
        
        # Convert sets to lists for JSON serialization
        for prefix_data in prefix_stats.values():
            prefix_data['base_genres'] = list(prefix_data['base_genres'])
            
        return prefix_stats
    
    def consolidate_by_prefix(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Dict]:
        """Consolidate tags by separating prefixes and grouping by base genre."""
        base_genre_groups = {}
        
        for tag, frequency in tag_frequency_map.items():
            separated_tag, prefix, base_genre = self.separate_prefix(tag)
            
            if base_genre not in base_genre_groups:
                base_genre_groups[base_genre] = {
                    'base_genre': base_genre,
                    'variants': [],
                    'total_frequency': 0,
                    'prefixes': set()
                }
            
            base_genre_groups[base_genre]['variants'].append({
                'original_tag': tag,
                'separated_tag': separated_tag,
                'prefix': prefix,
                'frequency': frequency
            })
            base_genre_groups[base_genre]['total_frequency'] += frequency
            
            if prefix:
                base_genre_groups[base_genre]['prefixes'].add(prefix)
        
        # Convert sets to lists and sort by frequency
        for group_data in base_genre_groups.values():
            group_data['prefixes'] = list(group_data['prefixes'])
            group_data['variants'].sort(key=lambda v: v['frequency'], reverse=True)
        
        # Sort groups by total frequency
        return dict(sorted(base_genre_groups.items(), 
                          key=lambda x: x[1]['total_frequency'], 
                          reverse=True))

if __name__ == "__main__":
    # Test the prefix separator
    separator = PrefixSeparator()
    
    test_tags = [
        "post-metal", "post metal", "postmetal",
        "neo-prog", "neo prog", "neoprog",
        "avant-garde metal", "avant garde metal", "avant-metal",
        "proto-punk", "proto punk", "protopunk",
        "post-black metal", "neo-classical", "avant-garde jazz"
    ]
    
    print("PREFIX SEPARATION TEST")
    print("=" * 40)
    
    for tag in test_tags:
        separated, prefix, base = separator.separate_prefix(tag)
        print(f"'{tag}' → '{separated}' (prefix: '{prefix}', base: '{base}')")
