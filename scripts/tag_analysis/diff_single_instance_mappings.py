import json
from pathlib import Path
b=Path('tag_rules_backup_apply_singletons_20251116_174858.json')
cur=Path('src/albumexplore/config/tag_rules.json')
if not b.exists():
    print('Backup not found:', b)
    raise SystemExit(1)
if not cur.exists():
    print('Current not found:', cur)
    raise SystemExit(1)
bb=json.loads(b.read_text(encoding='utf-8'))
cc=json.loads(cur.read_text(encoding='utf-8'))
bm=bb.get('single_instance_mappings',{})
cm=cc.get('single_instance_mappings',{})
added=[k for k in cm.keys() if k not in bm]
removed=[k for k in bm.keys() if k not in cm]
changed=[k for k in cm.keys() if k in bm and bm[k]!=cm[k]]
print('Added (keys present in current but not backup):')
for k in sorted(added): print('  ',k, '->', cm[k])
print('\nRemoved (keys present in backup but not current):')
for k in sorted(removed): print('  ',k, '->', bm[k])
print('\nChanged (value differs):')
for k in sorted(changed): print('  ',k, bm[k], '->', cm[k])
print('\nCounts: added=%d removed=%d changed=%d' % (len(added),len(removed),len(changed)))
