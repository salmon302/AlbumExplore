"""Simple runner to validate query module without pytest dependencies.

Run with: python tools/run_query_demo.py
"""
import importlib.util
from pathlib import Path


def load_query_module() -> object:
    root = Path(__file__).parent.parent
    module_path = root / "src" / "albumexplore" / "search" / "query.py"
    spec = importlib.util.spec_from_file_location("qe_module", str(module_path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_query_module()
    evaluate_query = mod.evaluate_query
    explain_query = mod.explain_query

    sample_index = {
        "TagA": {1, 2, 3, 4},
        "TagB": {2, 3},
        "TagC": {3, 5},
        "TagD": {1},
    }
    all_ids = {1, 2, 3, 4, 5}

    q = 'TagA AND (TagB OR TagC)'
    res = evaluate_query(q, sample_index, all_ids)
    print(f"Query: {q}\nResult IDs: {sorted(res)}")

    q2 = 'TagA AND NOT TagD'
    res2 = evaluate_query(q2, sample_index, all_ids)
    print(f"Query: {q2}\nResult IDs: {sorted(res2)}")

    print('\nExplain:')
    print(explain_query('TagA AND (TagB OR TagC)', sample_index, all_ids))


if __name__ == '__main__':
    main()
