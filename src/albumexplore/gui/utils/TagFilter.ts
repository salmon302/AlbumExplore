// src/albumexplore/gui/utils/TagFilter.ts
// Small utility for evaluating boolean tag expressions using BitSet

import BitSet from './BitSet';

export type TagMap = { [tag: string]: BitSet };

// Expression AST types
export type Expr =
    | { type: 'tag'; tag: string }
    | { type: 'and'; left: Expr; right: Expr }
    | { type: 'or'; left: Expr; right: Expr }
    | { type: 'not'; expr: Expr };

export default class TagFilter {
    private tagMap: TagMap;

    constructor(tagMap: TagMap) {
        this.tagMap = tagMap;
    }

    evaluate(expr: Expr): BitSet {
        switch (expr.type) {
            case 'tag':
                return this.tagMap[expr.tag] ? this.tagMap[expr.tag].clone() : new BitSet(0);
            case 'and': {
                const L = this.evaluate(expr.left);
                const R = this.evaluate(expr.right);
                return L.intersect(R);
            }
            case 'or': {
                const L = this.evaluate(expr.left);
                const R = this.evaluate(expr.right);
                return L.union(R);
            }
            case 'not': {
                // not is taken relative to the universe: compute universe bitset as union of all tags
                const universe = this.universe();
                const inner = this.evaluate(expr.expr);
                return universe.difference(inner);
            }
            default:
                return new BitSet(0);
        }
    }

    // quickly compute universe (cacheable optimization could be added)
    universe(): BitSet {
        const tags = Object.keys(this.tagMap);
        if (tags.length === 0) return new BitSet(0);
        let out = this.tagMap[tags[0]].clone();
        for (let i = 1; i < tags.length; i++) out = out.union(this.tagMap[tags[i]]);
        return out;
    }

    // helper: compute Matching counts for a set of candidate tags, returning { tag, count }
    matchingCountsForVisible(expr: Expr | null, visibleTags: string[]): { tag: string; count: number }[] {
        const base = expr ? this.evaluate(expr) : null;
        const out: { tag: string; count: number }[] = [];
        for (const tag of visibleTags) {
            const b = this.tagMap[tag] || new BitSet(0);
            const c = base ? base.intersect(b).size() : b.size();
            out.push({ tag, count: c });
        }
        return out;
    }

    // get samples (album ids) for an expression (limit)
    samplesFor(expr: Expr | null, limit = 5): number[] {
        const set = expr ? this.evaluate(expr) : this.universe();
        return set.toArray().slice(0, limit);
    }
}
