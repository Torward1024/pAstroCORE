# cli_request.py
"""One request, typed rather than clicked: `<operation> <address> key=value ...` (L4).

**No new language.** A request is already data -- an operation, the object it is about, and its
attributes -- and this is only that, written on one line:

    inspect  OBS001/sources          get_items
    configure OBS001/sources         deactivate_item=3C273
    compute  project                 method=run  calculations='["uv_coverage"]'  targets='["@OBS001"]'
    save     project                 path=survey.pastro

- **The operation** is one the orchestrator has registered, and nothing else is accepted.
- **The address** names an object the way a person does: `project`, `OBS001`,
  `OBS001/telescopes/ALMA`. The backend resolves it (`inspect(method="locate")`).
- **Each attribute** is `key=value`. A value is JSON when it reads as JSON -- `600`, `true`,
  `["a", "b"]`, `{"item_code": "OBS2"}` -- and text otherwise. `key` alone passes nothing, which is how
  a method with no arguments is named. A text value starting with `@` is an address, and the object
  there is passed: that is how a request names another part of the project.

Everything it checks before sending -- that the operation exists, that a handler or a method is one
the object has -- is asked of the orchestrator, so nothing here is a list to keep in step with the
window. Shared by `pastrocore-cli ask` and `pastrocore-cli shell`.
"""
import difflib
import json
import logging
import math
import shlex
from typing import Any, Dict, List, Tuple

#: What a text value starts with to be read as an address.
REFERENCE = "@"


class Refused(Exception):
    """A request that was not sent, and why -- a mistake to correct rather than a failure."""


def split(line: str) -> List[str]:
    """Split a typed line into words, keeping quoted text together.

    Notes:
        - A backslash is kept as it is: on Windows it is how a path is written, and a shell's
          escape character would have turned `C:\\data\\re03fr.vex` into `C:datare03fr.vex`.
    """
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    return list(lexer)


