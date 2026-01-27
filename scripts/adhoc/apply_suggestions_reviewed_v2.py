#!/usr/bin/env python3
"""
Batch Application of Tag Suggestions (REVIEWED V2).
Based on scripts/adhoc/apply_suggestions_20260127_133914.py
"""

import sys
import os
from pathlib import Path

# Add src to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent if script_dir.name == 'adhoc' else script_dir.parent
sys.path.append(str(project_root / 'src'))

from albumexplore.tags.config.tag_rules_config import TagRulesConfig

SUGGESTED_MAPPINGS = {
    'woodland black metal': 'black metal',
    'vocal post rock': 'post rock',
    'usway brutal death metal': 'brutal death metal',
    'usa black metal': 'black metal',
    'unblack metal': 'black metal',
    'ukrainian metal': 'ukrainian',
    'uk garage': 'garage',
    'trash metal': 'thrash metal',
    'traditional metal': 'traditional metal',
    'thrashcore': 'thrash core',
    'thrash death metal': 'death metal',
    'thezekinators 2024 album of the year selection': '2024',
    'thezekinators 2024 album of the year runner up': '2024',
    'the best symphonic metal tracks ever recorded': 'symphonic metal',
    'technical thrash': 'technical thrash',
    'technical progressive metal': 'technical progressive metal',
    'technical progressive deathcore': 'technical progressive deathcore',
    'technical progressive death metal': 'technical progressive death metal',
    'technical metalcore': 'metalcore',
    'technical death metal avant garde death metal': 'avant garde death metal',
    'synth metal': 'synth metal',
    # 'symphonic melodic death metal': 'metal', # Too broad
    'symphonic gothic metal': 'symphonic gothic metal',
    'symphonic experimental metal': 'symphonic experimental metal',
    'swedish death metal': 'death metal',
    'speed rock': 'rock',
    'sludge stoner': 'sludge stoner',
    'sludge doom metal': 'doom metal',
    'sludge djent': 'djent',
    'slamming guttural brutal test metal': 'brutal test metal',
    'skate punk': 'skatepunk',
    'serbian pop alchemy': 'serbia',
    'serbian': 'serbia',
    'seattle metal': 'seattle',
    'scifi doom': 'doom',
    # 'sci fi metal': 'metal', # Too broad
    'saxodoom': 'doom',
    'sassy mathcore': 'mathcore',
    'romanian folk music': 'folk',
    'rock n roll': 'rock n\' roll',
    'rock musical': 'rock musical',
    'rock modern': 'rock modern',
    'rock metal': 'rock metal',
    'rock francophone': 'rock',
    'roadburn festival': 'roadburn',
    'releases': 'release',
    # 'release': 'releases', # REMOVED (Circular)
    'regressive metalcore': 'progressive metalcore',
    'punk black metal': 'black metal',
    'psytrance': 'psy trance',
    'psychodelic': 'psychedelic',
    'psychedelic rock neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock space rock stoner thessaloniki': 'psychedelic rock',
    'psychedelic progressive metal': 'psychedelic',
    'psychedelic noise': 'psychedelic',
    'psychedelic drone rock': 'drone',
    'progrock': 'prog-rock',
    'progressive technical death metal': 'technical death metal',
    'progressive stoner': 'progressive stoner',
    'progressive space rock': 'space rock',
    'progressive rock prog rock prog melodic progrock djent': 'melodic', 
    'progressive post metal rock': 'progressive post metal rock',
    'progressive noise rock': 'progressive noise rock',
    'progressive melodic punk a ha black metal': 'black metal',
    # 'progressive mathcore': 'progressive deathcore', # REMOVED (Incorrect)
    'progressive heavy metal': 'progressive heavy metal',
    'progressive groove metal': 'groove metal',
    'progressive doom metal': 'doom metal',
    'progressive death thrash metal': 'thrash metal',
    'progressive brutal death metal': 'death metal',
    'progressive black doom metal': 'progressive black metal',
    'progressive alternative metal': 'progressive alternative metal',
    'progress rock': 'progressive rock',
    'progerssive rock': 'progressive rock',
    'pro rock': 'prog rock',
    'powermetal': 'power metal',
    'post screamo': 'post screamo',
    'post progressive rock': 'post progressive rock',
    'post powerviolence': 'powerviolence',
    'post metalcore': 'metalcore',
    'post grindcore': 'grindcore',
    'post deathcore': 'deathcore',
    'polish black metal': 'black metal',
    'peogressive rock': 'progressive rock',
    # 'orchestral metal': 'metal', # REMOVED (Too Broad)
    'operatic black metal': 'black metal',
    'on vinyl': 'on vinyl',
    # 'olivia': 'bolivia', # REMOVED (Risky)
    'old school progressive metalcore': 'metalcore',
    'old school grindcore': 'grindcore',
    'old school grind': 'grind',
    'ocult rock': 'occult rock',
    'nujazz': 'nu jazz',
    'not djent': 'djent',
    'norwegian death metal': 'death metal',
    # 'northern silence': 'silence', # REMOVED (Label)
    'northern nspordy recs': 'nspordy recs',
    'noise sludge metalcore': 'metalcore',
    'noise metalcore': 'metalcore',
    'noise metal': 'noise metal',
    'new wave of british heavy metal': 'new wave of heavy metal',
    'new metal': 'new metal',
    'new berklee core prog metal': 'new berklee core progressive metal',
    'neoclassicall new age': 'neoclassical new age',         # FIXED
    'neoclassicall melodic death metal': 'neoclassical melodic death metal', # FIXED
    'neo-classical': 'neo classical',
    'neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock psychedelic rock space rock stoner thessaloniki': 'psychedelic rock',
    'neo classical metal': 'neo classical metal',
    'mostly instrumental progressive rock': 'progressive rock',
    'mostly instrumental prog rock': 'prog rock',
    'mostly instrumental prog metal': 'prog metal',
    'modern shoegaze': 'shoegaze',
    'modern melodic death metal': 'modern melodic death metal',
    'modern hardcore': 'hardcore',
    'modern fusion': 'fusion',
    'modern folk metal': 'folk metal',
    'modern emo': 'modern emo',
    # 'modern death metal': 'metal', # REMOVED (Too Broad)
    'modern alternative rock': 'modern alternative rock',
    'midwestern emo': 'midwest emo',
    'microtonal black metal': 'black metal',
    'metal progressive metal': 'progressive metal',
    'melodic thrash metal': 'thrash metal',
    # 'melodic thrash': 'melodic', # REMOVED (Too Broad)
    'melodic post hardcore': 'post hardcore',
    'melodic goregrind': 'goregrind',
    'melodic death power metal': 'power metal',
    'melodic death doom metal': 'doom metal',
    'melancholic black metal': 'melancholic black metal',
    'lol doomergaze': 'doomergaze',
    'live album': 'live',
    'kraut rock': 'krautrock',
    'jazz piano': 'jazz piano',
    # 'japanese psych rock': 'psych rock', # REMOVED (Keep Country)
    'italian progressive rock': 'progressive rock',
    'israeli': 'israel',
    'instrumental progressive death metal': 'instrumental progressive metal',
    'instrumental neo classical progressive death metal': 'instrumental',
    'instrumental ambient': 'ambient',
    'inide rock': 'indie rock',
    'industrial sludge metal': 'sludge metal',
    'industrial dance': 'industrial dance',
    'indonesian black metal': 'indonesia',
    'indigenous north american music': 'indigenous north music',
    'indie folk rock': 'folk rock',
    'indie emo': 'indie emo',
    'in love': 'love',
    'icelandic': 'iceland',
    'hypnogogic pop': 'hypnagogic pop',
    'high speed metal': 'speed metal',
    'heavy thrash metal': 'thrash metal',
    'heavy progressive': 'heavy progressive',
    'heavy power metal': 'power metal',
    'heavy jazz': 'heavy jazz',
    'heavy death metal': 'death metal',
    'hard rock francophone': 'rock',
    'groove deathcore': 'deathcore',
    'grass album art': 'album art',
    'gothic funeral doom metal': 'doom metal',
    'gothic doom': 'gothic doom',
    'german new wave': 'new wave',
    # 'german metal': 'metal', # REMOVED (Keep Country)
    # 'garbage': 'garage', # REMOVED (Likely Band)
    'folk power metal': 'power metal',
    'folk noir': 'folk noir',
    'folk indie': 'folk indie',
    'folk doom metal': 'doom metal',
    'folk doom': 'folk doom',
    'folk death metal': 'folk death metal',
    'flop era': 'flop',
    'finnish melodic death metal': 'melodic death metal',
    'female vocal': 'female vocalists',
    'female singer songwriter': 'singer songwriter',
    'female fronted rock': 'rock',
    'extreme piano metal': 'extreme piano',
    'experimental guitar': 'experimental',
    'experimental grindcore': 'grindcore',
    'experimental deathcore': 'deathcore',
    'estonian': 'estonia',
    'epic folk metal': 'folk metal',
    'english black metal': 'english',
    'emo violence': 'emoviolence',
    'electronic jazz': 'electronic jazz',
    'electro swing': 'electro swing',
    'electro rock': 'electro rock',
    # 'electro metal': 'metal', # REMOVED (Too Broad)
    'elctronic': 'electronic',
    'egyptian': 'egypt',
    'ecletic metal': 'eclectic metal',
    'eclectic metal': 'eclectic metal',
    'drone doom metal': 'doom metal',
    'drone ambient': 'ambient',
    'doombrass': 'doom',
    'dissonant death metalavant garde metal': 'avant garde metal',
    # 'dissonant blackened death metal': 'metal', # REMOVED (Too Broad)
    'dissonance death metal': 'dissonant death metal',
    'deva prog': 'prog',
    'deppresive black metal': 'depressive black metal',
    'deathened metalcore': 'metalcore',
    'deathcore galore': 'deathcore',
    'death sludge': 'sludge',
    'death grind': 'deathgrind',
    'darkfolk': 'dark folk',
    'dark progressive metal': 'progressive metal',
    'cosmic death metal': 'death metal',
    'comedy metal': 'comedy metal',
    'colours': 'colors',
    'colour': 'colors',
    # 'colors': 'colours', # REMOVED (Circular)
    'color': 'colors',
    # 'classical black metal': 'metal', # REMOVED (Too Broad)
    'chilean metal': 'chile',
    'chilean': 'chile',
    'chaotic metalcore': 'metalcore',
    'chamber post metal': 'chamber post metal',
    'chamber metal': 'chamber',
    'celtic punk': 'punk',
    'catholic black metal': 'black metal',
    'cascadian black metal': 'black metal',
    'canadian black metal': 'black metal',
    'california folk': 'folk',
    'british progressive jazz': 'progressive jazz',
    'british indie': 'indie',
    'british folk': 'folk',
    'breakup album': 'break up album',
    'breakbeat hardcore': 'breakbeat hardcore',
    'break up album': 'breakup album',
    'brazillian metal': 'brazil',
    'brazilian folk': 'brazil',
    'boston indie': 'boston',
    'blood metal': 'metal',
    'blackwave': 'black wave',
    'blackned death metal': 'blackened death metal',
    'blackened technical death metal': 'death metal',
    'blackened skramz': 'skramz',
    'blackened power metal': 'power metal',
    'blackened post metal': 'post metal',
    'blackened nu deathcore': 'blackened deathcore',
    'blackened chiptune': 'chiptune',
    'blackened brutal death metal': 'death metal',
    'black wave': 'blackwave',
    'black hardcore': 'blackened hardcore',
    'black doom metal': 'black doom metal',
    'black doom': 'black doom',
    'bhangra metal': 'bhangra',
    'bestalbums2021': 'best albums 2021',
    'best of2024': 'best of 2024',
    # 'best of 2001': 'best of 2021', # REMOVED (Wrong Date)
    'best albums of 2023': 'best albums 2023',
    'best albums of 2022': 'best albums 2022',
    # 'best albums 2019': 'best albums 2021', # REMOVED (Wrong Date)
    # 'best albums 2017': 'best albums 2021', # REMOVED (Wrong Date)
    'best album 2022': 'best albums 2022',
    'best 2025': '2025',
    'ballymena town centre september 2025': '2025',
    'balearic folk': 'folk',
    'babymetal': 'metal',
    'avant-jazz': 'avant jazz',
    'avant death metal': 'death metal',
    'australian thrash metal': 'thrash metal',
    'australian metal': 'australia',
    'atmospheric technical deathcore': 'deathcore',
    'atmospheric blackened death metal': 'death metal',
    'atmospheric black meta': 'atmospheric black metal',
    'athmospheric black metal': 'atmospheric black metal',
    'artcore': 'art core',
    'art puk': 'art punk',
    # 'art metal': 'party metal', # REMOVED (Gross Error)
    'armenian folk music': 'armenia',
    'armenian': 'armenia',
    'aoty2023list': '2023',
    'aoty 2020': 'aoty 2020',
    'aoty 2018': '2018',
    'animal album art': 'album art',
    'ambient sludge': 'sludge',
    'ambient music': 'ambient',
    'alternative indie rock': 'alternative indie rock',
    'alternative indie': 'alternative indie',
    'alternative folk': 'alternative folk',
    'alternative country': 'alternative country',
    'album 2019': '2019',
    'adventure rock': 'rock',
    'acoustic metal': 'acoustic metal',
    'acid techno': 'acid techno',
    '70s rock': 'rock',
    '2024 album of the year runner up': '2024',
    '2022 best albums': '2022',
    '2020 favourite albums': '2020',
    '2020 albums': '2020 albums',
    '2019 releases': 'release',
    # '2018 metal': 'metal', # REMOVED (Too Broad)
    '2018 albums': '2018 albums',
    # '2010s metal': 'metal', # REMOVED (Too Broad)
}

