#!/usr/bin/env python3
"""
Phase 5 Strategic Implementation - Apply high-confidence ultra-aggressive optimizations
Focus on maximum impact while preserving music discovery value
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def apply_phase5_strategic_optimization():
    """Apply strategic ultra-aggressive optimizations to reach <600 tags."""
    
    config_path = Path('../src/albumexplore/config/tag_rules.json')
    
    # Create backup
    backup_path = f'tag_rules_backup_phase5_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    shutil.copy(config_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    # Load current config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Current counts
    current_deletions = len(config.get('tag_deletions', []))
    current_substitutions = len(config.get('tag_substitutions', {}))
    current_decompositions = len(config.get('atomic_decomposition', {}))
    
    print("=== Phase 5 Strategic Ultra-Aggressive Optimization ===")
    print("Target: Reach <600 tags with strategic deletions")
    
    # High-confidence strategic deletions
    new_deletions = set(config.get('tag_deletions', []))
    
    # 1. Ultra-aggressive singleton deletions (high confidence)
    ultra_aggressive_singletons = [
        # Technical artifacts and format tags
        'vgm', 'midi', '8-bit', 'lo-fi', 'electroclash', 'electronicore', 'electropunk',
        'cybergrunge', 'dreamcore', 'deathjazz', 'deathgaze', 'darksynth',
        
        # Geographic over-specificity
        'african', 'american', 'gaelic', 'ethio', 'animistic', 'anti',
        
        # Overly niche descriptors
        'adventure', 'big', 'nature', 'witch', 'smooth soul', 'lover rock',
        'quasi metal', 'scum rock', 'egg punk', 'brostep', 'slushwave',
        'dolewave', 'visepop', 'skatepunk', 'mincecore', 'spacegrind',
        
        # Technical fragments
        'band', 'breaks', 'collage', 'dirt', 'dubstep', 'house', 'shanty',
        'apocalyptic', 'fi house', 'fi shanty', 'garde', 'garde black metal',
        'garde jazz', 'garde metal', 'gaze', 'grrrl', 'guitar', 'holler',
        'hop', 'mex', 'music', 'pagan folk', 'psych', 'punk revival',
        'revival', 'rock/metal', 'metal/rock', 'metalcore', 'roll', 'score',
        'songwriter', 'wave', 'word'
    ]
    
    # 2. Low-frequency aggressive deletions (2-3 count)
    low_freq_deletions = [
        'adult', 'alt-blues', 'appalachian', 'breakbeat', 'chanson', 'chaotic',
        'chicago', 'country blues', 'country folk', 'cyberpunk', 'dark electro',
        'disco-funk', 'dsbm', 'easycore', 'electro house', 'electro-funk',
        'emo punk', 'emocore', 'experimental folk', 'experimental noise',
        'film', 'french pop', 'gothic pop', 'heavy blues', 'hindustani',
        'jazz pop', 'jazz rap', 'jazz-core', 'jazz-pop', 'jazzgrind',
        'kawaii metal', 'mittelalter-metal', 'nautical metal', 'nordic',
        'nugaze', 'osdm', 'party metal', 'pagan metal', 'pirate metal',
        'proto-metal', 'proto-punk', 'retro rock', 'ritual', 'rockabilly',
        'roots', 'sasscore', 'stomp', 'stargaze', 'sunshine pop', 'swing',
        'synthrock', 'tex', 'third stream', 'trip', 'tropical', 'twee',
        'uk', 'viking', 'vocal', 'war', 'warr', 'windmill'
    ]
    
    # 3. Technical and format artifacts (medium frequency)
    technical_artifacts = [
        'digital', 'bitpop', 'bitprog', 'chiptune', 'glitch bitpop', 'glitch hop',
        'glitch metal', 'tape music', 'techno house', 'trance house', 'trance metal'
    ]
    
    # Apply all deletions
    all_strategic_deletions = ultra_aggressive_singletons + low_freq_deletions + technical_artifacts
    
    for tag in all_strategic_deletions:
        new_deletions.add(tag)
    
    # Strategic decompositions for high-value compound tags
    new_decompositions = config.get('atomic_decomposition', {}).copy()
    
    # High-confidence compound decompositions
    strategic_decompositions = {
        # Alt- compounds
        'alt-drone': ['alt', 'drone'],
        'alt-gothic': ['alt', 'gothic'],
        'alt-jazz': ['alt', 'jazz'],
        'alt-prog': ['alt', 'prog'],
        
        # Atmospheric compounds
        'atmospheric drum and bass': ['atmospheric', 'drum', 'bass'],
        'atmospheric dark rock': ['atmospheric', 'dark', 'rock'],
        'atmospheric rock': ['atmospheric', 'rock'],
        'atmospheric sludge': ['atmospheric', 'sludge'],
        
        # Alternative compounds
        'alternative hip hop': ['alternative', 'hip', 'hop'],
        'alternative pop': ['alternative', 'pop'],
        'alternative reggae': ['alternative', 'reggae'],
        'alternative rock/indie rock/emo': ['alternative', 'rock', 'indie', 'emo'],
        
        # Ambient compounds  
        'ambient country': ['ambient', 'country'],
        'ambient dub': ['ambient', 'dub'],
        
        # Black metal compounds
        'atmosheric black metal': ['atmospheric', 'black', 'metal'],
        'blackened doom': ['blackened', 'doom'],
        'blackened grindcore': ['blackened', 'grindcore'],
        'blackened/melodic death metal': ['blackened', 'melodic', 'death', 'metal'],
        'black metal/death metal': ['black', 'metal', 'death', 'metal'],
        'black n\' roll': ['black', 'roll'],
        'black noise': ['black', 'noise'],
        
        # Chamber compounds
        'chamber prog': ['chamber', 'prog'],
        'chamber rock': ['chamber', 'rock'],
        
        # Contemporary compounds
        'contemporary blues': ['contemporary', 'blues'],
        'contemporary classic': ['contemporary', 'classic'],
        'contemporary funk': ['contemporary', 'funk'],
        'contemporary pop': ['contemporary', 'pop'],
        'contemporary rock': ['contemporary', 'rock'],
        'contemporary soul': ['contemporary', 'soul'],
        
        # Country compounds
        'country doom': ['country', 'doom'],
        'country pop': ['country', 'pop'],
        'country soul': ['country', 'soul'],
        
        # Death metal compounds
        'doom death metal': ['doom', 'death', 'metal'],
        'death black': ['death', 'black'],
        'death rock': ['death', 'rock'],
        
        # Dream compounds
        'dream metal': ['dream', 'metal'],
        'dream punk': ['dream', 'punk'],
        
        # Experimental compounds
        'experimental big band': ['experimental', 'big', 'band'],
        'experimental doom metal': ['experimental', 'doom', 'metal'],
        'experimental drone': ['experimental', 'drone'],
        'experimental drone metal': ['experimental', 'drone', 'metal'],
        'experimental folk rock': ['experimental', 'folk', 'rock'],
        'experimental hardcore': ['experimental', 'hardcore'],
        'experimental pop rock': ['experimental', 'pop', 'rock'],
        'experimental sludge metal': ['experimental', 'sludge', 'metal'],
        
        # Instrumental compounds
        'instrumental math rock': ['instrumental', 'math', 'rock'],
        'instrumental post-rock': ['instrumental', 'post', 'rock'],
        'instrumental progressive metal': ['instrumental', 'progressive', 'metal'],
        'instrumental progressive rock': ['instrumental', 'progressive', 'rock'],
        'instrumental rock': ['instrumental', 'rock'],
        
        # Melodic compounds
        'melodic guitar': ['melodic', 'guitar'],
        'melodic house': ['melodic', 'house'],
        'melodic prog': ['melodic', 'prog'],
        'melodic prog-metal': ['melodic', 'prog', 'metal'],
        'melodic prog-metal/rock': ['melodic', 'prog', 'metal', 'rock'],
        'melodic rock': ['melodic', 'rock'],
        'melodic/blackened death metal': ['melodic', 'blackened', 'death', 'metal'],
        'melodic/technical death metal': ['melodic', 'technical', 'death', 'metal'],
        
        # Post compounds
        'post-black': ['post', 'black'],
        'post-metal/hardcore': ['post', 'metal', 'hardcore'],
        'post-rock/alternative': ['post', 'rock', 'alternative'],
        
        # Progressive compounds
        'progressive beats': ['progressive', 'beats'],
        
        # Psychedelic compounds
        'psychedelic death metal': ['psychedelic', 'death', 'metal'],
        'psychedelic doom metal': ['psychedelic', 'doom', 'metal'],
        'psychedelic funk': ['psychedelic', 'funk'],
        'psychedelic sludge metal': ['psychedelic', 'sludge', 'metal'],
        'psychedelic stoner metal': ['psychedelic', 'stoner', 'metal'],
        'psychedelic trance': ['psychedelic', 'trance'],
        'psychedelic/space rock': ['psychedelic', 'space', 'rock'],
        'psychedelick rock': ['psychedelic', 'rock'],
        
        # Space compounds
        'space black metal': ['space', 'black', 'metal'],
        'space-punk': ['space', 'punk'],
        
        # Symphonic compounds
        'symphonic black': ['symphonic', 'black'],
        'symphonic folk metal': ['symphonic', 'folk', 'metal'],
        'symphonic prog-rock': ['symphonic', 'prog', 'rock'],
        'symphonic progressive rock': ['symphonic', 'progressive', 'rock'],
        
        # Technical compounds
        'technical black metal': ['technical', 'black', 'metal'],
        'technical punk': ['technical', 'punk'],
        'technical/melodic death metal': ['technical', 'melodic', 'death', 'metal'],
        
        # Synth compounds
        'synth doom': ['synth', 'doom'],
        'synth pop': ['synth', 'pop'],
        'synth rock': ['synth', 'rock'],
        'synth-pop': ['synth', 'pop'],
        'synthgaze': ['synth', 'gaze']
    }
    
    new_decompositions.update(strategic_decompositions)
    
    # Strategic substitutions and normalizations
    new_substitutions = config.get('tag_substitutions', {}).copy()
    new_substitutions.update({
        # Fix typos
        'atmosheric black metal': 'atmospheric black metal',
        'blackend hardcore': 'blackened hardcore',
        'bluegras': 'bluegrass',
        'electonic': 'electronic',
        'ghotic metal': 'gothic metal',
        'kosmsiche': 'kosmische',
        'mitteralter metal': 'mittelalter metal',
        'neoclassica': 'neoclassical',
        'pschedelic': 'psychedelic',
        'pscyhedelic rock': 'psychedelic rock',
        'psyechedelic': 'psychedelic',
        'pyschedelic rock': 'psychedelic rock',
        'sympohnic': 'symphonic',
        'tharsh metal': 'thrash metal',
        'yatch rock': 'yacht rock',
        'zheul': 'zeuhl',
        
        # Consolidate variants
        'metal-core': 'metalcore',
        'rock-pop': 'pop rock',
        'rock n\' roll': 'rock and roll',
        'soul-jazz': 'soul jazz',
        'post prog': 'post prog rock',
        'speed/thrash metal': 'speed thrash metal',
        'doom rock/metal': 'doom rock metal',
        'doom metal/rock': 'doom metal rock',
        'stoner metal/rock': 'stoner metal rock',
        'stoner rock/metal': 'stoner rock metal'
    })
    
    # Update config
    config['tag_deletions'] = sorted(list(new_deletions))
    config['tag_substitutions'] = new_substitutions
    config['atomic_decomposition'] = new_decompositions
    
    # Save updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # Report changes
    new_deletion_count = len(config['tag_deletions'])
    new_substitution_count = len(config['tag_substitutions'])
    new_decomposition_count = len(config['atomic_decomposition'])
    
    print("\n=== Phase 5 Strategic Optimization Applied ===")
    print(f"Deletions: {current_deletions} → {new_deletion_count} (+{new_deletion_count - current_deletions})")
    print(f"Substitutions: {current_substitutions} → {new_substitution_count} (+{new_substitution_count - current_substitutions})")
    print(f"Decompositions: {current_decompositions} → {new_decomposition_count} (+{new_decomposition_count - current_decompositions})")
    
    added_deletions = new_deletion_count - current_deletions
    added_substitutions = new_substitution_count - current_substitutions
    added_decompositions = new_decomposition_count - current_decompositions
    
    print(f"\nEstimated tag reduction:")
    print(f"- Direct deletions: ~{added_deletions}")
    print(f"- Consolidations: ~{added_substitutions}")
    print(f"- Decompositions: ~{added_decompositions * 0.7:.0f}")
    print(f"- **Total estimated reduction: ~{added_deletions + added_substitutions + (added_decompositions * 0.7):.0f} tags**")
    
    current_estimated = 757
    estimated_new_count = current_estimated - (added_deletions + added_substitutions + (added_decompositions * 0.7))
    total_reduction_from_original = 1010 - estimated_new_count
    
    print(f"\nProjected tag count: 757 → ~{estimated_new_count:.0f}")
    print(f"Total reduction from original 1,010: {total_reduction_from_original:.0f} tags ({(total_reduction_from_original / 1010 * 100):.1f}%)")
    
    if estimated_new_count < 600:
        print(f"\n🎉 TARGET ACHIEVED! Projected count ({estimated_new_count:.0f}) is under 600!")
    else:
        print(f"\n⚠️  Close to target. May need additional optimization.")
    
    print(f"\n✅ Phase 5 strategic optimization complete!")
    print(f"🔄 Next: Export new tag data to validate final impact")
    
    return True

if __name__ == '__main__':
    apply_phase5_strategic_optimization()
