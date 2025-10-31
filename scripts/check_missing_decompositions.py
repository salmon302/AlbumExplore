import json
candidates = [
"england / us / germany",
"new wave and prog rock",
"pa / norway / greece",
"sweden / germany / us",
"us / uk / sweden",
"atmospheric drum and bass",
"czech republic / netherlands",
"dancefloor drum and bass",
"east coast hip hop",
"el mas de flors",
"epic vampyric black metal",
"old school death metal",
"philippines / south korea",
"acoustic doom metal",
"african folk music",
"afro latin funk",
"aix en provence",
"alternative rock/indie rock/emo",
"andorra la vella",
"appalachian folk music",
"arabic folk music",
"atmosheric black metal",
"atmospheric dark rock",
"australia / uk",
"balkan folk music",
"big band jazz"
]
with open('src/albumexplore/config/tag_rules.json', encoding='utf-8') as f:
    j=json.load(f)
atomic=j.get('atomic_decomposition',{})
present=[]
missing=[]
for c in candidates:
    if c in atomic:
        present.append(c)
    else:
        missing.append(c)
print('Present ({}):'.format(len(present)))
for p in present:
    print('  ',p)
print('\nMissing ({}):'.format(len(missing)))
for m in missing:
    print('  ',m)
