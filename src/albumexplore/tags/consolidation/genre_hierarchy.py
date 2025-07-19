#!/usr/bin/env python3
"""Genre hierarchy system for tag consolidation."""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class GenreCategory(Enum):
    """Primary genre categories."""
    METAL = "metal"
    ROCK = "rock" 
    PROGRESSIVE = "progressive"
    ELECTRONIC = "electronic"
    JAZZ = "jazz"
    FOLK = "folk"
    PUNK = "punk"
    POP = "pop"
    EXPERIMENTAL = "experimental"
    CLASSICAL = "classical"
    OTHER = "other"

@dataclass
class GenreNode:
    """Node in the genre hierarchy tree."""
    name: str
    category: GenreCategory
    parent: Optional['GenreNode'] = None
    children: List['GenreNode'] = None
    aliases: List[str] = None
    priority: int = 1  # Higher priority = preferred canonical form
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.aliases is None:
            self.aliases = []

class GenreHierarchy:
    """Manages genre hierarchy and consolidation."""
    
    def __init__(self):
        self.root_genres: Dict[GenreCategory, GenreNode] = {}
        self.genre_lookup: Dict[str, GenreNode] = {}
        self._build_hierarchy()
    
    def _build_hierarchy(self):
        """Build the complete genre hierarchy."""
        
        # METAL HIERARCHY
        metal_root = GenreNode("metal", GenreCategory.METAL, priority=10)
        self.root_genres[GenreCategory.METAL] = metal_root
        
        # Core metal subgenres
        heavy_metal = GenreNode("heavy-metal", GenreCategory.METAL, metal_root, priority=9)
        death_metal = GenreNode("death-metal", GenreCategory.METAL, metal_root, priority=9)
        black_metal = GenreNode("black-metal", GenreCategory.METAL, metal_root, priority=9)
        doom_metal = GenreNode("doom-metal", GenreCategory.METAL, metal_root, priority=9)
        thrash_metal = GenreNode("thrash-metal", GenreCategory.METAL, metal_root, priority=9)
        power_metal = GenreNode("power-metal", GenreCategory.METAL, metal_root, priority=9)
        
        # Add children to metal root
        metal_root.children.extend([heavy_metal, death_metal, black_metal, doom_metal, thrash_metal, power_metal])
        
        # Technical metal subgenres (children of death/black metal)
        tech_death = GenreNode("technical-death-metal", GenreCategory.METAL, death_metal, 
                              aliases=["tech-death", "technical death metal"], priority=8)
        melodic_death = GenreNode("melodic-death-metal", GenreCategory.METAL, death_metal,
                                 aliases=["melodic death metal"], priority=8)
        brutal_death = GenreNode("brutal-death-metal", GenreCategory.METAL, death_metal,
                                aliases=["brutal death metal"], priority=8)
        
        # Add children to death metal
        death_metal.children.extend([tech_death, melodic_death, brutal_death])
        
        atmospheric_black = GenreNode("atmospheric-black-metal", GenreCategory.METAL, black_metal,
                                     aliases=["atmospheric black metal"], priority=8)
        melodic_black = GenreNode("melodic-black-metal", GenreCategory.METAL, black_metal,
                                 aliases=["melodic black metal"], priority=8)
        
        # Add children to black metal
        black_metal.children.extend([atmospheric_black, melodic_black])
        
        # Sludge/Stoner metal family
        sludge_metal = GenreNode("sludge-metal", GenreCategory.METAL, metal_root, priority=8)
        stoner_metal = GenreNode("stoner-metal", GenreCategory.METAL, metal_root, priority=8)
        drone_metal = GenreNode("drone-metal", GenreCategory.METAL, metal_root, priority=8)
        
        # Add to metal root
        metal_root.children.extend([sludge_metal, stoner_metal, drone_metal])
        
        # Core genres (metalcore family)
        metalcore = GenreNode("metalcore", GenreCategory.METAL, metal_root, priority=8)
        deathcore = GenreNode("deathcore", GenreCategory.METAL, metalcore, priority=7)
        mathcore = GenreNode("mathcore", GenreCategory.METAL, metalcore, priority=7)
        
        # Add metalcore to metal root and its children
        metal_root.children.append(metalcore)
        metalcore.children.extend([deathcore, mathcore])
        
        # Other metal
        folk_metal = GenreNode("folk-metal", GenreCategory.METAL, metal_root, priority=8)
        gothic_metal = GenreNode("gothic-metal", GenreCategory.METAL, metal_root, priority=8)
        symphonic_metal = GenreNode("symphonic-metal", GenreCategory.METAL, metal_root, priority=8)
        industrial_metal = GenreNode("industrial-metal", GenreCategory.METAL, metal_root, priority=8)
        avant_garde_metal = GenreNode("avant-garde-metal", GenreCategory.METAL, metal_root, priority=8)
        
        # Add to metal root
        metal_root.children.extend([folk_metal, gothic_metal, symphonic_metal, industrial_metal, avant_garde_metal])
        
        # PROGRESSIVE HIERARCHY
        prog_root = GenreNode("progressive", GenreCategory.PROGRESSIVE, priority=10)
        self.root_genres[GenreCategory.PROGRESSIVE] = prog_root
        
        progressive_metal = GenreNode("progressive-metal", GenreCategory.PROGRESSIVE, prog_root,
                                     aliases=["prog-metal", "prog metal"], priority=9)
        prog_rock = GenreNode("prog-rock", GenreCategory.PROGRESSIVE, prog_root,
                             aliases=["progressive rock", "prog rock"], priority=9)
        
        # Add children to progressive root
        prog_root.children.extend([progressive_metal, prog_rock])
        
        # ROCK HIERARCHY  
        rock_root = GenreNode("rock", GenreCategory.ROCK, priority=10)
        self.root_genres[GenreCategory.ROCK] = rock_root
        
        # Core rock subgenres
        hard_rock = GenreNode("hard-rock", GenreCategory.ROCK, rock_root, priority=9)
        psychedelic_rock = GenreNode("psychedelic-rock", GenreCategory.ROCK, rock_root, priority=9)
        indie_rock = GenreNode("indie-rock", GenreCategory.ROCK, rock_root, priority=9)
        alt_rock = GenreNode("alt-rock", GenreCategory.ROCK, rock_root, 
                            aliases=["alternative rock", "alternative-rock"], priority=9)
        
        # Add core rock subgenres to root
        rock_root.children.extend([hard_rock, psychedelic_rock, indie_rock, alt_rock])
        
        # Specialized rock
        math_rock = GenreNode("math-rock", GenreCategory.ROCK, rock_root, priority=8)
        noise_rock = GenreNode("noise-rock", GenreCategory.ROCK, rock_root, priority=8)
        art_rock = GenreNode("art-rock", GenreCategory.ROCK, rock_root, priority=8)
        garage_rock = GenreNode("garage-rock", GenreCategory.ROCK, rock_root, priority=8)
        space_rock = GenreNode("space-rock", GenreCategory.ROCK, rock_root, priority=8)
        stoner_rock = GenreNode("stoner-rock", GenreCategory.ROCK, rock_root, priority=8)
        folk_rock = GenreNode("folk-rock", GenreCategory.ROCK, rock_root, priority=8)
        
        # Add specialized rock to root
        rock_root.children.extend([math_rock, noise_rock, art_rock, garage_rock, space_rock, stoner_rock, folk_rock])
        
        # POP HIERARCHY
        pop_root = GenreNode("pop", GenreCategory.POP, priority=10)
        self.root_genres[GenreCategory.POP] = pop_root
        
        indie_pop = GenreNode("indie-pop", GenreCategory.POP, pop_root, priority=9)
        dream_pop = GenreNode("dream-pop", GenreCategory.POP, pop_root, priority=9)
        art_pop = GenreNode("art-pop", GenreCategory.POP, pop_root, priority=9)
        psychedelic_pop = GenreNode("psychedelic-pop", GenreCategory.POP, pop_root, priority=9)
        
        # Add children to pop root
        pop_root.children.extend([indie_pop, dream_pop, art_pop, psychedelic_pop])
        
        # PUNK HIERARCHY
        punk_root = GenreNode("punk", GenreCategory.PUNK, priority=10)
        self.root_genres[GenreCategory.PUNK] = punk_root
        
        hardcore = GenreNode("hardcore", GenreCategory.PUNK, punk_root, priority=9)
        post_hardcore = GenreNode("post-hardcore", GenreCategory.PUNK, hardcore, priority=8)
        pop_punk = GenreNode("pop-punk", GenreCategory.PUNK, punk_root, priority=8)
        hardcore_punk = GenreNode("hardcore-punk", GenreCategory.PUNK, hardcore, priority=8)
        
        # Add children to punk root and hardcore
        punk_root.children.extend([hardcore, pop_punk])
        hardcore.children.extend([post_hardcore, hardcore_punk])
        
        # ELECTRONIC HIERARCHY
        electronic_root = GenreNode("electronic", GenreCategory.ELECTRONIC, priority=10)
        self.root_genres[GenreCategory.ELECTRONIC] = electronic_root
        
        ambient = GenreNode("ambient", GenreCategory.ELECTRONIC, electronic_root, priority=9)
        industrial = GenreNode("industrial", GenreCategory.ELECTRONIC, electronic_root, priority=9)
        synthwave = GenreNode("synthwave", GenreCategory.ELECTRONIC, electronic_root, priority=8)
        darkwave = GenreNode("darkwave", GenreCategory.ELECTRONIC, electronic_root, priority=8)
        
        # Add children to electronic root
        electronic_root.children.extend([ambient, industrial, synthwave, darkwave])
        
        # JAZZ HIERARCHY
        jazz_root = GenreNode("jazz", GenreCategory.JAZZ, priority=10)
        self.root_genres[GenreCategory.JAZZ] = jazz_root
        
        jazz_fusion = GenreNode("jazz-fusion", GenreCategory.JAZZ, jazz_root, 
                               aliases=["fusion", "jazz fusion"], priority=9)
        jazz_rock = GenreNode("jazz-rock", GenreCategory.JAZZ, jazz_root, priority=8)
        
        # Add children to jazz root
        jazz_root.children.extend([jazz_fusion, jazz_rock])
        
        # Build lookup table
        self._build_lookup_table()
    
    def _build_lookup_table(self):
        """Build lookup table for all genres and aliases."""
        def add_node_to_lookup(node: GenreNode):
            # Add primary name
            self.genre_lookup[node.name.lower()] = node
            
            # Add aliases
            for alias in node.aliases:
                self.genre_lookup[alias.lower()] = node
            
            # Process children
            for child in node.children:
                add_node_to_lookup(child)
        
        for root_genre in self.root_genres.values():
            add_node_to_lookup(root_genre)
    
    def get_canonical_form(self, genre: str) -> str:
        """Get the canonical form of a genre."""
        genre_lower = genre.lower().strip()
        
        if genre_lower in self.genre_lookup:
            return self.genre_lookup[genre_lower].name
        
        return genre  # Return original if not found
    
    def get_parent_genre(self, genre: str) -> Optional[str]:
        """Get the parent genre of a given genre."""
        genre_lower = genre.lower().strip()
        
        if genre_lower in self.genre_lookup:
            node = self.genre_lookup[genre_lower]
            if node.parent:
                return node.parent.name
        
        return None
    
    def get_category(self, genre: str) -> Optional[GenreCategory]:
        """Get the category of a genre."""
        genre_lower = genre.lower().strip()
        
        if genre_lower in self.genre_lookup:
            return self.genre_lookup[genre_lower].category
        
        return None
    
    def consolidate_by_hierarchy(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Dict]:
        """Consolidate tags using genre hierarchy."""
        consolidated = {}
        
        for tag, frequency in tag_frequency_map.items():
            canonical = self.get_canonical_form(tag)
            category = self.get_category(tag)
            parent = self.get_parent_genre(tag)
            
            if canonical not in consolidated:
                consolidated[canonical] = {
                    'canonical_form': canonical,
                    'category': category.value if category else 'other',
                    'parent_genre': parent,
                    'variants': [],
                    'total_frequency': 0
                }
            
            consolidated[canonical]['variants'].append({
                'original_tag': tag,
                'frequency': frequency
            })
            consolidated[canonical]['total_frequency'] += frequency
        
        # Sort by frequency
        return dict(sorted(consolidated.items(), 
                          key=lambda x: x[1]['total_frequency'], 
                          reverse=True))
    
    def get_hierarchy_stats(self, tag_frequency_map: Dict[str, int]) -> Dict[str, Dict]:
        """Get statistics about genre hierarchy usage."""
        category_stats = {}
        
        for tag, frequency in tag_frequency_map.items():
            category = self.get_category(tag)
            category_name = category.value if category else 'other'
            
            if category_name not in category_stats:
                category_stats[category_name] = {
                    'total_frequency': 0,
                    'unique_genres': 0,
                    'examples': []
                }
            
            category_stats[category_name]['total_frequency'] += frequency
            category_stats[category_name]['unique_genres'] += 1
            
            if len(category_stats[category_name]['examples']) < 5:
                canonical = self.get_canonical_form(tag)
                category_stats[category_name]['examples'].append(f"{tag} → {canonical}")
        
        return category_stats

if __name__ == "__main__":
    # Test the hierarchy
    hierarchy = GenreHierarchy()
    
    test_tags = [
        "prog metal", "progressive metal", "tech death", "melodic death metal",
        "atmospheric black metal", "indie rock", "math rock", "post-hardcore",
        "dream pop", "jazz fusion"
    ]
    
    print("GENRE HIERARCHY TEST")
    print("=" * 40)
    
    for tag in test_tags:
        canonical = hierarchy.get_canonical_form(tag)
        parent = hierarchy.get_parent_genre(tag)
        category = hierarchy.get_category(tag)
        
        print(f"'{tag}' → '{canonical}' (parent: {parent}, category: {category.value if category else 'N/A'})")
