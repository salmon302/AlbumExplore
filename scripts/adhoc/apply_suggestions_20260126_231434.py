#!/usr/bin/env python3
"""
Batch Application of Tag Suggestions.
Generated on 2026-01-26T23:14:34.110393

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
    'gothic funeral doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'progressive rock prog rock prog melodic progrock djent': 'melodic',  # Score: 0.95, Reason: contains-sibling:djent
    'speed rock': 'rock',  # Score: 0.95, Reason: contains-sibling:rock
    'psychedelic rock neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock space rock stoner thessaloniki': 'psychedelic rock',  # Score: 0.95, Reason: contains-sibling:thessaloniki
    'not djent': 'djent',  # Score: 0.95, Reason: contains-sibling:djent
    'experimental deathcore': 'deathcore',  # Score: 0.95, Reason: contains-sibling:deathcore
    'rock francophone': 'rock',  # Score: 0.95, Reason: contains-sibling:rock
    'animal album art': 'album art',  # Score: 0.95, Reason: contains-sibling:album art
    'dissonant death metalavant garde metal': 'avant garde metal',  # Score: 0.95, Reason: contains-sibling:dissonant death metal
    'blackened power metal': 'power metal',  # Score: 0.95, Reason: contains-sibling:power metal
    'drone doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'old school grind': 'grind',  # Score: 0.95, Reason: contains-sibling:grind
    'folk power metal': 'power metal',  # Score: 0.95, Reason: contains-sibling:power metal
    'polish black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'high speed metal': 'speed metal',  # Score: 0.95, Reason: contains-sibling:speed metal
    'noise sludge metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:sludge metal
    'thezekinators 2024 album of the year selection': '2024',  # Score: 0.95, Reason: contains-sibling:2024
    'dark progressive metal': 'progressive metal',  # Score: 0.95, Reason: contains-sibling:progressive metal
    'post metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'instrumental neo classical progressive death metal': 'instrumental',  # Score: 0.95, Reason: contains-sibling:instrumental
    'experimental guitar': 'experimental',  # Score: 0.95, Reason: contains-sibling:experimental
    'hard rock francophone': 'rock',  # Score: 0.95, Reason: contains-sibling:hard rock
    'heavy death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'brazillian metal': 'brazil',  # Score: 0.95, Reason: contains-sibling:brazil
    'blackened skramz': 'skramz',  # Score: 0.95, Reason: contains-sibling:skramz
    'seattle metal': 'seattle',  # Score: 0.95, Reason: contains-sibling:seattle
    'live album': 'live',  # Score: 0.95, Reason: contains-sibling:live
    'egyptian': 'egypt',  # Score: 0.95, Reason: contains-sibling:egypt
    'flop era': 'flop',  # Score: 0.95, Reason: contains-sibling:flop
    '2018 metal': 'metal',  # Score: 0.95, Reason: contains-sibling:2018
    'progressive groove metal': 'groove metal',  # Score: 0.95, Reason: contains-sibling:groove metal
    'psychedelic drone rock': 'drone',  # Score: 0.95, Reason: contains-sibling:drone
    'cascadian black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    '70s rock': 'rock',  # Score: 0.95, Reason: contains-sibling:rock
    'thrash death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'experimental grindcore': 'grindcore',  # Score: 0.95, Reason: contains-sibling:grindcore
    'babymetal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'heavy power metal': 'power metal',  # Score: 0.95, Reason: contains-sibling:power metal
    'english black metal': 'english',  # Score: 0.95, Reason: contains-sibling:black metal
    'boston indie': 'boston',  # Score: 0.95, Reason: contains-sibling:boston
    'doombrass': 'doom',  # Score: 0.95, Reason: contains-sibling:doom
    'psychedelic progressive metal': 'psychedelic',  # Score: 0.95, Reason: contains-sibling:psychedelic
    'atmospheric blackened death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'melodic thrash': 'melodic',  # Score: 0.95, Reason: contains-sibling:melodic
    'post powerviolence': 'powerviolence',  # Score: 0.95, Reason: contains-sibling:powerviolence
    'ukrainian metal': 'ukrainian',  # Score: 0.95, Reason: contains-sibling:ukrainian
    'mostly instrumental progressive rock': 'progressive rock',  # Score: 0.95, Reason: contains-sibling:prog
    'old school grindcore': 'grindcore',  # Score: 0.95, Reason: contains-sibling:grindcore
    'adventure rock': 'rock',  # Score: 0.95, Reason: contains-sibling:rock
    'sassy mathcore': 'mathcore',  # Score: 0.95, Reason: contains-sibling:mathcore
    '2020 favourite albums': '2020',  # Score: 0.95, Reason: contains-sibling:2020
    'ballymena town centre september 2025': '2025',  # Score: 0.95, Reason: contains-sibling:2025
    'female fronted rock': 'rock',  # Score: 0.95, Reason: contains-sibling:rock
    'dissonant blackened death metal': 'metal',  # Score: 0.95, Reason: contains-sibling:blackened death metal
    'avant death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'aoty2023list': '2023',  # Score: 0.95, Reason: contains-sibling:2023
    'sludge djent': 'djent',  # Score: 0.95, Reason: contains-sibling:djent
    'punk black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'canadian black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'balearic folk': 'folk',  # Score: 0.95, Reason: contains-sibling:balearic
    'catholic black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'modern death metal': 'metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'usa black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'swedish death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'chilean': 'chile',  # Score: 0.95, Reason: contains-sibling:chile
    'indonesian black metal': 'indonesia',  # Score: 0.95, Reason: contains-sibling:indonesia
    '2022 best albums': '2022',  # Score: 0.95, Reason: contains-sibling:2022
    'post grindcore': 'grindcore',  # Score: 0.95, Reason: contains-sibling:grindcore
    'melodic post hardcore': 'post hardcore',  # Score: 0.95, Reason: contains-sibling:post hardcore
    'drone ambient': 'ambient',  # Score: 0.95, Reason: contains-sibling:ambient
    'folk doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'female singer songwriter': 'singer songwriter',  # Score: 0.95, Reason: contains-sibling:singer songwriter
    'microtonal black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'extreme piano metal': 'extreme piano',  # Score: 0.95, Reason: contains-sibling:extreme piano
    'blackened brutal death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    '2024 album of the year runner up': '2024',  # Score: 0.95, Reason: contains-sibling:2024
    'icelandic': 'iceland',  # Score: 0.95, Reason: contains-sibling:iceland
    'modern shoegaze': 'shoegaze',  # Score: 0.95, Reason: contains-sibling:shoegaze
    'technical metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'modern folk metal': 'folk metal',  # Score: 0.95, Reason: contains-sibling:folk metal
    'australian metal': 'australia',  # Score: 0.95, Reason: contains-sibling:australia
    'heavy thrash metal': 'thrash metal',  # Score: 0.95, Reason: contains-sibling:thrash metal
    'groove deathcore': 'deathcore',  # Score: 0.95, Reason: contains-sibling:deathcore
    'aoty 2018': '2018',  # Score: 0.95, Reason: contains-sibling:2018
    'blackened post metal': 'post metal',  # Score: 0.95, Reason: contains-sibling:post metal
    'post deathcore': 'deathcore',  # Score: 0.95, Reason: contains-sibling:deathcore
    'deathcore galore': 'deathcore',  # Score: 0.95, Reason: contains-sibling:deathcore
    'progressive doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'modern fusion': 'fusion',  # Score: 0.95, Reason: contains-sibling:fusion
    'california folk': 'folk',  # Score: 0.95, Reason: contains-sibling:folk
    'australian thrash metal': 'thrash metal',  # Score: 0.95, Reason: contains-sibling:australia
    '2010s metal': 'metal',  # Score: 0.95, Reason: contains-sibling:2010s
    'progressive melodic punk a ha black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'technical death metal avant garde death metal': 'avant garde death metal',  # Score: 0.95, Reason: contains-sibling:avant garde death metal
    'romanian folk music': 'folk',  # Score: 0.95, Reason: contains-sibling:romania
    'death sludge': 'sludge',  # Score: 0.95, Reason: contains-sibling:sludge
    'metal progressive metal': 'progressive metal',  # Score: 0.95, Reason: contains-sibling:metal
    'melodic goregrind': 'goregrind',  # Score: 0.95, Reason: contains-sibling:goregrind
    'woodland black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'usway brutal death metal': 'brutal death metal',  # Score: 0.95, Reason: contains-sibling:brutal death metal
    'classical black metal': 'metal',  # Score: 0.95, Reason: contains-sibling:black metal
    'the best symphonic metal tracks ever recorded': 'symphonic metal',  # Score: 0.95, Reason: contains-sibling:symphonic metal
    'norwegian death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'mostly instrumental prog rock': 'prog rock',  # Score: 0.95, Reason: contains-sibling:prog rock
    'atmospheric technical deathcore': 'deathcore',  # Score: 0.95, Reason: contains-sibling:deathcore
    'operatic black metal': 'black metal',  # Score: 0.95, Reason: contains-sibling:opera
    'modern hardcore': 'hardcore',  # Score: 0.95, Reason: contains-sibling:hardcore
    'blackened technical death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'progressive brutal death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'electro metal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'chamber metal': 'chamber',  # Score: 0.95, Reason: contains-sibling:chamber
    'old school progressive metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'slamming guttural brutal test metal': 'brutal test metal',  # Score: 0.95, Reason: contains-sibling:brutal test metal
    'sci fi metal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'progressive technical death metal': 'technical death metal',  # Score: 0.95, Reason: contains-sibling:technical death metal
    'noise metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'orchestral metal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'brazilian folk': 'brazil',  # Score: 0.95, Reason: contains-sibling:brazil
    'chaotic metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'saxodoom': 'doom',  # Score: 0.95, Reason: contains-sibling:doom
    'grass album art': 'album art',  # Score: 0.95, Reason: contains-sibling:grass
    'progressive space rock': 'space rock',  # Score: 0.95, Reason: contains-sibling:space rock
    'album 2019': '2019',  # Score: 0.95, Reason: contains-sibling:2019
    'mostly instrumental prog metal': 'prog metal',  # Score: 0.95, Reason: contains-sibling:prog metal
    'deva prog': 'prog',  # Score: 0.95, Reason: contains-sibling:prog
    'industrial sludge metal': 'sludge metal',  # Score: 0.95, Reason: contains-sibling:sludge metal
    'thezekinators 2024 album of the year runner up': '2024',  # Score: 0.95, Reason: contains-sibling:2024 album of the year runner up
    'melodic death doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'melodic thrash metal': 'thrash metal',  # Score: 0.95, Reason: contains-sibling:thrash metal
    'cosmic death metal': 'death metal',  # Score: 0.95, Reason: contains-sibling:death metal
    'indie folk rock': 'folk rock',  # Score: 0.95, Reason: contains-sibling:folk rock
    'psychedelic noise': 'psychedelic',  # Score: 0.95, Reason: contains-sibling:psychedelic
    'neo prog progressive rock rock heavy psych heavy psych rock neo progressive rock prog rock psych rock psychedelic rock space rock stoner thessaloniki': 'psychedelic rock',  # Score: 0.95, Reason: contains-sibling:thessaloniki
    'ambient sludge': 'sludge',  # Score: 0.95, Reason: contains-sibling:sludge
    'melodic death power metal': 'power metal',  # Score: 0.95, Reason: contains-sibling:power metal
    'in love': 'love',  # Score: 0.95, Reason: contains-sibling:love
    'deathened metalcore': 'metalcore',  # Score: 0.95, Reason: contains-sibling:metalcore
    'instrumental ambient': 'ambient',  # Score: 0.95, Reason: contains-sibling:instrumental
    'serbian pop alchemy': 'serbia',  # Score: 0.95, Reason: contains-sibling:serbia
    'blood metal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'chilean metal': 'chile',  # Score: 0.95, Reason: contains-sibling:chile
    'ambient music': 'ambient',  # Score: 0.95, Reason: contains-sibling:ambient
    'blackened chiptune': 'chiptune',  # Score: 0.95, Reason: contains-sibling:chiptune
    'best 2025': '2025',  # Score: 0.95, Reason: contains-sibling:2025
    'symphonic melodic death metal': 'metal',  # Score: 0.95, Reason: contains-sibling:metal
    'scifi doom': 'doom',  # Score: 0.95, Reason: contains-sibling:doom
    'progressive death thrash metal': 'thrash metal',  # Score: 0.95, Reason: contains-sibling:thrash metal
    'finnish melodic death metal': 'melodic death metal',  # Score: 0.95, Reason: contains-sibling:melodic death metal
    'sludge doom metal': 'doom metal',  # Score: 0.95, Reason: contains-sibling:doom metal
    'black wave': 'blackwave',  # Score: 0.9473684210526315, Reason: fuzzy-cooccurrence:0.67
    # 'blackwave': 'black wave',  # Score: 0.9473684210526315, Reason: fuzzy-cooccurrence:0.60
    # 'release': 'releases',  # Score: 0.9333333333333333, Reason: fuzzy-cooccurrence:0.12
    'releases': 'release',  # Score: 0.9333333333333333, Reason: contains-sibling:release
    'colours': 'colors',  # Score: 0.9230769230769231, Reason: contains-sibling:colour
    # 'colour': 'colours',  # Score: 0.9230769230769231, Reason: fuzzy-cooccurrence:0.25
    # 'colors': 'colours',  # Score: 0.9230769230769231, Reason: contains-sibling:color
    'color': 'colors',  # Score: 0.9090909090909091, Reason: fuzzy-cooccurrence:0.27
    'progress rock': 'progressive rock',  # Score: 0.896551724137931, Reason: fuzzy-cooccurrence:0.82
    'new berklee core prog metal': 'new berklee core progressive metal',  # Score: 0.8852459016393442, Reason: fuzzy-cooccurrence:0.48
    'midwestern emo': 'midwest emo',  # Score: 0.88, Reason: fuzzy-cooccurrence:0.88
    'black hardcore': 'blackened hardcore',  # Score: 0.875, Reason: fuzzy-cooccurrence:0.56
    'female vocal': 'female vocalists',  # Score: 0.8571428571428571, Reason: fuzzy-cooccurrence:0.50
    'vocal post rock': 'post rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: post rock
    'unblack metal': 'black metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: black metal
    'uk garage': 'garage',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'trash metal': 'thrash metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: thrash metal
    'thrashcore': 'thrash core',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'skate punk': 'skatepunk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: punk
    'serbian': 'serbia',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: serbia
    'rock n roll': 'rock n\' roll',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: rock
    'roadburn festival': 'roadburn',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: roadburn
    'regressive metalcore': 'progressive metalcore',  # Score: N/A, Reason: fuzzy-match
    'psytrance': 'psy trance',  # Score: N/A, Reason: fuzzy-match
    'psychodelic': 'psychedelic',  # Score: N/A, Reason: fuzzy-match
    'progrock': 'prog-rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: rock
    'progressive mathcore': 'progressive deathcore',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: mathcore
    'progressive black doom metal': 'progressive black metal',  # Score: N/A, Reason: fuzzy-match
    'progerssive rock': 'progressive rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: rock
    'pro rock': 'prog rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: prog rock
    'powermetal': 'power metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: power metal
    'peogressive rock': 'progressive rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: progressive rock
    'olivia': 'bolivia',  # Score: N/A, Reason: fuzzy-match
    'ocult rock': 'occult rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: occult rock
    'nujazz': 'nu jazz',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: jazz
    'northern silence': 'silence',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'northern nspordy recs': 'nspordy recs',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'new wave of british heavy metal': 'new wave of heavy metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'neoclassicall new age': 'neoclassicalll new age',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: new age
    'neoclassicall melodic death metal': 'neoclassicalll melodic death metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: melodic death metal
    'neo-classical': 'neo classical',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'lol doomergaze': 'doomergaze',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: doomergaze
    'kraut rock': 'krautrock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: rock
    'japanese psych rock': 'psych rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: japan
    'italian progressive rock': 'progressive rock',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: progressive rock
    'israeli': 'israel',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: israel
    'instrumental progressive death metal': 'instrumental progressive metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: instrumental
    'inide rock': 'indie rock',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: rock
    'indigenous north american music': 'indigenous north music',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'hypnogogic pop': 'hypnagogic pop',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: hypnagogic pop
    'hard prog': 'hard prog',  # Score: N/A, Reason: atomic-decompose; ALSO co-occurrence: prog
    'german new wave': 'new wave',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: new wave
    'german metal': 'metal',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'garbage': 'garage',  # Score: N/A, Reason: fuzzy-match
    'estonian': 'estonia',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: estonia
    'epic folk metal': 'folk metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: folk metal
    'emo violence': 'emoviolence',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: emoviolence
    'elctronic': 'electronic',  # Score: N/A, Reason: fuzzy-match
    'ecletic metal': 'eclectic metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: eclectic metal
    # 'eclectic metal': 'ecletic metal',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: ecletic metal
    'dissonance death metal': 'dissonant death metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: dissonant death metal
    'deppresive black metal': 'depressive black metal',  # Score: N/A, Reason: fuzzy-match
    'death grind': 'deathgrind',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: deathgrind
    'darkfolk': 'dark folk',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: dark folk
    'celtic punk': 'punk',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: celtic
    'british progressive jazz': 'progressive jazz',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'british indie': 'indie',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'british folk': 'folk',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'breakup album': 'break up album',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: break up album
    'break up album': 'breakup album',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: breakup album
    'blackned death metal': 'blackened death metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: death metal
    'blackened nu deathcore': 'blackened deathcore',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: deathcore
    'bhangra metal': 'bhangra',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: bhangra
    'bestalbums2021': 'best albums 2021',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2021
    'best of2024': 'best of 2024',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2024
    # 'best of 2001': 'best of 2021',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2001 (Year swap error)
    'best albums of 2023': 'best albums 2023',  # Score: N/A, Reason: fuzzy-match
    'best albums of 2022': 'best albums 2022',  # Score: N/A, Reason: fuzzy-match
    # 'best albums 2019': 'best albums 2021',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2019 (Year swap error)
    # 'best albums 2017': 'best albums 2021',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2017 (Year swap error)
    'best album 2022': 'best albums 2022',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: best albums 2022
    'avant-jazz': 'avant jazz',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: jazz
    'atmospheric black meta': 'atmospheric black metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: atmospheric black metal
    'athmospheric black metal': 'atmospheric black metal',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: black metal
    'artcore': 'art core',  # Score: N/A, Reason: rules-mapped-after-enhanced
    'art puk': 'art punk',  # Score: N/A, Reason: fuzzy-match
    # 'art metal': 'party metal',  # Score: N/A, Reason: fuzzy-match (Unlikely match)
    'armenian folk music': 'armenia',  # Score: N/A, Reason: rules-mapped-after-enhanced; ALSO co-occurrence: armenia
    'armenian': 'armenia',  # Score: N/A, Reason: fuzzy-match
    # '2020 albums': '2023 albums',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2020 (Year swap error)
    # '2019 releases': '2018 releases',  # Score: N/A, Reason: fuzzy-match; ALSO co-occurrence: 2019 (Year swap error)
    # '2018 albums': '2019 albums',  # Score: N/A, Reason: fuzzy-match (Year swap error)
}

def apply_mappings():
    print("Loading TagRulesConfig...")
    config = TagRulesConfig()
    # Force load to ensure we have latest version
    config._load_config()

    if 'single_instance_mappings' not in config._config:
        config._config['single_instance_mappings'] = {}

    current_mappings = config._config['single_instance_mappings']
    count = 0
    updated = 0

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

    if count > 0 or updated > 0:
        config.save_changes()
        print(f"Success: Added {count} new mappings, updated {updated} existing mappings.")
    else:
        print("No changes needed (all mappings already exist).")

if __name__ == "__main__":
    apply_mappings()
