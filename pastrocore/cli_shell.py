# cli_shell.py
"""`pastrocore-cli shell`: one project open, and requests typed one after another (L4).

Every line is what `pastrocore-cli ask` takes after the project -- `<operation> <address>
key=value` -- so there is nothing to learn twice, and a line that works here works in a script.
Three words are the shell's own: `help`, and `exit` or `quit`.

Tab completes what the orchestrator says there is: the operations, the addresses one level at a
time, a handler after `method=`, the methods an object has for `inspect` and `configure`, the
keys a handler reads, and an address after `=@`. Nothing is listed here.

**Nothing is saved until asked.** A request that changes the project marks it changed; `save
project` writes it -- to where it was opened from when no `path` is given -- and leaving with changes
not saved asks first. What was asked is recorded, so `export project method=journal path=...` writes
the session, and `pastrocore-cli replay` runs it again: a script is a session file.
"""
from typing import Callable, Dict, Iterable, List, Optional

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from pastrocore import cli_request

#: The shell's own words. Everything else is a request.
OWN = ("help", "exit", "quit")


class Shell:
    """A project, an orchestrator, and what has not been saved.

    Args:
        manipulator (ScheduleManipulator): Managing the open project, with a journal.
        path (Optional[str]): Where the project was opened from; where `save` writes by default.
    """

    def __init__(self, manipulator, path: Optional[str] = None):
        self.manipulator = manipulator
        self.path = path
        self.changed = False
        self._contents: Dict[str, List[dict]] = {}
        self._offers: Dict[tuple, dict] = {}

    # --- a line ----------------------------------------------------------------------------------

    def handle(self, line: str) -> Optional[str]:
        """Run one typed line and return what to print, or None to leave.

        Notes:
            - A mistake -- an unknown operation, a misspelt address -- is printed, not raised: a
              shell that ended on a typo would lose the session.
        """
        try:
            words = cli_request.split(line)
        except ValueError as e:
            return f"  {e}"
        if not words:
            return ""
        if words[0] in ("exit", "quit"):
            return None
        if words[0] == "help":
            return self.help(words[1:])

        words = self._with_default_path(words)
        try:
            operation, address, target, response = cli_request.send(self.manipulator, words)
        except cli_request.Refused as refusal:
            return f"  {refusal}"
        finally:
            # Whatever was asked may have changed what is there to complete.
            self._contents.clear()
            self._offers.clear()

        if not response.ok:
            return f"  {response.error}"
        if self.manipulator.changes(operation):
            self.changed = True
        if operation == "save" and target is self.manipulator.get_managing_object():
            self.changed = False
            self.path = response.value.get("path", self.path) if isinstance(response.value, dict) \
                else self.path
        return cli_request.render(self.manipulator, response.value)

    def _with_default_path(self, words: List[str]) -> List[str]:
        """`save project` writes to where the project came from, when no `path` is given."""
        if (len(words) >= 2 and words[0] == "save" and self.path
                and not any(word.startswith("path=") for word in words[2:])):
            return words + [f"path={self.path}"]
        return words

    def leave(self, ask: Callable[[str], str]) -> bool:
        """Say whether the shell may close, asking first when there are changes not saved.

        Args:
            ask: Shows a question and returns the answer typed.

        Returns:
            bool: True to close.
        """
        if not self.changed:
            return True
        where = self.path or "a path you give"
        answer = ask(f"The project has changes that are not saved. Save them to {where}? "
                     f"[y]es, [n]o, [c]ancel: ").strip().lower()
        if answer.startswith("c"):
            return False
        if answer.startswith("y"):
            if not self.path:
                print("  No path to save to: save project path=...")
                return False
            said = self.handle("save project")
            print(said)
            return not self.changed
        return True

    # --- help ------------------------------------------------------------------------------------

    def help(self, words: List[str]) -> str:
        """What can be asked: every operation, one of them, or one of them of one object."""
        described = self.manipulator.describe_operations()
        if not words:
            lines = ["<operation> <address> key=value ...   help <operation> [address]   exit", ""]
            for operation in sorted(described):
                kind = ("reads" if self.manipulator.reads(operation) else
                        "changes the project" if self.manipulator.changes(operation) else "files")
                handlers = ", ".join(sorted(described[operation])) or "-"
                lines.append(f"  {operation:10} {kind:20} {handlers}")
            lines += ["", "Addresses: project, OBS001, OBS001/sources, OBS001/telescopes/ALMA, "
                          "OBS001/scans/#3",
                      "Values are JSON when they read as JSON, and @address passes the object there."]
            return "\n".join(lines)

        operation, address = words[0], (words[1] if len(words) > 1 else "project")
        answer = self.manipulator.inspect(obj=self.manipulator.get_managing_object(),
                                          method="offers", operation=operation, address=address,
                                          raise_on_error=False)
        if not answer.ok:
            return f"  {answer.error}"
        offers = answer.value
        lines = []
        if offers["methods"]:
            lines.append(f"{operation} {address} <method>[=value]:")
            lines.append("  " + ", ".join(offers["methods"]))
        if offers["handlers"]:
            lines.append(f"{operation} {address} method=<handler> key=value:")
            for name, accepts in offers["handlers"].items():
                lines.append(f"  {name:14} {', '.join(accepts)}")
        return "\n".join(lines) or f"  {operation} takes its attributes as they are"

    # --- completion ------------------------------------------------------------------------------

    def contents(self, address: str) -> List[dict]:
        if address not in self._contents:
            answer = self.manipulator.inspect(obj=self.manipulator.get_managing_object(),
                                              method="contents", address=address,
                                              raise_on_error=False)
            self._contents[address] = answer.value if answer.ok else []
        return self._contents[address]

    def offers(self, operation: str, address: str) -> dict:
        key = (operation, address)
        if key not in self._offers:
            answer = self.manipulator.inspect(obj=self.manipulator.get_managing_object(),
                                              method="offers", operation=operation,
                                              address=address, raise_on_error=False)
            self._offers[key] = answer.value if answer.ok else {"handlers": {}, "methods": []}
        return self._offers[key]


