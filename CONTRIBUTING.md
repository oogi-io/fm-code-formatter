# Contributing to fmstyle

Thanks for helping. The one rule that matters most: **there are two engines and
they must stay identical.**

## The two engines

- **Python** (`fmstyle/`) is the reference implementation.
- **JavaScript** is a hand-written port embedded in `fmstyle/web/index.html`,
  between the `/* fmstyle-engine-start */` and `/* fmstyle-engine-end */` markers.

Any change to the lexer, parser, printer, config, or lint rules must be made in
**both**. The test harness enforces byte-for-byte agreement, so a one-sided change
will fail CI.

## Workflow

```bash
# 1. run the Python tests
python3 tests/test_fmstyle.py

# 2. regenerate the parity fixtures from the Python reference
python3 tests/gen_parity_fixtures.py

# 3. run the JS engine (extracted from index.html) against those fixtures
node tests/test_parity.mjs
```

`tests/parity_fixtures.json` is generated — commit it whenever it changes, and CI
will fail if it is stale (i.e. if you changed the engine but did not regenerate).

## Conventions

- Python 3.10+, standard library only. No runtime dependencies.
- The formatter must never change what a calculation computes: every `format`
  re-tokenizes its output and raises `FormatSafetyError` unless the code tokens and
  comments are identical to the input. Keep that guarantee intact.
- Do not commit client data. No real solution schema in examples, tests, or
  fixtures — use invented names (`Contacts::FullName`, `kStatus.active`, …).
- Add a test for every behaviour change, and a parity fixture for anything the web
  app must reproduce.
- **Licensing of contributions:** by submitting a contribution you license it
  under this project's MIT license and additionally grant OOGI BV the right to
  relicense it as part of the project. (Keeps future licensing decisions
  possible without chasing every past contributor.)
