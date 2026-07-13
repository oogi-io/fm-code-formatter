# fmstyle test calculations

Deliberately messy FileMaker calculations for exercising the formatter. Each
file is a single calculation you can paste into the web app or run through the
CLI. They double as a manual smoke test of the tricky cases.

## Run them

```bash
# format one (OOGI house style)
fmstyle --preset oogi format examples/01-claris-while-let.fmcalc

# check they all still parse + are stable
fmstyle --preset oogi format --check examples/*.fmcalc

# see the guideline findings on the intentionally-bad one
fmstyle --preset oogi lint examples/06-lint-violations.fmcalc
```

Or paste any file's contents into the web app (`fmstyle/web/index.html`) and
switch the Preset dropdown between OOGI and Compact to compare house styles.

## What each one tests

| File | Exercises |
|---|---|
| `01-claris-while-let` | The official Claris While/Let example — comments in **every** position (before-loop, initial-vars, condition, logic, result, after-loop), a nested Let-in-While, scope reuse, `¶`. The stress test for comment placement. Note: its outer result is an *expression*, so lint also flags `let-explicit-result`. |
| `02-let-nested-messy` | Fully minified input (no spaces), a nested `Let` inside a `Let`, a `Case` as a variable value, `::` field references, `¶`. Proves the formatter reconstructs structure from a one-liner. |
| `03-case-long` | A long `Case` that must explode into `condition ; result` pairs, with a **trailing semicolon** (valid FileMaker) that is preserved. |
| `04-jsonsetelement` | The leading-semicolon `JSONSetElement` shape (`"leading"` layout in the OOGI preset). |
| `05-real-world-names` | Names the naive grammar chokes on: `$$~DISABLE_FLAG`, `#ResultJSON`, `Triggers.AreDisabled`, `Session.Get`, a repetition `Config::WizardStep_g[113]`, `::` fields. |
| `06-lint-violations` | Intentionally breaks the guidelines: `PascalCase` locals instead of `_camelCase`, no explicit `result`, an inline return. Formats fine; **lint reports 4 findings**. |

Everything here is verified: `01`, `05`'s syntax, the trailing semicolon in `03`,
and the comment placement in `01` are all covered by the test suite
(`tests/test_fmstyle.py`) and the JS↔Python parity fixtures.
