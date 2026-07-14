---
name: fmstyle
description: Format and style-check FileMaker calculations deterministically. Run any calculation (Let, While, Case, If, custom functions, JSONSetElement, plain expressions) through the fmstyle CLI to produce house-style output, and lint it against an organisation's guideline rules. Use whenever you write, edit, paste, or review FileMaker calculation code, when the user asks to format or clean up a calc, or when a project defines an fmstyle.json or a house style. Formatting is token-safe - it never changes what the calculation computes.
---

You format FileMaker calculations with the `fmstyle` CLI. Do not hand-format
calculations or eyeball indentation - the formatter is deterministic, so the
output is identical every time and never changes what the calculation computes.

## When to use this

- You just wrote or edited a FileMaker calculation (a field calc, custom
  function body, auto-enter, script Set Variable/Set Field value, a merge
  expression) - run it through `fmstyle format` before presenting it, so it
  matches the house style exactly instead of approximately.
- The user asks to format, tidy, or standardise a calc.
- The user asks whether a calc follows their guidelines - use `fmstyle lint`.
- A project contains an `fmstyle.json` - that is the org's style pack; use it.

This is the deterministic half of writing FileMaker code with an LLM: you supply
the logic, `fmstyle` supplies the shape. Prompting yourself to "always format
Let like X" is approximate; piping through `fmstyle format` is exact.

## Format

```bash
# from stdin (preferred for a calc you just produced)
printf '%s' 'Let([x=1;result=x];result)' | fmstyle format

# a file
fmstyle format path/to/calc.fmcalc

# in an org's house style: a named preset, or the project's fmstyle.json
fmstyle --preset oogi format calc.fmcalc
fmstyle --config ./fmstyle.json format calc.fmcalc     # auto-used if ./fmstyle.json exists
fmstyle presets                                        # list available presets
```

If `fmstyle` is not on PATH: `pipx install fmstyle` (PyPI), or fall back to
`python3 -m fmstyle.cli` from a checkout of github.com/oogi-io/fm-code-formatter.

## The token-safe guarantee

After formatting, `fmstyle` re-tokenizes the output and refuses (exit 2,
`FormatSafetyError`) unless it is identical to the input in every code token and
comment. So the formatter can never silently change what a calculation does; if
it cannot parse an input it changes nothing and tells you. You can trust the
output without re-reading it for correctness - only for style.

## Lint (guideline rules, beyond layout)

```bash
fmstyle --preset oogi lint calc.fmcalc
```

Reports findings like `let-explicit-result` (a Let must define and return an
explicit `result`, not an inline expression) and `variable-naming` (locals must
match the configured pattern). Exit 1 if there are findings, 0 if clean. Use it
when reviewing someone else's calc or checking your own before handing it over.

## Style packs and presets

A style pack is machine-readable house style - `fmstyle.json` - with two
halves: **formatting** (top level: indent, width, spacing, wrap, comments,
per-function shapes) and **lint** (opinionated practice rules, each opt-in):

```json
{
  "indent": "tab",
  "width": 96,
  "keyword_case": "lower",
  "comments": "preserve",
  "wrap": { "operator_position": "leading" },
  "spacing": { "inside_parens": true, "before_semicolon": true },
  "functions": {
    "let":   { "layout": "let",   "multiline": "always" },
    "case":  { "layout": "pairs" },
    "jsonsetelement": { "layout": "leading", "multiline": "always" }
  },
  "lint": {
    "let-explicit-result": { "result_name": "result" },
    "variable-naming":     { "pattern": "^[_a-z][A-Za-z0-9]*$" }
  }
}
```

With no `lint` section, no practice rules run - bare fmstyle has no opinions
you didn't give it. Per-function `layout` is `args` | `pairs` | `let` |
`while` | `leading`; `multiline` is `auto` or `always`. Built-in presets:
`oogi` (blank-line Let blocks + lint rules) and `compact` (tabs, compact
blocks, no lint). List them with `fmstyle presets`.

## Authoring a style pack for a team

When the user wants to set up their house style ("configure fmstyle for us",
"make our style pack", "our team formats like this"), follow
**style-pack.md in this skill's directory** - it has the full dimension
taxonomy, the interview questions, and the proving loop. The short version:
observe or ask how THEY format (never impose defaults as if they were rules),
encode only what they stated, keep lint rules opt-in, then PROVE the pack by
formatting their own representative calcs with it and iterating until the
output matches how they write.

## What it does NOT do

- Calculation expressions only, not full script steps (`Set Field [ ... ]`
  lines) - those come from SaXML, not the calc grammar.
- It does not rename functions or change casing of function names; it lays out
  what you wrote.
- If it refuses an input (exit 2), report that and leave the calc unchanged -
  do not hand-format around it. An unusual construct that it cannot parse is a
  bug worth reporting, not a reason to bypass the guarantee.

## Refresh

Update this skill after upgrading the package: `fmstyle install-skill`
(`fmstyle install-skill --check` compares the installed copy against the one
shipped with the current version).
