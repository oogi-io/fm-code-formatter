"""Lint rules - opinionated practice checks, each individually OPT-IN.

A rule runs only when enabled in the style pack's "lint" section. With no
rules enabled, lint returns nothing: bare fmstyle has no opinions you didn't
give it. The registry of rules and their default parameters lives in
config.LINT_RULES.

- let-explicit-result: a Let must define an explicit result variable as its
  final declaration and return it (never an inline expression).
  Params: result_name.
- variable-naming: Let-local variable names must match a pattern.
  Params: pattern.
"""

from __future__ import annotations

import re

from .config import Style
from .parser import Assign, Bin, Brackets, Call, Literal, Node, Paren, Rep, Unary


def lint(node: Node, style: Style | None = None) -> list[tuple[str, str]]:
    style = style or Style()
    issues: list[tuple[str, str]] = []
    if not style.lint:
        return issues
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

    explicit = style.lint.get("let-explicit-result")
    if explicit:
        name = explicit["result_name"]
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

    naming = style.lint.get("variable-naming")
    if naming:
        pattern = re.compile(naming["pattern"])
        for item in items:
            if isinstance(item, Assign) and not pattern.match(item.target.text):
                issues.append(
                    (
                        "variable-naming",
                        f"variable `{item.target.text}` does not match {naming['pattern']}",
                    )
                )