def value_of(text: str) -> Any:
    """Read one attribute's value: JSON when it is JSON, the text itself otherwise."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def parse(words: List[str]) -> Tuple[str, str, Dict[str, Any]]:
    """Return the operation, the address and the attributes a line of words names.

    Raises:
        Refused: When there is no operation or no address.
    """
    if len(words) < 2:
        raise Refused("Write an operation and what it is about: inspect project get_observations")
    operation, address, pairs = words[0], words[1], words[2:]
    attributes: Dict[str, Any] = {}
    for pair in pairs:
        key, sep, text = pair.partition("=")
        if not key:
            raise Refused(f"'{pair}' names no attribute; write key=value")
        attributes[key] = value_of(text) if sep else None
    return operation, address, attributes


def _root(manipulator):
    return manipulator.get_managing_object()


def locate(manipulator, address: str) -> Any:
    """Return the object at an address, or refuse with what the backend said is there.

    Notes:
        - A misspelt address is expected here, and what the backend says about it is printed as
          the refusal. msb_arch also logs every failed request, which put the same sentence on the
          screen twice -- and in the shell, across the prompt -- so it is quiet for this question.
    """
    framework = logging.getLogger("msb_arch")
    level = framework.level
    framework.setLevel(logging.CRITICAL)
    try:
        answer = manipulator.inspect(obj=_root(manipulator), method="locate", address=address,
                                     raise_on_error=False)
    finally:
        framework.setLevel(level)
    if not answer.ok:
        raise Refused(answer.error)
    return answer.value


def _referenced(manipulator, value: Any) -> Any:
    """Replace every `@address` in a value with the object it names, however deep."""
    if isinstance(value, str) and value.startswith(REFERENCE) and len(value) > 1:
        return locate(manipulator, value[len(REFERENCE):])
    if isinstance(value, list):
        return [_referenced(manipulator, item) for item in value]
    if isinstance(value, dict):
        return {key: _referenced(manipulator, item) for key, item in value.items()}
    return value


def _suggest(wrong: str, offered: List[str]) -> str:
    near = difflib.get_close_matches(wrong, offered, n=1)
    return f" -- did you mean '{near[0]}'?" if near else ""


def check(manipulator, operation: str, address: str, attributes: Dict[str, Any]) -> Any:
    """Refuse a request that cannot work, before it is sent, and return the object it is about.

    Notes:
        - A request that names what the object does not have is not a failure of the request: it
          is a typo, and the useful answer is what was meant. The nearest spelling is offered,
          and what there is.
    """
    described = manipulator.describe_operations()
    if operation not in described:
        raise Refused(f"No operation called '{operation}'{_suggest(operation, list(described))} "
                      f"There is: {', '.join(sorted(described))}")
    target = locate(manipulator, address)

    handler = attributes.get("method")
    offers = manipulator.inspect(obj=_root(manipulator), method="offers", operation=operation,
                                 address=address)
    if handler is not None:
        if handler not in offers["handlers"]:
            raise Refused(f"'{operation}' has no '{handler}'"
                          f"{_suggest(str(handler), list(offers['handlers']))} "
                          f"It has: {', '.join(offers['handlers']) or 'nothing by name'}")
    elif operation in manipulator.CALLING:
        asked = [key for key in attributes if key != "name"]
        if not asked:
            raise Refused(f"Name what to {operation} on {address}: "
                          f"{', '.join(offers['methods'][:10])}"
                          + (" ..." if len(offers["methods"]) > 10 else ""))
        for key in asked:
            if key in offers["methods"]:
                continue
            if operation == "inspect":
                # The object has it, and it is not a read: said as such, since msb_arch would
                # refuse it anyway and "no such method" would be untrue.
                every = manipulator.inspect(obj=_root(manipulator), method="offers",
                                            operation="configure", address=address)["methods"]
                if key in every:
                    raise Refused(f"'{key}' changes {address}, and inspect only reads: "
                                  f"configure {address} {key}=...")
            raise Refused(f"{address} has no method '{key}'{_suggest(key, offers['methods'])} "
                          f"It has: {', '.join(offers['methods'][:10])}"
                          + (" ..." if len(offers["methods"]) > 10 else ""))
    return target


def send(manipulator, words: List[str]):
    """Check a typed request, send it, and return what came back.

    Returns:
        tuple: `(operation, address, target, response)` -- the response as MSB returns it, not
            raised, so a caller prints a failure rather than a traceback.

    Raises:
        Refused: For a request that was not sent.
    """
    operation, address, attributes = parse(words)
    target = check(manipulator, operation, address, attributes)
    attributes = _referenced(manipulator, attributes)
    facade = getattr(manipulator, operation)
    response = facade(obj=target, raise_on_error=False, **attributes)
    return operation, address, target, response


# --- showing an answer ------------------------------------------------------------------------------

def plain(manipulator, value: Any) -> Any:
    """Return an answer as plain data: a part of the project by its address, a table as rows.

    Notes:
        - What `--json` prints, and what the readable form is drawn from. A model object is not
          data a terminal can show, and its address is what a person types to ask about it again.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if hasattr(value, "to_dicts") and hasattr(value, "columns"):         # a results table
        return {"columns": list(value.columns),
                "rows": [plain(manipulator, row) for row in value.to_dicts()]}
    if hasattr(value, "isot"):                                           # a moment
        return value.isot
    if hasattr(value, "to_dict") and hasattr(value, "name"):             # a part of the project
        answer = manipulator.inspect(obj=_root(manipulator), method="address", object=value,
                                     raise_on_error=False)
        return (f"{type(value).__name__} {answer.value}" if answer.ok and answer.value
                else f"{type(value).__name__} {value.name}")
    if isinstance(value, dict):
        return {str(key): plain(manipulator, item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [plain(manipulator, item) for item in value]
    return str(value)


def render(manipulator, value: Any, as_json: bool = False, rows: int = 10) -> str:
    """Return an answer as text: JSON when asked, and something to read otherwise.

    Args:
        manipulator: What to ask for the addresses of parts of the project.
        value: The answer.
        as_json: Print it whole, as JSON, for a script.
        rows: How many rows of a table to show when reading rather than scripting.
    """
    if as_json:
        return json.dumps(plain(manipulator, value), indent=2, ensure_ascii=False)
    if hasattr(value, "to_dicts") and hasattr(value, "height"):
        shown = value.head(rows)
        return (f"{value.height} row(s), {len(value.columns)} column(s)"
                + (f", the first {rows}" if value.height > rows else "") + f"\n{shown}")
    return _readable(plain(manipulator, _abridged(value, rows)), 0) or "done"


def _abridged(value: Any, rows: int) -> Any:
    """Shorten every table in an answer to its size and first rows, however deep it sits.

    Notes:
        - A result comes back as `{"data": <table>, "metadata": {...}}`, and a day of sampling is
          thousands of rows: printed whole it scrolls the question off the screen. `--json` is
          what gives all of it.
    """
    if hasattr(value, "to_dicts") and hasattr(value, "height"):
        return {"rows": value.height, "columns": list(value.columns),
                f"first {min(rows, value.height)}": value.head(rows).to_dicts()}
    if isinstance(value, dict):
        return {key: _abridged(item, rows) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_abridged(item, rows) for item in value]
    return value


def _readable(value: Any, depth: int) -> str:
    pad = "  " * depth
    if isinstance(value, dict):
        if not value:
            return f"{pad}(empty)"
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.append(_readable(item, depth + 1))
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}(none)"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}-")
                lines.append(_readable(item, depth + 1))
            else:
                lines.append(f"{pad}- {_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{_scalar(value)}" if value is not None else ""


def _scalar(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return "(empty)" if not value else json.dumps(value, ensure_ascii=False)
    return "-" if value is None else str(value)
