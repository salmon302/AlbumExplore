import csv
from collections import Counter
import sys
p='tagoutput/raw_tags_singles.csv'
rows=[]
try:
    with open(p, encoding='utf-8') as f:
        r=csv.DictReader(f)
        for row in r:
            tag=row['Tag'].strip()
            count=int(row['Count'])
            # only multi-word tags
            if len(tag.split())>1:
                rows.append((tag,count))
except FileNotFoundError:
    print('File not found:',p)
    sys.exit(2)
# Rank by count desc then word count desc then lexicographic
rows.sort(key=lambda x:(-x[1], -len(x[0].split()), x[0]))
for i,(tag,c) in enumerate(rows[:50],1):
    print(f"{i:02d}. {tag!r} (count={c}, words={len(tag.split())})")

# Also output a plain list for copy/paste
print('\n--LIST--')
for tag,c in rows[:25]:
    print(tag)
