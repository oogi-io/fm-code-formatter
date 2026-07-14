# Changelog

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
