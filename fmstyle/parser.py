"""Recursive-descent parser for FileMaker calculations.

Produces a small AST. Comments are attached to the nearest node (leading /
trailing / post) so the printer can re-emit them. `a = b` at the top level of
a bracket list is recognised as a Let/While-style assignment.
"""

from __future__ import annotations

from .lexer import Token

CMP_OPS = {"=", "≠", "<>", "<", ">", "≤", "≥", "<=", ">="}

PRECEDENCE = {
    "or": 1, "xor": 1,
    "and": 2,
    "not": 3,
    "=": 4, "≠": 4, "<>": 4, "<": 4, ">": 4, "≤": 4, "≥": 4, "<=": 4, ">=": 4,
    "&": 5,
    "+": 6, "-": 6,
    "*": 7, "/": 7,
    "^": 8,
}


class ParseError(ValueError):
    pass


class Node:
    def __init__(self):
        self.leading = []   # comments printed before the node
        self.trailing = []  # inline comments printed at the end of its line
        self.post = []      # own-line comments printed after the node

    def has_comments(self) -> bool:
        return bool(self.leading or self.trailing or self.post)


class Literal(Node):
    def __init__(self, kind: str, text: str):
        super().__init__()
        self.kind = kind  # NUMBER | STRING | NAME
        self.text = text


class Unary(Node):
    def __init__(self, op: str, operand: Node):
        super().__init__()
        self.op = op
        self.operand = operand


class Bin(Node):
    def __init__(self, op: str, left: Node, right: Node):
        super().__init__()
        self.op = op
        self.left = left
        self.right = right


class Paren(Node):
    def __init__(self, inner: Node):
        super().__init__()
        self.inner = inner


class Brackets(Node):
    def __init__(self):
        super().__init__()
        self.items: list[Node] = []
        self.trailing_semi = False  # FileMaker tolerates `[ a ; b ; ]`


class Assign(Node):
    def __init__(self, target: Literal, value: Node):
        super().__init__()
        self.target = target
        self.value = value


class Call(Node):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.args: list[Node] = []
        self.trailing_semi = False  # FileMaker tolerates `Case ( a ; b ; )`


class Rep(Node):
    """Repetition reference: field[2], $var[$i + 1]."""

    def __init__(self, target: Literal, index: Node):
        super().__init__()
        self.target = target
        self.index = index


class Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.i = 0

    def cur(self) -> Token:
        return self.toks[self.i]

    def eat(self, kind: str | None = None) -> Token:
        t = self.cur()
        if kind and t.kind != kind:
            raise ParseError(f"expected {kind}, got {t.kind} {t.text!r} (line {t.line})")
        self.i += 1
        return t

    def at_op(self, *names: str) -> bool:
        t = self.cur()
        return t.kind == "OP" and t.text.lower() in names

    @staticmethod
    def _absorb(node: Node, sep: Token) -> None:
        """Move comments sitting before a separator/closer onto the node."""
        for c in sep.pre_comments:
            (node.post if c.own_line else node.trailing).append(c)
        sep.pre_comments = []

    def _trailing_after_sep(self, node: Node) -> None:
        """A comment on the same line as (and after) a `;` describes the item
        just closed, not the next one - `x = 1 ; // note`. The lexer attaches
        it to the following token; move that same-line run onto this item."""
        tok = self.cur()
        while tok.pre_comments and not tok.pre_comments[0].own_line:
            node.trailing.append(tok.pre_comments.pop(0))

    @staticmethod
    def _mkbin(op: str, left: Node, right: Node) -> "Bin":
        """Build a binary node, hoisting the left operand's leading comments up
        to the whole expression. A comment before the leftmost leaf sits before
        the entire expression, so keeping it on the leaf would (wrongly) block
        the expression from rendering inline."""
        node = Bin(op, left, right)
        node.leading = left.leading
        left.leading = []
        return node

    # ------------------------------------------------------------------ api

    def parse(self) -> Node:
        node = self.expr()
        eof = self.cur()
        if eof.kind != "EOF":
            raise ParseError(f"unexpected {eof.kind} {eof.text!r} (line {eof.line})")
        node.post.extend(eof.pre_comments)
        return node

    # ------------------------------------------------- precedence climbing

    def expr(self) -> Node:
        return self._binary(("or", "xor"), self._and)

    def _and(self) -> Node:
        return self._binary(("and",), self._not)

    def _not(self) -> Node:
        if self.at_op("not"):
            t = self.eat()
            node = Unary(t.text, self._not())
            node.leading = t.pre_comments
            return node
        return self._cmp()

    def _cmp(self) -> Node:
        left = self._concat()
        while self.cur().kind == "OP" and self.cur().text in CMP_OPS:
            t = self.eat()
            right = self._concat()
            right.leading = t.pre_comments + right.leading
            left = self._mkbin(t.text, left, right)
        return left

    def _concat(self) -> Node:
        return self._binary_text(("&",), self._add)

    def _add(self) -> Node:
        return self._binary_text(("+", "-"), self._mul)

    def _mul(self) -> Node:
        return self._binary_text(("*", "/"), self._pow)

    def _pow(self) -> Node:
        return self._binary_text(("^",), self._unary)

    def _binary(self, ops: tuple, next_level) -> Node:
        left = next_level()
        while self.at_op(*ops):
            t = self.eat()
            right = next_level()
            right.leading = t.pre_comments + right.leading
            left = self._mkbin(t.text, left, right)
        return left

    def _binary_text(self, ops: tuple, next_level) -> Node:
        left = next_level()
        while self.cur().kind == "OP" and self.cur().text in ops:
            t = self.eat()
            right = next_level()
            right.leading = t.pre_comments + right.leading
            left = self._mkbin(t.text, left, right)
        return left

    def _unary(self) -> Node:
        t = self.cur()
        if t.kind == "OP" and t.text in ("-", "+"):
            self.eat()
            node = Unary(t.text, self._unary())
            node.leading = t.pre_comments
            return node
        return self._primary()

    # ----------------------------------------------------------- primaries

    def _primary(self) -> Node:
        t = self.cur()

        if t.kind in ("NUMBER", "STRING"):
            self.eat()
            node = Literal(t.kind, t.text)
            node.leading = t.pre_comments
            return node

        if t.kind == "NAME":
            self.eat()
            if self.cur().kind == "LPAREN":
                lp = self.eat()
                call = Call(t.text)
                call.leading = t.pre_comments + lp.pre_comments
                if self.cur().kind == "RPAREN":
                    rp = self.cur()
                    self._absorb(call, rp)
                    self.eat()
                    return call
                while True:
                    arg = self._brackets_or_expr()
                    call.args.append(arg)
                    sep = self.cur()
                    self._absorb(arg, sep)
                    if sep.kind == "SEMI":
                        self.eat()
                        self._trailing_after_sep(arg)
                        if self.cur().kind == "RPAREN":  # trailing semicolon
                            call.trailing_semi = True
                            self._absorb(call, self.cur())
                            self.eat()
                            break
                        continue
                    if sep.kind == "RPAREN":
                        self.eat()
                        break
                    raise ParseError(
                        f"expected ';' or ')', got {sep.kind} {sep.text!r} (line {sep.line})"
                    )
                return call
            node = Literal("NAME", t.text)
            node.leading = t.pre_comments
            if self.cur().kind == "LBRACKET":  # repetition: field[2]
                self.eat()
                index = self.expr()
                rb = self.cur()
                self._absorb(index, rb)
                self.eat("RBRACKET")
                return Rep(node, index)
            return node

        if t.kind == "LPAREN":
            self.eat()
            inner = self.expr()
            rp = self.cur()
            self._absorb(inner, rp)
            self.eat("RPAREN")
            node = Paren(inner)
            node.leading = t.pre_comments
            return node

        raise ParseError(f"unexpected {t.kind} {t.text!r} (line {t.line})")

    def _brackets_or_expr(self) -> Node:
        t = self.cur()
        if t.kind != "LBRACKET":
            return self.expr()

        self.eat()
        node = Brackets()
        node.leading = t.pre_comments
        if self.cur().kind == "RBRACKET":
            rb = self.cur()
            self._absorb(node, rb)
            self.eat()
            return node
        while True:
            # `name = expr` opening a bracket item is an assignment whose value
            # is a FULL expression (so `x = not y` / `x = a and b` parse right)
            nxt = self.toks[self.i + 1] if self.i + 1 < len(self.toks) else None
            if (
                self.cur().kind == "NAME"
                and nxt is not None
                and nxt.kind == "OP"
                and nxt.text == "="
            ):
                name_tok = self.eat()
                eq = self.eat()
                target = Literal("NAME", name_tok.text)
                target.leading = name_tok.pre_comments
                value = self.expr()
                value.leading = eq.pre_comments + value.leading
                item: Node = Assign(target, value)
            else:
                item = self.expr()
                if (
                    isinstance(item, Bin)
                    and item.op == "="
                    and isinstance(item.left, Literal)
                    and item.left.kind == "NAME"
                ):
                    assign = Assign(item.left, item.right)
                    assign.leading = item.leading
                    item = assign
            node.items.append(item)
            sep = self.cur()
            self._absorb(item, sep)
            if sep.kind == "SEMI":
                self.eat()
                self._trailing_after_sep(item)
                if self.cur().kind == "RBRACKET":  # trailing semicolon
                    node.trailing_semi = True
                    self._absorb(node, self.cur())
                    self.eat()
                    break
                continue
            if sep.kind == "RBRACKET":
                self.eat()
                break
            raise ParseError(
                f"expected ';' or ']', got {sep.kind} {sep.text!r} (line {sep.line})"
            )
        return node
