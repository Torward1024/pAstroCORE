"""Hold a commit message to the house style, before it becomes history.

Usage:
    python tools/check_commit_message.py <file>     check a message in a file
    git log -1 --format=%B | python tools/check_commit_message.py -

Notes:
    - The style was agreed and then broken twice in a row by the hand that wrote it, because
      nothing counted. A subject is 72 characters including its date, a body is 80 words, a
      line is 80 characters, and the subject is followed by a blank line.
"""
import pathlib
import re
import sys

SUBJECT = 72
BODY = 80
WIDTH = 80
DATED = re.compile(r"^\d{2}\.\d{2}\.\d{4} -- \S")


def owed(message):
    """Return what one message owes the style, a line apiece."""
    lines = message.rstrip().splitlines()
    if not lines:
        return ["an empty message"]

    found = []
    subject = lines[0]
    if len(subject) > SUBJECT:
        found.append(f"a subject of {len(subject)} characters")
    if not DATED.match(subject):
        found.append("a subject that does not start `DD.MM.YYYY -- `")
    if not subject.rstrip().endswith((".", ":")):
        found.append("a subject with no full stop")
    if len(lines) > 1 and lines[1].strip():
        found.append("no blank line under the subject")

    body = " ".join(lines[1:]).split()
    if len(body) > BODY:
        found.append(f"a body of {len(body)} words")
    for number, line in enumerate(lines, 1):
        if len(line) > WIDTH:
            found.append(f"line {number} of {len(line)} characters")
    return found


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    where = sys.argv[1]
    message = (sys.stdin.read() if where == "-"
               else pathlib.Path(where).read_text(encoding="utf-8"))
    # What git itself drops: a comment line is not part of the message.
    message = "\n".join(l for l in message.splitlines() if not l.startswith("#"))

    found = owed(message)
    for fault in found:
        print(fault, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