SUGGESTED_ATOMIC_DECOMPOSITIONS = {
    'eclectic metal': ['eclectic', 'metal'],
}

def apply_mappings():
    print("Loading TagRulesConfig...")
    config = TagRulesConfig()
    # Force load to ensure we have latest version
    config._load_config()

    if 'single_instance_mappings' not in config._config:
        config._config['single_instance_mappings'] = {}
    if 'atomic_decomposition' not in config._config:
        config._config['atomic_decomposition'] = {}

    current_mappings = config._config['single_instance_mappings']
    current_atomic = config._config['atomic_decomposition']
    count = 0
    updated = 0

    print("--- Applying Single Instance Mappings ---")
    for original, normalized in SUGGESTED_MAPPINGS.items():
        if original in current_mappings:
            if current_mappings[original] == normalized:
                # Already exists
                continue
            else:
                print(f"Updating {original}: {current_mappings[original]} -> {normalized}")
                current_mappings[original] = normalized
                updated += 1
        else:
            current_mappings[original] = normalized
            count += 1

    print("--- Applying Atomic Decompositions ---")
    for original, decomposed_list in SUGGESTED_ATOMIC_DECOMPOSITIONS.items():
        if original in current_atomic:
            # Check if same
            if current_atomic[original] == decomposed_list:
                continue
            else:
                print(f"Updating Atomic {original}: {current_atomic[original]} -> {decomposed_list}")
                current_atomic[original] = decomposed_list
                updated += 1
        else:
            print(f"Adding Atomic {original}: {decomposed_list}")
            current_atomic[original] = decomposed_list
            count += 1

    if count > 0 or updated > 0:
        config.save_changes()
        print(f"Success: Added {count} new mappings, updated {updated} existing mappings.")
    else:
        print("No changes needed (all mappings already exist).")

if __name__ == "__main__":
    apply_mappings()
