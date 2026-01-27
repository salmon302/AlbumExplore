"""Tag normalization system with atomic tag support."""
import re
import json
import os
import logging
import unicodedata
from typing import Dict, Optional, List, Set, Tuple
from collections import defaultdict
from albumexplore.tags.config.tag_rules_config import TagRulesConfig

logger = logging.getLogger(__name__)

class TagNormalizer:
    """Handles tag normalization and variant consolidation with atomic tag support."""
    
    def __init__(self, test_mode: bool = False, enable_atomic_tags: bool = True, rules_file: str = None):
        """Initialize the normalizer with rules.
        
        Args:
            test_mode: If True, use test configuration instead of production rules
            enable_atomic_tags: If True, enable atomic tag decomposition
        """
        self._rules_config = TagRulesConfig(test_mode=test_mode)
        self._variant_cache = {}
        self._single_instance_tags = set()
        self._merge_history = []
        self._similarity_threshold = 0.7
        self._min_frequency_for_normalization = 2
        self._active = True  # Added: Normalization is active by default
        
        # Atomic tag system
        self._enable_atomic_tags = enable_atomic_tags
        # Optional override for the rules file path (useful for dry-run/testing)
        self._rules_file = rules_file
        self._atomic_config = {}
        self._atomic_decomposition_cache = {}
        self._valid_atomic_tags = set()
        # Rule application statistics (counts how many tags each rule modified)
        self._rule_stats = defaultdict(int)
        
        # Enhanced normalization patterns
        self._hyphen_compounds = {
            # Post- prefixes
            'post-metal', 'post-rock', 'post-punk', 'post-hardcore',
            'post-black', 'post-grunge', 'post-industrial', 'post-bop',
            # Alt- prefixes
            'alt-rock', 'alt-metal', 'alt-country', 'alt-folk', 'alt-pop',
            'alt-blues', 'alt-jazz', 'alt-punk', 'alt-prog',
            # Avant- prefixes
            'avant-garde', 'avant-metal', 'avant-folk', 'avant-jazz',
            'avant-pop', 'avant-prog', 'avant-rock', 'avant-punk',
            'avant-black', 'avant-funk', 'avant-latin',
            # Neo- prefixes
            'neo-prog', 'neo-psychedelia', 'neo-folk', 'neo-soul',
            'neo-classical', 'neo-medieval', 'neo-punk',
            # Art- prefixes (only art-rock and art-punk use hyphens)
            'art-rock', 'art-punk',
            # Prog- prefixes  
            'prog-metal', 'prog-rock',
            # Death- compounds
            'death-doom', 'death-industrial',
            # Other compounds
            'singer-songwriter', 'stoner-rock',
            'd-beat', 'no-wave', 'lo-fi',
        }
        
        # Suffix patterns for compound normalization
        # These should generally NOT use hyphens (e.g., "blackgaze" not "black-gaze")
        self._suffix_compounds = {
            'gaze': {'blackgaze', 'doomgaze', 'grungegaze', 'noisegaze', 'nugaze', 'shoegaze'},
            'core': {'deathcore', 'metalcore', 'grindcore', 'hardcore', 'emocore', 'mathcore'},
            'wave': {'darkwave', 'coldwave', 'chillwave', 'synthwave', 'dolewave'},
        }
        
        if self._enable_atomic_tags:
            self._load_atomic_config()
        
    def set_active(self, active: bool):
        """Set the active state of the normalizer."""
        self._active = active

    def is_active(self) -> bool:
        """Check if normalization is currently active."""
        return self._active

    def normalize(self, tag: str) -> str:
        """Convert a tag to its normalized form."""
        if not tag:
            return tag
            
        # Convert to lowercase and strip whitespace
        original_cleaned_tag = tag.lower().strip()

        if not self._active:
            return original_cleaned_tag # Return cleaned original if normalization is off
            
        # Check cache first
        if original_cleaned_tag in self._variant_cache:
            return self._variant_cache[original_cleaned_tag]
        # Apply enhanced normalization (whitespace, misspellings, punctuation, diacritics, compounds)
        enhanced = self.normalize_enhanced(original_cleaned_tag)

        # Get normalized form from config based on enhanced token
        normalized = self._rules_config.get_normalized_form(enhanced)

        # Cache and return result
        self._variant_cache[original_cleaned_tag] = normalized
        return normalized
        
    def get_category(self, tag: str) -> str:
        """Get the category for a tag based on the config mappings."""
        normalized = self.normalize(tag)
        category = self._rules_config.get_category_for_tag(normalized)
        return category if category else 'other'
        
    def register_single_instance_tag(self, tag: str, frequency: int = 1):
        """Register a tag as a single-instance tag for special handling."""
        if frequency <= self._min_frequency_for_normalization:
            self._single_instance_tags.add(tag.lower().strip())
    
    def get_single_instance_tags(self) -> Set[str]:
        """Get all registered single-instance tags."""
        return self._single_instance_tags
    
    def suggest_normalization_for_single_instance(self, tag: str) -> List[Tuple[str, float, str]]:
        """Suggest possible normalizations for a single-instance tag."""
        tag = tag.lower().strip()
        suggestions = []
        
        # Check existing mappings in config
        single_instance_mappings = self._rules_config.get_single_instance_mappings()
        if tag in single_instance_mappings:
            suggestions.append((single_instance_mappings[tag], 1.0, "Existing rule"))
            
        # Get category information
        category = self._rules_config.get_category_for_tag(tag)
        if category:
            category_info = self._rules_config.get_category_info(category)
            if category_info:
                # Check if it matches any core terms
                for term in category_info.get('core_terms', []):
                    if term in tag:
                        suggestions.append((category, 0.8, "Genre extraction"))
                        break
                
                # Check if it's a modified primary genre
                for genre in category_info.get('primary_genres', []):
                    if genre in tag:
                        for modifier in category_info.get('modifiers', []):
                            if modifier in tag:
                                suggestion = f"{modifier} {genre}"
                                suggestions.append((suggestion, 0.9, "Category pattern"))
                                break
        
        # Return sorted suggestions
        return sorted(suggestions, key=lambda x: x[1], reverse=True)
    
    def add_variant(self, variant: str, canonical: str):
        """Register a new variant mapping."""
        variant = variant.lower().strip()
        canonical = canonical.lower().strip()
        self._variant_cache[variant] = canonical
        
        # If it was a single-instance tag, remove it
        if variant in self._single_instance_tags:
            self._single_instance_tags.remove(variant)
            
        # Add to merge history
        self._merge_history.append({
            'variant': variant,
            'canonical': canonical,
            'timestamp': self._get_timestamp()
        })
        
    def add_single_instance_rule(self, tag: str, normalized_tag: str):
        """Add a rule for normalizing a single-instance tag."""
        tag = tag.lower().strip()
        normalized_tag = normalized_tag.lower().strip()
        
        config = self._rules_config._config  # Access underlying config
        if 'single_instance_mappings' not in config:
            config['single_instance_mappings'] = {}
            
        config['single_instance_mappings'][tag] = normalized_tag
        self._variant_cache[tag] = normalized_tag
        
        # Save changes to config file
        self._rules_config.save_changes()
        
        # If it was in single-instance tags set, remove it
        if tag in self._single_instance_tags:
            self._single_instance_tags.remove(tag)
    
    def get_merge_history(self) -> List[Dict]:
        """Get the history of all tag merges."""
        return self._merge_history
    
    def clear_cache(self):
        """Clear the variant cache."""
        self._variant_cache.clear()
        
    def reload_config(self):
        """Reload the configuration file."""
        self._rules_config.reload()
        self.clear_cache()
        
    def _get_timestamp(self) -> str:
        """Get current timestamp for merge history."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    # ===== ATOMIC TAG SYSTEM METHODS =====
    
    def _load_atomic_config(self):
        """Load atomic tag configuration from the main config file."""
        try:
            # Get the config file path relative to this module
            # Navigate from tags/normalizer/ to the config directory
            if self._rules_file:
                config_path = self._rules_file
            else:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                albumexplore_dir = os.path.dirname(os.path.dirname(current_file_dir))  # Go up from tags/normalizer/ to albumexplore/
                config_path = os.path.join(albumexplore_dir, 'config', 'tag_rules.json')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load atomic decomposition rules
            self._atomic_config = config.get('atomic_decomposition', {})
            
            # Load valid atomic tags
            atomic_tags_config = config.get('atomic_tags', {})
            if 'all_valid_tags' in atomic_tags_config:
                self._valid_atomic_tags = set(atomic_tags_config['all_valid_tags'])
            
            logger.info(f"Loaded {len(self._atomic_config)} atomic decomposition rules")
            logger.info(f"Loaded {len(self._valid_atomic_tags)} valid atomic tags")
            
        except Exception as e:
            logger.warning(f"Could not load atomic config: {e}")
            self._atomic_config = {}
            self._valid_atomic_tags = set()
    
    def is_atomic_enabled(self) -> bool:
        """Check if atomic tag system is enabled."""
        return self._enable_atomic_tags
    
    def enable_atomic_tags(self, enable: bool = True):
        """Enable or disable atomic tag processing."""
        self._enable_atomic_tags = enable
        if enable and not self._atomic_config:
            self._load_atomic_config()
    
    def set_atomic_mode(self, enabled: bool):
        """Set atomic mode on/off (alias for enable_atomic_tags for compatibility).
        
        Args:
            enabled: True to enable atomic tag processing, False to disable
        """
        self.enable_atomic_tags(enabled)
    
    def get_atomic_mode(self) -> bool:
        """Get current atomic mode state (alias for is_atomic_enabled for compatibility).
        
        Returns:
            True if atomic mode is enabled, False otherwise
        """
        return self.is_atomic_enabled()
    
    def normalize_to_atomic(self, tag: str) -> List[str]:
        """Normalize a tag and decompose to atomic components.
        
        Args:
            tag: The tag to normalize and decompose
            
        Returns:
            List of atomic components for the tag
        """
        if not tag or not self._enable_atomic_tags:
            return [self.normalize(tag)] if tag else []
        
        # Clean and normalize basic format
        cleaned_tag = tag.lower().strip()
        
        # Check cache first
        if cleaned_tag in self._atomic_decomposition_cache:
            return self._atomic_decomposition_cache[cleaned_tag]
        
        # Apply atomic decomposition if rule exists
        if cleaned_tag in self._atomic_config:
            atomic_components = self._atomic_config[cleaned_tag].copy()
            self._atomic_decomposition_cache[cleaned_tag] = atomic_components
            return atomic_components
        
        # Check for case variations and format variations
        normalized_for_lookup = cleaned_tag.replace('-', ' ').replace('_', ' ')
        for rule_tag, components in self._atomic_config.items():
            rule_normalized = rule_tag.replace('-', ' ').replace('_', ' ')
            if rule_normalized == normalized_for_lookup:
                atomic_components = components.copy()
                self._atomic_decomposition_cache[cleaned_tag] = atomic_components
                return atomic_components
        
        # If no decomposition rule found, return normalized single tag
        normalized_single = self.normalize(tag)
        result = [normalized_single]
        self._atomic_decomposition_cache[cleaned_tag] = result
        return result
    
    def normalize_tag_list_to_atomic(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags using atomic decomposition.
        
        Args:
            tags: List of tags to normalize and decompose
            
        Returns:
            List of unique atomic components from all tags
        """
        if not tags:
            return []
        
        if not self._enable_atomic_tags:
            return [self.normalize(tag) for tag in tags if tag]
        
        atomic_tags = []
        for tag in tags:
            if tag:  # Skip empty tags
                atomic_components = self.normalize_to_atomic(tag)
                atomic_tags.extend(atomic_components)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_atomic_tags = []
        for tag in atomic_tags:
            if tag and tag not in seen:
                seen.add(tag)
                unique_atomic_tags.append(tag)
        
        return unique_atomic_tags
    
    def validate_atomic_tag(self, tag: str) -> bool:
        """Check if a tag is a valid atomic component.
        
        Args:
            tag: The tag to validate
            
        Returns:
            True if the tag is a valid atomic component
        """
        if not self._enable_atomic_tags:
            return True
        
        return tag.lower().strip() in self._valid_atomic_tags
    
    def get_atomic_statistics(self) -> Dict[str, any]:
        """Get statistics about atomic tag system usage.
        
        Returns:
            Dictionary containing atomic tag statistics
        """
        return {
            'atomic_enabled': self._enable_atomic_tags,
            'decomposition_rules': len(self._atomic_config),
            'decomposition_cache_size': len(self._atomic_decomposition_cache),
            'valid_atomic_tags': len(self._valid_atomic_tags),
            'version': '1.0'
        }
    
    def clear_atomic_cache(self):
        """Clear the atomic decomposition cache."""
        self._atomic_decomposition_cache.clear()
    
    def reload_atomic_config(self):
        """Reload the atomic tag configuration."""
        if self._enable_atomic_tags:
            self._load_atomic_config()
            self.clear_atomic_cache()
    
    # ===== ENHANCED NORMALIZATION METHODS =====
    
    def normalize_enhanced(self, tag: str) -> str:
        """
        Enhanced normalization implementing prioritized rules A..F:
        A) Strip/normalize suffix qualifiers (ish, like, esque, related, oriented, ?)
        B) Connector normalization (slashes, multiple hyphens, ' - ' -> space)
        C) Unicode NFKD + diacritic stripping and invisible char removal
        D) Explicit misspelling map (high-confidence)
        E) Region decomposition (whitelist)
        F) Plural / spacing normalization (small high-confidence mappings)
        
        This function is intentionally conservative and tracks counts of
        how many tags each sub-rule modifies via self._rule_stats.
        """
        if not tag:
            return tag
        
        original = tag
        tag = tag.strip()
        
        # Lowercase for canonical processing
        tag = tag.lower()
        
        # ---- C: Unicode normalization & diacritic stripping + invisible char removal ----
        # Normalize to NFKD and remove combining diacritic marks
        try:
            nkfd = unicodedata.normalize('NFKD', tag)
            tag = ''.join(ch for ch in nkfd if not unicodedata.combining(ch))
        except Exception:
            # If unicodedata fails for any reason, continue with original lowercase
            pass
        # Remove directional/invisible/zero-width chars (common ranges)
        tag = re.sub(r'[\u200B-\u200F\u202A-\u202E\uFEFF]', '', tag)
        tag = tag.strip()
        
        # ---- A: Strip/normalize suffix qualifiers (conservative) ----
        # Modified to require a separator (hyphen or space) before the suffix
        # This prevents stripping 'ish' from words like 'swedish', 'british', 'polish'
        qualifier_re = re.compile(r"(?i)^\s*(?P<base>.+?)(?:[-\s](?:ish|like|esque|related|oriented)|\?)\s*$")
        m = qualifier_re.match(tag)
        if m:
            base = m.group("base").strip()
            if base and base != tag:
                self._rule_stats['suffix_qualifier'] += 1
                tag = base
        
        # ---- B: Connector normalization ----
        # Replace slashes with spaces
        before_connector = tag
        tag = tag.replace('/', ' ')
        # Collapse multiple hyphens to single space, and normalize " - " to space
        tag = re.sub(r'-{2,}', ' ', tag)          # multiple hyphens
        tag = re.sub(r'\s*-\s*', ' ', tag)        # hyphen with optional spaces
        # Collapse multiple spaces to single
        tag = re.sub(r'\s+', ' ', tag).strip()
        if tag != before_connector:
            self._rule_stats['connector_normalization'] += 1
        
        # ---- D: Explicit misspelling map (high-confidence) ----
        explicit_misspell_map = {
            "ghotic metal": "gothic metal",
            "sympohnic": "symphonic",
            "tharsh metal": "thrash metal",
            "acapella": "a capella",
            "bluegras": "bluegrass",
            "american privitsm": "american primitivism",
        }
        if tag in explicit_misspell_map:
            self._rule_stats['explicit_misspelling'] += 1
            tag = explicit_misspell_map[tag]
        
        # ---- Extra explicit examples (verbatim high-confidence mappings) ----
        # Conservative exact-match mappings from prioritized examples list.
        explicit_examples = {
            # Suffix removals (strip qualifiers)
            "deep purple-ish": "deep purple",
            "floyd-esque": "floyd",
            "crimson-esque": "crimson",
            "crimson-y": "crimson",
            "hawkwind-ish": "hawkwind",
            "king gizzard-like": "king gizzard",
            "riverside-esque": "riverside",
            "soft machine-related": "soft machine",
            "primus-related": "primus",
            "gong-related": "gong",
            "rush-oriented": "rush",
            "piano-oriented": "piano",
            "keyboard-driven": "keyboard",
            "fleetwood mac?": "fleetwood mac",
            "seventh wonder-ish": "seventh wonder",
            # Connector examples (prefer single-space separation)
            "afro-funk": "afro funk",
            "afro-rock": "afro rock",
            "bolero-beat": "bolero beat",
            "disco-funk": "disco funk",
            "disco-pop": "disco pop",
            "disco-punk": "disco punk",
            "electro-ambient": "electro ambient",
            "italo-disco": "italo disco",
            "death metal/heavy metal/osdm": "death metal heavy metal osdm",
            "doom metal/rock": "doom metal rock",
            "doom rock/metal": "doom rock metal",
            "powerviolence/black metal/death metal": "powerviolence black metal death metal",
            "prog -rock": "prog rock",
            "prog-?": "prog",
            # Unicode / invisible char edgecases (mapped to cleaned forms)
            "reggaetón": "reggaeton",
            "post-metal\u200e": "post-metal",
            "neue deutsche härte": "neue deutsche harte",
            # Region / plural explicit small mappings (verbatim)
            "korean folk": "folk",
            "italian prog": "prog",
            "scottish music": "music",
            "scottish folk music": "folk music",
            "welsh rock": "rock",
            "welsh folk music": "folk music",
            "oriental rock": "rock",
            "southern soul": "soul",
        }
        # Flexible lookup: allow hyphen/space variants to match explicit_examples keys
        lookup_variants = {tag, tag.replace(' ', '-'), tag.replace('-', ' ')}
        matched = None
        for ex_key, ex_val in explicit_examples.items():
            # Normalize key variants similarly
            key_variants = {ex_key, ex_key.replace(' ', '-'), ex_key.replace('-', ' ')}
            if lookup_variants & key_variants:
                matched = ex_val
                break
        if matched:
            self._rule_stats['explicit_examples'] += 1
            tag = matched
        
        # ---- E: Region decomposition (tokenization) ----
        # If tag is of form "<region> <genre...>" and region in whitelist, drop region
        region_re = re.compile(r"(?i)^(?P<region>\w+)\s+(?P<genre>.+)$")
        m2 = region_re.match(tag)
        # Removed "southern" to protect "Southern Rock/Metal"
        # Removed "oriental" to protect "Oriental Metal"
        # Removed "american" to protect "American Primitivism"
        region_whitelist = {"korean", "italian", "scottish", "welsh", "brazil", "british"}
        if m2:
            region = m2.group("region").lower()
            genre = m2.group("genre").strip()
            if region in region_whitelist and genre:
                self._rule_stats['region_decomposed'] += 1
                # Log original -> genre transformation for debugging
                logger.debug("Region decomposition: '%s' -> '%s' (dropped region '%s')", original, genre, region)
                tag = genre
        
        # ---- G: Modifier collapse (conservative) ----
        # Collapse "<modifier> <genre>" -> "<genre>" only when the derived genre is known/canonical.
        # This is intentionally conservative: only modifiers in the small whitelist are considered
        # and the collapse is applied only if the genre_candidate exists in known atomic/canonical tags.
        # Removed 'hard' to prevent 'hard rock' -> 'rock'
        modifier_re = re.compile(r'(?i)^(?P<modifier>(?:deep|cavernous|hellenic|hill|micro|early|late|proto))\s+(?P<genre>.+)$')
        m3 = modifier_re.match(tag)
        if m3:
            genre_candidate = m3.group('genre').strip()
            canonical_exists = False
            try:
                # Check against valid atomic tags loaded from config
                if genre_candidate in self._valid_atomic_tags:
                    canonical_exists = True
                # Check atomic decomposition keys from the rules config
                cfg = getattr(self._rules_config, '_config', {}) or {}
                atomic_keys = set(cfg.get('atomic_decomposition', {}).keys())
                if genre_candidate in atomic_keys:
                    canonical_exists = True
                # Check single_instance_mappings targets to avoid mapping to a non-canonical custom tag
                sims = cfg.get('single_instance_mappings', {}) or {}
                if genre_candidate in set(sims.values()):
                    canonical_exists = True
            except Exception:
                canonical_exists = False
            if canonical_exists:
                self._rule_stats['modifier_collapse'] += 1
                logger.debug("Modifier collapse: '%s' -> '%s' (dropped modifier)", original, genre_candidate)
                tag = genre_candidate
        
        # ---- F: Plural / small spacing normalization (high-confidence mappings) ----
        small_mappings = {
            "j pop": "j-pop",
            "j rock": "j-rock",
            "rock-pop": "rock pop",
        }
        if tag in small_mappings:
            self._rule_stats['small_mappings'] += 1
            tag = small_mappings[tag]
        
        # Conservative singularization: only for single-word tokens longer than 3 chars
        # Only singularize when the singular form is present in the known valid atomic tags
        if ' ' not in tag and tag.endswith('s') and len(tag) > 3:
            singular = tag[:-1]
            should_singularize = False
            try:
                if singular in self._valid_atomic_tags:
                    should_singularize = True
            except Exception:
                # If valid_atomic_tags not available, skip singularization
                should_singularize = False
            if should_singularize:
                self._rule_stats['simple_singularization'] += 1
                tag = singular
        
        # Final whitespace normalization
        tag = re.sub(r'\s+', ' ', tag).strip()
        
        # Return final normalized token
        return tag

        # Remove diacritics (normalize to ASCII)
        try:
            import unicodedata
            tag = unicodedata.normalize('NFKD', tag)
            tag = ''.join(c for c in tag if not unicodedata.combining(c))
        except Exception:
            # If unicodedata isn't available for some reason, continue
            pass

        # Normalize whitespace and special characters
        tag = self._normalize_whitespace(tag)

        # Remove surrounding punctuation and common wrappers
        tag = re.sub(r"^[\"'\(\[\{]+", '', tag)
        tag = re.sub(r"[\"'\)\]\}]+$", '', tag)
        tag = re.sub(r"[\.!\?,:;]+$", '', tag)

        # Apply word-level misspelling corrections
        tag = self._correct_misspellings_in_phrase(tag)

        # Handle hyphen/space normalization for known compounds
        tag = self._normalize_compound_format(tag)

        # Final whitespace normalization
        tag = self._normalize_whitespace(tag)

        return tag
    
    def _correct_misspellings_in_phrase(self, tag: str) -> str:
        """
        Correct misspellings in multi-word tags.
        
        Example: "atmosheric black metal" -> "atmospheric black metal"
        """
        misspellings = self._rules_config.get_misspellings()
        
        # Build a reverse mapping: variant -> correct
        variant_map = {}
        for correct, variants in misspellings.items():
            for variant in variants:
                variant_map[variant.lower()] = correct
        
        # Split tag into words and correct each
        words = tag.split()
        corrected_words = []
        
        for word in words:
            # Check if this word is a misspelling
            if word in variant_map:
                corrected_words.append(variant_map[word])
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
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
        1. Check suffix compounds (should be no hyphen/space)
        2. If exact match in hyphen_compounds, use hyphen
        3. Otherwise, check normalized versions
        """
        tag_normalized = tag.replace('-', ' ').replace('_', ' ')
        tag_normalized = ' '.join(tag_normalized.split())  # Normalize spaces
        
        # Check suffix compounds first (blackgaze, doomgaze, etc.)
        for suffix, compounds in self._suffix_compounds.items():
            for compound in compounds:
                # Create spaced version for comparison
                compound_spaced = re.sub(f'{suffix}$', f' {suffix}', compound)
                if tag_normalized == compound_spaced or tag_normalized == compound:
                    return compound  # Return without space/hyphen
        
        # Check if it matches a hyphen compound
        for compound in self._hyphen_compounds:
            compound_normalized = compound.replace('-', ' ')
            if tag_normalized == compound_normalized:
                return compound
        
        # No match, return with spaces normalized
        return tag_normalized
    
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
    
    def analyze_tag_consistency(self, tags: List[str]) -> Dict[str, any]:
        """
        Analyze tag list for consistency issues.
        
        Args:
            tags: List of tags to analyze
        
        Returns:
            Dictionary with analysis results including:
            - case_variants: Tags differing only in case
            - hyphen_variants: Tags differing in hyphen/space usage
            - multi_tags: Tags containing slashes
            - total_tags: Total number of tags
            - unique_normalized: Unique tags after normalization
            - reduction_count: Number of tags that would be eliminated
        """
        case_variants = defaultdict(list)
        hyphen_variants = defaultdict(list)
        multi_tags = []
        
        for tag in tags:
            # Check for case variants
            normalized_lower = tag.lower()
            case_variants[normalized_lower].append(tag)
            
            # Check for hyphen variants
            normalized_hyphen = normalized_lower.replace('-', ' ').replace('_', ' ')
            normalized_hyphen = ' '.join(normalized_hyphen.split())
            hyphen_variants[normalized_hyphen].append(tag)
            
            # Check for multi-tags
            if '/' in tag:
                multi_tags.append(tag)
        
        # Filter to only variants (more than one version)
        case_variants = {k: v for k, v in case_variants.items() if len(v) > 1}
        hyphen_variants = {k: v for k, v in hyphen_variants.items() if len(v) > 1}
        
        unique_normalized = len(set(self.normalize_enhanced(t) for t in tags))
        
        return {
            'case_variants': dict(case_variants),
            'hyphen_variants': dict(hyphen_variants),
            'multi_tags': multi_tags,
            'total_tags': len(tags),
            'unique_normalized': unique_normalized,
            'reduction_count': len(tags) - unique_normalized,
        }

