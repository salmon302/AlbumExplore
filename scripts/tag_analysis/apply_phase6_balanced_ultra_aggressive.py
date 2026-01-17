#!/usr/bin/env python3
"""
Phase 6 Balanced Ultra-Aggressive Implementation
Target: Reduce from 675 to <600 tags (75+ tag reduction) while preserving music discovery
"""

import json
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime

def apply_phase6_balanced_ultra_aggressive():
    """Apply balanced ultra-aggressive optimization to reach <600 tags safely."""
    
    config_path = Path('../src/albumexplore/config/tag_rules.json')
    
    # Create backup
    backup_path = f'tag_rules_backup_phase6_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    shutil.copy(config_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    # Load current config and CSV
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    df = pd.read_csv('../atomic_tags_export2.csv')
    
    print("=== Phase 6 Balanced Ultra-Aggressive Optimization ===")
    print("Target: 675 → <600 tags (75+ tag reduction)")
    print("Strategy: High-confidence deletions + strategic decompositions")
    
    # Current counts
    current_deletions = len(config.get('tag_deletions', []))
    current_substitutions = len(config.get('tag_substitutions', {}))
    current_decompositions = len(config.get('atomic_decomposition', {}))
    
    new_deletions = set(config.get('tag_deletions', []))
    new_substitutions = config.get('tag_substitutions', {}).copy()
    new_decompositions = config.get('atomic_decomposition', {}).copy()
    
    # 1. HIGH-CONFIDENCE SINGLETON DELETIONS (Target: ~200 deletions)
    print("\n1. High-confidence singleton deletions...")
    
    singletons = df[df['Count'] == 1]['Tag'].tolist()
    
    # Categories for aggressive deletion
    delete_patterns = {
        'technical_artifacts': [
            '8-bit', 'bitpop', 'bitprog', 'midi', 'vgm', 'lo-fi', 'fi house', 'fi shoegaze'
        ],
        'overly_specific_geography': [
            'african', 'american', 'gaelic', 'ethio', 'animistic', 'anti', 'cavernous death metal'
        ],
        'overly_niche_descriptors': [
            'adventure', 'big', 'nature', 'witch', 'anxiety pop', 'angular pop', 'arena',
            'apocalyptic', 'baggy', 'berlin school', 'brostep', 'bubblegum bass', 'cabaret',
            'cathedral bells', 'chillout', 'comedy', 'cosmic rock', 'dadaist', 'documentary',
            'dolewave', 'egg punk', 'fleetwood mac?', 'futuristic', 'global groove', 'igorrr'
        ],
        'style_suffixes': [
            'crimson-esque', 'crimson-y', 'deep purple-ish', 'djent-ish lite', 'floyd-esque',
            'gong-related', 'hawkwind-ish', 'king gizzard-like', 'primus-related', 'riverside-esque',
            'rush-oriented', 'seventh wonder-ish', 'soft machine-related'
        ],
        'technical_terms': [
            'artcore', 'breakbeats', 'cybergrunge', 'deathgaze', 'dreamcore', 'electroclash',
            'electronicore', 'electropunk', 'kawaii', 'mincecore', 'nintendocore', 'osdm',
            'outsider house', 'pigfuck', 'plunderphonics', 'scum rock', 'slushwave', 'visepop'
        ],
        'format_specific': [
            'audiobook', 'documentary', 'movie soundtrack', 'musical parody', 'musical theatre',
            'poems', 'soundtrack'
        ]
    }
    
    high_confidence_deletions = []
    for category, tags in delete_patterns.items():
        for tag in tags:
            if tag in singletons:
                high_confidence_deletions.append(tag)
                new_deletions.add(tag)
    
    # Add more singleton deletions for low-value tags
    additional_singletons = [
        'acapella', 'a capella', 'afro indie', 'afro-funk', 'afro-rock', 'afrolatin',
        'american privitsm', 'anternative', 'arabic pop', 'bolero-beat', 'boogie',
        'carnatic', 'chillstep', 'cinmatic', 'comedy rock', 'cosmic doom metal',
        'dance music', 'dance rock', 'deep funk', 'disco-pop', 'disco-punk',
        'djenty', 'drone pop', 'drum-oriented', 'east african music', 'eastern european',
        'eclectic rock', 'edm', 'electonic', 'electronic music', 'emocrust',
        'epic vampyric black metal', 'ethereal doom metal', 'fates warning related',
        'film', 'flamenco', 'folklore', 'french electro', 'fuzz funk', 'geek rock',
        'ghotic metal', 'glam punk', 'glitch bitpop', 'glitch hop', 'glitch metal',
        'gong-related', 'gospel', 'goth rock', 'grunegaze', 'guitar virtuoso',
        'hard prog', 'hardcore funk', 'hardcore hip hop', 'hardcore rap', 'heavy pop rock',
        'heavy twang', 'hellenic black metal', 'hill country blues', 'hip hop soul',
        'hip-hop soul', 'indian', 'indie hip hop', 'indie soul', 'industrial hardcore',
        'industrial punk', 'irish folk music', 'italian prog', 'italo-disco',
        'jangle punk', 'jangle rock', 'jazz-core', 'jazz-pop', 'keyboard', 'keyboard-driven',
        'korean folk', 'kosmsiche', 'latin big band', 'latin pop', 'latin rock', 'latin-jazz',
        'lo-fi', 'lounge', 'lover rock', 'mahraganat', 'malian soul', 'medieval folk metal',
        'micro', 'microtonal', 'middle-eastern', 'minimal folk', 'minimal synth', 'minimal wave',
        'mitteralter metal', 'mitteralter-metal', 'mongolian', 'mpb', 'musical', 'musical parody',
        'musical theatre', 'native america', 'neue deutsche härte', 'new rave',
        'new wave and prog rock', 'noise electronics', 'noisegaze', 'nordic folk rock',
        'nordic jazz', 'occult metal', 'oi!', 'old school death metal', 'opera',
        'operatic', 'operatic metal', 'orchestra', 'oriental rock', 'parody metal',
        'persian pop', 'philly soul', 'piano music', 'piano oriented', 'piano-oriented',
        'poems', 'pop art', 'pop metal', 'pop prog', 'pop rap', 'post prog',
        'post-metal‎', 'powerviolence/black metal/death metal', 'prairie gothic',
        'prog -rock', 'prog-?', 'psych rock', 'pub', 'quartet', 'quasi metal',
        'rautalanka', 'red', 'reductionism', 'reggaetón', 'religious', 'retro pop',
        'retro prog', 'rhythm & blues', 'riot', 'rnb', 'rock n\' roll', 'rock-pop',
        'romanian folk', 'sadcore', 'samurai metal', 'saxophone', 'scottish folk music',
        'scottish music', 'sea', 'shaabi', 'shimokita-kei', 'shred', 'sludge rock',
        'sludgecore', 'smooth soul', 'son cubano', 'sophisti-pop', 'soul pop',
        'soul-jazz', 'soundscape', 'southern soul', 'speed/thrash metal', 'steampunk',
        'steelpan', 'swamp', 'tech house', 'thall', 'tharsh metal', 'theatrical',
        'theatrical pop', 'theatrical rock', 'thrashcore', 'trad folk', 'traditional pop',
        'trance house', 'trance metal', 'tropicanibalismo', 'turkish psychedelic',
        'twang', 'uk hip hop', 'uk street soul', 'vampyric black metal', 'vibraphone',
        'welsh folk music', 'welsh rock', 'western noir', 'wind', 'world',
        'world fusion', 'world music (brazil)', 'yacht', 'yatch rock', 'zamrock',
        'zappa', 'zheul'
    ]
    
    for tag in additional_singletons:
        if tag in singletons:
            new_deletions.add(tag)
    
    # 2. LOW-FREQUENCY DELETIONS (Count 2-3)
    print("\n2. Low-frequency deletions...")
    
    low_freq_deletions = [
        'adult', 'appalachian', 'breakbeat', 'chanson', 'chaotic', 'chicago',
        'country blues', 'country folk', 'cyberpunk', 'dark electro', 'disco-funk',
        'dsbm', 'easycore', 'electro house', 'electro-funk', 'emo punk', 'emocore',
        'experimental folk', 'experimental noise', 'french pop', 'gothic pop',
        'heavy blues', 'hindustani', 'jazz pop', 'jazz rap', 'jazzgrind', 'kawaii metal',
        'mittelalter-metal', 'nautical metal', 'nugaze', 'osdm', 'party metal',
        'pagan metal', 'pirate metal', 'proto-metal', 'proto-punk', 'retro rock',
        'ritual', 'rockabilly', 'roots', 'sasscore', 'stomp', 'stargaze',
        'sunshine pop', 'swing', 'synthrock', 'tex', 'third stream', 'trip',
        'tropical', 'twee', 'uk', 'viking', 'vocal', 'war', 'warr', 'windmill'
    ]
    
    for tag in low_freq_deletions:
        new_deletions.add(tag)
    
    # 3. STRATEGIC DECOMPOSITIONS (High-frequency compounds)
    print("\n3. Strategic compound decompositions...")
    
    strategic_decompositions = {
        # High-value compounds that should be broken down
        'alternative hip hop': ['alternative', 'hip', 'hop'],
        'alternative pop': ['alternative', 'pop'],
        'alternative reggae': ['alternative', 'reggae'],
        'ambient country': ['ambient', 'country'],
        'ambient dub': ['ambient', 'dub'],
        'atmospheric drum and bass': ['atmospheric', 'drum', 'bass'],
        'atmospheric dark rock': ['atmospheric', 'dark', 'rock'],
        'atmospheric rock': ['atmospheric', 'rock'],
        'atmospheric sludge': ['atmospheric', 'sludge'],
        'blackened doom': ['blackened', 'doom'],
        'blackened grindcore': ['blackened', 'grindcore'],
        'chamber prog': ['chamber', 'prog'],
        'chamber rock': ['chamber', 'rock'],
        'contemporary blues': ['contemporary', 'blues'],
        'contemporary classic': ['contemporary', 'classic'],
        'contemporary funk': ['contemporary', 'funk'],
        'contemporary pop': ['contemporary', 'pop'],
        'contemporary rock': ['contemporary', 'rock'],
        'contemporary soul': ['contemporary', 'soul'],
        'country doom': ['country', 'doom'],
        'country pop': ['country', 'pop'],
        'country soul': ['country', 'soul'],
        'death rock': ['death', 'rock'],
        'dream metal': ['dream', 'metal'],
        'dream punk': ['dream', 'punk'],
        'experimental big band': ['experimental', 'big', 'band'],
        'experimental doom metal': ['experimental', 'doom', 'metal'],
        'experimental drone': ['experimental', 'drone'],
        'experimental drone metal': ['experimental', 'drone', 'metal'],
        'experimental folk rock': ['experimental', 'folk', 'rock'],
        'experimental hardcore': ['experimental', 'hardcore'],
        'experimental pop rock': ['experimental', 'pop', 'rock'],
        'experimental sludge metal': ['experimental', 'sludge', 'metal'],
        'instrumental math rock': ['instrumental', 'math', 'rock'],
        'instrumental post-rock': ['instrumental', 'post', 'rock'],
        'instrumental progressive metal': ['instrumental', 'progressive', 'metal'],
        'instrumental progressive rock': ['instrumental', 'progressive', 'rock'],
        'instrumental rock': ['instrumental', 'rock'],
        'melodic guitar': ['melodic', 'guitar'],
        'melodic house': ['melodic', 'house'],
        'melodic prog': ['melodic', 'prog'],
        'melodic rock': ['melodic', 'rock'],
        'post-black': ['post', 'black'],
        'psychedelic death metal': ['psychedelic', 'death', 'metal'],
        'psychedelic doom metal': ['psychedelic', 'doom', 'metal'],
        'psychedelic funk': ['psychedelic', 'funk'],
        'psychedelic sludge metal': ['psychedelic', 'sludge', 'metal'],
        'psychedelic stoner metal': ['psychedelic', 'stoner', 'metal'],
        'psychedelic trance': ['psychedelic', 'trance'],
        'space black metal': ['space', 'black', 'metal'],
        'symphonic black': ['symphonic', 'black'],
        'symphonic folk metal': ['symphonic', 'folk', 'metal'],
        'symphonic prog-rock': ['symphonic', 'prog', 'rock'],
        'symphonic progressive rock': ['symphonic', 'progressive', 'rock'],
        'technical black metal': ['technical', 'black', 'metal'],
        'technical punk': ['technical', 'punk'],
        'synth doom': ['synth', 'doom'],
        'synth pop': ['synth', 'pop'],
        'synth rock': ['synth', 'rock'],
        'synth-pop': ['synth', 'pop']
    }
    
    new_decompositions.update(strategic_decompositions)
    
    # 4. FRAGMENT CONSOLIDATIONS
    print("\n4. Fragment consolidations...")
    
    fragment_substitutions = {
        # Consolidate variant spellings and fragments
        'alternitive': 'alternative',
        'anternative': 'alternative',
        'progresive': 'progressive',
        'expirimental': 'experimental',
        'pschedelic': 'psychedelic',
        'pscyhedelic rock': 'psychedelic rock',
        'psyechedelic': 'psychedelic',
        'pyschedelic rock': 'psychedelic rock',
        'bluegras': 'bluegrass',
        'electonic': 'electronic',
        'ghotic metal': 'gothic metal',
        'kosmsiche': 'kosmische',
        'mitteralter metal': 'mittelalter metal',
        'neoclassica': 'neoclassical',
        'sympohnic': 'symphonic',
        'tharsh metal': 'thrash metal',
        'yatch rock': 'yacht rock',
        'zheul': 'zeuhl',
        
        # Standardize separators
        'metal-core': 'metalcore',
        'rock-pop': 'pop rock',
        'soul-jazz': 'soul jazz',
        
        # Consolidate variants
        'prog -rock': 'prog rock',
        'prog-?': 'prog rock',
        'avant-garde': 'avant garde'
    }
    
    new_substitutions.update(fragment_substitutions)
    
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
    
    print("\n=== Phase 6 Balanced Ultra-Aggressive Optimization Applied ===")
    print(f"Deletions: {current_deletions} → {new_deletion_count} (+{new_deletion_count - current_deletions})")
    print(f"Substitutions: {current_substitutions} → {new_substitution_count} (+{new_substitution_count - current_substitutions})")
    print(f"Decompositions: {current_decompositions} → {new_decomposition_count} (+{new_decomposition_count - current_decompositions})")
    
    added_deletions = new_deletion_count - current_deletions
    added_substitutions = new_substitution_count - current_substitutions
    added_decompositions = new_decomposition_count - current_decompositions
    
    print(f"\nEstimated tag reduction:")
    print(f"- Direct deletions: ~{added_deletions}")
    print(f"- Consolidations: ~{added_substitutions}")
    print(f"- Decompositions: ~{added_decompositions * 0.5:.0f}")
    total_reduction = added_deletions + added_substitutions + (added_decompositions * 0.5)
    print(f"- **Total estimated reduction: ~{total_reduction:.0f} tags**")
    
    estimated_new_count = 675 - total_reduction
    print(f"\nProjected tag count: 675 → ~{estimated_new_count:.0f}")
    
    if estimated_new_count < 600:
        print(f"\n🎉 TARGET ACHIEVED! Projected count ({estimated_new_count:.0f}) is under 600!")
    else:
        print(f"\n⚠️  Close to target. Additional optimization may be needed.")
    
    print(f"\n✅ Phase 6 balanced ultra-aggressive optimization complete!")
    print(f"🔄 Next: Export new tag data to validate actual impact")
    
    return True

if __name__ == '__main__':
    apply_phase6_balanced_ultra_aggressive()
