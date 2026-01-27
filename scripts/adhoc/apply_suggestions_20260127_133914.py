#!/usr/bin/env python3
"""
Batch Application of Tag Suggestions.
Generated on 2026-01-27T13:39:14.728392

AI AGENT INSTRUCTIONS:
1. Review the 'SUGGESTED_MAPPINGS' dictionary below.
2. Remove or comment out any mappings that seem incorrect.
3. Run this script to apply the changes to tag_rules.json.
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
    'woodland black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'vocal post rock': 'post rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: post rock
    'usway brutal death metal': 'brutal death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: brutal death metal
    'usa black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'unblack metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'ukrainian metal': 'ukrainian',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: ukrainian
    'uk garage': 'garage',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'trash metal': 'thrash metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: thrash metal
    'traditional metal': 'traditional metal',  # Score: N/A, Reason: atomic-decompose
    'thrashcore': 'thrash core',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'thrash death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'thezekinators 2024 album of the year selection': '2024',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2024
    'thezekinators 2024 album of the year runner up': '2024',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2024
    'the best symphonic metal tracks ever recorded': 'symphonic metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: symphonic metal
    'technical thrash': 'technical thrash',  # Score: N/A, Reason: atomic-decompose
    'technical progressive metal': 'technical progressive metal',  # Score: N/A, Reason: atomic-decompose
    'technical progressive deathcore': 'technical progressive deathcore',  # Score: N/A, Reason: atomic-decompose
    'technical progressive death metal': 'technical progressive death metal',  # Score: N/A, Reason: atomic-decompose
    'technical metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'technical death metal avant garde death metal': 'avant garde death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: avant garde death metal
    'synth metal': 'synth metal',  # Score: N/A, Reason: atomic-decompose
    'symphonic melodic death metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'symphonic gothic metal': 'symphonic gothic metal',  # Score: N/A, Reason: atomic-decompose
    'symphonic experimental metal': 'symphonic experimental metal',  # Score: N/A, Reason: atomic-decompose
    'swedish death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'speed rock': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'sludge stoner': 'sludge stoner',  # Score: N/A, Reason: atomic-decompose
    'sludge doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'sludge djent': 'djent',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: djent
    'slamming guttural brutal test metal': 'brutal test metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: brutal test metal
    'skate punk': 'skatepunk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: punk
    'serbian pop alchemy': 'serbia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: serbia
    'serbian': 'serbia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: serbia
    'seattle metal': 'seattle',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: seattle
    'scifi doom': 'doom',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom
    'sci fi metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'saxodoom': 'doom',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom
    'sassy mathcore': 'mathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: mathcore
    'romanian folk music': 'folk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk
    'rock n roll': 'rock n\' roll',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'rock musical': 'rock musical',  # Score: N/A, Reason: atomic-decompose
    'rock modern': 'rock modern',  # Score: N/A, Reason: atomic-decompose
    'rock metal': 'rock metal',  # Score: N/A, Reason: atomic-decompose
    'rock francophone': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'roadburn festival': 'roadburn',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: roadburn
    'releases': 'release',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: release
    'release': 'releases',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: releases
    'regressive metalcore': 'progressive metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'punk black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'psytrance': 'psy trance',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'psychodelic': 'psychedelic',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'psychedelic rock neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock space rock stoner thessaloniki': 'psychedelic rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: psychedelic rock
    'psychedelic progressive metal': 'psychedelic',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: psychedelic
    'psychedelic noise': 'psychedelic',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: psychedelic
    'psychedelic drone rock': 'drone',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: drone
    'progrock': 'prog-rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'progressive technical death metal': 'technical death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: technical death metal
    'progressive stoner': 'progressive stoner',  # Score: N/A, Reason: atomic-decompose
    'progressive space rock': 'space rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: space rock
    'progressive rock prog rock prog melodic progrock djent': 'melodic',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: melodic
    'progressive post metal rock': 'progressive post metal rock',  # Score: N/A, Reason: atomic-decompose
    'progressive noise rock': 'progressive noise rock',  # Score: N/A, Reason: atomic-decompose
    'progressive melodic punk a ha black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'progressive mathcore': 'progressive deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: mathcore
    'progressive heavy metal': 'progressive heavy metal',  # Score: N/A, Reason: atomic-decompose
    'progressive groove metal': 'groove metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: groove metal
    'progressive doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'progressive death thrash metal': 'thrash metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: thrash metal
    'progressive brutal death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'progressive black doom metal': 'progressive black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'progressive alternative metal': 'progressive alternative metal',  # Score: N/A, Reason: atomic-decompose
    'progress rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive rock
    'progerssive rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'pro rock': 'prog rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: prog rock
    'powermetal': 'power metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: power metal
    'post screamo': 'post screamo',  # Score: N/A, Reason: atomic-decompose
    'post progressive rock': 'post progressive rock',  # Score: N/A, Reason: atomic-decompose
    'post powerviolence': 'powerviolence',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: powerviolence
    'post metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'post grindcore': 'grindcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: grindcore
    'post deathcore': 'deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'polish black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'peogressive rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive rock
    'orchestral metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'operatic black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'on vinyl': 'on vinyl',  # Score: N/A, Reason: atomic-decompose
    'olivia': 'bolivia',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'old school progressive metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'old school grindcore': 'grindcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: grindcore
    'old school grind': 'grind',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: grind
    'ocult rock': 'occult rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: occult rock
    'nujazz': 'nu jazz',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: jazz
    'not djent': 'djent',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: djent
    'norwegian death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'northern silence': 'silence',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'northern nspordy recs': 'nspordy recs',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'noise sludge metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'noise metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'noise metal': 'noise metal',  # Score: N/A, Reason: atomic-decompose
    'new wave of british heavy metal': 'new wave of heavy metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'new metal': 'new metal',  # Score: N/A, Reason: atomic-decompose
    'new berklee core prog metal': 'new berklee core progressive metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: new berklee core progressive metal
    'neoclassicall new age': 'neoclassical new age',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: new age
    'neoclassicall melodic death metal': 'neoclassical melodic death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: melodic death metal
    'neo-classical': 'neo classical',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock psychedelic rock space rock stoner thessaloniki': 'psychedelic rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: psychedelic rock
    'neo classical metal': 'neo classical metal',  # Score: N/A, Reason: atomic-decompose
    'mostly instrumental progressive rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive rock
    'mostly instrumental prog rock': 'prog rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: prog rock
    'mostly instrumental prog metal': 'prog metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: prog metal
    'modern shoegaze': 'shoegaze',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: shoegaze
    'modern melodic death metal': 'modern melodic death metal',  # Score: N/A, Reason: atomic-decompose
    'modern hardcore': 'hardcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: hardcore
    'modern fusion': 'fusion',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: fusion
    'modern folk metal': 'folk metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk metal
    'modern emo': 'modern emo',  # Score: N/A, Reason: atomic-decompose
    'modern death metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'modern alternative rock': 'modern alternative rock',  # Score: N/A, Reason: atomic-decompose
    'midwestern emo': 'midwest emo',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: midwest emo
    'microtonal black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'metal progressive metal': 'progressive metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive metal
    'melodic thrash metal': 'thrash metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: thrash metal
    'melodic thrash': 'melodic',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: melodic
    'melodic post hardcore': 'post hardcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: post hardcore
    'melodic goregrind': 'goregrind',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: goregrind
    'melodic death power metal': 'power metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: power metal
    'melodic death doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'melancholic black metal': 'melancholic black metal',  # Score: N/A, Reason: atomic-decompose
    'lol doomergaze': 'doomergaze',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doomergaze
    'live album': 'live',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: live
    'kraut rock': 'krautrock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'jazz piano': 'jazz piano',  # Score: N/A, Reason: atomic-decompose
    'japanese psych rock': 'psych rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: japan
    'italian progressive rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive rock
    'israeli': 'israel',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: israel
    'instrumental progressive death metal': 'instrumental progressive metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: instrumental
    'instrumental neo classical progressive death metal': 'instrumental',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: instrumental
    'instrumental ambient': 'ambient',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: ambient
    'inide rock': 'indie rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'industrial sludge metal': 'sludge metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: sludge metal
    'industrial dance': 'industrial dance',  # Score: N/A, Reason: atomic-decompose
    'indonesian black metal': 'indonesia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: indonesia
    'indigenous north american music': 'indigenous north music',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'indie folk rock': 'folk rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk rock
    'indie emo': 'indie emo',  # Score: N/A, Reason: atomic-decompose
    'in love': 'love',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: love
    'icelandic': 'iceland',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: iceland
    'hypnogogic pop': 'hypnagogic pop',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: hypnagogic pop
    'high speed metal': 'speed metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: speed metal
    'heavy thrash metal': 'thrash metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: thrash metal
    'heavy progressive': 'heavy progressive',  # Score: N/A, Reason: atomic-decompose
    'heavy power metal': 'power metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: power metal
    'heavy jazz': 'heavy jazz',  # Score: N/A, Reason: atomic-decompose
    'heavy death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'hard rock francophone': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'groove deathcore': 'deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'grass album art': 'album art',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: album art
    'gothic funeral doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'gothic doom': 'gothic doom',  # Score: N/A, Reason: atomic-decompose
    'german new wave': 'new wave',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: new wave
    'german metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'garbage': 'garage',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'folk power metal': 'power metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: power metal
    'folk noir': 'folk noir',  # Score: N/A, Reason: atomic-decompose
    'folk indie': 'folk indie',  # Score: N/A, Reason: atomic-decompose
    'folk doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'folk doom': 'folk doom',  # Score: N/A, Reason: atomic-decompose
    'folk death metal': 'folk death metal',  # Score: N/A, Reason: atomic-decompose
    'flop era': 'flop',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: flop
    'finnish melodic death metal': 'melodic death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: melodic death metal
    'female vocal': 'female vocalists',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: female vocalists
    'female singer songwriter': 'singer songwriter',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: singer songwriter
    'female fronted rock': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'extreme piano metal': 'extreme piano',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: extreme piano
    'experimental guitar': 'experimental',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: experimental
    'experimental grindcore': 'grindcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: grindcore
    'experimental deathcore': 'deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'estonian': 'estonia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: estonia
    'epic folk metal': 'folk metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk metal
    'english black metal': 'english',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: english
    'emo violence': 'emoviolence',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: emoviolence
    'electronic jazz': 'electronic jazz',  # Score: N/A, Reason: atomic-decompose
    'electro swing': 'electro swing',  # Score: N/A, Reason: atomic-decompose
    'electro rock': 'electro rock',  # Score: N/A, Reason: atomic-decompose
    'electro metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'elctronic': 'electronic',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'egyptian': 'egypt',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: egypt
    'ecletic metal': 'eclectic metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: eclectic metal
    'drone doom metal': 'doom metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom metal
    'drone ambient': 'ambient',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: ambient
    'doombrass': 'doom',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doom
    'dissonant death metalavant garde metal': 'avant garde metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: avant garde metal
    'dissonant blackened death metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'dissonance death metal': 'dissonant death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: dissonant death metal
    'deva prog': 'prog',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: prog
    'deppresive black metal': 'depressive black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'deathened metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'deathcore galore': 'deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'death sludge': 'sludge',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: sludge
    'death grind': 'deathgrind',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathgrind
    'darkfolk': 'dark folk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: dark folk
    'dark progressive metal': 'progressive metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive metal
    'cosmic death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'comedy metal': 'comedy metal',  # Score: N/A, Reason: atomic-decompose
    'colours': 'colors',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: colors
    'colour': 'colors',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: colours
    'colors': 'colours',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: colours
    'color': 'colors',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: colors
    'classical black metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'chilean metal': 'chile',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: chile
    'chilean': 'chile',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: chile
    'chaotic metalcore': 'metalcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metalcore
    'chamber post metal': 'chamber post metal',  # Score: N/A, Reason: atomic-decompose
    'chamber metal': 'chamber',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: chamber
    'celtic punk': 'punk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: celtic
    'catholic black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'cascadian black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'canadian black metal': 'black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'california folk': 'folk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk
    'british progressive jazz': 'progressive jazz',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'british indie': 'indie',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'british folk': 'folk',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'breakup album': 'break up album',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: break up album
    'breakbeat hardcore': 'breakbeat hardcore',  # Score: N/A, Reason: atomic-decompose
    'break up album': 'breakup album',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: breakup album
    'brazillian metal': 'brazil',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: brazil
    'brazilian folk': 'brazil',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: brazil
    'boston indie': 'boston',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: boston
    'blood metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'blackwave': 'black wave',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black wave
    'blackned death metal': 'blackened death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'blackened technical death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'blackened skramz': 'skramz',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: skramz
    'blackened power metal': 'power metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: power metal
    'blackened post metal': 'post metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: post metal
    'blackened nu deathcore': 'blackened deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'blackened chiptune': 'chiptune',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: chiptune
    'blackened brutal death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'black wave': 'blackwave',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: blackwave
    'black hardcore': 'blackened hardcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: blackened hardcore
    'black doom metal': 'black doom metal',  # Score: N/A, Reason: atomic-decompose
    'black doom': 'black doom',  # Score: N/A, Reason: atomic-decompose
    'bhangra metal': 'bhangra',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: bhangra
    'bestalbums2021': 'best albums 2021',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2021
    'best of2024': 'best of 2024',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2024
    'best of 2001': 'best of 2021',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2001
    'best albums of 2023': 'best albums 2023',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'best albums of 2022': 'best albums 2022',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'best albums 2019': 'best albums 2021',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2019
    'best albums 2017': 'best albums 2021',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2017
    'best album 2022': 'best albums 2022',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: best albums 2022
    'best 2025': '2025',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2025
    'ballymena town centre september 2025': '2025',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2025
    'balearic folk': 'folk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk
    'babymetal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    'avant-jazz': 'avant jazz',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: jazz
    'avant death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'australian thrash metal': 'thrash metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: thrash metal
    'australian metal': 'australia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: australia
    'atmospheric technical deathcore': 'deathcore',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: deathcore
    'atmospheric blackened death metal': 'death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: death metal
    'atmospheric black meta': 'atmospheric black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: atmospheric black metal
    'athmospheric black metal': 'atmospheric black metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: black metal
    'artcore': 'art core',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'art puk': 'art punk',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'art metal': 'party metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'armenian folk music': 'armenia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: armenia
    'armenian': 'armenia',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'aoty2023list': '2023',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2023
    'aoty 2020': 'aoty 2020',  # Score: N/A, Reason: atomic-decompose
    'aoty 2018': '2018',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2018
    'animal album art': 'album art',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: album art
    'ambient sludge': 'sludge',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: sludge
    'ambient music': 'ambient',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: ambient
    'alternative indie rock': 'alternative indie rock',  # Score: N/A, Reason: atomic-decompose
    'alternative indie': 'alternative indie',  # Score: N/A, Reason: atomic-decompose
    'alternative folk': 'alternative folk',  # Score: N/A, Reason: atomic-decompose
    'alternative country': 'alternative country',  # Score: N/A, Reason: atomic-decompose
    'album 2019': '2019',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2019
    'adventure rock': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    'acoustic metal': 'acoustic metal',  # Score: N/A, Reason: atomic-decompose
    'acid techno': 'acid techno',  # Score: N/A, Reason: atomic-decompose
    '70s rock': 'rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: rock
    '2024 album of the year runner up': '2024',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2024
    '2022 best albums': '2022',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2022
    '2020 favourite albums': '2020',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2020
    '2020 albums': '2020 albums',  # Score: N/A, Reason: atomic-decompose; ALSO co-occurrence: 2020
    '2019 releases': 'release',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: 2019
    '2018 metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
    '2018 albums': '2018 albums',  # Score: N/A, Reason: atomic-decompose
    '2010s metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: metal
}

SUGGESTED_ATOMIC_DECOMPOSITIONS = {
    'eclectic metal': ['eclectic', 'metal'],  # Score: N/A, Reason: atomic-candidate; ALSO co-occurrence: ecletic metal
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
