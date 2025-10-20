#!/usr/bin/env python3
"""
Tag Rules Review and Fix Script

This script addresses the specific tag normalization issues identified in the atomic_tags_export2.csv
and improves the overall tag system by:

1. Fixing typos and misspellings
2. Consolidating fragmented atomic components 
3. Improving atomic decomposition rules
4. Adding proper substitution rules
5. Cleaning up problematic tags

Usage:
    python tag_rules_review_and_fix.py [--dry-run] [--backup]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class TagRulesReviewer:
    """Comprehensive tag rules review and improvement system."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = Path(__file__).parent / 'src' / 'albumexplore' / 'config' / 'tag_rules.json'
        else:
            self.config_path = Path(config_path)
        
        self.backup_dir = Path(__file__).parent / 'tag_analysis'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load current configuration
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.changes_made = []
        self.issues_found = []
        
    def create_backup(self) -> str:
        """Create timestamped backup of current configuration."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f'tag_rules_backup_review_{timestamp}.json'
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created backup: {backup_path}")
        return str(backup_path)
    
    def fix_typos_and_misspellings(self):
        """Fix typos and misspellings in tags and rules."""
        print("🔧 Fixing typos and misspellings...")
        
        # Typos to fix
        typo_fixes = {
            'expirimental': 'experimental',
            'alternitive': 'alternative', 
            'progresive': 'progressive',
            'pyschedelic rock': 'psychedelic rock',
            'pscyhedelic rock': 'psychedelic rock',
            'tharsh metal': 'thrash metal',
            'ghotic metal': 'gothic metal',
            'sympohnic': 'symphonic',
            'kosmsiche': 'kosmische',
            'zheul': 'zeuhl',
            'mitteralter metal': 'mittelalter metal',
            'mitteralter-metal': 'mittelalter-metal',
            'cinmatic': 'cinematic',
            'american privitsm': 'american primitivism',
            'blackend hardcore': 'blackened hardcore',
            'bluegras': 'bluegrass',
            'electonic': 'electronic',
            'neoclassica': 'neoclassical',
            'yatch rock': 'yacht rock',
            'skatepunk': 'skate punk'
        }
        
        # Add to tag_normalizations section
        if 'tag_normalizations' not in self.config:
            self.config['tag_normalizations'] = {}
        
        for typo, correct in typo_fixes.items():
            if typo not in self.config['tag_normalizations']:
                self.config['tag_normalizations'][typo] = correct
                self.changes_made.append(f"Added normalization: {typo} → {correct}")
        
        # Add to substitutions for atomic processing
        if 'substitutions' not in self.config:
            self.config['substitutions'] = {}
            
        for typo, correct in typo_fixes.items():
            if typo not in self.config['substitutions']:
                self.config['substitutions'][typo] = correct
                self.changes_made.append(f"Added substitution: {typo} → {correct}")
    
    def fix_fragmented_atomic_components(self):
        """Fix problematic atomic components that should be consolidated."""
        print("🔧 Fixing fragmented atomic components...")
        
        atomic_fixes = {
            # Singer/songwriter should remain together
            'singer': 'singer-songwriter',
            'songwriter': 'singer-songwriter',
            
            # Garde components should be consolidated
            'garde': 'avant-garde',
            'garde metal': 'avant-garde metal',
            'garde jazz': 'avant-garde jazz', 
            'garde black metal': 'avant-garde black metal',
            
            # Electronic variations
            'electronics': 'electronic',
            'electronica': 'electronic',
            
            # Psychedelic variations
            'psych': 'psychedelic',
            'psychedelia': 'psychedelic',
            
            # Metal/rock compound fixes
            'metal/rock': 'metal rock',
            'rock/metal': 'rock metal',
            
            # Hip-hop components
            'hop': 'hip-hop',
            
            # Wave components  
            'wave': 'wave music',
            
            # Core components
            'core': 'hardcore',
            
            # Revival components
            'revival': 'revival music',
            
            # Other fragments
            "'n'": 'and',
            'no': '',  # Remove problematic 'no' tag
            'and': '',  # Remove generic 'and' 
            'bop': 'bebop',
            'beat': 'beatdown',
            'roll': 'rock-and-roll',
            'gaze': 'shoegaze',
            'tronica': 'electronica'
        }
        
        # Add to substitutions
        for fragment, replacement in atomic_fixes.items():
            if fragment and replacement:  # Skip empty replacements for now
                if fragment not in self.config['substitutions']:
                    self.config['substitutions'][fragment] = replacement
                    self.changes_made.append(f"Added atomic fix: {fragment} → {replacement}")
        
        # Add problematic fragments to deletions list
        problematic_fragments = ['no', 'and', "'n'", 'word', 'score', 'band', 'mex', 'beats', 'breaks']
        
        if 'tag_deletions' not in self.config:
            self.config['tag_deletions'] = []
        
        for fragment in problematic_fragments:
            if fragment not in self.config['tag_deletions']:
                self.config['tag_deletions'].append(fragment)
                self.changes_made.append(f"Added to deletions: {fragment}")
    
    def improve_atomic_decomposition_rules(self):
        """Improve atomic decomposition rules for problematic tags."""
        print("🔧 Improving atomic decomposition rules...")
        
        # Improved decomposition rules
        improved_rules = {
            # Fix compound genres that should stay together
            'singer-songwriter': ['singer-songwriter'],  # Don't decompose this
            'avant-garde': ['avant-garde'],  # Don't decompose this
            'avant-garde metal': ['avant-garde', 'metal'],
            'avant-garde jazz': ['avant-garde', 'jazz'],
            'avant-garde black metal': ['avant-garde', 'black', 'metal'],
            
            # Blackgaze (black + shoegaze fusion) 
            'blackgaze': ['black', 'shoegaze'],
            
            # Grungegaze (grunge + shoegaze fusion)
            'grungegaze': ['grunge', 'shoegaze'],
            
            # Neo- prefixed genres
            'neoclassical': ['neo', 'classical'],
            'neofolk': ['neo', 'folk'],
            'neoclassical darkwave': ['neo', 'classical', 'darkwave'],
            
            # Tronica genres (electronic fusion)
            'folktronica': ['folk', 'electronic'],
            'indietronica': ['indie', 'electronic'],
            'livetronica': ['live', 'electronic'],
            
            # Modern compound genres
            'modern rock': ['modern', 'rock'],
            'modern metal': ['modern', 'metal'],
            
            # Progressive variants
            'prog pop': ['progressive', 'pop'],
            'prog rock': ['progressive', 'rock'],
            'prog metal': ['progressive', 'metal'],
            
            # Trap fusion
            'trap metal': ['trap', 'metal'],
            
            # Doom variants
            'doom rock': ['doom', 'rock'],
            'doom metal': ['doom', 'metal'],
            'doomgaze': ['doom', 'shoegaze'],
            
            # Acid genres
            'acid folk': ['acid', 'folk'],
            'acid rock': ['acid', 'rock'],
            'acid jazz': ['acid', 'jazz'],
            
            # Jazz fusion variants
            'jazz rap': ['jazz', 'rap'],
            'jazzcore': ['jazz', 'hardcore'],
            
            # Industrial variants
            'industrial techno': ['industrial', 'techno'],
            
            # Dissonant variants
            'dissonant metal': ['dissonant', 'metal'],
            
            # Epic variants
            'epic black metal': ['epic', 'black', 'metal'],
            
            # Blackened variants
            'blackened death metal': ['blackened', 'death', 'metal'],
            
            # Electro variants
            'electro house': ['electro', 'house'],
            'electro funk': ['electro', 'funk'],
            'electro ambient': ['electro', 'ambient']
        }
        
        # Add improved rules to atomic decomposition
        if 'atomic_decomposition' not in self.config:
            self.config['atomic_decomposition'] = {}
        
        for compound, components in improved_rules.items():
            if compound not in self.config['atomic_decomposition']:
                self.config['atomic_decomposition'][compound] = components
                self.changes_made.append(f"Added decomposition: {compound} → {components}")
            else:
                # Check if existing rule needs updating
                existing = self.config['atomic_decomposition'][compound]
                if existing != components:
                    self.config['atomic_decomposition'][compound] = components
                    self.changes_made.append(f"Updated decomposition: {compound} → {components} (was {existing})")
    
    def remove_problematic_decompositions(self):
        """Remove or fix problematic atomic decompositions."""
        print("🔧 Removing problematic decompositions...")
        
        # Tags that should NOT be decomposed (keep as single units)
        keep_whole = [
            'singer-songwriter',  # This is a single concept
            'avant-garde',        # This is a single concept
            'hip-hop',           # This is a single concept
            'rock-and-roll',     # This is a single concept
            'rhythm-and-blues',  # This is a single concept
        ]
        
        # Fix decompositions that are breaking these
        for tag in keep_whole:
            if tag in self.config['atomic_decomposition']:
                # Check if it's being incorrectly decomposed
                current = self.config['atomic_decomposition'][tag]
                if len(current) > 1:
                    # Set to single component
                    self.config['atomic_decomposition'][tag] = [tag]
                    self.changes_made.append(f"Fixed decomposition to keep whole: {tag}")
        
        # Fix specific problematic decompositions
        problematic_fixes = {
            'new wave and progrock': ['new', 'wave', 'progressive', 'rock'],
            'film score': ['film', 'soundtrack'],
            'spoken word': ['spoken-word'],  # Keep as single concept
            'stomp and holler': ['stomp', 'holler'],  # Remove the 'and'
            "black 'n' roll": ['black', 'rock-and-roll'],  # Fix the n' roll part
            'no wave': ['no-wave'],  # Keep as single genre concept
        }
        
        for compound, fixed_components in problematic_fixes.items():
            if compound in self.config['atomic_decomposition']:
                current = self.config['atomic_decomposition'][compound]
                self.config['atomic_decomposition'][compound] = fixed_components
                self.changes_made.append(f"Fixed problematic decomposition: {compound} → {fixed_components} (was {current})")
        
        # Find remaining problematic decompositions
        remaining_problematic = []
        
        for compound, components in list(self.config['atomic_decomposition'].items()):
            # Check for remaining problematic components
            if any(comp in ['and', "'n'", 'word', 'score'] for comp in components):
                if compound not in problematic_fixes:  # Only flag if we haven't already fixed it
                    remaining_problematic.append(compound)
                    self.issues_found.append(f"Remaining problematic decomposition: {compound} → {components}")
        
        # Log any remaining issues
        for compound in remaining_problematic:
            print(f"⚠️  Still needs review: {compound} → {self.config['atomic_decomposition'][compound]}")
    
    def add_tag_consolidation_rules(self):
        """Add rules to consolidate similar tags."""
        print("🔧 Adding tag consolidation rules...")
        
        # Consolidation rules for similar tags
        consolidation_rules = {
            # Alternative variants
            'alternitive': 'alternative',
            'anternative': 'alternative',
            'alt-rock': 'alternative rock',
            'alt-metal': 'alternative metal',
            'alt-punk': 'alternative punk',
            
            # Progressive variants  
            'progresive': 'progressive',
            'prog': 'progressive',
            'prog-rock': 'progressive rock',
            'prog-metal': 'progressive metal',
            
            # Experimental variants
            'expirimental': 'experimental',
            'exp': 'experimental',
            'exp-electronic': 'experimental electronic',
            
            # Psychedelic variants
            'psych': 'psychedelic',
            'psychedelia': 'psychedelic',
            'pscyhedelic': 'psychedelic',
            'pyschedelic': 'psychedelic',
            
            # Electronic variants
            'electonic': 'electronic',
            'electronics': 'electronic',
            'electronica': 'electronic',
            
            # Metal variants
            'metal/rock': 'metal rock',
            'rock/metal': 'rock metal',
            'heavy-metal': 'heavy metal',
            'death-metal': 'death metal',
            'black-metal': 'black metal',
            
            # Neo variants
            'neo-folk': 'neofolk',
            'neo-classical': 'neoclassical',
            'neo-soul': 'neo soul'
        }
        
        # Add to tag_substitutions
        if 'tag_substitutions' not in self.config:
            self.config['tag_substitutions'] = {}
        
        for variant, canonical in consolidation_rules.items():
            if variant not in self.config['tag_substitutions']:
                self.config['tag_substitutions'][variant] = canonical
                self.changes_made.append(f"Added consolidation: {variant} → {canonical}")
    
    def clean_problematic_csv_tags(self):
        """Clean up specific problematic tags identified in the CSV export."""
        print("🔧 Cleaning problematic tags from CSV analysis...")
        
        # Tags that should be deleted/ignored (from CSV analysis)
        tags_to_delete = [
            "'n'", "and", "band", "bass", "beats", "bop", "breaks", "collage", 
            "core", "dance", "disco", "electronics", "fi house", "fi shoegaze",
            "garde", "gaze", "guitar", "hop", "house", "mex", "music", "no",
            "opera", "psych", "revival", "roll", "score", "songwriter", "wave",
            "word", "holler", "shanty", "big", "drum", "dirt"
        ]
        
        # Add these to tag_deletions if not already there
        if 'tag_deletions' not in self.config:
            self.config['tag_deletions'] = []
        
        added_deletions = 0
        for tag in tags_to_delete:
            if tag not in self.config['tag_deletions']:
                self.config['tag_deletions'].append(tag)
                added_deletions += 1
        
        if added_deletions > 0:
            self.changes_made.append(f"Added {added_deletions} problematic tags to deletion list")
        
        # Tags that need substitution/consolidation (from CSV analysis)
        csv_substitutions = {
            # Misspellings and typos
            'expirimental': 'experimental',
            'alternitive': 'alternative',
            'progresive': 'progressive',
            'pyschedelic rock': 'psychedelic rock',
            'pscyhedelic rock': 'psychedelic rock',
            
            # Fragmentations that should be consolidated
            'garde metal': 'avant-garde metal',
            'garde jazz': 'avant-garde jazz',
            'garde black metal': 'avant-garde black metal',
            'metal/rock': 'metal rock',
            'rock/metal': 'rock metal',
            
            # Electronic variants
            'electronics': 'electronic',
            'electronica': 'electronic',
            
            # Core corrections
            'core': 'hardcore',
            'gaze': 'shoegaze',
            'wave': 'wave music',
            'hop': 'hip-hop',
            'psych': 'psychedelic',
            'psychedelia': 'psychedelic',
            
            # Singer-songwriter fix
            'singer': 'singer-songwriter',
            'songwriter': 'singer-songwriter',
            
            # Neo- variants
            'neo folk': 'neofolk',
            'neo-folk': 'neofolk',
            'neo classical': 'neoclassical',
            'neo-classical': 'neoclassical',
            
            # Tronica variants  
            'folktronica': 'folk electronic',
            'indietronica': 'indie electronic',
            
            # Blackgaze and related
            'blackgaze': 'black shoegaze',
            'grungegaze': 'grunge shoegaze',
            
            # Modern variations
            'modern rock': 'contemporary rock',
            'modern metal': 'contemporary metal',
            
            # Other cleanups
            'trap metal': 'trap metal fusion',
            'doom rock': 'doom-influenced rock',
            'jazzcore': 'jazz hardcore',
            'no wave': 'no-wave'
        }
        
        # Add to substitutions
        if 'substitutions' not in self.config:
            self.config['substitutions'] = {}
        
        added_subs = 0
        for original, replacement in csv_substitutions.items():
            if original not in self.config['substitutions']:
                self.config['substitutions'][original] = replacement
                added_subs += 1
        
        if added_subs > 0:
            self.changes_made.append(f"Added {added_subs} CSV-based substitution rules")
    
    def optimize_atomic_decomposition_for_csv_issues(self):
        """Optimize atomic decompositions to address CSV filtering issues."""
        print("🔧 Optimizing atomic decompositions for CSV issues...")
        
        # Fix decompositions for tags that have zero matching count in CSV
        zero_match_fixes = {
            # These should not be standalone atomic components
            'black metal': ['black', 'metal'],  # Keep decomposed
            'metal/rock': ['metal', 'rock'],    # Fix the slash
            'rock/metal': ['rock', 'metal'],    # Fix the slash
            'garde metal': ['avant-garde', 'metal'],    # Fix garde fragment
            'garde jazz': ['avant-garde', 'jazz'],      # Fix garde fragment
            'garde black metal': ['avant-garde', 'black', 'metal'], # Fix garde fragment
            
            # Alternative/progressive variants
            'alternitive': ['alternative'],      # Fix typo
            'alternative': ['alternative'],      # Keep as single
            'progressive': ['progressive'],      # Keep as single
            'expirimental': ['experimental'],    # Fix typo
            
            # Electronic variants
            'electronics': ['electronic'],       # Consolidate
            'electronica': ['electronic'],       # Consolidate
            
            # Psychedelic variants
            'psych': ['psychedelic'],            # Expand abbreviation
            'psychedelia': ['psychedelic'],      # Consolidate
            
            # Singer-songwriter fix (should be single concept)
            'singer': ['singer-songwriter'],
            'songwriter': ['singer-songwriter'],
            'singer-songwriter': ['singer-songwriter'],  # Keep whole
            
            # Neo- variants
            'neoclassical': ['neoclassical'],    # Keep as single modern term
            'neofolk': ['neofolk'],              # Keep as single modern term
            
            # Avant-garde should be kept whole
            'avant-garde': ['avant-garde'],
            'avant': ['avant-garde'],            # Expand fragment
            
            # Modern electronic fusion terms
            'folktronica': ['folk', 'electronic'],
            'indietronica': ['indie', 'electronic'],
            'neoclassical darkwave': ['neoclassical', 'darkwave'],
            
            # Gaze variations
            'blackgaze': ['black', 'shoegaze'],
            'grungegaze': ['grunge', 'shoegaze'],
            'doomgaze': ['doom', 'shoegaze'],
            
            # Core variations (hardcore is the full term)
            'jazzcore': ['jazz', 'hardcore'],
            'mathcore': ['math', 'hardcore'],
            'emocore': ['emo', 'hardcore'],
            
            # Modern terms that should stay whole
            'trap metal': ['trap', 'metal'],
            'doom rock': ['doom', 'rock'],
            'acid folk': ['acid', 'folk'],
            'acid rock': ['acid', 'rock'],
            'jazz rap': ['jazz', 'rap'],
            'industrial techno': ['industrial', 'techno'],
            'dissonant metal': ['dissonant', 'metal'],
            'epic black metal': ['epic', 'black', 'metal'],
            'blackened death metal': ['blackened', 'death', 'metal'],
            'modern rock': ['contemporary', 'rock'],
            'prog pop': ['progressive', 'pop']
        }
        
        # Update decomposition rules
        if 'atomic_decomposition' not in self.config:
            self.config['atomic_decomposition'] = {}
        
        updates_made = 0
        for tag, components in zero_match_fixes.items():
            if tag not in self.config['atomic_decomposition']:
                self.config['atomic_decomposition'][tag] = components
                updates_made += 1
                self.changes_made.append(f"Added decomposition for CSV issue: {tag} → {components}")
            else:
                # Check if it needs updating
                current = self.config['atomic_decomposition'][tag]
                if current != components:
                    self.config['atomic_decomposition'][tag] = components
                    updates_made += 1
                    self.changes_made.append(f"Updated decomposition for CSV issue: {tag} → {components} (was {current})")
        
        if updates_made > 0:
            self.changes_made.append(f"Optimized {updates_made} decompositions for CSV filtering issues")
    
    def validate_atomic_tags_list(self):
        """Validate and improve the atomic tags list."""
        print("🔧 Validating atomic tags list...")
        
        # Collect all atomic components used in decompositions
        used_atomics = set()
        for components in self.config.get('atomic_decomposition', {}).values():
            used_atomics.update(components)
        
        # Add core atomic tags that should always be valid
        core_atomics = {
            'rock', 'metal', 'pop', 'folk', 'jazz', 'blues', 'country', 'electronic', 
            'classical', 'ambient', 'punk', 'hardcore', 'alternative', 'indie', 
            'progressive', 'experimental', 'post', 'avant-garde', 'psychedelic',
            'atmospheric', 'technical', 'melodic', 'brutal', 'heavy', 'dark',
            'doom', 'death', 'black', 'thrash', 'power', 'speed', 'groove',
            'stoner', 'sludge', 'drone', 'funeral', 'symphonic', 'gothic',
            'industrial', 'noise', 'math', 'art', 'dream', 'shoegaze',
            'grunge', 'britpop', 'garage', 'surf', 'ska', 'reggae',
            'hip-hop', 'rap', 'soul', 'funk', 'disco', 'house', 'techno',
            'trance', 'dnb', 'dub', 'dubstep', 'trap', 'lo-fi', 'chillout',
            'singer-songwriter', 'chamber', 'orchestral', 'tribal', 'world',
            'latin', 'celtic', 'medieval', 'baroque', 'romantic', 'modern',
            'contemporary', 'neo', 'new', 'old', 'traditional', 'acoustic',
            'electric', 'instrumental', 'vocal', 'live', 'studio', 'neoclassical',
            'neofolk', 'darkwave', 'blackened', 'epic', 'dissonant', 'acid',
            'cinematic', 'space', 'cosmic', 'ethereal', 'atmospheric'
        }
        
        used_atomics.update(core_atomics)
        
        # Update atomic_tags section
        if 'atomic_tags' not in self.config:
            self.config['atomic_tags'] = {}
        
        if 'all_valid_tags' not in self.config['atomic_tags']:
            self.config['atomic_tags']['all_valid_tags'] = []
        
        current_valid = set(self.config['atomic_tags']['all_valid_tags'])
        new_valid = used_atomics - current_valid
        
        if new_valid:
            self.config['atomic_tags']['all_valid_tags'].extend(sorted(new_valid))
            self.changes_made.append(f"Added {len(new_valid)} new valid atomic tags")
        """Validate and improve the atomic tags list."""
        print("🔧 Validating atomic tags list...")
        
        # Collect all atomic components used in decompositions
        used_atomics = set()
        for components in self.config.get('atomic_decomposition', {}).values():
            used_atomics.update(components)
        
        # Add core atomic tags that should always be valid
        core_atomics = {
            'rock', 'metal', 'pop', 'folk', 'jazz', 'blues', 'country', 'electronic', 
            'classical', 'ambient', 'punk', 'hardcore', 'alternative', 'indie', 
            'progressive', 'experimental', 'post', 'avant-garde', 'psychedelic',
            'atmospheric', 'technical', 'melodic', 'brutal', 'heavy', 'dark',
            'doom', 'death', 'black', 'thrash', 'power', 'speed', 'groove',
            'stoner', 'sludge', 'drone', 'funeral', 'symphonic', 'gothic',
            'industrial', 'noise', 'math', 'art', 'dream', 'shoegaze',
            'grunge', 'britpop', 'garage', 'surf', 'ska', 'reggae',
            'hip-hop', 'rap', 'soul', 'funk', 'disco', 'house', 'techno',
            'trance', 'dnb', 'dub', 'dubstep', 'trap', 'lo-fi', 'chillout',
            'singer-songwriter', 'chamber', 'orchestral', 'tribal', 'world',
            'latin', 'celtic', 'medieval', 'baroque', 'romantic', 'modern',
            'contemporary', 'neo', 'new', 'old', 'traditional', 'acoustic',
            'electric', 'instrumental', 'vocal', 'live', 'studio'
        }
        
        used_atomics.update(core_atomics)
        
        # Update atomic_tags section
        if 'atomic_tags' not in self.config:
            self.config['atomic_tags'] = {}
        
        if 'all_valid_tags' not in self.config['atomic_tags']:
            self.config['atomic_tags']['all_valid_tags'] = []
        
        current_valid = set(self.config['atomic_tags']['all_valid_tags'])
        new_valid = used_atomics - current_valid
        
        if new_valid:
            self.config['atomic_tags']['all_valid_tags'].extend(sorted(new_valid))
            self.changes_made.append(f"Added {len(new_valid)} new valid atomic tags")
    
    def run_comprehensive_review(self, dry_run: bool = True) -> Dict:
        """Run comprehensive review and fix process."""
        print("🚀 Starting comprehensive tag rules review...")
        print(f"📊 Current config has {len(self.config.get('atomic_decomposition', {}))} decomposition rules")
        
        if not dry_run:
            backup_path = self.create_backup()
        
        # Run all fix processes
        self.fix_typos_and_misspellings()
        self.fix_fragmented_atomic_components()
        self.clean_problematic_csv_tags()
        self.improve_atomic_decomposition_rules()
        self.optimize_atomic_decomposition_for_csv_issues()
        self.remove_problematic_decompositions()
        self.add_tag_consolidation_rules()
        self.validate_atomic_tags_list()
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'changes_made': len(self.changes_made),
            'issues_found': len(self.issues_found),
            'decomposition_rules_after': len(self.config.get('atomic_decomposition', {})),
            'valid_atomic_tags': len(self.config.get('atomic_tags', {}).get('all_valid_tags', [])),
            'changes': self.changes_made,
            'issues': self.issues_found
        }
        
        if not dry_run:
            # Save updated configuration
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ Updated configuration saved to {self.config_path}")
            report['backup_path'] = backup_path
        
        return report
    
    def print_report(self, report: Dict):
        """Print comprehensive report of changes."""
        print("\n" + "="*70)
        print("📋 TAG RULES REVIEW REPORT")
        print("="*70)
        print(f"🕒 Timestamp: {report['timestamp']}")
        print(f"🔄 Mode: {'DRY RUN' if report['dry_run'] else 'APPLIED'}")
        print(f"✅ Changes made: {report['changes_made']}")
        print(f"⚠️  Issues found: {report['issues_found']}")
        print(f"📊 Decomposition rules: {report['decomposition_rules_after']}")
        print(f"🏷️  Valid atomic tags: {report['valid_atomic_tags']}")
        
        if report.get('backup_path'):
            print(f"💾 Backup created: {report['backup_path']}")
        
        if report['changes']:
            print(f"\n📝 CHANGES MADE ({len(report['changes'])}):")
            for i, change in enumerate(report['changes'][:20], 1):  # Show first 20
                print(f"  {i:2d}. {change}")
            if len(report['changes']) > 20:
                print(f"     ... and {len(report['changes']) - 20} more")
        
        if report['issues']:
            print(f"\n⚠️  ISSUES FOUND ({len(report['issues'])}):")
            for i, issue in enumerate(report['issues'], 1):
                print(f"  {i:2d}. {issue}")
        
        print("\n" + "="*70)
        
        if report['dry_run']:
            print("🔴 This was a DRY RUN - no changes were applied")
            print("   Run with --apply to make changes")
        else:
            print("✅ Changes have been applied to the configuration")
        
        print("="*70)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Review and fix tag rules configuration')
    parser.add_argument('--dry-run', action='store_true', default=True,
                      help='Show what would be changed without applying (default)')
    parser.add_argument('--apply', action='store_true',
                      help='Apply changes to configuration (overrides --dry-run)')
    parser.add_argument('--config', type=str,
                      help='Path to tag rules config file (optional)')
    
    args = parser.parse_args()
    
    # Override dry_run if --apply is specified
    dry_run = not args.apply
    
    try:
        reviewer = TagRulesReviewer(args.config)
        report = reviewer.run_comprehensive_review(dry_run=dry_run)
        reviewer.print_report(report)
        
        if dry_run:
            print("\n💡 To apply these changes, run:")
            print("   python tag_rules_review_and_fix.py --apply")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during review: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
