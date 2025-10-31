import csv
import json
from collections import defaultdict

RULES_PATH='src/albumexplore/config/tag_rules.json'
SINGLES_CSV='tagoutput/raw_tags_singles.csv'

with open(RULES_PATH, encoding='utf-8') as f:
    rules=json.load(f)
atomic=rules.get('atomic_decomposition',{})

rows=[]
with open(SINGLES_CSV, encoding='utf-8') as f:
    r=csv.DictReader(f)
    for row in r:
        tag=row['Tag'].strip()
        count=int(row['Count'])
        if len(tag.split())>1:
            rows.append((tag,count))

missing=[]
for tag,count in rows:
    if tag not in atomic:
        missing.append((tag,count))

# sort by count desc, words desc, lexicographic
missing.sort(key=lambda x:(-x[1], -len(x[0].split()), x[0]))
print(f"Found {len(missing)} multi-word single-instance tags missing from atomic_decomposition")
print('\nTop 50 missing:')
for i,(tag,c) in enumerate(missing[:50],1):
    print(f"{i:02d}. {tag!r} (count={c}, words={len(tag.split())})")

print('\n--LIST--')
for tag,c in missing[:25]:
    print(tag)
