"""Tests: exact style-guide output, idempotence, token safety, lint rules.

Runnable via pytest or directly: python3 tests/test_fmstyle.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fmstyle import Style, format_calc, lint_calc  # noqa: E402
from fmstyle.presets import preset_names, preset_style  # noqa: E402

GUIDE_LET = 'Let ( [ _foo = "" ; result = _foo ] ; result )'

EXPECTED_LET = """Let ( [

	_foo = "" ;

	result = _foo

] ;
	result
)
"""

GUIDE_WHILE = (
    'While ( [ someList = $someList ; limit = ValueCount ( someList ) ; i = 1 ; '
    'result = "" ] ; i ≤ limit ; '
    "[ value = GetValue ( someList ; i ) ; i = i + 1 ] ; result )"
)

EXPECTED_WHILE = """While (
[
	someList = $someList ;
	limit = ValueCount ( someList ) ;
	i = 1 ;
	result = ""
] ;
	i ≤ limit ;
[
	value = GetValue ( someList ; i ) ;
	i = i + 1
] ;
	result
)
"""

SAMPLES = [
    GUIDE_LET,
    GUIDE_WHILE,
    '"a" & "b" & Contacts::First Name',
    'Substitute ( text ; [ "a" ; "b" ] ; [ "c" ; "d" ] )',
    'Case ( score ≥ 90 ; "A" ; score ≥ 80 ; "B" ; "C" )',
    'If ( not IsEmpty ( $$cache ) ; $$cache ; "empty" )',
    'Let ( [ inner = Let ( [ x = 1 ; result = x ] ; result ) ; result = inner ] ; result )',
    '1 + 2 * 3 ^ -4 <> 5 and x ≠ y or a xor b',
    '"escaped \\" quote" & ¶ & ${Weird Field Name!}',
    'GetLayoutObjectAttribute ( "btn" ; "content" )',
    "Invoice Lines::Amount 2 + 1",
    '$$~DISABLE_FLAG or #ResultJSON ( 0 ; Session.Get ( "x" ) ; "" )',
    "Config::WizardStep_g[113] & $var[$i + 1]",
    "Table~X::Field~extra & kStatus.active",
    'Let ( [ trigger = _trigger.lastStep ; result = Case ( a ; b ; ) ] ; result )',
    "${Sale Price} - Fee 5¢ Surcharge",
]


def test_let_matches_style_guide():
    assert format_calc(GUIDE_LET) == EXPECTED_LET


def test_let_from_messy_input():
    messy = 'Let([_foo="";result=_foo];result)'
    assert format_calc(messy) == EXPECTED_LET


def test_while_matches_style_guide():
    assert format_calc(GUIDE_WHILE) == EXPECTED_WHILE


def test_idempotent():
    for src in SAMPLES:
        once = format_calc(src)
        assert format_calc(once) == once, f"not idempotent: {src!r}"


def test_short_expressions_stay_inline():
    assert format_calc('"a" & "b"') == '"a" & "b"\n'
    assert (
        format_calc('Substitute(text;["a";"b"])')
        == 'Substitute ( text ; [ "a" ; "b" ] )\n'
    )


def test_field_names_with_spaces_survive():
    src = 'Contacts::First Name & " " & Contacts::Last Name'
    assert format_calc(src) == src + "\n"


CLARIS_WHILE = """Let (
    [ // Before While loop
        it1 = "a"; // scope note
        it2 = 1; // another note
        out = "1.0 " & it1 & ¶
    ];
    While (
        [ i = 0 ; out = out & "2.0 " & ¶ ];
        // Condition
        i < 2;
        [ i = i + 1 ; it1 = "c" ; out = out & "5." & i & ¶ ];
        out & "6.0 " & ¶
    )
    & "7.0 " & ¶
)"""


def test_inline_comment_stays_on_its_declaration():
    out = format_calc('Let ( [ it1 = "a" ; // scope\nresult = it1 ] ; result )')
    assert 'it1 = "a" ; // scope' in out  # trailing on it1, not floated to result


def test_leading_comment_keeps_expression_inline():
    # own-line comment before an expression: prints above, expression stays inline
    out = format_calc("If ( x ;\n// note\ni < 2 ; false )")
    assert "\t// note\n\ti < 2 ;" in out


def test_claris_while_example():
    out = format_calc(CLARIS_WHILE)
    # inline scope comments land on the right declarations
    assert 'it1 = "a" ; // scope note' in out
    assert "it2 = 1 ; // another note" in out
    # condition comment above, condition inline
    assert "// Condition\n\t\ti < 2 ;" in out
    # while result comment above, result inline
    assert '// After' not in out  # (not in this trimmed variant)
    assert format_calc(out) == out  # idempotent


def test_comments_preserved():
    src = (
        "Let ( [ // init\n"
        '_foo = "" ; /* mid */ result = _foo ] ; result ) // done'
    )
    out = format_calc(src)
    assert "// init" in out
    assert "/* mid */" in out
    assert "// done" in out


def test_keywords_lowercased():
    assert format_calc("x AND y OR NOT z") == "x and y or not z\n"


def test_indent_config():
    assert "\t_foo" in format_calc(GUIDE_LET)  # default is tab
    assert "  _foo" in format_calc(GUIDE_LET, Style(indent="  "))
    assert "    _foo" in format_calc(GUIDE_LET, Style.from_dict({"indent": 4}))


def test_case_explodes_when_long():
    src = (
        'Case ( $status = "open" ; "Openstaand dossier" ; $status = "closed" ; '
        '"Afgesloten dossier" ; $status = "pending" ; "Wachtend op goedkeuring" ; '
        '"Onbekende status" )'
    )
    out = format_calc(src)
    lines = out.splitlines()
    assert lines[0] == "Case ("
    assert lines[1] == '\t$status = "open" ; "Openstaand dossier" ;'
    assert lines[-2] == '\t"Onbekende status"'
    assert lines[-1] == ")"


def test_nested_let_layout():
    src = 'Let ( [ inner = Let ( [ x = 1 ; result = x ] ; result ) ; result = inner ] ; result )'
    out = format_calc(src)
    assert "\tinner =\n" in out
    assert "\t\tLet ( [" in out


def test_function_rule_force_multiline():
    style = Style.from_dict({"functions": {"if": {"multiline": "always"}}})
    assert format_calc("If ( a ; b ; c )", style) == "If (\n\ta ;\n\tb ;\n\tc\n)\n"


def test_function_rule_pairs_layout():
    style = Style.from_dict({"functions": {"choose": {"layout": "pairs", "multiline": "always"}}})
    assert (
        format_calc('Choose ( idx ; "a" ; "b" ; "c" )', style)
        == 'Choose (\n\tidx ; "a" ;\n\t"b" ; "c"\n)\n'
    )


def test_function_rules_do_not_break_defaults():
    style = Style.from_dict({"functions": {"if": {"multiline": "always"}}})
    assert format_calc(GUIDE_LET, style) == EXPECTED_LET


def test_force_multiline_legacy_key():
    style = Style.from_dict({"force_multiline": ["let", "while", "getsummary"]})
    assert (
        format_calc("GetSummary ( Total ; Group )", style)
        == "GetSummary (\n\tTotal ;\n\tGroup\n)\n"
    )


def test_function_rule_validation():
    for bad in (
        {"functions": {"if": {"layout": "banana"}}},
        {"functions": {"if": {"nope": True}}},
        {"functions": {"if": "always"}},
    ):
        try:
            Style.from_dict(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad}")


def test_real_world_names():
    for src in (
        "$$~DISABLETRIGGERS",
        '#ResultJSON ( 0 ; "" ; "" )',
        "Triggers.Disable",
        "$sub.errorCode",
        "Demo 0.4.0 Kit::Bundle",
        "Fee 5¢ Surcharge + 1",
    ):
        assert format_calc(src) == src + "\n"


def test_repetition_reference():
    assert format_calc("Config::WizardStep_g[ 113 ]") == "Config::WizardStep_g[113]\n"
    assert format_calc("$var[$i + 1] & x") == "$var[$i + 1] & x\n"


def test_assignment_value_is_full_expression():
    src = "Let ( [ _applied = not IsEmpty ( x ) ; result = _applied and true ] ; result )"
    out = format_calc(src)
    assert "_applied = not IsEmpty ( x ) ;" in out
    assert "result = _applied and true" in out


def test_trailing_semicolon_preserved():
    assert format_calc('Case ( a ; b ; )') == "Case ( a ; b ; )\n"
    out = format_calc('Let ( [ x = 1 ; ] ; x )')
    assert "\tx = 1 ;" in out  # trailing semi kept on last declaration


def test_comment_only_calc_kept():
    src = "/* Let ( [ x = 1 ] ; x ) */"
    assert format_calc(src) == src


def test_leading_layout():
    style = Style.from_dict({"functions": {"jsonsetelement": {"layout": "leading", "multiline": "always"}}})
    src = 'JSONSetElement ( "" ; [ "foo" ; $bar ; JSONString ] ; [ "s" ; "a" ; JSONString ] )'
    assert format_calc(src, style) == (
        'JSONSetElement ( ""\n'
        '\t; [ "foo" ; $bar ; JSONString ]\n'
        '\t; [ "s" ; "a" ; JSONString ]\n'
        ")\n"
    )


def test_presets():
    assert preset_names() == ["compact", "oogi"]
    assert format_calc(GUIDE_LET, preset_style("oogi")) == EXPECTED_LET
    compact = format_calc(GUIDE_LET, preset_style("compact"))
    assert "\t_foo" in compact and "\n\n" not in compact  # tabs, no blank lines


def test_lint_off_by_default():
    # bare fmstyle has no opinions you didn't give it
    assert lint_calc("Let ( [ x = 1 ] ; x + 1 )") == []


def test_lint_flags_missing_result():
    issues = lint_calc("Let ( [ x = 1 ] ; x + 1 )", preset_style("oogi"))
    rules = [r for r, _ in issues]
    assert rules.count("let-explicit-result") == 2


def test_lint_flags_bad_variable_name():
    issues = lint_calc('Let ( [ FooBar = 1 ; result = FooBar ] ; result )', preset_style("oogi"))
    assert "variable-naming" in [r for r, _ in issues]


def test_lint_rule_opt_in_shorthand():
    style = Style.from_dict({"lint": {"let-explicit-result": True}})
    issues = lint_calc("Let ( [ x = 1 ] ; x + 1 )", style)
    assert [r for r, _ in issues] == ["let-explicit-result", "let-explicit-result"]
    # explicitly disabled rule stays off even with legacy shorthand present
    style = Style.from_dict({"result_name": "result", "lint": {"let-explicit-result": False}})
    assert lint_calc("Let ( [ x = 1 ] ; x + 1 )", style) == []


def test_lint_legacy_keys_enable_rules():
    style = Style.from_dict({"result_name": "output"})
    issues = lint_calc("Let ( [ output = 1 ] ; output )", style)
    assert issues == []
    issues = lint_calc("Let ( [ result = 1 ] ; result )", style)
    assert [r for r, _ in issues] == ["let-explicit-result", "let-explicit-result"]


def test_lint_clean_let_passes():
    assert lint_calc(GUIDE_LET, preset_style("oogi")) == []


def test_spacing_dense():
    style = Style.from_dict({
        "spacing": {
            "inside_parens": False,
            "before_paren": False,
            "inside_brackets": False,
            "before_semicolon": False,
        }
    })
    assert (
        format_calc('Substitute ( text ; [ "a" ; "b" ] )', style)
        == 'Substitute(text; ["a"; "b"])\n'
    )


def test_spacing_around_operators():
    style = Style.from_dict({"spacing": {"around_operators": False}})
    assert format_calc("1 + 2 * 3", style) == "1+2*3\n"
    # word operators keep their space regardless
    assert format_calc("a and b", style) == "a and b\n"


def test_operator_position_trailing():
    style = Style.from_dict({"wrap": {"operator_position": "trailing"}, "width": 14})
    assert format_calc('"aaa" & "bbb" & "ccc"', style) == '"aaa" &\n"bbb" &\n"ccc"\n'


def test_comments_above():
    style = Style.from_dict({"comments": "above"})
    out = format_calc("Let ( [ x = 1 ; // one\nresult = x ] ; result )", style)
    assert "\t// one\n\tx = 1 ;" in out
    assert format_calc(out, style) == out  # idempotent


def test_keyword_case():
    assert format_calc("x AND y", Style.from_dict({"keyword_case": "upper"})) == "x AND y\n"
    assert format_calc("x and y", Style.from_dict({"keyword_case": "upper"})) == "x AND y\n"
    assert format_calc("x AND y", Style.from_dict({"keyword_case": "preserve"})) == "x AND y\n"
    assert format_calc("x AND y", Style.from_dict({"lowercase_keywords": True})) == "x and y\n"


def test_init_writes_preset():
    import json
    import os
    import shutil
    import tempfile

    from fmstyle.cli import main
    from fmstyle.presets import preset_dict

    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        os.chdir(d)
        assert main(["init", "--preset", "oogi"]) == 0
        assert json.loads(open("fmstyle.json").read()) == preset_dict("oogi")
        assert main(["init", "--preset", "oogi"]) == 1  # refuses to clobber
        assert main(["init", "--preset", "oogi", "--force"]) == 0  # --force overwrites
        assert main(["init"]) == 1  # still refuses without --force
        assert main(["init", "--force"]) == 0  # empty defaults file
        assert json.loads(open("fmstyle.json").read()) == {}
    finally:
        os.chdir(cwd)
        shutil.rmtree(d, ignore_errors=True)


def _lex_error(source, style=None):
    from fmstyle.lexer import LexError

    try:
        format_calc(source, style)
    except LexError as exc:
        return str(exc)
    raise AssertionError(f"expected LexError for {source!r}")


def test_decimal_separator_round_trips():
    # EU stays EU, US stays US; each is idempotent
    eu = format_calc("Case ( VAT_Rate > 0 ; VAT_Rate ; 0,21 )")
    assert "0,21" in eu and format_calc(eu) == eu
    us = format_calc("Case ( VAT_Rate > 0 ; VAT_Rate ; 0.21 )")
    assert "0.21" in us and format_calc(us) == us


def test_decimal_leading_zero_normalization():
    assert format_calc(",21") == "0,21\n"
    assert format_calc(".21") == "0.21\n"
    assert format_calc("-,5") == "-0,5\n"  # minus is its own OP token
    assert format_calc("0,21") == "0,21\n"  # already normalized: untouched


def test_decimal_ambiguous_under_auto():
    msg = _lex_error("x + 1,234")
    assert msg == (
        "ambiguous number '1,234': 1234 (US) or 1.234 (EU); set "
        'decimal_separator to "comma" or "period" in the style pack (line 1)'
    )
    # unambiguous comma literals pass: leading zero, !=3 decimals, >3-digit int
    for ok in ("0,123", "1,23", "1,2345", "1234,567", ",234"):
        assert format_calc(ok)  # must not raise


def test_decimal_comma_mode_reads_thousands_pattern_as_decimal():
    style = Style.from_dict({"decimal_separator": "comma"})
    assert format_calc("x + 1,234", style) == "x + 1,234\n"


def test_decimal_grouped_numbers_rejected():
    for bad in ("1,234,567", "1,234.56", "1.234,56"):
        msg = _lex_error(f"x + {bad}")
        assert msg == (
            f"grouped number '{bad}' is not valid FileMaker calculation "
            "syntax; remove the thousands separators (line 1)"
        )


def test_decimal_period_mode_stays_legacy_with_better_message():
    style = Style.from_dict({"decimal_separator": "period"})
    assert format_calc("1 + 0.5", style) == "1 + 0.5\n"
    expected = (
        "unexpected ',' in number: decimal_separator is \"period\"; "
        'use "comma" or "auto" for EU notation (line 1)'
    )
    assert _lex_error("x + 1,5", style) == expected
    assert _lex_error("x + ,5", style) == expected
    # digit before the comma also triggers it (argument-separator typo)
    assert _lex_error("Case ( a ; 1, 2 )", style) == expected
    # in auto, a comma that joins no number keeps the bare legacy message
    assert _lex_error("Case ( a ; 1, 2 )") == "unexpected character ',' (line 1)"


def test_decimal_error_line_numbers_with_crlf():
    msg = _lex_error("x +\r\n1,234")
    assert msg.endswith("(line 2)")


def test_mixed_decimal_separators_lint():
    auto = Style.from_dict({"lint": {"mixed-decimal-separators": True}})
    assert lint_calc("0,21 + 3.142", auto) == [
        (
            "mixed-decimal-separators",
            "calculation mixes decimal separators: `0,21` (comma) and `3.142` (period)",
        )
    ]
    assert lint_calc("0,21 + 1,5", auto) == []
    assert lint_calc("0.21 + 1.5", auto) == []
    comma = Style.from_dict(
        {"decimal_separator": "comma", "lint": {"mixed-decimal-separators": True}}
    )
    assert lint_calc("0,21 + 3.142 + 2.718", comma) == [
        ("mixed-decimal-separators", "number `3.142` uses '.' but decimal_separator is \"comma\""),
        ("mixed-decimal-separators", "number `2.718` uses '.' but decimal_separator is \"comma\""),
    ]


def test_decimal_format_and_lint_agree_on_same_input():
    # the regression this guards: format accepting what lint's tokenizer rejects
    style = Style.from_dict(
        {"decimal_separator": "comma", "lint": {"mixed-decimal-separators": True}}
    )
    src = "0,21 + 1,234"
    assert format_calc(src, style) == "0,21 + 1,234\n"
    assert lint_calc(src, style) == []


def test_decimal_integration_normalize_ambiguity_lint():
    # ,5 normalizes, 0,21 passes ambiguity, mixed lint still fires - one source
    style = Style.from_dict({"lint": {"mixed-decimal-separators": True}})
    src = "Case ( x > 3.142 ; 0,21 ; ,5 )"
    out = format_calc(src, style)
    assert "0,5" in out and "0,21" in out and "3.142" in out
    issues = lint_calc(src, style)
    assert [rule for rule, _ in issues] == ["mixed-decimal-separators"]


def test_decimal_separator_config_validation():
    try:
        Style.from_dict({"decimal_separator": "dot"})
    except ValueError as exc:
        assert "decimal_separator" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    # an init-written oogi pack loads back through normal resolution
    from fmstyle.presets import preset_dict

    style = Style.from_dict(preset_dict("oogi"))
    assert style.decimal_separator == "auto"
    assert "mixed-decimal-separators" in style.lint


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
