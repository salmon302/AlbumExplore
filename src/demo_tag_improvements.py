#!/usr/bin/env python3
"""
Demonstration of Enhanced Tag Consolidation Improvements
Shows how the system would improve the tag organization based on the actual data output.
"""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

class TagCategory:
    GENRE = "genre"
    STYLE_MODIFIER = "style_modifier"
    TECHNIQUE = "technique"  
    REGIONAL = "regional"
    LOCATION = "location"
    VOCAL_STYLE = "vocal_style"
    THEME = "theme"
    UNKNOWN = "unknown"

class SimpleTagAnalyzer:
    """Simplified version for demonstration without external dependencies."""
    
    def __init__(self):
        # Sample problematic tags from the actual output
        self.sample_tags = [
            # Location tags (should be filtered)
            "Mahopac", "Rijsbergen", "Marseille", "Yonkers", "Zulte", "Malaga", 
            "Swansea", "Rijeka", "Coquimbo", "Kenora", "Wrexham", "Stockholm",
            "Gothenburg", "London", "Berlin", "Montreal", "Tokyo", "Dublin",
            "Birmingham", "New Orleans", "San Francisco", "California", "Seattle",
            "Manchester", "Phoenix", "New York", "Chicago", "Portland",
            "Canada/UK", "Sweden/UK", "USA/Finland", "USA/UK", "UK/Australia",
            
            # Genre variations (should be consolidated)
            "black metal", "blackmetal", "epic blackmetal", "vampyric blackmetal", 
            "western blackmetal", "ecstatic blackmetal", "epic vampyric blackmetal",
            "death metal", "deathmetal", "slam deathmetal", "orchestral deathmetal",
            "doom-deathmetal", "melodic-deathmetal", "technical death metal",
            "doom metal", "doommetal", "acoustic doommetal",
            "progressive metal", "prog metal", "progmetal", "extreme progmetal",
            "folk metal", "folkmetal", "symphonic-folkmetal", "celtic-metal",
            "viking-metal", "samuraimetal", "viking metal", "celtic metal",
            "post metal", "post-metal", "postmetal",
            "pirate metal", "piratemetal", "nautical metal", "nauticalmetal",
            "power metal", "powermetal", "us powermetal",
            "thrash metal", "thrashmetal", "tharsh metal",
            "heavy metal", "alt metal", "altmetal", "alternative metal",
            "sludge metal", "sludgemetal", "prog-sludgemetal",
            "southern metal", "southernmetal", "gothic metal", "gothicmetal",
            "industrial metal", "nu metal", "drone metal", "stoner metal",
            
            # Core genres
            "metalcore", "metal-core", "melodic-deathcore", "deathcore", 
            "death-core", "hardcore", "hard-core", "post-hardcore", 
            "posthardcore", "mathcore", "math-core", "grindcore", "grind-core",
            
            # Rock variations
            "progressive rock", "prog rock", "progrock", "psychedelic rock",
            "psych rock", "pscyhedelic rock", "post rock", "post-rock", 
            "postrock", "orchestral postrock", "instrumental postrock",
            "indie rock", "indierock", "alternative rock", "alt rock", "altrock",
            "garage rock", "garagerock", "hard rock", "hardrock", "art rock",
            "space rock", "spacerock", "stoner rock", "blues rock", "bluesrock",
            "country rock", "countryrock", "folk rock", "folkrock", 
            "exp-folkrock", "nordic folkrock", "punk rock", "punkrock",
            "glam rock", "glamrock", "gothic rock", "gothrock", 
            "instrumental rock", "instrumentalrock", "noise rock", "noiserock",
            "experimental rock", "experimentalrock", "arena rock", "arenarock",
            "surf rock", "surfrock", "acoustic rock", "acousticrock",
            "electronic rock", "electrorock", "dance rock", "dancerock",
            "roots rock", "rootsrock", "heartland rock", "heartlandrock",
            "theatrical rock", "theatricalrock", "chamber rock", "chamberrock",
            "orchestral rock", "orchestralrock", "anatolian rock", "anatolianrock",
            "celtic rock", "celticrock", "latin rock", "latinrock",
            
            # Pop variations
            "synth pop", "synthpop", "synth-pop", "dream pop", "dreampop",
            "indie pop", "indiepop", "alt pop", "altpop", "alternative pop",
            "art pop", "artpop", "art-pop", "chamber pop", "chamberpop",
            "prog pop", "progpop", "progressive pop", "dance pop", "dancepop",
            "dance-pop", "pop metal", "popmetal", "emo pop", "emopop",
            "emo-pop", "dark pop", "darkpop", "future pop", "futurepop",
            "experimental pop", "exppop", "contemporary pop", "contemporarypop",
            "baroque pop", "baroquepop", "jangle pop", "janglepop",
            "garage pop", "garagepop", "math pop", "mathpop", "drone pop",
            "dronepop", "glitch pop", "glitchpop", "bedroom pop", "bedroompop",
            "sunshine pop", "sunshinepop", "anxiety pop", "anxietypop",
            "retro pop", "retropop", "angular pop", "angularpop",
            "gothic pop", "gothicpop", "hypnagogic pop", "hypnagogicpop",
            "twee pop", "tweepop", "sophisti-pop", "sophistipop",
            "post-modern pop", "post-modernpop", "traditional pop", "traditionalpop",
            "arabic pop", "arabicpop", "persian pop", "persianpop",
            "soul pop", "soulpop", "country pop", "countrypop",
            "folk pop", "folkpop", "folk-pop", "j-pop", "jpop",
            "french pop", "frenchpop", "latin pop", "latinpop",
            "disco pop", "discopop", "disco-pop",
            
            # Punk variations
            "pop punk", "poppunk", "pop-punk", "ska punk", "skapunk",
            "folk punk", "folkpunk", "garage punk", "garagepunk",
            "street punk", "streetpunk", "surf punk", "surfpunk",
            "noise punk", "noisepunk", "anarcho punk", "anarchopunk",
            "anarcho-punk", "glam punk", "glampunk", "dance punk", "dancepunk",
            "dance-punk", "disco punk", "discopunk", "disco-punk",
            "indie punk", "indiepunk", "emo punk", "emopunk", "alt punk",
            "altpunk", "alt-punk", "art punk", "artpunk", "art-punk",
            "avant punk", "avantpunk", "avant-punk", "neo punk", "neopunk",
            "neo-punk", "proto punk", "protopunk", "proto-punk",
            "egg punk", "eggpunk", "jangle punk", "janglepunk",
            "skate punk", "skatepunk", "synth punk", "synthpunk",
            
            # Jazz variations
            "progressive jazz", "progjazz", "experimental jazz", "expjazz",
            "fusion jazz", "jazzfusion", "jazz fusion", "jazz-fusion",
            "avant jazz", "avantjazz", "avant-jazz", "avant-garde jazz",
            "avant-gardejazz", "free jazz", "freejazz", "nu jazz", "nujazz",
            "modern jazz", "modernjazz", "contemporary jazz", "contemporaryjazz",
            "spiritual jazz", "spiritualjazz", "chamber jazz", "chamberjazz",
            "vocal jazz", "vocaljazz", "smooth jazz", "smoothjazz",
            "acid jazz", "acidjazz", "jazz pop", "jazzpop", "jazz-pop",
            "soul jazz", "souljazz", "soul-jazz", "doom jazz", "doomjazz",
            "brutal jazz", "brutaljazz", "grunge jazz", "grungejazz",
            "math jazz", "mathjazz", "psychedelic jazz", "psychedelicjazz",
            "noir jazz", "noirjazz", "future jazz", "futurejazz",
            "crossover jazz", "crossoverjazz", "improv jazz", "improvjazz",
            "big band jazz", "big bandjazz", "classical jazz", "classicaljazz",
            "nordic jazz", "nordicjazz", "arabic jazz", "arabicjazz",
            "ethio jazz", "ethiojazz", "ethio-jazz", "latin jazz", "latinjazz",
            "latin-jazz", "jazz-core", "jazzcore", "jazz-funk", "jazzfunk",
            
            # Electronic variations
            "synth wave", "synthwave", "synth-wave", "new wave", "newwave",
            "new-wave", "dark wave", "darkwave", "minimal wave", "minimalwave",
            "synth funk", "synthfunk", "synth rock", "synthrock",
            "electro funk", "electrofunk", "electro-funk", "disco funk",
            "discofunk", "disco-funk", "electronic music", "electro-music",
            "electronic pop", "electropop", "electronic dance music",
            "electro-dance music", "progressive electronic", "prog-electronic",
            "experimental electronic", "exp-electronic", "electronic avant-garde",
            "electro-avant-garde", "ambient noise", "ambientnoise",
            "noise ambient", "noiseambient", "space ambient", "spaceambient",
            "ritual ambient", "ritualambient", "tribal ambient", "tribalambient",
            "industrial noise", "industrialnoise", "power noise", "power-noise",
            "black noise", "black-noise", "glitch", "electronic rock", "electrorock",
            "industrial rock", "industrialrock", "industrial punk", "industrialpunk",
            "electro house", "electro-house", "melodic house", "melodic-house",
            "tech house", "tech-house", "psychedelic trance", "psychedelic-trance",
            
            # Style modifiers
            "atmospheric", "atmo", "atmo-rock", "technical", "tech", "melodic",
            "progressive", "prog", "experimental", "exp", "avant-garde",
            "avantgarde", "symphonic", "orchestral", "ambient", "epic",
            "dark", "brutal", "blackened", "psychedelic", "psych", "industrial",
            "post", "neo", "retro", "modern", "traditional", "contemporary",
            "minimal", "minimalist", "heavy", "soft", "hard", "fast", "slow",
            "raw", "clean", "dirty", "cold", "warm", "cosmic", "space",
            "ritualistic", "occult", "esoteric", "mystical", "spiritual",
            "religious", "christian", "pagan", "satanic", "political",
            "anarchist", "horror", "gothic", "fantasy", "mythological",
            "medieval", "ancient", "futuristic", "cinematic", "theatrical",
            
            # Technique/instrument terms
            "blast beats", "tremolo", "palm muting", "sweep picking", "tapping",
            "shredding", "djent", "heavy riffs", "polyrhythmic", "complex rhythm",
            "improvised", "jamming", "looping", "sampling", "programming",
            "analog", "digital", "acoustic", "electric", "distorted",
            "fuzzed", "compressed", "reverb", "delay", "chorus", "flanger",
            "phaser", "overdrive", "clean", "harsh", "growling", "screaming",
            "whispering", "falsetto", "operatic", "choral", "instrumental",
            "vocal", "guitar", "bass", "drums", "keyboards", "synthesizer",
            "piano", "violin", "cello", "trumpet", "saxophone", "flute",
            
            # Regional/cultural (keep these)
            "celtic", "viking", "norse", "nordic", "medieval", "mitteralter-metal",
            "mitteraltermetal", "oriental", "eastern", "latin", "latino", "arabic",
            "middle eastern", "tribal", "ethno", "ethnic", "anatolian",
            
            # Themes
            "nautical", "pirate", "maritime", "space", "cosmic", "sci-fi",
            "nature", "forest", "earth", "war", "battle", "military",
            "occult", "esoteric", "mystical", "religious", "spiritual",
            "christian", "political", "anarchist", "horror", "dark", "gothic",
            "fantasy", "mythological", "love", "romantic", "introspective",
            "philosophical",
            
            # Misc/Comedy
            "comedy", "comedyrock", "parody metal", "parodymetal",
            
            # Common misspellings that should be corrected
            "tharsh metal", "pscyhedelic rock", "ghoticmetal", "kawaii metal",
            "kawaiimetal", "HI", "KA", "NO", "MX", "l", "VW",
        ]
        
        # Create frequency counts (simulating real data)
        self.tag_frequencies = Counter()
        for tag in self.sample_tags:
            # Give higher frequencies to more common/important tags
            if "metal" in tag.lower():
                freq = 15 + hash(tag) % 20  # 15-35
            elif "rock" in tag.lower():
                freq = 10 + hash(tag) % 15  # 10-25
            elif "pop" in tag.lower():
                freq = 8 + hash(tag) % 12   # 8-20
            elif "punk" in tag.lower():
                freq = 6 + hash(tag) % 10   # 6-16
            elif "jazz" in tag.lower():
                freq = 5 + hash(tag) % 8    # 5-13
            elif len(tag) <= 5 and tag[0].isupper():  # Location tags
                freq = 1 + hash(tag) % 3    # 1-4 (low frequency)
            else:
                freq = 3 + hash(tag) % 8    # 3-11
            self.tag_frequencies[tag] = freq

