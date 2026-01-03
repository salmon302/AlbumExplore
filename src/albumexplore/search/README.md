Boolean Tag Query API

This folder provides a small, pragmatic backend for evaluating boolean tag
queries used by the Tag Explorer advanced UI.

Key functions

- `execute_query(query: str, session: Session, limit: Optional[int]=None, offset: int=0)`:
  Build an in-memory tag->album index from the DB and evaluate the boolean
  expression. Returns `{"total_count": int, "ids": List[str], "explain": dict}`.

- `simple_filters_to_query(includes: List[str], excludes: List[str]) -> str`:
  Convert the existing simple include/exclude tag lists into a boolean query
  string (useful when switching between simple and advanced UI modes).

Integration notes

- This implementation is intentionally DB-agnostic: it loads per-tag
  album-id sets into memory and uses set operations. That makes it easy to
  compute counts for sub-expressions (used by the explain feature).

- For very large datasets you can optimize by:
  - Using bitmaps (RoaringBitmap / `pyroaring`) instead of Python sets for
    memory and speed gains.
  - Translating top-level AND/OR-only queries to SQL when appropriate.
  - Caching popular tag sets or recent query results.

Client/UI responsibilities

- Call `execute_query` with the user's boolean expression; use `explain`
  to show sub-expression counts and help the user debug complex queries.
- When converting between simple and advanced modes use
  `simple_filters_to_query` to preserve user choices.

Example

```py
from albumexplore.search.api import execute_query, simple_filters_to_query

query = simple_filters_to_query(['psychedelic','avant-garde'], ['live'])
# -> 'psychedelic AND avant-garde AND NOT live'

result = execute_query(query, session, limit=100, offset=0)
print(result['total_count'], result['ids'][:20])
print(result['explain'])
```
