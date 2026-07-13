"""Tokenizer for FileMaker calculation expressions.

Design rules:

- Verbatim tokens: a token's text is the exact source slice (field names keep
  their original interior spacing), so the printer can never alter a name.
- Comments ride on the next code token (`pre_comments`); the formatter's safety
  check compares code tokens and comment texts of input vs output, so nothing
  can be dropped silently.
- Anything we do not understand raises LexError - the formatter then leaves the
  source untouched instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KEYWORD_OPS = {"and", "or", "xor", "not"}
TWO_CHAR_OPS = ("<>", "<=", ">=")
SINGLE_CHAR_OPS = set("&+-*/^=<>≠≤≥")  # incl. != / <= / >= unicode forms


class LexError(ValueError):
    pass


@dataclass
class Comment:
    text: str
    own_line: bool  # True when only whitespace precedes it on its line


@dataclass
class Token:
    kind: str  # NAME NUMBER STRING OP LPAREN RPAREN LBRACKET RBRACKET SEMI EOF
    text: str
    line: int
    pre_comments: list = field(default_factory=list)


UNICODE_OPS = "≠≤≥¶"


def _is_name_char(ch: str) -> bool:
    # ~ # . appear in real-world FileMaker names: $$~DISABLETRIGGERS,
    # #ScriptResultJSON, Triggers.Disable, $sub.errorCode, Field~extra.
    # Any non-ASCII char that is not an operator is a name char too
    # (field names like "Rep 5¢ Commission" exist in the wild).
    if ch.isalnum() or ch in "_~#.":
        return True
    return ord(ch) > 127 and ch not in UNICODE_OPS


def _is_name_start(ch: str) -> bool:
    if ch.isalpha() or ch in "_~#":
        return True
    return ord(ch) > 127 and ch not in UNICODE_OPS


def _extend_name_run(s: str, end: int) -> int:
    """Merge following space-separated words into one name (FileMaker field
    names may contain spaces). Stops at keywords, operators, newlines, and
    words that start a function call."""
    n = len(s)
    while True:
        k = end
        while k < n and s[k] in " \t":
            k += 1
        if k == end or k >= n or not _is_name_char(s[k]):
            break
        j = k
        while j < n and _is_name_char(s[j]):
            j += 1
        if s[k:j].lower() in KEYWORD_OPS:
            break
        m = j
        while m < n and s[m] in " \t":
            m += 1
        if m < n and s[m] == "(":  # that word is a function name
            break
        end = j
    return end


def _qualify(s: str, end: int, line: int) -> int:
    """Extend a name across a `::` field qualifier if present."""
    n = len(s)
    m = end
    while m < n and s[m] in " \t":
        m += 1
    if not s.startswith("::", m):
        return end
    m += 2
    while m < n and s[m] in " \t":
        m += 1
    if s.startswith("${", m):
        k = s.find("}", m)
        if k == -1:
            raise LexError(f"unterminated ${{...}} name (line {line})")
        return k + 1
    if m < n and _is_name_char(s[m]):
        j = m
        while j < n and _is_name_char(s[j]):
            j += 1
        return _extend_name_run(s, j)
    raise LexError(f"expected a field name after '::' (line {line})")


def tokenize(source: str) -> list[Token]:
    n = len(source)
    i = 0
    line = 1
    fresh = True  # only whitespace so far on the current line
    pending: list[Comment] = []
    tokens: list[Token] = []

    def add(kind: str, text: str) -> None:
        nonlocal pending, fresh
        tokens.append(Token(kind, text, line, pending))
        pending = []
        fresh = False

    while i < n:
        ch = source[i]

        if ch == "\n":
            line += 1
            i += 1
            fresh = True
            continue
        if ch in " \t\r":
            i += 1
            continue

        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j == -1 else j
            pending.append(Comment(source[i:j].rstrip(), fresh))
            fresh = False
            i = j
            continue

        if source.startswith("/*", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                if source.startswith("/*", j):
                    depth += 1
                    j += 2
                elif source.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    if source[j] == "\n":
                        line += 1
                    j += 1
            if depth:
                raise LexError(f"unterminated block comment (line {line})")
            pending.append(Comment(source[i:j], fresh))
            fresh = False
            i = j
            continue

        if ch == '"':
            j = i + 1
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == '"':
                    break
                if source[j] == "\n":
                    line += 1
                j += 1
            if j >= n:
                raise LexError(f"unterminated string (line {line})")
            add("STRING", source[i : j + 1])
            i = j + 1
            continue

        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            j = i
            seen_dot = False
            while j < n and (source[j].isdigit() or (source[j] == "." and not seen_dot)):
                if source[j] == ".":
                    seen_dot = True
                j += 1
            add("NUMBER", source[i:j])
            i = j
            continue

        if ch == "$":
            j = i
            while j < n and source[j] == "$":
                j += 1
            if j - i > 2:
                raise LexError(f"too many '$' (line {line})")
            if j < n and source[j] == "{":
                k = source.find("}", j)
                if k == -1:
                    raise LexError(f"unterminated ${{...}} name (line {line})")
                end = _qualify(source, k + 1, line)
                add("NAME", source[i:end])
                i = end
                continue
            if j < n and _is_name_char(source[j]):
                k = j
                while k < n and _is_name_char(source[k]):
                    k += 1
                add("NAME", source[i:k])
                i = k
                continue
            raise LexError(f"bare '$' (line {line})")

        if ch == "¶":  # pilcrow literal
            add("NAME", ch)
            i += 1
            continue

        if _is_name_start(ch):
            j = i
            while j < n and _is_name_char(source[j]):
                j += 1
            if source[i:j].lower() in KEYWORD_OPS:
                add("OP", source[i:j])
                i = j
                continue
            end = _extend_name_run(source, j)
            end = _qualify(source, end, line)
            add("NAME", source[i:end])
            i = end
            continue

        matched = False
        for two in TWO_CHAR_OPS:
            if source.startswith(two, i):
                add("OP", two)
                i += 2
                matched = True
                break
        if matched:
            continue

        if ch in SINGLE_CHAR_OPS:
            add("OP", ch)
            i += 1
            continue
        if ch == "(":
            add("LPAREN", ch)
            i += 1
            continue
        if ch == ")":
            add("RPAREN", ch)
            i += 1
            continue
        if ch == "[":
            add("LBRACKET", ch)
            i += 1
            continue
        if ch == "]":
            add("RBRACKET", ch)
            i += 1
            continue
        if ch == ";":
            add("SEMI", ch)
            i += 1
            continue

        raise LexError(f"unexpected character {ch!r} (line {line})")

    tokens.append(Token("EOF", "", line, pending))
    return tokens
