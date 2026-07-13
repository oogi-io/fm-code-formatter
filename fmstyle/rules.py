"""Lint rules - guideline checks that go beyond pure formatting.

v0 ships two rules from the style guide:

- let-explicit-result: a Let must define an explicit result variable as its
  final declaration and return it (never an inline expression).
- variable-naming: Let-local variable names must match the configured pattern.
"""

from __future__ import annotations

import re

from .config import Style
from .parser import Assign, Bin, Brackets, Call, Literal, Node, Paren, Rep, Unary


def lint(node: Node, style: Style | None = None) -> list[tuple[str, str]]:
    style = style or Style()
    issues: list[tuple[str, str]] = []
    _walk(node, style, issues)
    return issues


def _walk(node: Node, style: Style, issues: list) -> None:
    if isinstance(node, Call):
        if node.name.lower() == "let" and len(node.args) == 2 and isinstance(node.args[0], Brackets):
            _check_let(node, style, issues)
        for arg in node.args:
            _walk(arg, style, issues)
    elif isinstance(node, Bin):
        _walk(node.left, style, issues)
        _walk(node.right, style, issues)
    elif isinstance(node, Unary):
        _walk(node.operand, style, issues)
    elif isinstance(node, Paren):
        _walk(node.inner, style, issues)
    elif isinstance(node, Brackets):
        for item in node.items:
            _walk(item, style, issues)
    elif isinstance(node, Assign):
        _walk(node.value, style, issues)
    elif isinstance(node, Rep):
        _walk(node.index, style, issues)


def _check_let(call: Call, style: Style, issues: list) -> None:
    items = call.args[0].items
    name = style.result_name

    last = items[-1] if items else None
    if not (isinstance(last, Assign) and last.target.text == name):
        issues.append(
            ("let-explicit-result", f"Let should define `{name}` as its final variable")
        )
    result = call.args[1]
    if not (isinstance(result, Literal) and result.kind == "NAME" and result.text == name):
        issues.append(
            ("let-explicit-result", f"Let should return `{name}`, not an inline expression")
        )

    pattern = re.compile(style.local_variable_pattern)
    for item in items:
        if isinstance(item, Assign) and not pattern.match(item.target.text):
            issues.append(
                (
                    "variable-naming",
                    f"variable `{item.target.text}` does not match {style.local_variable_pattern}",
                )
            )
