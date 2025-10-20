"""
Simple TagFilter implemented in Python using BitSet for demo/prototyping.

API:
  - TagFilter(tag_map: Dict[str, BitSet])
  - evaluate(expr) -> BitSet  (expr is a small AST built as tuples/dicts)
  - matching_counts_for_visible(expr, visible_tags) -> list of {tag, count}
  - samples_for(expr, limit)

This mirrors the TypeScript TagFilter we added earlier so UI code can be
implemented either in Python or TS depending on the view.
"""
from typing import Dict, List, Optional
from .bitset import BitSet


TagMap = Dict[str, BitSet]


class TagFilter:
    def __init__(self, tag_map: TagMap):
        self.tag_map = tag_map

    def evaluate(self, expr) -> BitSet:
        if expr is None:
            # empty expression -> universe
            return self.universe()
        t = expr.get('type')
        if t == 'tag':
            return self.tag_map.get(expr.get('tag'), BitSet())
        elif t == 'and':
            return self.evaluate(expr['left']).intersect(self.evaluate(expr['right']))
        elif t == 'or':
            return self.evaluate(expr['left']).union(self.evaluate(expr['right']))
        elif t == 'not':
            return self.universe().difference(self.evaluate(expr['expr']))
        else:
            return BitSet()

    def universe(self) -> BitSet:
        out: Optional[BitSet] = None
        for k in self.tag_map:
            if out is None:
                out = self.tag_map[k].clone()
            else:
                out = out.union(self.tag_map[k])
        return out or BitSet()

    def matching_counts_for_visible(self, expr, visible_tags: List[str]):
        base = self.evaluate(expr) if expr is not None else None
        out = []
        for tag in visible_tags:
            b = self.tag_map.get(tag, BitSet())
            c = base.intersect(b).size() if base is not None else b.size()
            out.append({'tag': tag, 'count': c})
        return out

    def samples_for(self, expr, limit=5) -> List[int]:
        s = self.evaluate(expr) if expr is not None else self.universe()
        return s.to_list()[:limit]
