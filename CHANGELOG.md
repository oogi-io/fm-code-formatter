# Changelog

## 1.3.0 — 2026-08-19

**EU number notation: new `decimal_separator` style-pack key** (`"period"` |
`"comma"` | `"auto"`, default `"auto"`) — closes
[#1](https://github.com/oogi-io/fm-code-formatter/issues/1).

- **Behavior change:** under the new `"auto"` default, comma decimal literals
  (`0,21` — how every EU-locale FileMaker file writes them) now parse and
  format instead of erroring. Each literal keeps the separator the source
  used: an EU calculation formats to EU notation, a US one to US notation.
- `"comma"` additionally reads `1,234` as one-point-two-three-four; under
  `"auto"` that one pattern (1–3 leading digits, comma, exactly 3 digits) is
  genuinely ambiguous against US thousands notation and fails loudly, naming
  the literal and this setting. `"period"` is the pre-1.3 behavior, with a
  clearer message when a comma touches a digit.
- Thousands-grouped numbers (`1,234,567`, `1,234.56`) are rejected with a
  dedicated message — FileMaker never accepts grouping in calculations.
- Asymmetry, documented deliberately: period literals are never flagged as
  ambiguous (flagging would break every existing `3.142`-style constant).
  A pasted EU-grouped `1.234` therefore passes silently; the new lint rule
  below is the net for that.
- **Normalization (first literal rewrite, value-preserving):** a literal
  starting with its separator gains a leading zero — `,21` → `0,21`,
  `.21` → `0.21`. What the calculation computes never changes.
- **New opt-in lint rule `mixed-decimal-separators`:** flags a calculation
  mixing comma and period literals (under `"auto"`), or any period literal
  when the pack pins `"comma"`. Enabled in the `oogi` preset.
- Error messages are now part of the Python↔JS parity contract, fixture-tested
  byte-for-byte (including line numbers, also across CRLF sources).
- Compatibility: packs that set `decimal_separator` need fmstyle ≥ 1.3.0
  (older versions reject unknown keys by design).

## 1.2.0 — 2026-08 (retro-noted)

- `fmstyle init` scaffolds a project `fmstyle.json` from a preset.

## 1.1.0 — 2026-08 (retro-noted)

- Status splash on bare `fmstyle`: presets, resolved pack, skill state.

## 1.0.2 — 2026-07 (retro-noted)

- Brand mark: R2C1 indent-bars logo, terminal twin `≡`.

## 1.0.1 — 2026-07-14

- **Default indent corrected to tab** (was 4 spaces). The 4-space default was
  a transcription error against the reference style guide, fixed hours after
  1.0.0 before any adoption. Packs that set `indent` explicitly are unaffected;
  `"indent": 4` still gives spaces.
- The `oogi` preset now specifies `"indent": "tab"` accordingly.

## 1.0.0 — 2026-07-14

First stable release — same code as 0.3.1, now with a compatibility promise:

- **The style-pack schema is stable.** Packs written against the documented
  `fmstyle.json` options (formatting top level + opt-in `lint` section) will
  keep working across 1.x releases; 0.2.x legacy keys remain accepted.
- The token-safety guarantee is validated against 136,000+ calculations from
  two independent production solutions.
- Repository is public from this release onward.

## 0.3.1 — 2026-07-13

Housekeeping before the repository goes public.

### Changed
- Example strings in docs/tests replaced with fully synthetic names.
- Authoring guide: acronym-policy recipes for `variable-naming`
  (`clientId` vs `clientID`), explicit scope note (Let locals only), and
  column alignment documented as a fixed (unsupported) dimension.

### Added
- `SECURITY.md` (private reporting contact).
- Trademark notice (FileMaker is a trademark of Claris International Inc.).
- Contribution licensing note in CONTRIBUTING.md.

## 0.3.0 — 2026-07-13

The style pack now describes *your* style instead of assuming one.

### Changed
- **Style packs split into two halves.** Top level = mechanical formatting.
  New `"lint"` section = practice rules, each individually **opt-in**; with no
  `lint` section, no rules run. `result_name` and `local_variable_pattern`
  moved into the rules (`let-explicit-result`, `variable-naming`); the old
  top-level keys still work as legacy shorthands that enable the rule.
- `lowercase_keywords` generalized to `keyword_case`: `"lower"` / `"upper"` /
  `"preserve"` (legacy key still accepted).
- `space_before_semicolon` moved to `spacing.before_semicolon` (legacy key
  still accepted).
- An early third-party-named preset was replaced by the neutral `compact`
  (tab indent, compact Let blocks, no lint opinions).

### Added
- **`spacing`** — `inside_parens` (`Name ( x )` vs `Name (x)`), `before_paren`
  (`If (` vs `If(`), `inside_brackets`, `before_semicolon`, `around_operators`.
- **`wrap.operator_position`** — `"leading"` (`& "b"` starts the wrapped line)
  or `"trailing"` (`"a" &` ends it).
- **`comments`** — `"preserve"` (as authored) or `"above"` (inline comments
  move to their own line above the code).
- **Authoring guide** (`fmstyle/skill/style-pack.md`): the full dimension
  taxonomy (including which dimensions are fixed for now), three authoring
  paths, and the proving loop — written for an AI assistant building a team's
  pack. `fmstyle install-skill` now installs it alongside the skill.
- `fmstyle lint` prints a hint instead of silence when no rules are enabled.

## 0.2.0 — 2026-07-13 [yanked]
- Initial PyPI release: formatter + lint + CLI, client-side web app,
  Claude Code skill, presets. Yanked: an early preset named a third party.
