"""fmstyle - deterministic formatter + style engine for FileMaker calculations.

Public API:

    format_calc(source, style)  -> formatted text (token-preservation verified)
    lint_calc(source, style)    -> [(rule_id, message), ...]
    Style                       -> configuration (an org's mechanical rules)
"""

from __future__ import annotations

from .config import Style
from .lexer import LexError, tokenize
from .parser import ParseError, Parser
from .printer import Printer
from .rules import lint as _lint

__version__ = "0.3.0"

__all__ = [
    "format_calc",
    "lint_calc",
    "Style",
    "LexError",
    "ParseError",
    "FormatSafetyError",
]


class FormatSafetyError(RuntimeError):
    """Formatting would have changed the token stream - refused."""


def _signature(source: str):
    code = []
    comments = []
    for tok in tokenize(source):
        comments.extend(c.text for c in tok.pre_comments)
        if tok.kind != "EOF":
            text = tok.text.lower() if tok.kind == "OP" else tok.text
            code.append((tok.kind, text))
    return code, comments


def format_calc(source: str, style: Style | None = None) -> str:
    """Format a FileMaker calculation. Guaranteed semantics-preserving: the
    output must re-tokenize to the exact same code tokens and comments as the
    input, otherwise FormatSafetyError is raised and nothing is changed."""
    style = style or Style()
    tokens = tokenize(source)
    if len(tokens) == 1:  # comments only (e.g. a commented-out calc) - keep as is
        return source
    node = Parser(tokens).parse()
    out = Printer(style).format(node)
    if _signature(source) != _signature(out):
        raise FormatSafetyError(
            "formatting would alter the token stream; refusing (please report this input)"
        )
    return out


def lint_calc(source: str, style: Style | None = None):
    """Run guideline lint rules over a calculation."""
    style = style or Style()
    tokens = tokenize(source)
    if len(tokens) == 1:  # comments only - nothing to lint
        return []
    return _lint(Parser(tokens).parse(), style)
