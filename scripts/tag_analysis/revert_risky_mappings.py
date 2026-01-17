import json,datetime
from pathlib import Path
backup = Path('tag_rules_backup_apply_singletons_20251116_174858.json')
cur = Path('src/albumexplore/config/tag_rules.json')
keys_to_revert = ['american privitsm','middle-eastern']
if not backup.exists():
    print('Backup not found:', backup)
    raise SystemExit(1)
if not cur.exists():
    print('Current not found:', cur)
    raise SystemExit(1)
bb = json.loads(backup.read_text(encoding='utf-8'))
cc = json.loads(cur.read_text(encoding='utf-8'))
bm = bb.get('single_instance_mappings',{})
cm = cc.get('single_instance_mappings',{})
# create a timestamped backup of current
ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
out_backup = Path(f'tag_rules_backup_before_revert_{ts}.json')
out_backup.write_text(json.dumps(cc,ensure_ascii=False,indent=2),encoding='utf-8')
changed = {}
for k in keys_to_revert:
    if k in bm:
        old = bm[k]
        curv = cm.get(k)
        if curv != old:
            cm[k] = old
            changed[k] = (curv, old)
# write back
cc['single_instance_mappings'] = cm
cur.write_text(json.dumps(cc,ensure_ascii=False,indent=2),encoding='utf-8')
print('Wrote backup of current to', out_backup)
if changed:
    print('Reverted these mappings:')
    for k,(before,after) in changed.items():
        print('  ',k, before, '->', after)
else:
    print('No changes were needed (current matches backup for keys).')
print('Done.')
