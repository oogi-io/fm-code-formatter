"""Generate parity fixtures: Python is the reference implementation.

Writes tests/parity_fixtures.json with {source, style?, expected, lint} cases;
tests/test_parity.mjs replays them through the JS engine embedded in
fmstyle/web/index.html and asserts byte-identical output.

Regenerate after any engine change:  python3 tests/gen_parity_fixtures.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fmstyle import Style, format_calc, lint_calc  # noqa: E402
from fmstyle.presets import preset_dict  # noqa: E402
from test_fmstyle import CLARIS_WHILE, GUIDE_LET, GUIDE_WHILE, SAMPLES  # noqa: E402

LONG_CASE = (
    'Case ( $status = "open" ; "Openstaand dossier" ; $status = "closed" ; '
    '"Afgesloten dossier" ; $status = "pending" ; "Wachtend op goedkeuring" ; '
    '"Onbekende status" )'
)

CASES: list[dict] = (
    [{"source": s} for s in SAMPLES]
    + [
        {"source": 'Let([_foo="";result=_foo];result)'},
        {"source": GUIDE_LET, "style": {"indent": "tab"}},
        {"source": GUIDE_WHILE, "style": {"indent": 2}},
        {"source": LONG_CASE},
        {"source": LONG_CASE, "style": {"width": 60}},
        {
            "source": "Let ( [ // init\n_foo = \"\" ; /* mid */ result = _foo ] ; result ) // done"
        },
        {"source": "Let ( [ x = 1 ] ; x + 1 )"},
        {"source": "Let ( [ FooBar = 1 ; result = FooBar ] ; result )"},
        {"source": "x AND y OR NOT z"},
        {
            "source": GUIDE_LET,
            "style": {"space_before_semicolon": False, "let_blank_lines": False},
        },
        {"source": '"a" & "b"'},
        {"source": "If ( a > 1 and b ≤ 2 ; -a ; not b )"},
        {"source": "If ( a ; b ; c )", "style": {"functions": {"if": {"multiline": "always"}}}},
        {
            "source": 'Choose ( idx ; "a" ; "b" ; "c" )',
            "style": {"functions": {"choose": {"layout": "pairs", "multiline": "always"}}},
        },
        {
            "source": "GetSummary ( Total ; Group )",
            "style": {"force_multiline": ["let", "while", "getsummary"]},
        },
        {
            "source": GUIDE_LET,
            "style": {"functions": {"let": {"multiline": "auto"}}, "width": 200},
        },
        {
            "source": 'Let ( [ longText = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" & '
            '"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" & "cccccccccccccccccccccccc" ; '
            "result = longText ] ; result )"
        },
        # real-world syntax discovered by the DDR corpus audit
        {"source": '$$~DISABLETRIGGERS or #ScriptResultJSON ( 0 ; Session.GetValue ( "x" ) ; "" )'},
        {"source": "Config::WizardStep_g[ 113 ] & $var[$i + 1]"},
        {"source": "Rep 5¢ Commission + Carafe 0.4.0 Bundle::Bundle"},
        {"source": "Case ( a ; b ; )"},
        {"source": "Let ( [ x = 1 ; ] ; x )"},
        {"source": "Let ( [ _applied = not IsEmpty ( x ) ; result = _applied ] ; result )"},
        {"source": "/* commented-out calc */"},
        {"source": CLARIS_WHILE},
        {"source": 'Let ( [ it1 = "a" ; // scope\nresult = it1 ] ; result )'},
        {"source": "If ( x ;\n// note\ni < 2 ; false )"},
        # presets
        {
            "source": 'JSONSetElement ( "" ; [ "foo" ; $bar ; JSONString ] ; [ "s" ; "a" ; JSONString ] )',
            "style": preset_dict("oogi"),
        },
        {"source": GUIDE_LET, "style": preset_dict("oogi")},
        {"source": GUIDE_LET, "style": preset_dict("compact")},
    ]
)


def main() -> None:
    for case in CASES:
        style = Style.from_dict(case.get("style", {}))
        case["expected"] = format_calc(case["source"], style)
        case["lint"] = [rule for rule, _ in lint_calc(case["source"], style)]
    out = ROOT / "tests" / "parity_fixtures.json"
    out.write_text(json.dumps(CASES, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(CASES)} cases -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
