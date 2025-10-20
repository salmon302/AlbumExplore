"""Enhanced tag normalization system with improved pattern recognition."""
import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from .tag_normalizer import TagNormalizer

logger = logging.getLogger(__name__)


class EnhancedTagNormalizer(TagNormalizer):
    """
    Enhanced tag normalizer with improved:
    - Case normalization
    - Hyphen/space handling
    - Misspelling detection
    - Compound genre recognition
    - Multi-tag splitting
    """
    
    def __init__(self, test_mode: bool = False, enable_atomic_tags: bool = True):
        """Initialize with enhanced normalization rules."""
        super().__init__(test_mode=test_mode, enable_atomic_tags=enable_atomic_tags)
        
        # Enhanced misspelling dictionary
        self._enhanced_misspellings = {
            # Core misspellings
            "progresive": "progressive",
            "alternitive": "alternative",
            "expirimental": "experimental",
            
            # New additions from analysis
            "atmosheric": "atmospheric",
            "anternative": "alternative",
            "bluegras": "bluegrass",
            "ghotic": "gothic",
            "cinmatic": "cinematic",
            "electonic": "electronic",
            "pschedelic": "psychedelic",
            "psyechedelic": "psychedelic",
            "pscyhedelic": "psychedelic",
            "kosmsiche": "kosmische",
            "melancolic": "melancholic",
            "tharsh": "thrash",
            "symphnoic": "symphonic",
            "sympohnic": "symphonic",
            "slugde": "sludge",
            "mittelalter-metal": "medieval metal",
            "mitteralter": "medieval",
            "neoclassica": "neoclassical",
            "acapella": "a capella",
            "privitsm": "primitivism",
            "blackend": "blackened",
        }
        
        # Acronyms that should stay uppercase
        self._acronyms = {
            'DSBM', 'OSDM', 'NWOBHM', 'IDM', 'EBM', 'EDM', 
            'MPB', 'AOR', 'EAI', 'RPI', 'RABM'
        }
        
        # Hyphenated compounds (keep hyphen)
        self._hyphen_compounds = {
            'post-metal', 'post-rock', 'post-punk', 'post-hardcore',
            'post-black', 'post-grunge', 'post-industrial', 'post-bop',
            'alt-rock', 'alt-metal', 'alt-country', 'alt-folk', 'alt-pop',
            'avant-garde', 'avant-metal', 'avant-folk', 'avant-jazz',
            'neo-prog', 'neo-psychedelia', 'neo-folk', 'neo-soul',
            'neo-classical', 'neo-medieval',
            'singer-songwriter', 'avant-garde',
            'd-beat', 'no-wave', 'lo-fi',
            'art-rock', 'art-pop', 'art-punk',
            'prog-metal', 'prog-rock',
        }
        
        # Space-separated compounds (keep space)
        self._space_compounds = {
            'death metal', 'black metal', 'doom metal', 'heavy metal',
            'power metal', 'thrash metal', 'speed metal', 'groove metal',
            'drone metal', 'sludge metal', 'folk metal',
            'dream pop', 'indie pop', 'art pop', 'synth pop',
            'noise rock', 'math rock', 'garage rock', 'kraut rock',
            'hard rock', 'space rock', 'psychedelic rock',
            'free jazz', 'jazz fusion', 'jazz funk',
            'a capella', 'new wave', 'new age', 'big band',
        }
        
        # Suffix patterns to normalize
        self._suffix_patterns = {
            'core': {
                'variants': ['core', '-core', ' core'],
                'canonical': 'core',
                'examples': {'metalcore', 'deathcore', 'grindcore', 'mathcore', 'jazzcore'}
            },
            'gaze': {
                'variants': ['gaze', '-gaze'],
                'canonical': 'gaze',
                'examples': {'shoegaze', 'blackgaze', 'doomgaze', 'grungegaze', 'noisegaze', 'nugaze'}
            },
            'wave': {
                'variants': ['wave', '-wave', ' wave'],
                'canonical': 'wave',
                'examples': {'darkwave', 'coldwave', 'chillwave', 'synthwave', 'minimal wave'}
            }
        }
        
        # Modifiers that can prefix base genres
        self._modifiers = {
            'atmospheric', 'melodic', 'technical', 'brutal', 'progressive',
            'experimental', 'avant-garde', 'epic', 'symphonic', 'orchestral',
            'blackened', 'ambient', 'cosmic', 'depressive', 'dissonant',
            'funeral', 'medieval', 'pagan', 'folk', 'viking', 'pirate',
            'industrial', 'electronic', 'acoustic', 'instrumental', 'cinematic',
            'dark', 'gothic', 'occult', 'ritual', 'spiritual', 'ethereal',
            'drone', 'minimalist', 'maximalist', 'neo', 'post', 'proto',
            'old school', 'modern', 'classic', 'traditional', 'contemporary',
            'alternative', 'indie', 'underground', 'mainstream',
        }
        
    def normalize_enhanced(self, tag: str) -> str:
        """
        Enhanced normalization with improved pattern recognition.
        
        Args:
            tag: Raw tag string to normalize
            
        Returns:
            Normalized tag string
        """
        if not tag:
            return tag
            
        # Step 1: Basic cleanup
        tag = tag.strip()
        
        # Step 2: Handle acronyms (preserve before lowercasing)
        is_acronym = tag.upper() in self._acronyms
        
        # Step 3: Lowercase (except acronyms)
        if not is_acronym:
            tag = tag.lower()
        
        # Step 4: Fix misspellings
        tag = self._fix_misspellings(tag)
        
        # Step 5: Normalize whitespace and special characters
        tag = self._normalize_whitespace(tag)
        
        # Step 6: Handle hyphen vs space for known compounds
        tag = self._normalize_compound_format(tag)
        
        # Step 7: Normalize suffix patterns (e.g., -core, -gaze, -wave)
        tag = self._normalize_suffixes(tag)
        
        # Step 8: Handle case variations of multi-word tags
        tag = self._normalize_case_variants(tag)
        
        return tag
    
    def _fix_misspellings(self, tag: str) -> str:
        """Fix common misspellings."""
        tag_lower = tag.lower()
        
        # Check for exact match first
        if tag_lower in self._enhanced_misspellings:
            return self._enhanced_misspellings[tag_lower]
        
        # Check for misspellings within the tag
        for misspelling, correction in self._enhanced_misspellings.items():
            if misspelling in tag_lower:
                tag = tag_lower.replace(misspelling, correction)
        
        return tag
    
    def _normalize_whitespace(self, tag: str) -> str:
        """Normalize whitespace and remove extra spaces."""
        # Replace tabs, newlines, multiple spaces with single space
        tag = re.sub(r'\s+', ' ', tag)
        
        # Remove spaces around hyphens for consistency
        tag = re.sub(r'\s*-\s*', '-', tag)
        
        # Remove spaces around slashes
        tag = re.sub(r'\s*/\s*', '/', tag)
        
        return tag.strip()
    
    def _normalize_compound_format(self, tag: str) -> str:
        """
        Normalize hyphen vs space for known compound tags.
        
        Priority:
        1. If exact match in hyphen_compounds, use hyphen
        2. If exact match in space_compounds, use space
        3. Otherwise, check normalized versions
        """
        tag_normalized = tag.replace('-', ' ').replace('_', ' ')
        tag_normalized = ' '.join(tag_normalized.split())  # Normalize spaces
        
        # Check if it matches a hyphen compound
        for compound in self._hyphen_compounds:
            compound_normalized = compound.replace('-', ' ')
            if tag_normalized == compound_normalized:
                return compound
        
        # Check if it matches a space compound
        for compound in self._space_compounds:
            if tag_normalized == compound:
                return compound
        
        # No match, return with spaces normalized
        return tag_normalized
    
    def _normalize_suffixes(self, tag: str) -> str:
        """Normalize suffix patterns (-core, -gaze, -wave, etc.)."""
        for suffix_type, config in self._suffix_patterns.items():
            canonical = config['canonical']
            examples = config['examples']
            
            # Check if tag is in examples (exact match)
            tag_no_space = tag.replace(' ', '').replace('-', '')
            for example in examples:
                example_no_space = example.replace(' ', '').replace('-', '')
                if tag_no_space == example_no_space:
                    return example
        
        return tag
    
    def _normalize_case_variants(self, tag: str) -> str:
        """
        Ensure consistent casing for multi-word tags.
        Already lowercased, so this mainly ensures consistency.
        """
        return tag
    
    def split_multi_tags(self, tag: str) -> List[str]:
        """
        Split tags containing slashes or other separators.
        
        Examples:
            "Death Metal/Heavy Metal/OSDM" -> ["death metal", "heavy metal", "osdm"]
            "Alternative Rock/Indie Rock/Emo" -> ["alternative rock", "indie rock", "emo"]
        
        Args:
            tag: Tag potentially containing multiple tags
            
        Returns:
            List of individual normalized tags
        """
        # Check for slash separator
        if '/' in tag:
            parts = [p.strip() for p in tag.split('/')]
            return [self.normalize_enhanced(part) for part in parts if part.strip()]
        
        # Single tag
        return [self.normalize_enhanced(tag)]
    
    def get_normalization_stats(self) -> Dict[str, int]:
        """Get statistics on normalization improvements."""
        return {
            'enhanced_misspellings': len(self._enhanced_misspellings),
            'hyphen_compounds': len(self._hyphen_compounds),
            'space_compounds': len(self._space_compounds),
            'suffix_patterns': len(self._suffix_patterns),
            'modifiers': len(self._modifiers),
            'acronyms': len(self._acronyms),
        }
    
    def suggest_corrections(self, tags: List[str]) -> Dict[str, str]:
        """
        Analyze a list of tags and suggest corrections.
        
        Args:
            tags: List of tags to analyze
            
        Returns:
            Dictionary mapping original tags to suggested corrections
        """
        suggestions = {}
        
        for tag in tags:
            normalized = self.normalize_enhanced(tag)
            if normalized != tag.lower():
                suggestions[tag] = normalized
        
        return suggestions
    
    def analyze_tag_consistency(self, tags: List[str]) -> Dict[str, any]:
        """
        Analyze tag list for consistency issues.
        
        Returns:
            Dictionary with analysis results including:
            - case_variants: Tags differing only in case
            - hyphen_variants: Tags differing in hyphen/space usage
            - misspellings: Detected misspellings
            - multi_tags: Tags containing slashes
        """
        from collections import defaultdict
        
        case_variants = defaultdict(list)
        hyphen_variants = defaultdict(list)
        misspellings = []
        multi_tags = []
        
        for tag in tags:
            # Check for case variants
            normalized_lower = tag.lower()
            case_variants[normalized_lower].append(tag)
            
            # Check for hyphen variants
            normalized_hyphen = normalized_lower.replace('-', ' ').replace('_', ' ')
            normalized_hyphen = ' '.join(normalized_hyphen.split())
            hyphen_variants[normalized_hyphen].append(tag)
            
            # Check for misspellings
            if normalized_lower in self._enhanced_misspellings:
                misspellings.append((tag, self._enhanced_misspellings[normalized_lower]))
            
            # Check for multi-tags
            if '/' in tag:
                multi_tags.append(tag)
        
        # Filter to only variants (more than one version)
        case_variants = {k: v for k, v in case_variants.items() if len(v) > 1}
        hyphen_variants = {k: v for k, v in hyphen_variants.items() if len(v) > 1}
        
        return {
            'case_variants': dict(case_variants),
            'hyphen_variants': dict(hyphen_variants),
            'misspellings': misspellings,
            'multi_tags': multi_tags,
            'total_tags': len(tags),
            'unique_normalized': len(set(self.normalize_enhanced(t) for t in tags)),
            'reduction_count': len(tags) - len(set(self.normalize_enhanced(t) for t in tags)),
        }


