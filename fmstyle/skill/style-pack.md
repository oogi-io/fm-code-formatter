# Authoring a style pack (fmstyle.json)

Instructions for building a team's `fmstyle.json` — written for an AI assistant
doing the authoring, equally usable by a human. The goal: capture how THIS team
formats FileMaker calculations, without imposing anyone else's habits.

## The two halves — keep them apart

1. **Formatting (top level).** Mechanical layout: indent, width, spacing,
   wrapping, comment placement, per-function shapes. Every team has *some*
   answer here and any answer is valid. The formatter enforces it token-safely.
2. **Lint (the `"lint"` section).** Opinionated practice rules — e.g. "a Let
   must end in an explicit `result` variable". These are judgments, not layout.
   **Every rule is opt-in.** Never enable a lint rule the team didn't ask for
   or demonstrate. A team that likes expressions as Let results simply doesn't
   enable `let-explicit-result` — that is a valid style, not a defect.

## The dimension taxonomy

Ask about (or observe) each dimension. `configurable` dimensions go in the
pack; `fixed` dimensions are what the formatter currently emits regardless —
tell the user honestly when their preference is not yet configurable, and do
not improvise keys for it.

| Dimension | Key | Values | Status |
|---|---|---|---|
| Indent character | `indent` | `"tab"`, `4`, `2`, any string | configurable |
| Line width before exploding | `width` | number (default 96) | configurable |
| Blank lines between Let declarations | `let_blank_lines` | true / false | configurable |
| Keyword casing (and/or/not/xor) | `keyword_case` | `"lower"` / `"upper"` / `"preserve"` | configurable |
| Inline comments stay inline or move above | `comments` | `"preserve"` / `"above"` | configurable |
| Wrapped operator at line start or end | `wrap.operator_position` | `"leading"` / `"trailing"` | configurable |
| Space inside call/group parens `( x )` | `spacing.inside_parens` | true / false | configurable |
| Space between name and paren `If (` | `spacing.before_paren` | true / false | configurable |
| Space inside brackets `[ a ; b ]` | `spacing.inside_brackets` | true / false | configurable |
| Space before semicolons `a ; b` | `spacing.before_semicolon` | true / false | configurable |
| Space around symbol operators `a & b` | `spacing.around_operators` | true / false | configurable |
| Per-function shape | `functions.<name>.layout` | `args` / `pairs` / `let` / `while` / `leading` | configurable |
| Per-function explode threshold | `functions.<name>.multiline` | `auto` / `always` | configurable |
| Space after semicolons | — | always one space | fixed |
| Space around `=` in Let assignments | — | always `x = 1` | fixed |
| Closing `)` placement when exploded | — | own line at construct indent | fixed |
| Let/While bracket columns | — | the shapes shown by the layouts | fixed |
| Repetition brackets | — | compact `field[2]` | fixed |
| Function-name casing | — | kept as written | fixed |
| Blank lines outside Let | — | none inserted | fixed |

Lint rules available (each opt-in; `true` = defaults, object = parameters):

| Rule | Checks | Parameters |
|---|---|---|
| `let-explicit-result` | Let defines a final result variable and returns it bare | `result_name` (default `"result"`) |
| `variable-naming` | Let-local names match a pattern | `pattern` (regex) |

## Three ways to form the pack

**A. From a written style guide.** Map each prose rule to a key using the
taxonomy. Rules about layout → top level. Rules about practice ("always name
the result", "locals are camelCase") → `lint`. Prose that maps to no key
(philosophy, naming semantics) stays prose — do not force it into JSON.

**B. From existing code (preferred when samples exist).** Ask for 3–5
representative calculations the team considers well-formatted. Read them
against the taxonomy: tabs or spaces? blank lines in Let? `Name (` or
`Name(`? operators leading or trailing when wrapped? comments inline or
above? explicit result variable — and is that consistent enough to be a rule,
or just a habit? Encode only what you observe; leave the rest at defaults.

**C. Interview.** Ask at most these questions, in this order, then stop:
1. Tabs or spaces (and how many)?
2. Blank lines between Let declarations, or compact?
3. When a long expression wraps, does the `&` end the line or start the next?
4. `If ( x ; y )` or `If(x; y)` — padded or tight?
5. Inline comments after the code, or on their own line above?
6. Any functions that should *always* explode (JSONSetElement is the common
   one — `layout: "leading"` gives it the leading-semicolon shape)?
7. Practice rules, only if they volunteer them: explicit result variable?
   a naming convention for locals?

## The proving loop — a pack is not done until it survives this

1. Draft the pack from A, B, or C.
2. Format the team's own representative calcs with it:
   `fmstyle --config draft.json format their-calc.fmcalc`
3. Show the output next to their original. Differences are either (a) a knob
   set wrong — fix the pack, or (b) a fixed dimension — say so explicitly.
4. Repeat until the team says "that's how we write it".
5. Idempotence and token-safety are automatic; you do not need to verify them.

## Hard rules for the authoring assistant

- **Never invent keys.** The validator rejects unknown options with a clear
  error. A validation error means *fix the pack to the taxonomy*, not work
  around the validator.
- **Never enable lint rules speculatively.** No rules is a perfectly good
  pack. Formatting-only packs are common.
- Start from a preset only if the team asks for one (`fmstyle presets`); a
  `--config` file overrides preset keys.
- Keep the pack minimal: omit keys that equal the defaults, unless the team
  wants them pinned explicitly.
- The pack is versioned in the team's repo, next to their code.

## Worked example

Team says: tabs, compact Lets, trailing `&`, tight parens, comments above,
JSONSetElement always exploded leading-style, and "we insist on an explicit
`result`". That becomes exactly:

```json
{
  "indent": "tab",
  "let_blank_lines": false,
  "wrap": { "operator_position": "trailing" },
  "spacing": { "inside_parens": false, "before_paren": false },
  "comments": "above",
  "functions": {
    "jsonsetelement": { "layout": "leading", "multiline": "always" }
  },
  "lint": {
    "let-explicit-result": true
  }
}
```

Nothing more. Everything unspecified stays at defaults, and no opinion they
didn't state is in the pack.
