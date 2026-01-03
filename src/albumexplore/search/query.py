"""Boolean tag query parser and evaluator.

This module implements a small boolean expression language for tags with
operators AND, OR, NOT and parentheses. It provides parsing (tokenize -> RPN),
evaluation against a `tag_index: Dict[str, Set[int]]` and an explain function
that returns a tree with match counts for each sub-expression.

This is intended to be used by the Tag Explorer advanced query UI.
"""
from __future__ import annotations

import re
from typing import Dict, Set, List, Tuple, Union, Any


class QueryError(Exception):
    pass


_TOKEN_RE = re.compile(r'''
    \s*
    (
      "(?:[^"\\]|\\.)+"        |   # quoted tag "Tag C"
      \(|\)                        |   # parens
      \bAND\b|\bOR\b|\bNOT\b   |   # operators
      [^\s()]+                        # bare tag
    )
''', re.IGNORECASE | re.VERBOSE)


def tokenize(query: str) -> List[str]:
    tokens = [m.group(1) for m in _TOKEN_RE.finditer(query)]
    raw_tokens: List[str] = []
    for t in tokens:
        up = t.upper()
        if up in ("AND", "OR", "NOT"):
            raw_tokens.append(up)
        else:
            raw_tokens.append(t)

    # Insert implicit ANDs
    final_tokens: List[str] = []
    if not raw_tokens:
        return final_tokens

    final_tokens.append(raw_tokens[0])

    for i in range(1, len(raw_tokens)):
        prev = raw_tokens[i - 1]
        curr = raw_tokens[i]

        # Insert AND if:
        # prev is a Tag or ')'
        # AND
        # curr is a Tag or '(' or 'NOT'

        prev_is_tag = prev not in ("AND", "OR", "NOT", "(", ")")
        prev_is_close_paren = prev == ")"
        should_insert_after_prev = prev_is_tag or prev_is_close_paren

        curr_is_tag = curr not in ("AND", "OR", "NOT", "(", ")")
        curr_is_open_paren = curr == "("
        curr_is_not = curr == "NOT"
        should_insert_before_curr = curr_is_tag or curr_is_open_paren or curr_is_not

        if should_insert_after_prev and should_insert_before_curr:
            final_tokens.append("AND_IMPLICIT")

        final_tokens.append(curr)

    return final_tokens


def to_rpn(tokens: List[str]) -> List[Union[Tuple[str, str], str]]:
    """Convert tokens to RPN. Tags become ('TAG', value), operators stay as strings."""
    # AND_IMPLICIT has lower precedence (0) than OR (1)
    prec = {"NOT": 3, "AND": 2, "OR": 1, "AND_IMPLICIT": 0}
    output: List[Union[Tuple[str, str], str]] = []
    stack: List[str] = []
    for t in tokens:
        if t == "(":
            stack.append(t)
        elif t == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise QueryError("Mismatched parentheses")
            stack.pop()  # pop '('
        elif t in prec:
            # NOT is unary and higher precedence
            while stack and stack[-1] in prec and prec[stack[-1]] >= prec[t]:
                output.append(stack.pop())
            stack.append(t)
        else:
            # tag -- strip surrounding quotes if present
            tt = t
            if tt.startswith('"') and tt.endswith('"') and len(tt) >= 2:
                tt = tt[1:-1].replace('\"', '"')
            output.append(("TAG", tt))
    while stack:
        op = stack.pop()
        if op in ("(", ")"):
            raise QueryError("Mismatched parentheses")
        output.append(op)
    return output


class Node:
    pass


class TagNode(Node):
    def __init__(self, tag: str) -> None:
        self.tag = tag


class OpNode(Node):
    def __init__(self, op: str, children: List[Node]) -> None:
        self.op = op
        self.children = children


def rpn_to_tree(rpn: List[Union[Tuple[str, str], str]]) -> Node:
    stack: List[Node] = []
    for tok in rpn:
        if isinstance(tok, tuple) and tok[0] == "TAG":
            stack.append(TagNode(tok[1]))
        elif tok == "NOT":
            if not stack:
                raise QueryError("NOT operator without operand")
            c = stack.pop()
            stack.append(OpNode("NOT", [c]))
        elif tok in ("AND", "OR", "AND_IMPLICIT"):
            if len(stack) < 2:
                raise QueryError(f"{tok} operator without enough operands")
            b = stack.pop()
            a = stack.pop()
            # Treat AND_IMPLICIT as standard AND in the tree
            op_name = "AND" if tok == "AND_IMPLICIT" else tok
            stack.append(OpNode(op_name, [a, b]))
        else:
            raise QueryError(f"Unknown token in RPN: {tok!r}")
    if len(stack) != 1:
        raise QueryError("Invalid expression")
    return stack[0]


def parse_query(query: str) -> Node:
    tokens = tokenize(query)
    rpn = to_rpn(tokens)
    return rpn_to_tree(rpn)


def _eval_node(node: Node, tag_index: Dict[str, Set[int]], all_ids: Set[int]) -> Set[int]:
    if isinstance(node, TagNode):
        # tag lookup: normalize lookup to exact match; missing tag -> empty set
        return set(tag_index.get(node.tag, set()))
    elif isinstance(node, OpNode):
        if node.op == "NOT":
            child = _eval_node(node.children[0], tag_index, all_ids)
            return all_ids - child
        elif node.op == "AND":
            a = _eval_node(node.children[0], tag_index, all_ids)
            b = _eval_node(node.children[1], tag_index, all_ids)
            return a & b
        elif node.op == "OR":
            a = _eval_node(node.children[0], tag_index, all_ids)
            b = _eval_node(node.children[1], tag_index, all_ids)
            return a | b
        else:
            raise QueryError(f"Unknown op: {node.op}")
    else:
        raise QueryError("Invalid node")


def evaluate_query(query: str, tag_index: Dict[str, Set[int]], all_ids: Set[int]) -> Set[int]:
    """Parse and evaluate the query, returning the set of matching album ids."""
    node = parse_query(query)
    return _eval_node(node, tag_index, all_ids)


def _explain_node(node: Node, tag_index: Dict[str, Set[int]], all_ids: Set[int]) -> Dict[str, Any]:
    if isinstance(node, TagNode):
        s = set(tag_index.get(node.tag, set()))
        return {"type": "tag", "tag": node.tag, "count": len(s), "ids_sample": list(sorted(s)[:10])}
    else:
        if node.op == "NOT":
            child = _explain_node(node.children[0], tag_index, all_ids)
            # child's ids
            child_ids = _eval_node(node.children[0], tag_index, all_ids)
            ids = all_ids - child_ids
            return {"type": "op", "op": "NOT", "count": len(ids), "children": [child]}
        else:
            left = _explain_node(node.children[0], tag_index, all_ids)
            right = _explain_node(node.children[1], tag_index, all_ids)
            left_ids = _eval_node(node.children[0], tag_index, all_ids)
            right_ids = _eval_node(node.children[1], tag_index, all_ids)
            if node.op == "AND":
                ids = left_ids & right_ids
            elif node.op == "OR":
                ids = left_ids | right_ids
            else:
                raise QueryError(f"Unknown op: {node.op}")
            return {"type": "op", "op": node.op, "count": len(ids), "children": [left, right]}


def explain_query(query: str, tag_index: Dict[str, Set[int]], all_ids: Set[int]) -> Dict[str, Any]:
    """Return a tree-like explanation with counts for each sub-expression."""
    node = parse_query(query)
    return _explain_node(node, tag_index, all_ids)
