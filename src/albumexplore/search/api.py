"""Backend helpers to execute boolean tag queries against the database.

This module offers a pragmatic implementation: it builds an in-memory tag->album
index from the DB for the current dataset and evaluates boolean expressions
using the set-based evaluator in `query.py`.

For very large datasets this can be optimized (bitmaps, DB-side translation),
but this approach is simple, deterministic, and mirrors the UI explain
requirements (we can compute sub-expression sizes cheaply).
"""
from typing import Dict, Set, List, Any, Optional
from sqlalchemy.orm import Session
from .query import evaluate_query, explain_query
from albumexplore.database.models import album_tags, Tag
from sqlalchemy import select


def build_tag_index(session: Session) -> Dict[str, Set[str]]:
    """Return a mapping tag_name -> set(album_id).

    This queries the `album_tags` association table joined to `tags` to get
    canonical tag names. Album IDs are returned as strings (same type as DB).
    """
    tag_index: Dict[str, Set[str]] = {}

    stmt = select(album_tags.c.album_id, Tag.name).join(Tag, album_tags.c.tag_id == Tag.id)
    for album_id, tag_name in session.execute(stmt):
        if tag_name not in tag_index:
            tag_index[tag_name] = set()
        tag_index[tag_name].add(album_id)
    return tag_index


def get_all_album_ids(session: Session) -> Set[str]:
    stmt = select(album_tags.c.album_id).distinct()
    return {row[0] for row in session.execute(stmt)}


def execute_query(
    query: str,
    session: Session,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    """Execute boolean tag query and return paginated results + explain.

    Returns dict with keys: `total_count`, `ids` (list), `explain` (tree).
    """
    tag_index = build_tag_index(session)
    all_ids = get_all_album_ids(session)

    result_set = evaluate_query(query, tag_index, all_ids)

    total = len(result_set)
    ids_list = list(result_set)
    # simple deterministic ordering for paging
    ids_list.sort()
    if limit is not None:
        ids_page = ids_list[offset : offset + limit]
    else:
        ids_page = ids_list[offset:]

    explain = explain_query(query, tag_index, all_ids)

    return {"total_count": total, "ids": ids_page, "explain": explain}


def simple_filters_to_query(includes: List[str], excludes: List[str]) -> str:
    """Convert simple include/exclude lists into an equivalent boolean query.

    Example: includes=['A','B'], excludes=['C'] -> 'A AND B AND NOT C'
    """
    parts: List[str] = []
    for tag in includes:
        # quote tag if it contains spaces
        if " " in tag:
            parts.append(f'"{tag}"')
        else:
            parts.append(tag)
    if excludes:
        for tag in excludes:
            if " " in tag:
                parts.append("AND NOT \"{}\"".format(tag))
            else:
                parts.append(f"AND NOT {tag}")
    return " AND ".join(parts) if parts else ""


def query_to_filter_state(query: str):
    """Attempt to convert a boolean query into a TagFilterState.

    Supported conversions:
    - Top-level OR of AND/Tag atoms -> multiple groups (OR)
    - Top-level AND of OR/Tag/NOT atoms -> multiple groups (AND)
    - Single AND expression -> single group (AND) + excludes

    Raises QueryError if the expression is too complex to convert losslessly.
    """
    from .query import parse_query, TagNode, OpNode, QueryError
    from albumexplore.tags.filters.tag_filter_state import TagFilterState, TagFilterGroup, FilterOperator, GroupOperator

    node = parse_query(query)

    def collect_and_not(n):
        # returns (positives_set, excludes_set) or raises QueryError
        if isinstance(n, TagNode):
            return {n.tag}, set()
        if isinstance(n, OpNode) and n.op == "NOT":
            c = n.children[0]
            if not isinstance(c, TagNode):
                raise QueryError("Cannot convert complex NOT expressions to simple filters")
            return set(), {c.tag}
        if isinstance(n, OpNode) and n.op == "AND":
            pos = set()
            exc = set()
            for child in n.children:
                p, e = collect_and_not(child)
                pos.update(p)
                exc.update(e)
            return pos, exc
        raise QueryError("Unsupported node type for conversion to filter state")

    def flatten_op(n, op_type):
        """Flatten nested binary operators of same type into a list."""
        if isinstance(n, OpNode) and n.op == op_type:
            res = []
            for child in n.children:
                res.extend(flatten_op(child, op_type))
            return res
        return [n]

    def collect_or_tags(n):
        """Collect tags from an OR tree. Raises error if not pure OR of tags."""
        if isinstance(n, TagNode):
            return {n.tag}
        if isinstance(n, OpNode) and n.op == "OR":
            tags = set()
            for child in n.children:
                tags.update(collect_or_tags(child))
            return tags
        raise QueryError("OR group must contain only tags")

    # 1. Try Top-level OR case (Global OR)
    # Structure: (A AND B) OR (C AND D) OR E
    if isinstance(node, OpNode) and node.op == "OR":
        try:
            children = flatten_op(node, "OR")
            groups = []
            for child in children:
                # child must be TagNode or AND of TagNodes (no NOT allowed in OR branches for now)
                if isinstance(child, TagNode):
                    groups.append({child.tag})
                elif isinstance(child, OpNode) and child.op == "AND":
                    pos, exc = collect_and_not(child)
                    if exc:
                        raise QueryError("Conversion: OR branches may not contain NOT")
                    groups.append(pos)
                else:
                    raise QueryError("Conversion: OR branches must be simple tag atoms or AND groups")
            
            state = TagFilterState(group_operator=FilterOperator.OR)
            for i, g in enumerate(groups, start=1):
                grp = TagFilterGroup(group_id=str(i), tags=set(g), operator=GroupOperator.AND)
                state.groups.append(grp)
            return state
        except QueryError:
            # If OR parsing failed, fall through to try AND parsing
            pass

    # 2. Try Top-level AND case (Global AND)
    # Structure: A AND B AND (C OR D) AND NOT E
    try:
        # Treat root as AND (even if it's just a Tag or NOT)
        children = flatten_op(node, "AND")
        
        main_and_group_tags = set()
        or_groups = []
        excludes = set()
        
        for child in children:
            if isinstance(child, TagNode):
                main_and_group_tags.add(child.tag)
            elif isinstance(child, OpNode) and child.op == "NOT":
                # Must be NOT(Tag)
                if isinstance(child.children[0], TagNode):
                    excludes.add(child.children[0].tag)
                else:
                    raise QueryError("Complex NOT not supported")
            elif isinstance(child, OpNode) and child.op == "OR":
                # Must be pure OR of tags
                tags = collect_or_tags(child)
                or_groups.append(tags)
            else:
                raise QueryError("Unsupported node in top-level AND")
        
        state = TagFilterState(group_operator=FilterOperator.AND)
        state.exclude_tags = excludes
        
        group_id_counter = 1
        
        # Add the main AND group if it has tags
        if main_and_group_tags:
            grp = TagFilterGroup(
                group_id=str(group_id_counter), 
                tags=main_and_group_tags, 
                operator=GroupOperator.AND
            )
            state.groups.append(grp)
            group_id_counter += 1
            
        # Add the OR groups
        for tags in or_groups:
            grp = TagFilterGroup(
                group_id=str(group_id_counter),
                tags=tags,
                operator=GroupOperator.OR
            )
            state.groups.append(grp)
            group_id_counter += 1
            
        return state
        
    except QueryError as e:
        raise e