class EnhancedTagDemo:
    def __init__(self):
        self.analyzer = SimpleTagAnalyzer()
        self.consolidation_rules = self._create_consolidation_rules()
        
    def _create_consolidation_rules(self):
        """Create comprehensive consolidation rules."""
        rules = []
        
        # Metal genre consolidation
        rules.extend([
            (r'black.?metal|blackmetal|epic blackmetal|vampyric blackmetal|western blackmetal|ecstatic blackmetal|epic vampyric blackmetal', 
             'black metal', TagCategory.GENRE),
            (r'death.?metal|deathmetal|slam deathmetal|orchestral deathmetal|doom-deathmetal|melodic-deathmetal', 
             'death metal', TagCategory.GENRE),
            (r'doom.?metal|doommetal|acoustic doommetal', 
             'doom metal', TagCategory.GENRE),
            (r'power.?metal|powermetal|us powermetal', 
             'power metal', TagCategory.GENRE),
            (r'thrash.?metal|thrashmetal|tharsh.*metal', 
             'thrash metal', TagCategory.GENRE),
            (r'prog.?metal|progressive.?metal|progmetal|extreme progmetal', 
             'progressive metal', TagCategory.GENRE),
            (r'folk.?metal|folkmetal|symphonic-folkmetal|celtic-metal|viking-metal|samuraimetal', 
             'folk metal', TagCategory.GENRE),
            (r'post.?metal|postmetal', 
             'post-metal', TagCategory.GENRE),
            (r'gothic.?metal|gothicmetal|ghoticmetal', 
             'gothic metal', TagCategory.GENRE),
            (r'heavy.?metal', 
             'heavy metal', TagCategory.GENRE),
            (r'alt.?metal|altmetal|alternative.?metal', 
             'alternative metal', TagCategory.GENRE),
            (r'sludge.?metal|sludgemetal|prog-sludgemetal', 
             'sludge metal', TagCategory.GENRE),
            (r'southern.?metal|southernmetal', 
             'southern metal', TagCategory.GENRE),
            (r'pirate.?metal|piratemetal|nautical.*metal|nauticalmetal', 
             'pirate metal', TagCategory.GENRE),
        ])
        
        # Core genre consolidation
        rules.extend([
            (r'metalcore|metal.?core|melodic-deathcore', 
             'metalcore', TagCategory.GENRE),
            (r'deathcore|death.?core', 
             'deathcore', TagCategory.GENRE),
            (r'hardcore|hard.?core', 
             'hardcore', TagCategory.GENRE),
            (r'post.?hardcore|posthardcore', 
             'post-hardcore', TagCategory.GENRE),
            (r'mathcore|math.?core', 
             'mathcore', TagCategory.GENRE),
            (r'grindcore|grind.?core', 
             'grindcore', TagCategory.GENRE),
        ])
        
        # Rock genre consolidation  
        rules.extend([
            (r'progressive.?rock|prog.?rock|progrock', 
             'progressive rock', TagCategory.GENRE),
            (r'psychedelic.?rock|psych.?rock|pscyhedelic.?rock', 
             'psychedelic rock', TagCategory.GENRE),
            (r'post.?rock|postrock|orchestral postrock|instrumental postrock', 
             'post-rock', TagCategory.GENRE),
            (r'indie.?rock|indierock', 
             'indie rock', TagCategory.GENRE),
            (r'alternative.?rock|alt.?rock|altrock', 
             'alternative rock', TagCategory.GENRE),
            (r'garage.?rock|garagerock', 
             'garage rock', TagCategory.GENRE),
            (r'hard.?rock|hardrock', 
             'hard rock', TagCategory.GENRE),
            (r'space.?rock|spacerock', 
             'space rock', TagCategory.GENRE),
            (r'folk.?rock|folkrock|exp-folkrock|nordic folkrock', 
             'folk rock', TagCategory.GENRE),
            (r'celtic.?rock|celticrock', 
             'celtic rock', TagCategory.GENRE),
        ])
        
        # Pop genre consolidation
        rules.extend([
            (r'synth.?pop|synthpop|synth-pop', 
             'synthpop', TagCategory.GENRE),
            (r'dream.?pop|dreampop', 
             'dream pop', TagCategory.GENRE),
            (r'indie.?pop|indiepop', 
             'indie pop', TagCategory.GENRE),
            (r'alt.?pop|altpop|alternative.?pop', 
             'alternative pop', TagCategory.GENRE),
            (r'art.?pop|artpop|art-pop', 
             'art pop', TagCategory.GENRE),
            (r'chamber.?pop|chamberpop', 
             'chamber pop', TagCategory.GENRE),
            (r'prog.?pop|progpop|progressive.?pop', 
             'progressive pop', TagCategory.GENRE),
        ])
        
        # Punk genre consolidation
        rules.extend([
            (r'pop.?punk|poppunk|pop-punk', 
             'pop punk', TagCategory.GENRE),
            (r'ska.?punk|skapunk', 
             'ska punk', TagCategory.GENRE),
            (r'folk.?punk|folkpunk', 
             'folk punk', TagCategory.GENRE),
            (r'garage.?punk|garagepunk', 
             'garage punk', TagCategory.GENRE),
            (r'street.?punk|streetpunk', 
             'street punk', TagCategory.GENRE),
            (r'surf.?punk|surfpunk', 
             'surf punk', TagCategory.GENRE),
            (r'noise.?punk|noisepunk', 
             'noise punk', TagCategory.GENRE),
            (r'anarcho.?punk|anarchopunk|anarcho-punk', 
             'anarcho punk', TagCategory.GENRE),
        ])
        
        # Jazz genre consolidation
        rules.extend([
            (r'progressive.?jazz|progjazz', 
             'progressive jazz', TagCategory.GENRE),
            (r'experimental.?jazz|expjazz', 
             'experimental jazz', TagCategory.GENRE),
            (r'fusion.?jazz|jazzfusion|jazz.?fusion|jazz-fusion', 
             'jazz fusion', TagCategory.GENRE),
            (r'avant.?jazz|avantjazz|avant-jazz|avant-garde.*jazz|avant-gardejazz', 
             'avant-garde jazz', TagCategory.GENRE),
            (r'free.?jazz|freejazz', 
             'free jazz', TagCategory.GENRE),
            (r'nu.?jazz|nujazz', 
             'nu jazz', TagCategory.GENRE),
        ])
        
        # Electronic/Wave consolidation
        rules.extend([
            (r'synth.?wave|synthwave|synth-wave', 
             'synthwave', TagCategory.GENRE),
            (r'new.?wave|newwave|new-wave', 
             'new wave', TagCategory.GENRE),
            (r'dark.?wave|darkwave', 
             'darkwave', TagCategory.GENRE),
        ])
        
        # Location filtering rules (these will be filtered out)
        location_patterns = [
            r'^[A-Z][a-z]+$',  # Single capitalized words
            r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # Two capitalized words  
            r'^\w+/\w+$',  # Country/Country format
            r'^[A-Z]{2}$',  # State codes like "HI", "KA"
        ]
        
        for pattern in location_patterns:
            rules.append((pattern, None, TagCategory.LOCATION))
        
        return rules
    
    def categorize_and_consolidate(self):
        """Categorize and consolidate tags."""
        categorized = defaultdict(lambda: defaultdict(int))
        filtered_tags = set()
        consolidated_mapping = {}
        
        for tag, count in self.analyzer.tag_frequencies.items():
            matched = False
            
            # Try to match against consolidation rules
            for pattern, target, category in self.consolidation_rules:
                if re.search(pattern, tag, re.IGNORECASE):
                    if category == TagCategory.LOCATION:
                        filtered_tags.add(tag)
                        matched = True
                        break
                    elif target:
                        categorized[category][target] += count
                        if tag != target:
                            consolidated_mapping[tag] = target
                        matched = True
                        break
            
            # If not matched, categorize heuristically
            if not matched and tag not in filtered_tags:
                category = self._heuristic_categorization(tag)
                categorized[category][tag] += count
        
        return dict(categorized), filtered_tags, consolidated_mapping
    
    def _heuristic_categorization(self, tag: str) -> str:
        """Categorize tags using heuristics."""
        tag_lower = tag.lower()
        
        # Genre indicators
        if any(word in tag_lower for word in ['metal', 'core', 'rock', 'punk', 'jazz', 'pop', 'electronic']):
            return TagCategory.GENRE
        
        # Style modifiers
        if any(word in tag_lower for word in ['atmospheric', 'heavy', 'dark', 'melodic', 'brutal', 'technical']):
            return TagCategory.STYLE_MODIFIER
        
        # Technique indicators
        if any(word in tag_lower for word in ['guitar', 'drum', 'bass', 'vocal', 'instrumental']):
            return TagCategory.TECHNIQUE
        
        # Theme indicators
        if any(word in tag_lower for word in ['war', 'love', 'death', 'life', 'nature', 'space']):
            return TagCategory.THEME
        
        # Regional/cultural
        if any(word in tag_lower for word in ['celtic', 'viking', 'medieval', 'tribal', 'oriental']):
            return TagCategory.REGIONAL
        
        return TagCategory.UNKNOWN
    
    def find_hierarchies(self, categorized_tags):
        """Find hierarchical relationships."""
        hierarchies = defaultdict(list)
        
        # Look for parent-child relationships in genre tags
        genre_tags = categorized_tags.get(TagCategory.GENRE, {})
        
        for tag in genre_tags:
            tokens = tag.split()
            if len(tokens) > 1:
                # Look for potential parent tags
                for i in range(len(tokens)):
                    for j in range(i + 1, len(tokens) + 1):
                        potential_parent = ' '.join(tokens[i:j])
                        if (potential_parent in genre_tags and 
                            potential_parent != tag and
                            len(potential_parent) < len(tag)):
                            hierarchies[potential_parent].append(tag)
        
        # Add known genre hierarchies
        known_hierarchies = {
            'metal': [tag for tag in genre_tags if 'metal' in tag and tag != 'metal'],
            'rock': [tag for tag in genre_tags if 'rock' in tag and tag != 'rock'],
            'punk': [tag for tag in genre_tags if 'punk' in tag and tag != 'punk'],
            'jazz': [tag for tag in genre_tags if 'jazz' in tag and tag != 'jazz'],
            'pop': [tag for tag in genre_tags if 'pop' in tag and tag != 'pop'],
        }
        
        for parent, children in known_hierarchies.items():
            if children:
                hierarchies[parent].extend(children)
                # Remove duplicates
                hierarchies[parent] = list(set(hierarchies[parent]))
        
        return dict(hierarchies)
    
    def generate_report(self):
        """Generate comprehensive analysis report."""
        print("=" * 60)
        print("ENHANCED TAG CONSOLIDATION ANALYSIS REPORT")
        print("=" * 60)
        
        # Before consolidation
        total_original = len(self.analyzer.tag_frequencies)
        total_instances = sum(self.analyzer.tag_frequencies.values())
        
        print(f"\n--- BEFORE CONSOLIDATION ---")
        print(f"Total unique tags: {total_original}")
        print(f"Total tag instances: {total_instances}")
        
        # Show most frequent tags before consolidation
        print(f"\nTop 15 most frequent tags (before):")
        for i, (tag, count) in enumerate(self.analyzer.tag_frequencies.most_common(15), 1):
            print(f"{i:2d}. {tag}: {count}")
        
        # Perform consolidation
        categorized, filtered, mapping = self.categorize_and_consolidate()
        
        # After consolidation
        total_after = sum(len(tags) for tags in categorized.values())
        total_filtered = len(filtered)
        
        print(f"\n--- AFTER CONSOLIDATION ---")
        print(f"Total categorized tags: {total_after}")
        print(f"Location tags filtered out: {total_filtered}")
        print(f"Net reduction: {total_original - total_after} tags ({((total_original - total_after) / total_original * 100):.1f}%)")
        
        # Show consolidation mappings
        if mapping:
            print(f"\n--- TAG CONSOLIDATIONS APPLIED ---")
            print(f"Number of tag merges: {len(mapping)}")
            print("Sample consolidations:")
            for i, (old_tag, new_tag) in enumerate(list(mapping.items())[:15], 1):
                old_count = self.analyzer.tag_frequencies[old_tag]
                print(f"{i:2d}. '{old_tag}' → '{new_tag}' (count: {old_count})")
        
        # Show filtered location tags
        if filtered:
            print(f"\n--- FILTERED LOCATION TAGS ({len(filtered)}) ---")
            location_tags = sorted([(tag, self.analyzer.tag_frequencies[tag]) for tag in filtered], 
                                 key=lambda x: x[1], reverse=True)
            for i, (tag, count) in enumerate(location_tags[:20], 1):
                print(f"{i:2d}. {tag}: {count}")
            if len(location_tags) > 20:
                print(f"    ... and {len(location_tags) - 20} more")
        
        # Show categorized results
        print(f"\n--- TAG CATEGORIES ---")
        for category, tags in categorized.items():
            if tags:
                print(f"\n{category.upper()}: {len(tags)} tags")
                sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
                for i, (tag, count) in enumerate(sorted_tags[:8], 1):
                    print(f"  {i}. {tag}: {count}")
                if len(sorted_tags) > 8:
                    print(f"     ... and {len(sorted_tags) - 8} more")
        
        # Show hierarchies
        hierarchies = self.find_hierarchies(categorized)
        if hierarchies:
            print(f"\n--- HIERARCHICAL RELATIONSHIPS ---")
            for parent, children in list(hierarchies.items())[:8]:
                if children:
                    print(f"\n{parent.upper()}:")
                    for child in sorted(children)[:5]:
                        parent_count = categorized.get(TagCategory.GENRE, {}).get(parent, 0)
                        child_count = categorized.get(TagCategory.GENRE, {}).get(child, 0)
                        print(f"  → {child} ({child_count})")
                    if len(children) > 5:
                        print(f"     ... and {len(children) - 5} more")
        
        # Summary statistics
        print(f"\n--- CONSOLIDATION IMPACT SUMMARY ---")
        print(f"Original tag count: {total_original}")
        print(f"After consolidation: {total_after}")
        print(f"Location tags removed: {total_filtered}")
        print(f"Tag merges applied: {len(mapping)}")
        print(f"Hierarchical relationships found: {sum(len(children) for children in hierarchies.values())}")
        print(f"Categories with tags: {sum(1 for tags in categorized.values() if tags)}")
        
        # Recommendations
        print(f"\n--- IMPLEMENTATION RECOMMENDATIONS ---")
        print("1. Apply location tag filtering to remove geographic noise")
        print("2. Implement genre consolidation rules for duplicate detection")
        print("3. Use hierarchical relationships for nested tag displays")
        print("4. Add category-based grouping in the tag explorer UI")
        print("5. Implement fuzzy matching for user tag searches")
        print("6. Add tag suggestion system based on similarities")
        print("7. Create tag validation rules for data imports")
        print("8. Implement user-controlled tag merge approvals")
        
        print(f"\n{'=' * 60}")
        print("ANALYSIS COMPLETE")
        print("=" * 60)

def main():
    """Run the tag consolidation demonstration."""
    print("Enhanced Tag Consolidation System - Demonstration")
    print("Based on actual AlbumExplore tag data analysis")
    
    demo = EnhancedTagDemo()
    demo.generate_report()

if __name__ == "__main__":
    main() 