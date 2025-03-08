"""
Tag Consolidation Rules

This module defines rules for consolidating similar tags based on analysis
of the tag data in the album database.
"""

from typing import Dict, List, Set, Tuple, Optional


class ConsolidationRules:
    """Rules for tag consolidation based on analysis."""

    # Primary tag mappings (variant -> canonical form)
    PRIMARY_MAPPINGS = {
        # Progressive metal variants
        "prog-metal": "progressive metal",
        "prog metal": "progressive metal",
        "prog-Metal": "progressive metal",
        "prog metal": "progressive metal",
        "progressive metalcore": "progressive metalcore",  # Keep as distinct subgenre
        "progressive jazz metal": "jazz metal",  # Map to jazz metal

        # Compound tags identified in analysis
        "prog-metal/rock": "progressive metal",  # Map to primary genre
        "melodic prog-metal/rock": "progressive metal",  # Map to primary genre
        "prog-rock/metal": "progressive metal",  # Map to primary genre
        "atmospheric/post-black metal": "atmospheric black metal",  # Consolidate compound
        "atmospheric sludge metal": "atmospheric metal",  # Consolidate compound
        "funeral doom metal": "funeral doom metal",  # Keep as distinct
        "blackened death metal": "blackened death metal",  # Keep as distinct
        "blackened sludge metal": "blackened metal",  # Consolidate

        # Death metal variants
        "death-metal": "death metal",
        "deathmetal": "death metal",
        "melodic death-metal": "melodic death metal",
        "melodic deathmetal": "melodic death metal",
        "melo-death": "melodic death metal",
        "melo death": "melodic death metal",
        "tech death": "technical death metal",
        "tech-death": "technical death metal",
        "technical-death": "technical death metal",
        "techdeath": "technical death metal",
        "technical death metal": "technical death metal",

        # Black metal variants
        "black-metal": "black metal",
        "blackmetal": "black metal",
        "atmospheric black-metal": "atmospheric black metal",
        "atmo black": "atmospheric black metal",
        "post-black": "post-black metal",
        "post black": "post-black metal",
        "blackgaze": "blackgaze",  # Keep as distinct subgenre

        # Doom metal variants
        "doom-metal": "doom metal",
        "doommetal": "doom metal",
        "funeral doom": "funeral doom metal",
        "funeral-doom": "funeral doom metal",

        # Core genre variants
        "metalcore": "metalcore",  # Standard form
        "metal-core": "metalcore",
        "deathcore": "deathcore",  # Standard form
        "death-core": "deathcore",
        "mathcore": "mathcore",  # Standard form
        "math-core": "mathcore",

        # Post-metal/rock variants
        "post-metal": "post-metal",  # Keep hyphenated form
        "post metal": "post-metal",
        "postmetal": "post-metal",
        "post-rock": "post-rock",  # Keep hyphenated form
        "post rock": "post-rock",
        "postrock": "post-rock",

        # Progressive rock variants
        "prog-rock": "progressive rock",
        "prog rock": "progressive rock",
        "progrock": "progressive rock",

        # Djent variants
        "djent": "djent",
        "progressive djent": "djent",  # Simplify to parent genre

        # Folk metal variants
        "folk metal": "folk metal",
        "folk-metal": "folk metal",
        "folkish metal": "folk metal",

        # Power metal variants
        "power metal": "power metal",
        "power-metal": "power metal",
        "powermetal": "power metal",

        # Electronic variants
        "electronic": "electronic",
        "electronica": "electronic",
        "electro": "electronic",

        # Jazz variants
        "jazz fusion": "jazz fusion",
        "jazz-fusion": "jazz fusion",
        "jazz rock": "jazz rock",
        "jazz-rock": "jazz rock",

        # Psychedelic variants
        "psychedelic": "psychedelic",
        "psych": "psychedelic",
        "psychedelic rock": "psychedelic rock",
        "psych rock": "psychedelic rock",
        "psych-rock": "psychedelic rock",
        "psychedelick rock": "psychedelic rock",  # Spelling correction found in analysis

        # Avant-garde variants
        "avant-garde": "avant-garde",
        "avant garde": "avant-garde",
        "avantgarde": "avant-garde",

        # Art rock variants
        "art rock": "art rock",
        "art-rock": "art rock",

        # Regional/style variants
        "oriental rock": "world fusion",
        "grunge rock": "grunge",

        # Spelling corrections
        "ambiental": "ambient",
        "atmosphereic": "atmospheric",
        "expiremental": "experimental",
        "symphonyc": "symphonic",
        "pyschedelic": "psychedelic",
        "progresive": "progressive",
        "proggressive": "progressive",
        "expermental": "experimental",
    }

    # Tag group hierarchies (child -> parent relationships)
    TAG_HIERARCHIES = {
        # Metal subgenres
        "progressive metal": "metal",
        "death metal": "metal",
        "black metal": "metal",
        "doom metal": "metal",
        "power metal": "metal",
        "thrash metal": "metal",
        "folk metal": "metal",
        "gothic metal": "metal",
        "djent": "metal",
        "sludge metal": "metal",
        "stoner metal": "metal",
        "metalcore": "metal",
        "deathcore": "metal",
        "technical death metal": "death metal",
        "melodic death metal": "death metal",
        "symphonic metal": "metal",
        "industrial metal": "metal",
        "nu metal": "metal",
        "groove metal": "metal",
        "funeral doom metal": "doom metal",
        "blackened death metal": "death metal",
        "blackened metal": "metal",
        
        # Rock subgenres
        "progressive rock": "rock",
        "psychedelic rock": "rock",
        "hard rock": "rock",
        "alternative rock": "rock",
        "post-rock": "rock",
        "math rock": "rock",
        "indie rock": "rock",
        "stoner rock": "rock",
        "space rock": "rock",
        "art rock": "rock",
        "grunge": "rock",
        
        # Jazz subgenres
        "jazz fusion": "jazz",
        "jazz rock": "jazz",
        "jazz metal": "jazz",
        
        # Electronic subgenres
        "industrial": "electronic",
        "synthwave": "electronic",
        "ambient": "electronic",
        "darkwave": "electronic",
        "ebm": "electronic",
        "idm": "electronic",
        
        # Core subgenres
        "deathcore": "core",
        "metalcore": "core",
        "mathcore": "core",
        "grindcore": "core",
        "hardcore": "core",
        "post-hardcore": "core",
        
        # Post subgenres
        "post-metal": "post",
        "post-rock": "post",
        "post-black metal": "post",
        "post-hardcore": "post",
        
        # Atmospheric subgenres
        "atmospheric black metal": "atmospheric metal",
        "atmospheric metal": "metal",
        
        # World fusion
        "world fusion": "fusion",
    }
    
    # Style modifiers that can be applied to genres
    STYLE_MODIFIERS = {
        "atmospheric", "technical", "melodic", "symphonic",
        "progressive", "experimental", "avant-garde", "instrumental",
        "brutal", "epic", "folk", "gothic", "industrial",
        "blackened", "cosmic", "dissonant", "electronic", "extreme",
        "heavy", "melodic", "neo", "raw", "traditional"
    }
    
    # Tags that should be preserved as distinct entities (not merged)
    PRESERVE_DISTINCT = {
        "blackgaze",  # Distinct from both black metal and shoegaze
        "djent",      # Distinct from progressive metal
        "mathcore",   # Distinct from math rock and metalcore
        "post-metal", # Distinct from post-rock and metal
        "folk metal", # Distinct genre fusion
        "jazz fusion", # Distinct genre
        "funeral doom metal", # Distinct doom subgenre
        "blackened death metal", # Distinct metal subgenre
    }

    # Split tag markers - these indicate compound tags that should be split
    SPLIT_MARKERS = ['/', '+', ' and ', ' & ', ' with ', ' meets ']

    @classmethod
    def get_canonical_form(cls, tag: str) -> str:
        """Get the canonical form of a tag based on consolidation rules.
        
        Args:
            tag: The original tag string
            
        Returns:
            The canonical form of the tag
        """
        tag = tag.lower().strip()
        
        # Direct mapping check
        if tag in cls.PRIMARY_MAPPINGS:
            return cls.PRIMARY_MAPPINGS[tag]
        
        # Check for compound tags that should be split
        for marker in cls.SPLIT_MARKERS:
            if marker in tag and marker != '/':  # Skip '/' as it's already handled in PRIMARY_MAPPINGS
                parts = [part.strip() for part in tag.split(marker)]
                # Take the first part only if it's a known tag
                for part in parts:
                    canonical = cls.get_canonical_form(part)
                    if canonical in cls.TAG_HIERARCHIES or canonical in cls.PRESERVE_DISTINCT:
                        return canonical
                
        return tag
    
    @classmethod
    def get_parent_tags(cls, tag: str) -> List[str]:
        """Get parent tags for a given tag.
        
        Args:
            tag: The tag to find parents for
            
        Returns:
            A list of parent tags
        """
        canonical = cls.get_canonical_form(tag)
        return [cls.TAG_HIERARCHIES[canonical]] if canonical in cls.TAG_HIERARCHIES else []
    
    @classmethod
    def is_style_modifier(cls, tag: str) -> bool:
        """Check if a tag is a style modifier.
        
        Args:
            tag: The tag to check
            
        Returns:
            True if the tag is a style modifier, False otherwise
        """
        return tag.lower() in cls.STYLE_MODIFIERS
    
    @classmethod
    def should_preserve_distinct(cls, tag: str) -> bool:
        """Check if a tag should be preserved as distinct.
        
        Args:
            tag: The tag to check
            
        Returns:
            True if the tag should be preserved as distinct, False otherwise
        """
        return tag.lower() in cls.PRESERVE_DISTINCT
    
    @classmethod
    def split_compound_tag(cls, tag: str) -> List[str]:
        """Split a compound tag into constituent parts.
        
        Args:
            tag: The tag to split
            
        Returns:
            List of constituent tags
        """
        tag = tag.lower().strip()
        
        # Check direct mappings first
        if tag in cls.PRIMARY_MAPPINGS:
            return [cls.PRIMARY_MAPPINGS[tag]]
            
        # Look for split markers
        for marker in cls.SPLIT_MARKERS:
            if marker in tag:
                parts = [part.strip() for part in tag.split(marker)]
                # Get canonical form for each part
                return [cls.get_canonical_form(part) for part in parts if part]
                
        # No splitting needed
        return [tag]