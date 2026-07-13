"""Style configuration - the machine-readable half of a team's FileMaker
guidelines.

A style pack has two honest halves:

- **formatting** (top level) - mechanical layout: indent, width, spacing,
  wrapping, per-function shapes. Every team has *some* answer; any answer is
  valid; the formatter enforces it token-safely.
- **lint** (the `"lint"` section) - opinionated practice rules. Each rule is
  OPT-IN: absent or `false` means it does not run. Bare fmstyle has no
  opinions you didn't give it.

Per-function rules: every FileMaker (or custom) function name can get its own
entry under "functions", controlling how that call is laid out:

    "functions": {
        "let":   { "layout": "let",   "multiline": "always" },
        "while": { "layout": "while", "multiline": "always" },
        "case":  { "layout": "pairs" },
        "if":    { "multiline": "always" }
    }

layout:    "args"    - one argument per line (default for any function)
           "pairs"   - condition ; result pairs per line (Case-style)
           "let"     - the Let block shape
           "while"   - the While block shape
           "leading" - first arg on the header line, leading-semicolon rest
           "auto"    - same as "args"
multiline: "auto"    - explode only when the call exceeds the line width
           "always"  - always explode, even when it would fit

Lint rules (each opt-in; `true` = defaults, object = parameters):

    "lint": {
        "let-explicit-result": { "result_name": "result" },
        "variable-naming":     { "pattern": "^[_a-z][A-Za-z0-9]*$" }
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

VALID_LAYOUTS = {"auto", "args", "pairs", "let", "while", "leading"}
VALID_MULTILINE = {"auto", "always"}
VALID_KEYWORD_CASE = {"lower", "upper", "preserve"}
VALID_COMMENTS = {"preserve", "above"}
VALID_OPERATOR_POSITION = {"leading", "trailing"}

DEFAULT_SPACING = {
    "inside_parens": True,     # Name ( x )  vs  Name (x)
    "before_paren": True,      # Name (      vs  Name(
    "inside_brackets": True,   # [ a ; b ]   vs  [a ; b]
    "before_semicolon": True,  # a ; b       vs  a; b
    "around_operators": True,  # a & b       vs  a&b (word ops keep their space)
}

DEFAULT_FUNCTIONS = {
    "let": {"layout": "let", "multiline": "always"},
    "while": {"layout": "while", "multiline": "always"},
    "case": {"layout": "pairs"},
}

# Rule registry: rule id -> default parameters. A rule runs only when enabled
# in the pack's "lint" section (or via a legacy shorthand key).
LINT_RULES = {
    "let-explicit-result": {"result_name": "result"},
    "variable-naming": {"pattern": r"^[_a-z][A-Za-z0-9]*$"},
}

_TOP_LEVEL_KEYS = {
    "indent", "width", "let_blank_lines", "keyword_case", "comments",
    "spacing", "wrap", "functions", "lint",
    # legacy shorthands (0.2.x packs keep working)
    "lowercase_keywords", "space_before_semicolon",
    "result_name", "local_variable_pattern", "force_multiline",
}


def _default_functions() -> dict:
    return {name: dict(rule) for name, rule in DEFAULT_FUNCTIONS.items()}


def _default_spacing() -> dict:
    return dict(DEFAULT_SPACING)


@dataclass
class Style:
    indent: str = "    "
    width: int = 96
    let_blank_lines: bool = True
    keyword_case: str = "lower"        # lower | upper | preserve
    comments: str = "preserve"         # preserve | above
    operator_position: str = "leading"  # leading | trailing (wrapped operators)
    spacing: dict = field(default_factory=_default_spacing)
    functions: dict = field(default_factory=_default_functions)
    lint: dict = field(default_factory=dict)  # enabled rules only: id -> params

    @classmethod
    def from_dict(cls, data: dict) -> "Style":
        unknown = set(data) - _TOP_LEVEL_KEYS
        if unknown:
            raise ValueError(f"unknown style option(s): {', '.join(sorted(unknown))}")

        kwargs: dict = {}
        for key in ("width", "let_blank_lines"):
            if key in data:
                kwargs[key] = data[key]

        if "indent" in data:
            v = data["indent"]
            if v == "tab":
                kwargs["indent"] = "\t"
            elif isinstance(v, int):
                kwargs["indent"] = " " * v
            else:
                kwargs["indent"] = v

        if "lowercase_keywords" in data:  # legacy
            kwargs["keyword_case"] = "lower" if data["lowercase_keywords"] else "preserve"
        if "keyword_case" in data:
            if data["keyword_case"] not in VALID_KEYWORD_CASE:
                raise ValueError(f"keyword_case must be one of {sorted(VALID_KEYWORD_CASE)}")
            kwargs["keyword_case"] = data["keyword_case"]

        if "comments" in data:
            if data["comments"] not in VALID_COMMENTS:
                raise ValueError(f"comments must be one of {sorted(VALID_COMMENTS)}")
            kwargs["comments"] = data["comments"]

        spacing = _default_spacing()
        if "space_before_semicolon" in data:  # legacy
            spacing["before_semicolon"] = bool(data["space_before_semicolon"])
        if "spacing" in data:
            bad = set(data["spacing"]) - set(DEFAULT_SPACING)
            if bad:
                raise ValueError(f"spacing: unknown key(s) {', '.join(sorted(bad))}")
            for k, v in data["spacing"].items():
                if not isinstance(v, bool):
                    raise ValueError(f"spacing.{k} must be true or false")
            spacing.update(data["spacing"])
        kwargs["spacing"] = spacing

        if "wrap" in data:
            bad = set(data["wrap"]) - {"operator_position"}
            if bad:
                raise ValueError(f"wrap: unknown key(s) {', '.join(sorted(bad))}")
            v = data["wrap"].get("operator_position")
            if v is not None:
                if v not in VALID_OPERATOR_POSITION:
                    raise ValueError(
                        f"wrap.operator_position must be one of {sorted(VALID_OPERATOR_POSITION)}"
                    )
                kwargs["operator_position"] = v

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

        lint: dict = {}
        if "result_name" in data:  # legacy: implies the rule, as 0.2.x behaved
            lint["let-explicit-result"] = {
                **LINT_RULES["let-explicit-result"], "result_name": data["result_name"],
            }
        if "local_variable_pattern" in data:  # legacy
            lint["variable-naming"] = {
                **LINT_RULES["variable-naming"], "pattern": data["local_variable_pattern"],
            }
        if "lint" in data:
            for rule, val in data["lint"].items():
                if rule not in LINT_RULES:
                    raise ValueError(
                        f"unknown lint rule {rule!r}; available: {', '.join(sorted(LINT_RULES))}"
                    )
                if val is False:
                    lint.pop(rule, None)
                    continue
                params = dict(LINT_RULES[rule])
                if val is True:
                    pass
                elif isinstance(val, dict):
                    bad = set(val) - set(params)
                    if bad:
                        raise ValueError(f"lint.{rule}: unknown key(s) {', '.join(sorted(bad))}")
                    params.update(val)
                else:
                    raise ValueError(f"lint.{rule} must be true, false, or an object")
                lint[rule] = params
        kwargs["lint"] = lint

        return cls(**kwargs)

    @classmethod
    def load(cls, path: str | Path) -> "Style":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
