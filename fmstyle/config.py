"""Style configuration - the machine-readable half of an organisation's
FileMaker guidelines. Defaults implement the Thomas DS style guide
(filemaker_development_style_guide.md, sections 3-4).

Per-function rules: every FileMaker (or custom) function name can get its own
entry under "functions", controlling how that call is laid out:

    "functions": {
        "let":   { "layout": "let",   "multiline": "always" },
        "while": { "layout": "while", "multiline": "always" },
        "case":  { "layout": "pairs" },
        "if":    { "multiline": "always" }
    }

layout:    "args"  - one argument per line (default for any function)
           "pairs" - condition ; result pairs per line (Case-style)
           "let"   - the mandatory Let block shape
           "while" - the mandatory While block shape
           "auto"  - same as "args"
multiline: "auto"   - explode only when the call exceeds the line width
           "always" - always explode, even when it would fit
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

_SIMPLE_KEYS = (
    "width",
    "let_blank_lines",
    "lowercase_keywords",
    "space_before_semicolon",
    "result_name",
    "local_variable_pattern",
)

VALID_LAYOUTS = {"auto", "args", "pairs", "let", "while", "leading"}
VALID_MULTILINE = {"auto", "always"}

DEFAULT_FUNCTIONS = {
    "let": {"layout": "let", "multiline": "always"},
    "while": {"layout": "while", "multiline": "always"},
    "case": {"layout": "pairs"},
}


def _default_functions() -> dict:
    return {name: dict(rule) for name, rule in DEFAULT_FUNCTIONS.items()}


@dataclass
class Style:
    indent: str = "    "
    width: int = 96
    let_blank_lines: bool = True
    lowercase_keywords: bool = True
    space_before_semicolon: bool = True
    result_name: str = "result"
    local_variable_pattern: str = r"^[_a-z][A-Za-z0-9]*$"
    functions: dict = field(default_factory=_default_functions)

    @classmethod
    def from_dict(cls, data: dict) -> "Style":
        known = {f.name for f in fields(cls)} | {"force_multiline", "indent"}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown style option(s): {', '.join(sorted(unknown))}")

        kwargs = {k: data[k] for k in _SIMPLE_KEYS if k in data}
        if "indent" in data:
            v = data["indent"]
            if v == "tab":
                kwargs["indent"] = "\t"
            elif isinstance(v, int):
                kwargs["indent"] = " " * v
            else:
                kwargs["indent"] = v

        functions = _default_functions()
        if "force_multiline" in data:  # legacy shorthand for multiline: always
            for rule in functions.values():
                rule.pop("multiline", None)
            for name in data["force_multiline"]:
                functions.setdefault(name.lower(), {})["multiline"] = "always"
        if "functions" in data:
            for name, rule in data["functions"].items():
                if not isinstance(rule, dict):
                    raise ValueError(f"functions.{name} must be an object")
                bad = set(rule) - {"layout", "multiline"}
                if bad:
                    raise ValueError(f"functions.{name}: unknown key(s) {', '.join(sorted(bad))}")
                if "layout" in rule and rule["layout"] not in VALID_LAYOUTS:
                    raise ValueError(f"functions.{name}.layout must be one of {sorted(VALID_LAYOUTS)}")
                if "multiline" in rule and rule["multiline"] not in VALID_MULTILINE:
                    raise ValueError(f"functions.{name}.multiline must be one of {sorted(VALID_MULTILINE)}")
                functions.setdefault(name.lower(), {}).update(rule)
        kwargs["functions"] = functions

        return cls(**kwargs)

    @classmethod
    def load(cls, path: str | Path) -> "Style":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
