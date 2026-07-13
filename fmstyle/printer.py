"""Deterministic printer: AST -> formatted FileMaker calculation.

Layout rules follow the configured Style; the defaults implement the style
guide's mandatory Let / While shapes. Anything that fits within the line
width and has no own-line comments is kept inline; Let and While are always
exploded (configurable via Style.force_multiline).
"""

from __future__ import annotations

from .config import Style
from .lexer import KEYWORD_OPS
from .parser import Assign, Bin, Brackets, Call, Literal, Node, Paren, PRECEDENCE, Rep, Unary


class Printer:
    def __init__(self, style: Style | None = None):
        self.style = style or Style()
        self.semi = " ;" if self.style.space_before_semicolon else ";"

    # ------------------------------------------------------------- helpers

    def ind(self, level: int) -> str:
        return self.style.indent * level

    def _op(self, op: str) -> str:
        if op.lower() in KEYWORD_OPS and self.style.lowercase_keywords:
            return op.lower()
        return op

    def _rule(self, name: str) -> dict:
        return self.style.functions.get(name.lower(), {})

    def _forced(self, node: Node) -> bool:
        return (
            isinstance(node, Call)
            and bool(node.args)
            and self._rule(node.name).get("multiline") == "always"
        )

    # ----------------------------------------------------------------- api

    def format(self, node: Node) -> str:
        return "\n".join(self.emit(node, 0)) + "\n"

    def emit(self, node: Node, level: int, prefix: str = "", suffix: str = "") -> list[str]:
        """Emit a node as indented lines. `prefix` is glued to the first body
        line (e.g. "x = "), `suffix` to the last (e.g. " ;")."""
        ind = self.ind(level)
        lines = [ind + c.text for c in node.leading]
        body = self._inline_body(node)
        if (
            body is not None
            and not self._forced(node)
            and len(ind + prefix + body + suffix) <= self.style.width
        ):
            lines.append(ind + prefix + body + suffix)
        else:
            lines.extend(self._multi(node, level, prefix, suffix))
        if node.trailing:
            lines[-1] += " " + " ".join(c.text for c in node.trailing)
        lines.extend(ind + c.text for c in node.post)
        return lines

    # -------------------------------------------------------------- inline

    def _inline(self, node: Node) -> str | None:
        """Inline rendering for a nested node - refuses if it carries any
        comments (those need their own lines)."""
        if node.has_comments():
            return None
        return self._inline_body(node)

    def _inline_body(self, node: Node) -> str | None:
        if isinstance(node, Literal):
            return node.text
        if isinstance(node, Unary):
            inner = self._inline(node.operand)
            if inner is None:
                return None
            op = self._op(node.op)
            return f"{op} {inner}" if op.isalpha() else f"{op}{inner}"
        if isinstance(node, Bin):
            left = self._inline(node.left)
            right = self._inline(node.right)
            if left is None or right is None:
                return None
            return f"{left} {self._op(node.op)} {right}"
        if isinstance(node, Paren):
            inner = self._inline(node.inner)
            return None if inner is None else f"( {inner} )"
        if isinstance(node, Rep):
            if node.target.has_comments():
                return None
            index = self._inline(node.index)
            return None if index is None else f"{node.target.text}[{index}]"
        if isinstance(node, Assign):
            if node.target.has_comments():
                return None
            value = self._inline(node.value)
            return None if value is None else f"{node.target.text} = {value}"
        if isinstance(node, Brackets):
            parts = [self._inline(x) for x in node.items]
            if any(p is None for p in parts):
                return None
            join = self.semi + " "
            tail = self.semi if node.trailing_semi else ""
            return "[ " + join.join(parts) + tail + " ]" if parts else "[ ]"
        if isinstance(node, Call):
            if self._forced(node):
                return None
            parts = [self._inline(a) for a in node.args]
            if any(p is None for p in parts):
                return None
            join = self.semi + " "
            tail = self.semi if node.trailing_semi else ""
            return f"{node.name} ( {join.join(parts)}{tail} )" if parts else f"{node.name} ( )"
        raise TypeError(f"unknown node {type(node).__name__}")

    # ----------------------------------------------------------- multiline

    def _multi(self, node: Node, level: int, prefix: str, suffix: str) -> list[str]:
        ind = self.ind(level)

        if isinstance(node, Literal):
            return [ind + prefix + node.text + suffix]

        if isinstance(node, Unary):
            op = self._op(node.op)
            glued = prefix + op + (" " if op.isalpha() else "")
            return self.emit(node.operand, level, prefix=glued, suffix=suffix)

        if isinstance(node, Paren):
            lines = [ind + prefix + "("]
            lines += self.emit(node.inner, level + 1)
            lines.append(ind + ")" + suffix)
            return lines

        if isinstance(node, Rep):
            lines = [ind + c.text for c in node.target.leading]
            lines.append(ind + prefix + node.target.text + "[")
            lines += self.emit(node.index, level + 1)
            lines.append(ind + "]" + suffix)
            return lines

        if isinstance(node, Bin):
            terms: list[tuple[str | None, Node]] = []
            self._flatten(node, terms)
            lines = self.emit(terms[0][1], level, prefix=prefix)
            rest = terms[1:]
            for idx, (op, term) in enumerate(rest):
                last = idx == len(rest) - 1
                lines += self.emit(
                    term, level, prefix=self._op(op) + " ", suffix=suffix if last else ""
                )
            return lines

        if isinstance(node, Assign):
            lines = [ind + c.text for c in node.target.leading]
            head = ind + prefix + node.target.text + " ="
            value = self._inline(node.value)
            if value is not None and len(head + " " + value + suffix) <= self.style.width:
                lines.append(head + " " + value + suffix)
                return lines
            lines.append(head)
            lines += self.emit(node.value, level + 1, suffix=suffix)
            return lines

        if isinstance(node, Brackets):
            lines = [ind + prefix + "["]
            lines += self._bracket_items(node, level + 1, blank=False)
            lines.append(ind + "]" + suffix)
            return lines

        if isinstance(node, Call):
            layout = self._rule(node.name).get("layout", "args")
            if layout == "let" and len(node.args) == 2 and isinstance(node.args[0], Brackets):
                return self._multi_let(node, level, prefix, suffix)
            if (
                layout == "while"
                and len(node.args) == 4
                and isinstance(node.args[0], Brackets)
                and isinstance(node.args[2], Brackets)
            ):
                return self._multi_while(node, level, prefix, suffix)
            if layout == "pairs" and len(node.args) >= 3:
                return self._multi_case(node, level, prefix, suffix)
            if layout == "leading" and len(node.args) >= 2:
                return self._multi_leading(node, level, prefix, suffix)
            return self._multi_call(node, level, prefix, suffix)

        raise TypeError(f"unknown node {type(node).__name__}")

    def _flatten(self, node: Bin, out: list) -> None:
        left = node.left
        if (
            isinstance(left, Bin)
            and not left.has_comments()
            and PRECEDENCE[left.op.lower()] == PRECEDENCE[node.op.lower()]
        ):
            self._flatten(left, out)
        else:
            out.append((None, left))
        out.append((node.op, node.right))

    def _bracket_items(self, node: Brackets, level: int, blank: bool) -> list[str]:
        lines: list[str] = []
        last_sfx = self.semi if node.trailing_semi else ""
        for i, item in enumerate(node.items):
            if blank and i > 0:
                lines.append("")
            sfx = self.semi if i < len(node.items) - 1 else last_sfx
            lines += self.emit(item, level, suffix=sfx)
        return lines

    def _multi_let(self, call: Call, level: int, prefix: str, suffix: str) -> list[str]:
        ind = self.ind(level)
        decls, result = call.args
        blank = self.style.let_blank_lines
        lines = [ind + prefix + call.name + " ( ["]
        lines += [self.ind(level + 1) + c.text for c in decls.leading]
        if blank:
            lines.append("")
        lines += self._bracket_items(decls, level + 1, blank=blank)
        lines += [self.ind(level + 1) + c.text for c in decls.trailing + decls.post]
        if blank:
            lines.append("")
        lines.append(ind + "]" + self.semi)
        lines += self.emit(result, level + 1, suffix=self.semi if call.trailing_semi else "")
        lines.append(ind + ")" + suffix)
        return lines

    def _multi_while(self, call: Call, level: int, prefix: str, suffix: str) -> list[str]:
        ind = self.ind(level)
        init, condition, logic, result = call.args
        lines = [ind + prefix + call.name + " ("]
        for block in (init, logic):
            lines += [self.ind(level + 1) + c.text for c in block.leading]
            lines.append(ind + "[")
            lines += self._bracket_items(block, level + 1, blank=False)
            lines += [self.ind(level + 1) + c.text for c in block.trailing + block.post]
            lines.append(ind + "]" + self.semi)
            if block is init:
                lines += self.emit(condition, level + 1, suffix=self.semi)
        lines += self.emit(result, level + 1, suffix=self.semi if call.trailing_semi else "")
        lines.append(ind + ")" + suffix)
        return lines

    def _multi_case(self, call: Call, level: int, prefix: str, suffix: str) -> list[str]:
        ind = self.ind(level)
        ind1 = self.ind(level + 1)
        args = call.args
        tail = self.semi if call.trailing_semi else ""
        lines = [ind + prefix + call.name + " ("]
        i = 0
        while i < len(args):
            if i == len(args) - 1:  # default value
                lines += self.emit(args[i], level + 1, suffix=tail)
                i += 1
                continue
            cond, value = args[i], args[i + 1]
            more = i + 2 < len(args)
            pair_sfx = self.semi if more else tail
            c = self._inline(cond)
            v = self._inline(value)
            if (
                c is not None
                and v is not None
                and len(ind1 + c + self.semi + " " + v + pair_sfx) <= self.style.width
            ):
                lines.append(ind1 + c + self.semi + " " + v + pair_sfx)
            else:
                lines += self.emit(cond, level + 1, suffix=self.semi)
                lines += self.emit(value, level + 1, suffix=pair_sfx)
            i += 2
        lines.append(ind + ")" + suffix)
        return lines

    def _multi_leading(self, call: Call, level: int, prefix: str, suffix: str) -> list[str]:
        """First argument on the header line, then leading-semicolon lines
        (the style guide's JSONSetElement shape)."""
        ind = self.ind(level)
        first = call.args[0]
        head = self._inline(first)
        if head is not None and len(ind + prefix + call.name + " ( " + head) <= self.style.width:
            lines = [ind + prefix + call.name + " ( " + head]
        else:
            lines = self.emit(first, level, prefix=prefix + call.name + " ( ")
        rest = call.args[1:]
        for i, arg in enumerate(rest):
            sfx = self.semi if call.trailing_semi and i == len(rest) - 1 else ""
            lines += self.emit(arg, level + 1, prefix="; ", suffix=sfx)
        lines.append(ind + ")" + suffix)
        return lines

    def _multi_call(self, call: Call, level: int, prefix: str, suffix: str) -> list[str]:
        ind = self.ind(level)
        last_sfx = self.semi if call.trailing_semi else ""
        lines = [ind + prefix + call.name + " ("]
        for i, arg in enumerate(call.args):
            sfx = self.semi if i < len(call.args) - 1 else last_sfx
            lines += self.emit(arg, level + 1, suffix=sfx)
        lines.append(ind + ")" + suffix)
        return lines
