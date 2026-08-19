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
        {"source": "Fee 5¢ Surcharge + Demo 0.4.0 Kit::Bundle"},
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
        # 0.3.0 dimensions: spacing / wrap / comments / keyword_case / lint opt-in
        {
            "source": 'Substitute ( text ; [ "a" ; "b" ] ; [ "c" ; "d" ] )',
            "style": {
                "spacing": {
                    "inside_parens": False,
                    "before_paren": False,
                    "inside_brackets": False,
                    "before_semicolon": False,
                }
            },
        },
        {"source": "1 + 2 * 3 & x", "style": {"spacing": {"around_operators": False}}},
        {
            "source": GUIDE_LET,
            "style": {"spacing": {"inside_parens": False, "before_paren": False}},
        },
        {
            "source": '"aaa" & "bbb" & "ccc" & "ddd"',
            "style": {"wrap": {"operator_position": "trailing"}, "width": 14},
        },
        {
            "source": GUIDE_LET,
            "style": {"wrap": {"operator_position": "trailing"}, "width": 20},
        },
        {
            "source": "Let ( [ x = 1 ; // one\nresult = x ] ; result ) // done",
            "style": {"comments": "above"},
        },
        {"source": "x AND y or NOT z", "style": {"keyword_case": "upper"}},
        {"source": "x AND y or NOT z", "style": {"keyword_case": "preserve"}},
        {"source": "Let ( [ x = 1 ] ; x + 1 )", "style": {"lint": {"let-explicit-result": True}}},
        {"source": "Let ( [ x = 1 ] ; x + 1 )", "style": {"result_name": "output"}},
        {
            "source": "Let ( [ BadName = 1 ; result = BadName ] ; result )",
            "style": {"lint": {"variable-naming": {"pattern": "^[a-z]+$"}}},
        },
        # 1.3.0: decimal_separator (EU comma notation) - format, errors, lint
        {"source": "Case ( VAT_Rate > 0 ; VAT_Rate ; ,21 )"},  # normalize + preserve comma
        {"source": "1 + .5"},  # normalize + preserve period
        {"source": "-,5"},
        {"source": ",234"},  # comma + 3 digits but 0-integer part: unambiguous
        {"source": "x + 1,234"},  # ambiguous under auto -> ERROR
        {"source": "x + 1,234", "style": {"decimal_separator": "comma"}},
        {"source": "x + 1,234,567"},  # grouped -> ERROR
        {"source": "x + 1,234.56"},  # grouped, mixed -> ERROR
        {"source": "x + 1,5", "style": {"decimal_separator": "period"}},  # upgraded msg
        {"source": "Case ( a ; 1, 2 )", "style": {"decimal_separator": "period"}},
        {"source": "Case ( a ; 1, 2 )"},  # auto: bare legacy message
        {"source": "x +\r\n1,234"},  # CRLF: line numbers must agree -> ERROR (line 2)
        {
            "source": "0,21 + 3.142",
            "style": {"lint": {"mixed-decimal-separators": True}},
        },
        {
            "source": "0,21 + 3.142",
            "style": {"decimal_separator": "comma", "lint": {"mixed-decimal-separators": True}},
        },
        {
            "source": "Case ( x > 3.142 ; 0,21 ; ,5 )",
            "style": {"lint": {"mixed-decimal-separators": True}},
        },
        {"source": "0,21 + 1,5", "style": preset_dict("oogi")},  # EU calc through the oogi preset
    ]
)


def main() -> None:
    for case in CASES:
        style = Style.from_dict(case.get("style", {}))
        # Errors are part of the parity contract: both engines must raise the
        # byte-identical message, recorded here as "ERROR: <message>".
        try:
            case["expected"] = format_calc(case["source"], style)
        except Exception as exc:  # noqa: BLE001 - message text is the fixture
            case["expected"] = f"ERROR: {exc}"
        try:
            case["lint"] = [rule for rule, _ in lint_calc(case["source"], style)]
        except Exception as exc:  # noqa: BLE001
            case["lint"] = [f"ERROR: {exc}"]
    out = ROOT / "tests" / "parity_fixtures.json"
    out.write_text(json.dumps(CASES, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(CASES)} cases -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
