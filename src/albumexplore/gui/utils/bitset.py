"""
Simple BitSet implementation using Python ints as backing storage.
Provides basic set operations useful for tag->album id mappings in-memory.

This is intentionally minimal and dependency free. For very large datasets
you can replace with a compressed bitmap library.
"""
from typing import Iterable, List


class BitSet:
    def __init__(self, ids: Iterable[int] | None = None):
        self._bits = 0
        if ids:
            for i in ids:
                if i >= 0:
                    self._bits |= (1 << i)

    def add(self, n: int) -> None:
        if n < 0:
            return
        self._bits |= (1 << n)

    def remove(self, n: int) -> None:
        if n < 0:
            return
        self._bits &= ~(1 << n)

    def has(self, n: int) -> bool:
        if n < 0:
            return False
        return (self._bits >> n) & 1 == 1

    def union(self, other: 'BitSet') -> 'BitSet':
        out = BitSet()
        out._bits = self._bits | other._bits
        return out

    def intersect(self, other: 'BitSet') -> 'BitSet':
        out = BitSet()
        out._bits = self._bits & other._bits
        return out

    def difference(self, other: 'BitSet') -> 'BitSet':
        out = BitSet()
        out._bits = self._bits & ~other._bits
        return out

    def size(self) -> int:
        # popcount
        return self._bits.bit_count()

    def to_list(self) -> List[int]:
        out: List[int] = []
        bits = self._bits
        idx = 0
        while bits:
            if bits & 1:
                out.append(idx)
            bits >>= 1
            idx += 1
        return out

    def clone(self) -> 'BitSet':
        return BitSet(self.to_list())

    @classmethod
    def from_list(cls, arr: Iterable[int]) -> 'BitSet':
        return cls(arr)