class ShellCompleter(Completer):
    """Completes a line from what the orchestrator says there is."""

    def __init__(self, shell: Shell):
        self.shell = shell

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text_before_cursor
        try:
            words = cli_request.split(text)
        except ValueError:
            words = text.split()
        if not text or text[-1].isspace():
            words.append("")
        position, word = len(words) - 1, words[-1]

        if position == 0:
            operations = sorted(self.shell.manipulator.describe_operations()) + list(OWN)
            yield from _starting(word, operations, "")
        elif words[0] == "help":
            if position == 1:
                yield from _starting(word, sorted(self.shell.manipulator.describe_operations()), "")
            elif position == 2:
                yield from self._addresses(word)
        elif position == 1:
            yield from self._addresses(word)
        else:
            yield from self._attribute(words[0], words[1], words[2:-1], word)

    def _addresses(self, word: str, prefix: str = "") -> Iterable[Completion]:
        parent, slash, fragment = word.rpartition("/")
        at = parent if slash else "project"
        for entry in self.shell.contents(at):
            if entry["segment"].startswith(fragment):
                yield Completion(entry["segment"], start_position=-len(fragment),
                                 display_meta=entry["type"])
        if not slash and "project".startswith(fragment) and not prefix:
            yield Completion("project", start_position=-len(fragment), display_meta="the project")

    def _attribute(self, operation: str, address: str, given: List[str],
                   word: str) -> Iterable[Completion]:
        offers = self.shell.offers(operation, address)
        key, sep, value = word.partition("=")
        chosen = next((pair.partition("=")[2] for pair in given if pair.startswith("method=")), None)

        if sep:
            if key == "method":
                yield from _starting(value, list(offers["handlers"]), "handler")
            elif value.startswith(cli_request.REFERENCE):
                yield from self._addresses(value[len(cli_request.REFERENCE):], prefix="@")
            return

        if chosen is not None:
            accepts = offers["handlers"].get(chosen, [])
            yield from _starting(word, [f"{name}=" for name in accepts], chosen)
            return
        yield from _starting(word, offers["methods"], "method")
        if offers["handlers"]:
            yield from _starting(word, ["method="], "a handler by name")


def _starting(fragment: str, candidates: Iterable[str], meta: str) -> Iterable[Completion]:
    for candidate in candidates:
        if candidate.startswith(fragment):
            yield Completion(candidate, start_position=-len(fragment), display_meta=meta)


def run(manipulator, path: Optional[str], input=None, output=None) -> int:
    """Read lines until the shell is left.

    Args:
        manipulator: Managing the open project.
        path: Where it was opened from.
        input, output: The terminal, by default; a pipe in a test, which is how the loop itself is
            run rather than only the parts it calls.

    Returns:
        int: What to exit with.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    from pastrocore.base.scratch import data_home

    shell = Shell(manipulator, path)
    data_home().mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(data_home() / "shell_history")),
                            completer=ShellCompleter(shell), complete_while_typing=False,
                            input=input, output=output)
    name = manipulator.get_managing_object().name
    print(f"pAstroCORE shell on '{name}'. help lists what can be asked; Tab completes; exit leaves.")
    while True:
        try:
            line = session.prompt(f"{name}> ")
        except KeyboardInterrupt:
            continue
        except EOFError:
            line = "exit"
        said = shell.handle(line)
        if said is None:
            if shell.leave(lambda question: session.prompt(question)):
                return 0
            continue
        if said:
            print(said)
