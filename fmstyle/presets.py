"""Named style presets - ready-made style packs.

A preset is just a plain fmstyle.json dict; teams fork one and version their
own copy. `--preset oogi` (CLI) or the preset picker (web app) loads it; an
explicit --config file overrides preset keys.

A preset carries BOTH halves of a pack: formatting choices and - explicitly -
the lint opinions of whoever the preset describes. Presets should describe a
real, adoptable convention. The long-term goal is a shared "community" preset
governed by public suggestions + voting, so the FileMaker world can converge
on one format the way gofmt/prettier did.
"""

from __future__ import annotations

from .config import Style

PRESETS: dict[str, dict] = {
    "oogi": {
        "description": "OOGI BV FileMaker style - tab indent, blank-line Let "
        "blocks, leading-semicolon JSONSetElement; lint: explicit result, "
        "camelCase locals",
        "style": {
            "indent": "tab",
            "width": 96,
            "let_blank_lines": True,
            "keyword_case": "lower",
            "functions": {
                "let": {"layout": "let", "multiline": "always"},
                "while": {"layout": "while", "multiline": "always"},
                "case": {"layout": "pairs"},
                "jsonsetelement": {"layout": "leading", "multiline": "always"},
            },
            "lint": {
                "let-explicit-result": {"result_name": "result"},
                "variable-naming": {"pattern": "^[_a-z][A-Za-z0-9]*$"},
            },
        },
    },
    "compact": {
        "description": "Tab indent, compact Let blocks (no blank lines), no lint "
        "opinions - a common alternative to the blank-line style",
        "style": {
            "indent": "tab",
            "width": 96,
            "let_blank_lines": False,
            "keyword_case": "lower",
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