def demonstrate_improvements():
    """Demonstrate the enhanced normalizer improvements."""
    normalizer = EnhancedTagNormalizer()
    
    print("=" * 80)
    print("ENHANCED TAG NORMALIZER DEMONSTRATION")
    print("=" * 80)
    
    test_cases = [
        # Case inconsistency
        ("Alt Metal", "alt-metal"),
        ("Alt-metal", "alt-metal"),
        ("Alt-Metal", "alt-metal"),
        
        # Misspellings
        ("Atmosheric Black metal", "atmospheric black metal"),
        ("ghotic metal", "gothic metal"),
        ("pschedelic rock", "psychedelic rock"),
        
        # Hyphen/space consistency
        ("Post Metal", "post-metal"),
        ("Post-Metal", "post-metal"),
        ("Post metal", "post-metal"),
        
        # Suffix patterns
        ("Metal-core", "metalcore"),
        ("Metal core", "metalcore"),
        ("Blackgaze", "blackgaze"),
        ("Black-gaze", "blackgaze"),
        
        # Multi-tags
        ("Death Metal/Heavy Metal/OSDM", "death metal/heavy metal/OSDM"),
    ]
    
    print("\nNormalization Examples:")
    print("-" * 80)
    for original, expected in test_cases:
        normalized = normalizer.normalize_enhanced(original)
        status = "✓" if normalized == expected else "✗"
        print(f"{status} '{original}' → '{normalized}' (expected: '{expected}')")
    
    print("\n" + "=" * 80)
    print("Statistics:")
    print("-" * 80)
    stats = normalizer.get_normalization_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return normalizer


if __name__ == "__main__":
    demonstrate_improvements()
