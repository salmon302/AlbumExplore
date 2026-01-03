import importlib.util
from pathlib import Path

files = [
    Path('src') / 'albumexplore' / 'gui' / 'widgets' / 'tokenized_query_input.py',
    Path('src') / 'albumexplore' / 'gui' / 'widgets' / 'query_editor.py',
    Path('src') / 'albumexplore' / 'gui' / 'widgets' / 'tag_filter_panel.py',
]

for p in files:
    try:
        spec = importlib.util.spec_from_file_location(p.stem, str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print('Imported', p)
    except Exception as e:
        print('FAILED', p, e)
