"""Write the command-line reference from the command line itself.

Usage:
    python tools/make_cli_reference.py            write docs/command-line-reference.md
    python tools/make_cli_reference.py --check    fail if the page has drifted

Notes:
    - A reference written by hand is a second place for a flag to live, and the one that goes
      stale: the page cannot know that a command gained an option. This reads `build_parser`,
      which is what `pastrocore-cli` itself is built from.
    - The suite runs `--check`, so adding a flag fails the build until the page is written
      again -- the same ratchet the generated forms are held to.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "command-line-reference.md"

HEAD = """\
# Every command, and what it takes

Generated from `pastrocore-cli` itself by `tools/make_cli_reference.py`, so a command that
gains an option gains a line here. What each one is *for*, with examples, is in
[from a terminal](command-line.md).

"""


def commands(parser):
    """Yield `(name, subparser)` for each command, in the order the parser offers them."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                yield name, sub


def arguments(parser):
    """Yield `(what to type, what it is)` for each argument a command takes."""
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        shown = ", ".join(f"`{o}`" for o in action.option_strings) or f"`{action.dest}`"
        said = (action.help or "").strip()
        if action.choices:
            said += f" One of: {', '.join(str(c) for c in action.choices)}."
        yield shown, said.strip()


def page():
    """Return the whole reference as markdown."""
    sys.path.insert(0, str(ROOT))
    from pastrocore.cli import build_parser

    parser = build_parser()
    out = [HEAD]
    for name, sub in commands(parser):
        out.append(f"## `{name}`\n")
        if sub.description:
            out.append(f"{sub.description.strip()}\n")
        out.append("```\n" + sub.format_usage().strip() + "\n```\n")
        rows = list(arguments(sub))
        if rows:
            out.append("| | |\n| --- | --- |")
            out.extend(f"| {shown} | {said} |" for shown, said in rows)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the page has drifted")
    asked = parser.parse_args()

    written = page()
    if not asked.check:
        PAGE.write_text(written, encoding="utf-8")
        print(PAGE.relative_to(ROOT).as_posix())
        return 0

    held = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""
    if held == written:
        return 0
    print(f"{PAGE.name} has drifted; run tools/make_cli_reference.py", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
