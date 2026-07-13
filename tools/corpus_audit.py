"""Audit fmstyle against a real solution: every calculation in an
fm-ddr-analyzer SQLite database is run through format_calc.

    python3 tools/corpus_audit.py path/to/solution.db [--functions]

Reports parse coverage (the formatter refuses rather than guesses, so a
failure means "left untouched", never "broken"), the top failure reasons
with samples, and optionally the function-usage inventory (--functions):
which built-in and custom functions the solution actually calls.
"""

from __future__ import annotations

import collections
import pathlib
import re
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fmstyle import FormatSafetyError, LexError, ParseError, format_calc  # noqa: E402

FUNC_RE = re.compile(r"([A-Za-z_#][A-Za-z0-9_.#]*)\s*\(")
NOT_FUNCTIONS = {"if", "and", "or", "not", "xor"}  # keyword false positives


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_functions = "--functions" in sys.argv
    if not args:
        sys.exit(__doc__)
    db_path = args[0]

    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT kind, name, calc_text FROM entities "
        "WHERE calc_text IS NOT NULL AND TRIM(calc_text) != ''"
    ).fetchall()
    custom_names = {
        (r[0] or "").lower()
        for r in con.execute("SELECT name FROM entities WHERE kind='custom_function'")
    }

    ok = 0
    failures: collections.Counter[str] = collections.Counter()
    samples: dict[str, tuple[str, str, str]] = {}
    func_usage: collections.Counter[str] = collections.Counter()

    for kind, name, calc in rows:
        for match in FUNC_RE.finditer(calc):
            fn = match.group(1)
            if fn.lower() not in NOT_FUNCTIONS:
                func_usage[fn] += 1
        # fm_ddr stores "Set Variable/Field" steps as value-calc + "\n" +
        # repetition-calc; strip a trivial trailing repetition before judging
        if kind == "script_step":
            calc = re.sub(r"\n\d+\s*$", "", calc)
        try:
            format_calc(calc)
            ok += 1
        except (LexError, ParseError, FormatSafetyError) as exc:
            reason = re.sub(r"\(line \d+\)", "", str(exc)).strip()
            reason = re.sub(r"'[^']*'|\"[^\"]*\"", "'…'", reason)
            failures[reason] += 1
            samples.setdefault(reason, (kind, name or "?", calc[:160]))

    total = len(rows)
    pct = 100.0 * ok / total if total else 0.0
    print(f"{db_path}: {ok}/{total} calculations format cleanly ({pct:.1f}%)")

    if failures:
        print("\nTop failure reasons:")
        for reason, count in failures.most_common(12):
            kind, name, snippet = samples[reason]
            print(f"  {count:5d}  {reason}")
            print(f"         e.g. [{kind}] {name}: {snippet!r}")

    if show_functions:
        builtins = [(f, c) for f, c in func_usage.most_common() if f.lower() not in custom_names]
        customs = [(f, c) for f, c in func_usage.most_common() if f.lower() in custom_names]
        print(f"\nBuilt-in functions used ({len(builtins)} distinct):")
        for fn, count in builtins[:40]:
            print(f"  {count:6d}  {fn}")
        print(f"\nCustom functions called ({len(customs)} distinct):")
        for fn, count in customs[:40]:
            print(f"  {count:6d}  {fn}")


if __name__ == "__main__":
    main()
