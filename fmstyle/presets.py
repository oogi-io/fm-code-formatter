"""Named style presets - ready-made style packs.

A preset is just a plain fmstyle.json dict; organisations fork one and version
their own copy. `--preset oogi` (CLI) or the preset picker (web app) loads it;
an explicit --config file overrides preset keys.

Presets should describe a real, adoptable convention, not an invented one. The
long-term goal is a shared "community" preset governed by public suggestions +
voting, so the FileMaker world can converge on one format the way gofmt/prettier
did.
"""

from __future__ import annotations

from .config import Style

PRESETS: dict[str, dict] = {
    "oogi": {
        "description": "OOGI BV FileMaker style - 4-space indent, blank-line Let "
        "blocks, explicit result, leading-semicolon JSONSetElement",
        "style": {
            "indent": 4,
            "width": 96,
            "let_blank_lines": True,
            "lowercase_keywords": True,
            "space_before_semicolon": True,
            "result_name": "result",
            "local_variable_pattern": "^[_a-z][A-Za-z0-9]*$",
            "functions": {
                "let": {"layout": "let", "multiline": "always"},
                "while": {"layout": "while", "multiline": "always"},
                "case": {"layout": "pairs"},
                "jsonsetelement": {"layout": "leading", "multiline": "always"},
            },
        },
    },
    "compact": {
        "description": "Tab indent, compact Let blocks (no blank lines), camelCase "
        "locals - a common alternative to the blank-line style",
        "style": {
            "indent": "tab",
            "width": 96,
            "let_blank_lines": False,
            "lowercase_keywords": True,
            "space_before_semicolon": True,
            "result_name": "result",
            "local_variable_pattern": "^_?[a-zA-Z][A-Za-z0-9_]*$",
            "functions": {
                "let": {"layout": "let", "multiline": "always"},
                "while": {"layout": "while", "multiline": "always"},
                "case": {"layout": "pairs"},
            },
        },
    },
}


def preset_names() -> list[str]:
    return sorted(PRESETS)


def preset_dict(name: str) -> dict:
    key = name.lower()
    if key not in PRESETS:
        raise KeyError(f"unknown preset {name!r}; available: {', '.join(preset_names())}")
    return PRESETS[key]["style"]


def preset_style(name: str) -> Style:
    return Style.from_dict(preset_dict(name))
