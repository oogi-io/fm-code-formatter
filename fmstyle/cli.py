"""fmstyle CLI - format / lint FileMaker calculations.

Exit codes: 0 ok, 1 check/lint findings, 2 input could not be parsed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import json

from . import FormatSafetyError, LexError, ParseError, __version__, format_calc, lint_calc
from .config import Style
from .presets import PRESETS, preset_dict, preset_names

SKILL_RAW_URL = (
    "https://raw.githubusercontent.com/oogi-io/fm-code-formatter/main/fmstyle/skill/SKILL.md"
)


def cmd_install_skill(args) -> int:
    """Install the fmstyle Claude Code skill, or check its freshness.

    --check   compare the installed skill against the one shipped with this
              fmstyle version (offline). 0 = up to date, 1 = differs, 2 = absent.
    --remote  compare against GitHub main instead (network).
    Neither flag: (re)install the packaged skill.
    """
    import hashlib
    import shutil

    src_dir = Path(__file__).resolve().parent / "skill"
    src_files = sorted(src_dir.glob("*.md"))
    dest_dir = Path("~/.claude/skills/fmstyle").expanduser()

    def digest(parts: list[bytes]) -> str:
        h = hashlib.sha256()
        for part in parts:
            h.update(part)
        return h.hexdigest()[:12]

    if args.check or args.remote:
        if not (dest_dir / "SKILL.md").exists():
            print(f"fmstyle skill is not installed ({dest_dir} missing). Run: fmstyle install-skill")
            return 2
        if args.remote:
            import urllib.request

            try:
                ref = [urllib.request.urlopen(SKILL_RAW_URL, timeout=10).read()]
            except Exception as exc:  # noqa: BLE001 - offline is fine, just report
                print(f"Could not fetch {SKILL_RAW_URL}: {exc}")
                return 2
            installed = [(dest_dir / "SKILL.md").read_bytes()]
            ref_label = "GitHub main (SKILL.md)"
            hint = "pipx upgrade fmstyle (or git pull), then: fmstyle install-skill"
        else:
            installed = [
                (dest_dir / f.name).read_bytes() if (dest_dir / f.name).exists() else b""
                for f in src_files
            ]
            ref = [f.read_bytes() for f in src_files]
            ref_label = f"the skill shipped with fmstyle {__version__}"
            hint = "run: fmstyle install-skill"
        if digest(installed) == digest(ref):
            print(f"fmstyle skill is up to date with {ref_label}.")
            return 0
        print(
            f"fmstyle skill DIFFERS from {ref_label} "
            f"(installed {digest(installed)}, reference {digest(ref)}). To update: {hint}"
        )
        return 1

    dest_dir.mkdir(parents=True, exist_ok=True)
    for f in src_files:
        shutil.copy(f, dest_dir / f.name)
    print(f"Installed the 'fmstyle' skill (fmstyle {__version__}) -> {dest_dir}")
    print("Claude Code can now format FileMaker calculations from any directory -")
    print("just write or paste a calc, or ask to format one.")
    print("Freshness check anytime: fmstyle install-skill --check (or --remote for GitHub main)")
    return 0


def _load_style(config: str | None, preset: str | None) -> Style:
    base = dict(preset_dict(preset)) if preset else {}
    path = Path(config) if config else Path("fmstyle.json")
    if config or (not preset and path.exists()):
        data = json.loads(path.read_text(encoding="utf-8"))
        functions = {**base.get("functions", {}), **data.get("functions", {})}
        base.update(data)
        if functions:
            base["functions"] = functions
    return Style.from_dict(base) if base else Style()


def _read_sources(paths: list[str]) -> list[tuple[str, str]]:
    if not paths or paths == ["-"]:
        return [("<stdin>", sys.stdin.read())]
    return [(p, Path(p).read_text(encoding="utf-8")) for p in paths]


def _banner() -> str:
    """One-line brand header: indent glyph + two-tone wordmark.
    Color only on a real terminal (and honor NO_COLOR); plain text otherwise."""
    import os
    if sys.stderr.isatty() and not os.environ.get("NO_COLOR"):
        b = "\033[1m"; a = "\033[38;5;75m"; d = "\033[38;5;244m"; r = "\033[0m"
        return f"{a}≡{r} {b}{a}fm{r}{b}style{r} {d}{__version__}{r}  FileMaker calculation formatter"
    return f"≡ fmstyle {__version__}  FileMaker calculation formatter"


_WORDMARK = [
    '    ____               __        __   ',
    '   / __/___ ___  _____/ /___  __/ /__ ',
    '  / /_/ __ `__ \\/ ___/ __/ / / / / _ \\',
    ' / __/ / / / / (__  ) /_/ /_/ / /  __/',
    '/_/ /_/ /_/ /_/____/\\__/\\__, /_/\\___/ ',
    '                       /____/         ',
]
# top-to-bottom blue gradient (matches the ≡ accent 38;5;75)
_WORD_GRAD = ("38;5;117", "38;5;111", "38;5;75", "38;5;69", "38;5;68", "38;5;33")


def _splash(stream=None) -> None:
    """Neofetch-style splash for bare `fmstyle`: blue wordmark + a live summary
    of presets, the resolved style pack, and skill state. Color only on a real
    terminal (honor NO_COLOR); plain text otherwise, so a pipe stays clean."""
    import os
    import platform
    if stream is None:
        stream = sys.stdout
    on = stream.isatty() and not os.environ.get("NO_COLOR")
    def c(code: str) -> str: return f"\033[{code}m" if on else ""
    def bg(n: int) -> str: return f"\033[48;5;{n}m" if on else ""
    GLOW = c("38;5;39"); LBL = c("1;38;5;75"); VAL = c("38;5;253")
    DIM = c("38;5;244"); R = c("0")

    out = [""]
    for i, line in enumerate(_WORDMARK):
        out.append(f"  {c(_WORD_GRAD[i])}{line}{R}")
    out.append(f"\n  {GLOW}≡{R} {DIM}v{__version__}{R}")
    out.append(f"  {DIM}{'─' * len(_WORDMARK[1])}{R}")

    def kv(k: str, v: str) -> None: out.append(f"  {LBL}{k:<9}{R}{VAL}{v}{R}")
    _os = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(
        platform.system(), platform.system())
    kv("Engine", "FileMaker calculation formatter")
    kv("Runtime", f"Python {platform.python_version()} · {_os} {platform.machine()}")
    kv("Presets", " · ".join(preset_names()))
    if Path("fmstyle.json").exists():
        kv("Config", "./fmstyle.json")
    else:
        kv("Config", f"no project pack · use {GLOW}--preset oogi{R}")
    try:
        lint = preset_dict("oogi").get("lint") or {}
        n = len([k for k, v in lint.items() if v]) if isinstance(lint, dict) else 0
        kv("Rules", f"oogi: {n} lint rules")
    except KeyError:
        pass
    skill = (Path("~/.claude/skills/fmstyle/SKILL.md").expanduser()).exists()
    kv("Skill", f"{GLOW}installed{R}" if skill else f"run {GLOW}fmstyle install-skill{R}")

    if on:
        out.append("")
        out.append("  " + "".join(f"{bg(x)}  {R} " for x in (17, 19, 25, 26, 33, 75)))
    out.append("")
    print("\n".join(out), file=stream)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="fmstyle",
        description="Deterministic formatter and style checker for FileMaker calculations.",
    )
    ap.add_argument("--version", action="version", version=f"fmstyle {__version__}")
    ap.add_argument("--config", help="path to fmstyle.json (default: ./fmstyle.json if present)")
    ap.add_argument("--preset", help="named style pack (see `fmstyle presets`); --config keys override it")
    sub = ap.add_subparsers(dest="command")

    sub.add_parser("presets", help="list available style presets")

    fmt = sub.add_parser("format", help="format calculation(s) (stdin by default)")
    fmt.add_argument("paths", nargs="*", help="files to format, '-' or empty for stdin")
    fmt.add_argument("-w", "--write", action="store_true", help="rewrite files in place")
    fmt.add_argument("--check", action="store_true", help="exit 1 if any file would change")

    ln = sub.add_parser("lint", help="run guideline rules over calculation(s)")
    ln.add_argument("paths", nargs="*", help="files to lint, '-' or empty for stdin")

    ins = sub.add_parser("install-skill", help="install the Claude Code skill globally (~/.claude/skills)")
    ins.add_argument("--check", action="store_true", help="compare installed skill vs this version's")
    ins.add_argument("--remote", action="store_true", help="compare installed skill vs GitHub main")

    args = ap.parse_args(argv)

    # Bare `fmstyle` (no subcommand): show the splash instead of an argparse error.
    if args.command is None:
        _splash(sys.stdout)
        return 0

    # Brand line on interactive runs; stderr so piped/parsed stdout stays clean
    if sys.stderr.isatty():
        print(_banner(), file=sys.stderr)

    if args.command == "presets":
        for name in preset_names():
            print(f"{name:10s} {PRESETS[name]['description']}")
        return 0

    if args.command == "install-skill":
        return cmd_install_skill(args)

    try:
        style = _load_style(args.config, args.preset)
    except KeyError as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 2
    rc = 0

    if args.command == "lint" and not style.lint:
        print(
            'no lint rules enabled - enable them under "lint" in fmstyle.json '
            "or use a preset (see: fmstyle presets)"
        )
        return 0

    for name, text in _read_sources(args.paths):
        try:
            if args.command == "format":
                out = format_calc(text, style)
                if args.check:
                    if out != text:
                        print(f"would reformat {name}")
                        rc = max(rc, 1)
                elif args.write and name != "<stdin>":
                    if out != text:
                        Path(name).write_text(out, encoding="utf-8")
                        print(f"reformatted {name}")
                else:
                    sys.stdout.write(out)
            else:
                for rule, message in lint_calc(text, style):
                    print(f"{name}: {rule}: {message}")
                    rc = max(rc, 1)
        except (LexError, ParseError, FormatSafetyError) as exc:
            print(f"{name}: error: {exc}", file=sys.stderr)
            rc = 2

    return rc


if __name__ == "__main__":
    sys.exit(main())
