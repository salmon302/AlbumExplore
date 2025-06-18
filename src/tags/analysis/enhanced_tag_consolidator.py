from typing import Dict, List, Tuple, Set, Optional
import pandas as pd
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from .tag_analyzer import TagAnalyzer
from .tag_similarity import TagSimilarity

class TagCategory(Enum):
    GENRE = "genre"
    STYLE_MODIFIER = "style_modifier"
    TECHNIQUE = "technique"
    REGIONAL = "regional"
    LOCATION = "location"
    VOCAL_STYLE = "vocal_style"
    INSTRUMENT = "instrument"
    THEME = "theme"
    ERA = "era"
    UNKNOWN = "unknown"

@dataclass
class TagRule:
    pattern: str
    category: TagCategory
    primary_tag: Optional[str] = None
    priority: int = 0
    filter_out: bool = False

@dataclass
class HierarchyRelation:
    parent: str
    child: str
    strength: float

class EnhancedTagConsolidator:
    def __init__(self, analyzer: TagAnalyzer):
        self.analyzer = analyzer
        self.similarity = TagSimilarity(analyzer)
        self.categorized_tags: Dict[TagCategory, Set[str]] = defaultdict(set)
        self.tag_hierarchies: Dict[str, List[str]] = defaultdict(list)
        self.consolidation_rules: List[TagRule] = []
        self.location_patterns: Set[str] = set()
        self._initialize_rules_and_patterns()

    def _initialize_rules_and_patterns(self):
        """Initialize comprehensive rules and patterns for tag categorization."""
        
        # Location patterns to filter out
        self.location_patterns.update([
            # Countries, cities, regions from the data
            r'^[A-Z][a-z]+$',  # Single capitalized words (likely places)
            r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # Two capitalized words
            r'^\w+/\w+$',  # Country/Country format
        ])
        
        # Genre consolidation rules
        genre_rules = [
            # Metal subgenres
            TagRule(r'black.?metal|blackmetal|epic blackmetal|vampyric blackmetal|western blackmetal|ecstatic blackmetal', 
                   TagCategory.GENRE, 'black metal', 1),
            TagRule(r'death.?metal|deathmetal|slam deathmetal|orchestral deathmetal|doom-deathmetal|melodic-deathmetal', 
                   TagCategory.GENRE, 'death metal', 1),
            TagRule(r'doom.?metal|doommetal|acoustic doommetal', 
                   TagCategory.GENRE, 'doom metal', 1),
            TagRule(r'power.?metal|powermetal|us powermetal', 
                   TagCategory.GENRE, 'power metal', 1),
            TagRule(r'thrash.?metal|thrashmetal|tharsh.*metal', 
                   TagCategory.GENRE, 'thrash metal', 1),
            TagRule(r'prog.?metal|progressive.?metal|progmetal|extreme progmetal', 
                   TagCategory.GENRE, 'progressive metal', 1),
            TagRule(r'folk.?metal|folkmetal|symphonic-folkmetal|celtic-metal|viking-metal|samuraimetal', 
                   TagCategory.GENRE, 'folk metal', 1),
            TagRule(r'post.?metal|postmetal', 
                   TagCategory.GENRE, 'post-metal', 1),
            TagRule(r'gothic.?metal|gothicmetal|ghoticmetal', 
                   TagCategory.GENRE, 'gothic metal', 1),
            TagRule(r'heavy.?metal', 
                   TagCategory.GENRE, 'heavy metal', 1),
            TagRule(r'industrial.?metal', 
                   TagCategory.GENRE, 'industrial metal', 1),
            TagRule(r'nu.?metal|numetal', 
                   TagCategory.GENRE, 'nu metal', 1),
            TagRule(r'alt.?metal|altmetal|alternative.?metal', 
                   TagCategory.GENRE, 'alternative metal', 1),
            TagRule(r'sludge.?metal|sludgemetal|prog-sludgemetal', 
                   TagCategory.GENRE, 'sludge metal', 1),
            TagRule(r'southern.?metal|southernmetal', 
                   TagCategory.GENRE, 'southern metal', 1),
            TagRule(r'stoner.?metal|stonermetal', 
                   TagCategory.GENRE, 'stoner metal', 1),
            TagRule(r'symphonic.?metal', 
                   TagCategory.GENRE, 'symphonic metal', 1),
            TagRule(r'technical.?metal', 
                   TagCategory.GENRE, 'technical metal', 1),
            TagRule(r'drone.?metal|dronemetal', 
                   TagCategory.GENRE, 'drone metal', 1),
            
            # Core genres
            TagRule(r'metalcore|metal.?core|melodic-deathcore', 
                   TagCategory.GENRE, 'metalcore', 1),
            TagRule(r'deathcore|death.?core', 
                   TagCategory.GENRE, 'deathcore', 1),
            TagRule(r'hardcore|hard.?core', 
                   TagCategory.GENRE, 'hardcore', 1),
            TagRule(r'post.?hardcore|posthardcore', 
                   TagCategory.GENRE, 'post-hardcore', 1),
            TagRule(r'mathcore|math.?core', 
                   TagCategory.GENRE, 'mathcore', 1),
            TagRule(r'grindcore|grind.?core', 
                   TagCategory.GENRE, 'grindcore', 1),
            
            # Rock genres
            TagRule(r'progressive.?rock|prog.?rock|progrock', 
                   TagCategory.GENRE, 'progressive rock', 1),
            TagRule(r'psychedelic.?rock|psych.?rock|pscyhedelic.?rock', 
                   TagCategory.GENRE, 'psychedelic rock', 1),
            TagRule(r'post.?rock|postrock|orchestral postrock|instrumental postrock', 
                   TagCategory.GENRE, 'post-rock', 1),
            TagRule(r'indie.?rock|indierock', 
                   TagCategory.GENRE, 'indie rock', 1),
            TagRule(r'alternative.?rock|alt.?rock|altrock', 
                   TagCategory.GENRE, 'alternative rock', 1),
            TagRule(r'garage.?rock|garagerock', 
                   TagCategory.GENRE, 'garage rock', 1),
            TagRule(r'hard.?rock|hardrock', 
                   TagCategory.GENRE, 'hard rock', 1),
            TagRule(r'art.?rock|artrock', 
                   TagCategory.GENRE, 'art rock', 1),
            TagRule(r'space.?rock|spacerock', 
                   TagCategory.GENRE, 'space rock', 1),
            TagRule(r'stoner.?rock|stonerrock', 
                   TagCategory.GENRE, 'stoner rock', 1),
            TagRule(r'arena.?rock|arenarock', 
                   TagCategory.GENRE, 'arena rock', 1),
            TagRule(r'blues.?rock|bluesrock', 
                   TagCategory.GENRE, 'blues rock', 1),
            TagRule(r'country.?rock|countryrock', 
                   TagCategory.GENRE, 'country rock', 1),
            TagRule(r'folk.?rock|folkrock|exp-folkrock|nordic folkrock', 
                   TagCategory.GENRE, 'folk rock', 1),
            TagRule(r'punk.?rock|punkrock', 
                   TagCategory.GENRE, 'punk rock', 1),
            TagRule(r'glam.?rock|glamrock', 
                   TagCategory.GENRE, 'glam rock', 1),
            TagRule(r'gothic.?rock|gothrock', 
                   TagCategory.GENRE, 'gothic rock', 1),
            TagRule(r'instrumental.?rock|instrumentalrock', 
                   TagCategory.GENRE, 'instrumental rock', 1),
            TagRule(r'noise.?rock|noiserock', 
                   TagCategory.GENRE, 'noise rock', 1),
            TagRule(r'surf.?rock|surfrock', 
                   TagCategory.GENRE, 'surf rock', 1),
            TagRule(r'experimental.?rock|experimentalrock', 
                   TagCategory.GENRE, 'experimental rock', 1),
            
            # Electronic genres  
            TagRule(r'synth.?pop|synthpop', 
                   TagCategory.GENRE, 'synthpop', 1),
            TagRule(r'synth.?wave|synthwave', 
                   TagCategory.GENRE, 'synthwave', 1),
            TagRule(r'new.?wave|newwave', 
                   TagCategory.GENRE, 'new wave', 1),
            TagRule(r'dark.?wave|darkwave', 
                   TagCategory.GENRE, 'darkwave', 1),
            
            # Pop genres
            TagRule(r'dream.?pop|dreampop', 
                   TagCategory.GENRE, 'dream pop', 1),
            TagRule(r'indie.?pop|indiepop', 
                   TagCategory.GENRE, 'indie pop', 1),
            TagRule(r'alt.?pop|altpop|alternative.?pop', 
                   TagCategory.GENRE, 'alternative pop', 1),
            TagRule(r'art.?pop|artpop', 
                   TagCategory.GENRE, 'art pop', 1),
            TagRule(r'chamber.?pop|chamberpop', 
                   TagCategory.GENRE, 'chamber pop', 1),
            TagRule(r'prog.?pop|progpop|progressive.?pop', 
                   TagCategory.GENRE, 'progressive pop', 1),
            
            # Punk genres
            TagRule(r'pop.?punk|poppunk', 
                   TagCategory.GENRE, 'pop punk', 1),
            TagRule(r'ska.?punk|skapunk', 
                   TagCategory.GENRE, 'ska punk', 1),
            TagRule(r'folk.?punk|folkpunk', 
                   TagCategory.GENRE, 'folk punk', 1),
            TagRule(r'garage.?punk|garagepunk', 
                   TagCategory.GENRE, 'garage punk', 1),
            TagRule(r'street.?punk|streetpunk', 
                   TagCategory.GENRE, 'street punk', 1),
            TagRule(r'surf.?punk|surfpunk', 
                   TagCategory.GENRE, 'surf punk', 1),
            TagRule(r'noise.?punk|noisepunk', 
                   TagCategory.GENRE, 'noise punk', 1),
            TagRule(r'anarcho.?punk|anarchopunk', 
                   TagCategory.GENRE, 'anarcho punk', 1),
            
            # Jazz genres
            TagRule(r'progressive.?jazz|progjazz', 
                   TagCategory.GENRE, 'progressive jazz', 1),
            TagRule(r'experimental.?jazz|expjazz', 
                   TagCategory.GENRE, 'experimental jazz', 1),
            TagRule(r'fusion.?jazz|jazzfusion', 
                   TagCategory.GENRE, 'jazz fusion', 1),
            TagRule(r'avant.?jazz|avantjazz|avant-gardejazz', 
                   TagCategory.GENRE, 'avant-garde jazz', 1),
            TagRule(r'free.?jazz|freejazz', 
                   TagCategory.GENRE, 'free jazz', 1),
            TagRule(r'nu.?jazz|nujazz', 
                   TagCategory.GENRE, 'nu jazz', 1),
        ]
        
        # Style modifier rules
        style_rules = [
            TagRule(r'atmospheric|atmo', TagCategory.STYLE_MODIFIER, 'atmospheric', 2),
            TagRule(r'technical|tech', TagCategory.STYLE_MODIFIER, 'technical', 2),
            TagRule(r'melodic', TagCategory.STYLE_MODIFIER, 'melodic', 2),
            TagRule(r'progressive|prog', TagCategory.STYLE_MODIFIER, 'progressive', 2),
            TagRule(r'experimental|exp', TagCategory.STYLE_MODIFIER, 'experimental', 2),
            TagRule(r'avant.?garde', TagCategory.STYLE_MODIFIER, 'avant-garde', 2),
            TagRule(r'symphonic', TagCategory.STYLE_MODIFIER, 'symphonic', 2),
            TagRule(r'orchestral', TagCategory.STYLE_MODIFIER, 'orchestral', 2),
            TagRule(r'ambient', TagCategory.STYLE_MODIFIER, 'ambient', 2),
            TagRule(r'epic', TagCategory.STYLE_MODIFIER, 'epic', 2),
            TagRule(r'dark', TagCategory.STYLE_MODIFIER, 'dark', 2),
            TagRule(r'brutal', TagCategory.STYLE_MODIFIER, 'brutal', 2),
            TagRule(r'blackened', TagCategory.STYLE_MODIFIER, 'blackened', 2),
            TagRule(r'psychedelic|psych', TagCategory.STYLE_MODIFIER, 'psychedelic', 2),
            TagRule(r'industrial', TagCategory.STYLE_MODIFIER, 'industrial', 2),
            TagRule(r'post', TagCategory.STYLE_MODIFIER, 'post', 2),
            TagRule(r'neo', TagCategory.STYLE_MODIFIER, 'neo', 2),
            TagRule(r'retro', TagCategory.STYLE_MODIFIER, 'retro', 2),
            TagRule(r'modern', TagCategory.STYLE_MODIFIER, 'modern', 2),
            TagRule(r'traditional', TagCategory.STYLE_MODIFIER, 'traditional', 2),
            TagRule(r'contemporary', TagCategory.STYLE_MODIFIER, 'contemporary', 2),
            TagRule(r'minimal|minimalist', TagCategory.STYLE_MODIFIER, 'minimal', 2),
            TagRule(r'heavy', TagCategory.STYLE_MODIFIER, 'heavy', 2),
            TagRule(r'soft', TagCategory.STYLE_MODIFIER, 'soft', 2),
            TagRule(r'hard', TagCategory.STYLE_MODIFIER, 'hard', 2),
            TagRule(r'fast', TagCategory.STYLE_MODIFIER, 'fast', 2),
            TagRule(r'slow', TagCategory.STYLE_MODIFIER, 'slow', 2),
        ]
        
        # Regional/Cultural rules (keep these, unlike location)
        regional_rules = [
            TagRule(r'celtic|celtic.?rock', TagCategory.REGIONAL, 'celtic', 2),
            TagRule(r'viking|norse|nordic', TagCategory.REGIONAL, 'viking', 2),
            TagRule(r'medieval|mitteralter.*', TagCategory.REGIONAL, 'medieval', 2),
            TagRule(r'oriental|eastern', TagCategory.REGIONAL, 'oriental', 2),
            TagRule(r'latin|latino', TagCategory.REGIONAL, 'latin', 2),
            TagRule(r'arabic|middle.?eastern', TagCategory.REGIONAL, 'arabic', 2),
            TagRule(r'tribal', TagCategory.REGIONAL, 'tribal', 2),
            TagRule(r'ethno|ethnic', TagCategory.REGIONAL, 'ethnic', 2),
            TagRule(r'anatolian', TagCategory.REGIONAL, 'anatolian', 2),
        ]
        
        # Location rules (to filter out)
        location_rules = [
            TagRule(r'^[A-Z][a-z]+$', TagCategory.LOCATION, filter_out=True, priority=3),
            TagRule(r'^[A-Z][a-z]+ [A-Z][a-z]+$', TagCategory.LOCATION, filter_out=True, priority=3),
            TagRule(r'^\w+/\w+$', TagCategory.LOCATION, filter_out=True, priority=3),
            TagRule(r'^[A-Z]{2}$', TagCategory.LOCATION, filter_out=True, priority=3),  # State codes
        ]
        
        # Theme/concept rules
        theme_rules = [
            TagRule(r'nautical|pirate|maritime', TagCategory.THEME, 'nautical', 2),
            TagRule(r'space|cosmic|sci.?fi', TagCategory.THEME, 'space', 2),
            TagRule(r'nature|forest|earth', TagCategory.THEME, 'nature', 2),
            TagRule(r'war|battle|military', TagCategory.THEME, 'war', 2),
            TagRule(r'occult|esoteric|mystical', TagCategory.THEME, 'occult', 2),
            TagRule(r'religious|spiritual|christian', TagCategory.THEME, 'religious', 2),
            TagRule(r'political|anarchist', TagCategory.THEME, 'political', 2),
            TagRule(r'horror|dark|gothic', TagCategory.THEME, 'dark', 2),
            TagRule(r'fantasy|mythological', TagCategory.THEME, 'fantasy', 2),
            TagRule(r'love|romantic', TagCategory.THEME, 'romantic', 2),
            TagRule(r'introspective|philosophical', TagCategory.THEME, 'philosophical', 2),
        ]
        
        # Vocal style rules
        vocal_rules = [
            TagRule(r'clean.*vocal|clean.*sing', TagCategory.VOCAL_STYLE, 'clean vocals', 2),
            TagRule(r'harsh.*vocal|growl|scream', TagCategory.VOCAL_STYLE, 'harsh vocals', 2),
            TagRule(r'operatic|opera', TagCategory.VOCAL_STYLE, 'operatic vocals', 2),
            TagRule(r'choral|choir', TagCategory.VOCAL_STYLE, 'choral', 2),
            TagRule(r'instrumental', TagCategory.VOCAL_STYLE, 'instrumental', 2),
        ]
        
        # Technique rules
        technique_rules = [
            TagRule(r'blast.*beat|blasting', TagCategory.TECHNIQUE, 'blast beats', 2),
            TagRule(r'tremolo|trem', TagCategory.TECHNIQUE, 'tremolo', 2),
            TagRule(r'palm.*mute|palm.*muting', TagCategory.TECHNIQUE, 'palm muting', 2),
            TagRule(r'sweep.*pick|sweeping', TagCategory.TECHNIQUE, 'sweep picking', 2),
            TagRule(r'tapping|tap', TagCategory.TECHNIQUE, 'tapping', 2),
            TagRule(r'shred|shredding', TagCategory.TECHNIQUE, 'shredding', 2),
            TagRule(r'djent', TagCategory.TECHNIQUE, 'djent', 2),
            TagRule(r'riff.*heavy|heavy.*riff', TagCategory.TECHNIQUE, 'heavy riffs', 2),
            TagRule(r'polyrhythm|complex.*rhythm', TagCategory.TECHNIQUE, 'polyrhythmic', 2),
        ]
        
        # Combine all rules
        self.consolidation_rules.extend(genre_rules)
        self.consolidation_rules.extend(style_rules)
        self.consolidation_rules.extend(regional_rules)
        self.consolidation_rules.extend(location_rules)
        self.consolidation_rules.extend(theme_rules)
        self.consolidation_rules.extend(vocal_rules)
        self.consolidation_rules.extend(technique_rules)
        
        # Sort by priority (higher priority first)
        self.consolidation_rules.sort(key=lambda x: x.priority, reverse=True)

    def categorize_and_consolidate(self) -> Dict[TagCategory, Dict[str, int]]:
        """Categorize all tags and consolidate similar ones."""
        categorized_counts: Dict[TagCategory, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        filtered_tags = set()
        
        for tag, count in self.analyzer.tag_frequencies.items():
            categorized = False
            
            # Try to match against consolidation rules
            for rule in self.consolidation_rules:
                if re.search(rule.pattern, tag, re.IGNORECASE):
                    if rule.filter_out:
                        filtered_tags.add(tag)
                        categorized = True
                        break
                    else:
                        target_tag = rule.primary_tag if rule.primary_tag else tag
                        categorized_counts[rule.category][target_tag] += count
                        categorized = True
                        break
            
            # If not categorized, try to determine category heuristically
            if not categorized and tag not in filtered_tags:
                category = self._heuristic_categorization(tag)
                categorized_counts[category][tag] += count
        
        # Log filtering results
        if filtered_tags:
            print(f"\n--- Filtered Out Tags ({len(filtered_tags)}) ---")
            for tag in sorted(filtered_tags):
                print(f"  {tag} (count: {self.analyzer.tag_frequencies[tag]})")
        
        return dict(categorized_counts)

    def _heuristic_categorization(self, tag: str) -> TagCategory:
        """Use heuristics to categorize uncategorized tags."""
        tag_lower = tag.lower()
        
        # Check for common genre indicators
        if any(word in tag_lower for word in ['metal', 'core', 'rock', 'punk', 'jazz', 'pop', 'electronic']):
            return TagCategory.GENRE
        
        # Check for style modifiers
        if any(word in tag_lower for word in ['atmospheric', 'heavy', 'dark', 'melodic', 'brutal']):
            return TagCategory.STYLE_MODIFIER
        
        # Check for technique indicators
        if any(word in tag_lower for word in ['guitar', 'drum', 'bass', 'vocal', 'instrumental']):
            return TagCategory.TECHNIQUE
        
        # Check for theme indicators
        if any(word in tag_lower for word in ['war', 'love', 'death', 'life', 'nature', 'space']):
            return TagCategory.THEME
        
        # Default to unknown
        return TagCategory.UNKNOWN

    def build_enhanced_hierarchies(self) -> Dict[str, List[HierarchyRelation]]:
        """Build enhanced hierarchical relationships between tags."""
        hierarchies = defaultdict(list)
        
        # Parent-child relationships based on token analysis
        for tag in self.analyzer.tag_frequencies:
            tokens = tag.split()
            if len(tokens) > 1:
                # Look for potential parent tags
                for i in range(len(tokens)):
                    for j in range(i + 1, len(tokens) + 1):
                        potential_parent = ' '.join(tokens[i:j])
                        if (potential_parent in self.analyzer.tag_frequencies and 
                            potential_parent != tag and
                            len(potential_parent) < len(tag)):
                            
                            # Calculate relationship strength
                            strength = self._calculate_hierarchy_strength(potential_parent, tag)
                            if strength > 0.3:  # Threshold for meaningful relationship
                                hierarchies[potential_parent].append(
                                    HierarchyRelation(potential_parent, tag, strength)
                                )
        
        # Genre-subgenre relationships
        genre_hierarchies = {
            'metal': ['black metal', 'death metal', 'doom metal', 'power metal', 'thrash metal', 
                     'folk metal', 'gothic metal', 'symphonic metal', 'progressive metal',
                     'post-metal', 'sludge metal', 'stoner metal', 'drone metal'],
            'rock': ['hard rock', 'progressive rock', 'psychedelic rock', 'post-rock',
                    'indie rock', 'alternative rock', 'art rock', 'garage rock', 'space rock'],
            'punk': ['pop punk', 'ska punk', 'folk punk', 'garage punk', 'street punk',
                    'surf punk', 'noise punk', 'anarcho punk'],
            'jazz': ['progressive jazz', 'experimental jazz', 'fusion jazz', 'avant-garde jazz',
                    'free jazz', 'nu jazz'],
            'pop': ['dream pop', 'indie pop', 'alternative pop', 'art pop', 'chamber pop'],
        }
        
        for parent, children in genre_hierarchies.items():
            for child in children:
                if (parent in self.analyzer.tag_frequencies and 
                    child in self.analyzer.tag_frequencies):
                    hierarchies[parent].append(
                        HierarchyRelation(parent, child, 0.8)
                    )
        
        return dict(hierarchies)

    def _calculate_hierarchy_strength(self, parent: str, child: str) -> float:
        """Calculate the strength of a hierarchical relationship."""
        # Frequency-based strength
        parent_freq = self.analyzer.tag_frequencies.get(parent, 0)
        child_freq = self.analyzer.tag_frequencies.get(child, 0)
        
        if parent_freq == 0 or child_freq == 0:
            return 0.0
        
        # Higher frequency parent with lower frequency child suggests hierarchy
        freq_ratio = min(parent_freq / child_freq, 1.0)
        
        # Token containment strength
        parent_tokens = set(parent.split())
        child_tokens = set(child.split())
        containment = len(parent_tokens.intersection(child_tokens)) / len(parent_tokens)
        
        # Co-occurrence strength (if available)
        co_occurrence = 0.5  # Default if not calculated
        if hasattr(self.analyzer, 'tag_relationships'):
            pair = tuple(sorted([parent, child]))
            co_occurrence = self.analyzer.tag_relationships.get(pair, 0.0)
        
        # Combine factors
        strength = (freq_ratio * 0.3 + containment * 0.5 + co_occurrence * 0.2)
        return min(strength, 1.0)

    def suggest_consolidations(self, min_frequency: int = 2) -> List[Dict]:
        """Generate consolidation suggestions with enhanced analysis."""
        suggestions = []
        categorized = self.categorize_and_consolidate()
        
        # Within-category consolidations
        for category, tags in categorized.items():
            if category == TagCategory.LOCATION:
                continue  # Skip location tags
                
            tag_list = list(tags.keys())
            for i, tag1 in enumerate(tag_list):
                for tag2 in tag_list[i+1:]:
                    if tags[tag1] < min_frequency or tags[tag2] < min_frequency:
                        continue
                    
                    similarity = self.similarity.calculate_similarity(tag1, tag2)
                    if similarity > 0.7:
                        primary = tag1 if tags[tag1] >= tags[tag2] else tag2
                        secondary = tag2 if primary == tag1 else tag1
                        
                        suggestions.append({
                            'category': category.value,
                            'primary_tag': primary,
                            'secondary_tag': secondary,
                            'similarity': similarity,
                            'primary_freq': tags[primary],
                            'secondary_freq': tags[secondary],
                            'confidence': self._calculate_consolidation_confidence(primary, secondary, category)
                        })
        
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

    def _calculate_consolidation_confidence(self, tag1: str, tag2: str, category: TagCategory) -> float:
        """Calculate confidence in a consolidation suggestion."""
        # Similarity score
        similarity = self.similarity.calculate_similarity(tag1, tag2)
        
        # Frequency ratio (closer frequencies = higher confidence)
        freq1 = self.analyzer.tag_frequencies.get(tag1, 0)
        freq2 = self.analyzer.tag_frequencies.get(tag2, 0)
        freq_ratio = min(freq1, freq2) / max(freq1, freq2) if max(freq1, freq2) > 0 else 0
        
        # Category confidence (some categories are more reliable)
        category_weights = {
            TagCategory.GENRE: 0.9,
            TagCategory.STYLE_MODIFIER: 0.8,
            TagCategory.TECHNIQUE: 0.7,
            TagCategory.REGIONAL: 0.8,
            TagCategory.THEME: 0.6,
            TagCategory.VOCAL_STYLE: 0.7,
            TagCategory.UNKNOWN: 0.3
        }
        category_weight = category_weights.get(category, 0.5)
        
        # Token overlap
        tokens1 = set(tag1.split())
        tokens2 = set(tag2.split())
        token_overlap = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
        
        # Combined confidence
        confidence = (similarity * 0.4 + freq_ratio * 0.2 + category_weight * 0.2 + token_overlap * 0.2)
        return min(confidence, 1.0)

    def generate_consolidation_report(self) -> str:
        """Generate a comprehensive consolidation report."""
        categorized = self.categorize_and_consolidate()
        hierarchies = self.build_enhanced_hierarchies()
        suggestions = self.suggest_consolidations()
        
        report = []
        report.append("=== ENHANCED TAG CONSOLIDATION REPORT ===\n")
        
        # Category breakdown
        report.append("--- TAG CATEGORIES ---")
        total_original = len(self.analyzer.tag_frequencies)
        total_categorized = sum(len(tags) for tags in categorized.values())
        
        for category, tags in categorized.items():
            if tags:  # Only show categories with tags
                report.append(f"{category.value.title()}: {len(tags)} tags")
                top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]
                for tag, count in top_tags:
                    report.append(f"  {tag}: {count}")
                report.append("")
        
        report.append(f"Original tags: {total_original}")
        report.append(f"Categorized tags: {total_categorized}")
        report.append(f"Reduction: {total_original - total_categorized} tags\n")
        
        # Hierarchy analysis
        report.append("--- HIERARCHICAL RELATIONSHIPS ---")
        for parent, relations in list(hierarchies.items())[:10]:  # Top 10
            if relations:
                report.append(f"{parent}:")
                for rel in sorted(relations, key=lambda x: x.strength, reverse=True)[:3]:
                    report.append(f"  → {rel.child} (strength: {rel.strength:.2f})")
                report.append("")
        
        # Top consolidation suggestions
        report.append("--- TOP CONSOLIDATION SUGGESTIONS ---")
        for suggestion in suggestions[:20]:  # Top 20
            report.append(
                f"{suggestion['primary_tag']} ← {suggestion['secondary_tag']} "
                f"(confidence: {suggestion['confidence']:.2f}, "
                f"category: {suggestion['category']})"
            )
        
        return "\n".join(report) 