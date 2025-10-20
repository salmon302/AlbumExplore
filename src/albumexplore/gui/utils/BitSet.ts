// src/albumexplore/gui/utils/BitSet.ts
// A compact, dependency-free BitSet implementation for album id sets.
// Uses Uint32Array as the backing store and supports union/intersection/difference.

export default class BitSet {
    private words: Uint32Array; // each bit represents an id
    private _size: number; // cached size, -1 if dirty

    constructor(sizeBits = 1024) {
        const words = Math.ceil(sizeBits / 32);
        this.words = new Uint32Array(words);
        this._size = 0;
    }

    // ensure backing store can hold bit 'n'
    private ensure(n: number) {
        const wordIndex = (n / 32) | 0;
        if (wordIndex >= this.words.length) {
            const newWords = new Uint32Array(Math.max(this.words.length * 2, wordIndex + 1));
            newWords.set(this.words, 0);
            this.words = newWords;
        }
    }

    add(n: number) {
        if (n < 0) return;
        this.ensure(n);
        const wi = (n / 32) | 0;
        const bit = 1 << (n & 31);
        const before = this.words[wi];
        this.words[wi] = before | bit;
        if ((before & bit) === 0) this._size = -1; // mark dirty
    }

    remove(n: number) {
        if (n < 0) return;
        const wi = (n / 32) | 0;
        if (wi >= this.words.length) return;
        const bit = 1 << (n & 31);
        const before = this.words[wi];
        this.words[wi] = before & ~bit;
        if ((before & bit) !== 0) this._size = -1;
    }

    has(n: number) {
        if (n < 0) return false;
        const wi = (n / 32) | 0;
        if (wi >= this.words.length) return false;
        const bit = 1 << (n & 31);
        return (this.words[wi] & bit) !== 0;
    }

    // bitwise operations return a new BitSet (immutable-style)
    union(other: BitSet): BitSet {
        const maxWords = Math.max(this.words.length, other.words.length);
        const out = new BitSet(maxWords * 32);
        out.words = new Uint32Array(maxWords);
        for (let i = 0; i < maxWords; i++) {
            const a = i < this.words.length ? this.words[i] : 0;
            const b = i < other.words.length ? other.words[i] : 0;
            out.words[i] = a | b;
        }
        out._size = -1;
        return out;
    }

    intersect(other: BitSet): BitSet {
        const maxWords = Math.min(this.words.length, other.words.length);
        const out = new BitSet(maxWords * 32);
        out.words = new Uint32Array(maxWords);
        for (let i = 0; i < maxWords; i++) {
            out.words[i] = this.words[i] & other.words[i];
        }
        out._size = -1;
        return out;
    }

    difference(other: BitSet): BitSet {
        const maxWords = this.words.length;
        const out = new BitSet(maxWords * 32);
        out.words = new Uint32Array(maxWords);
        for (let i = 0; i < maxWords; i++) {
            const b = i < other.words.length ? other.words[i] : 0;
            out.words[i] = this.words[i] & ~b;
        }
        out._size = -1;
        return out;
    }

    // cardinality (count bits)
    size(): number {
        if (this._size >= 0) return this._size;
        let count = 0;
        for (let i = 0; i < this.words.length; i++) {
            let v = this.words[i];
            // popcount
            while (v) {
                v &= v - 1;
                count++;
            }
        }
        this._size = count;
        return count;
    }

    // iterate set bits as numbers
    toArray(): number[] {
        const out: number[] = [];
        for (let wi = 0; wi < this.words.length; wi++) {
            let v = this.words[wi];
            while (v) {
                const t = v & -v;
                const bitIndex = Math.log2(t);
                out.push(wi * 32 + bitIndex);
                v &= v - 1;
            }
        }
        return out;
    }

    // clone
    clone(): BitSet {
        const out = new BitSet(this.words.length * 32);
        out.words = new Uint32Array(this.words);
        out._size = this._size;
        return out;
    }

    // helper to create a BitSet from array of ids
    static fromArray(arr: number[], maxIdHint = 0): BitSet {
        const maxId = Math.max(maxIdHint, ...arr, 0);
        const out = new BitSet(maxId + 1);
        for (const id of arr) out.add(id);
        return out;
    }
}
