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
- mixed-decimal-separators: number literals should agree on one decimal
  separator. Under decimal_separator "auto" it flags a calculation that mixes
  comma and period literals; under "comma" it flags each period literal.
  Under "period" the lexer already refuses comma literals, so there is
  nothing left for the rule to see. No params.
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
    if "mixed-decimal-separators" in style.lint:
        _check_decimal_separators(node, style, issues)
    return issues


def _collect_numbers(node: Node, out: list) -> None:
    if isinstance(node, Literal):
        if node.kind == "NUMBER":
            out.append(node.text)
    elif isinstance(node, Call):
        for arg in node.args:
            _collect_numbers(arg, out)
    elif isinstance(node, Bin):
        _collect_numbers(node.left, out)
        _collect_numbers(node.right, out)
    elif isinstance(node, Unary):
        _collect_numbers(node.operand, out)
    elif isinstance(node, Paren):
        _collect_numbers(node.inner, out)
    elif isinstance(node, Brackets):
        for item in node.items:
            _collect_numbers(item, out)
    elif isinstance(node, Assign):
        _collect_numbers(node.value, out)
    elif isinstance(node, Rep):
        _collect_numbers(node.index, out)


def _check_decimal_separators(node: Node, style: Style, issues: list) -> None:
    numbers: list[str] = []
    _collect_numbers(node, numbers)
    if style.decimal_separator == "comma":
        for text in numbers:
            if "." in text:
                issues.append(
                    (
                        "mixed-decimal-separators",
                        f'number `{text}` uses \'.\' but decimal_separator is "comma"',
                    )
                )
    elif style.decimal_separator == "auto":
        first_comma = next((t for t in numbers if "," in t), None)
        first_period = next((t for t in numbers if "." in t), None)
        if first_comma and first_period:
            issues.append(
                (
                    "mixed-decimal-separators",
                    f"calculation mixes decimal separators: `{first_comma}` (comma) "
                    f"and `{first_period}` (period)",
                )
            )


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
