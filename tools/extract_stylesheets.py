"""Collect every stylesheet out of the forms into one file (G1).

224 `styleSheet` properties were scattered across 24 `.ui` forms, which is one place to look per
widget and no place at all to look for "what does this application look like". This takes them
out of the forms and writes one `.qss`, which the application loads onto the `QApplication` at
startup.

**Deliberately by type, not by widget.** A sheet set on one widget applies to that widget; the
same rule at application level applies to every widget of that type. That difference is the
point rather than a hazard to work around: a `QLabel` rule reached 3 labels out of 121 and now
reaches all of them, which is what "one stylesheet" means. Where a type carried several
variants, the one used most often wins -- 34 spin boxes styled one way and 4 another is not a
design, it is what happens when a form is copied.

Some forms therefore change appearance, and that is intended. `tests/test_form_pixels.py` says
which ones, and its reference is regenerated deliberately once they have been looked at.

Run it, then regenerate the forms:

    python tools/extract_stylesheets.py
    python tools/regenerate_ui.py

`--dry-run` reports what it would do and writes nothing.
"""
import argparse
import collections
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).parent.parent
FORMS = ROOT / "pastrocore" / "gui_pyside"
STYLESHEET = ROOT / "pastrocore" / "gui" / "pastrocore.qss"

#: A sheet with no selector of its own is a property list. It sat on a form's top-level widget,
#: where it set the window's background and the font every child inherits -- so at application
#: level it belongs on the windows, not on every widget there is.
TOP_LEVEL_SELECTOR = "QDialog, QMainWindow"

#: Classes whose sheets are the *surface* a form is drawn on rather than the appearance of a
#: control. `QWidget` matches every widget there is -- including every button and every field --
#: so a `QWidget { background-color: ... }` rule emitted after `QPushButton` wins over it and
#: leaves every button flat. They go to the window rule, and the window rule goes first.
SURFACES = ("QDialog", "QMainWindow", "QWidget")

HEADER = """/* pAstroCORE -- one stylesheet, loaded onto the QApplication at startup.
 *
 * Collected out of 24 .ui forms, where 224 separate `styleSheet` properties made "what does
 * this application look like" a question with no answer, and where copying a form was how a
 * second variant of a rule came to exist.
 *
 * Every rule is written against a **type**, so it reaches every widget of that type: that is
 * what makes the application consistent, and it is the difference between this and 224
 * properties. To style one widget differently, give it an object name and add a `#name` rule
 * at the end of this file -- after the type rules, so it wins.
 *
 * Edit this file to change the appearance. Nothing needs regenerating.
 *
 * Generated once by tools/extract_stylesheets.py; maintained by hand from here.
 */
"""


def collect():
    """Return every styled widget in the forms: (form, class, name, sheet)."""
    found = []
    for path in sorted(FORMS.glob("*.ui")):
        for widget in ET.parse(path).iter("widget"):
            for prop in widget.findall("property"):
                if prop.get("name") != "styleSheet":
                    continue
                text = prop.find("string")
                sheet = (text.text or "").strip() if text is not None else ""
                if sheet:
                    found.append((path.name, widget.get("class"), widget.get("name"), sheet))
    return found


def population():
    """Return how many widgets of each class the forms hold, styled or not."""
    counted = collections.Counter()
    for path in sorted(FORMS.glob("*.ui")):
        for widget in ET.parse(path).iter("widget"):
            counted[widget.get("class")] += 1
    return counted


def indent(sheet: str) -> str:
    return "\n".join("    " + line if line.strip() else line for line in sheet.splitlines())


def build(styled, counted):
    """Return the stylesheet text and a row per type saying what was decided."""
    by_class = collections.defaultdict(collections.Counter)
    for _, klass, _, sheet in styled:
        by_class[klass][sheet] += 1

    blocks = [HEADER]
    decisions = []
    bare = collections.Counter()

    for klass in sorted(by_class):
        variants = by_class[klass].most_common()
        chosen, used = variants[0]
        dropped = sum(count for _, count in variants[1:])

        # A sheet carrying no selector is a property list. On a form's top-level widget it is
        # the window's own background and the font its children inherit, and that belongs on
        # the windows. On anything else it is that widget's own appearance, and wrapping it in
        # the type is what carries it across -- sending it to the windows instead would drop it.
        if "{" not in chosen:
            if klass in SURFACES:
                bare[chosen] += used
                decisions.append((klass, counted.get(klass, 0), used, dropped, "window rule"))
                continue
            chosen = f"{klass} {{\n{indent(chosen)}\n}}"

        blocks.append(
            f"/* {klass}: {used} of {counted.get(klass, 0)} carried this"
            + (f"; {dropped} carried something else" if dropped else "")
            + " */\n" + chosen)
        decisions.append((klass, counted.get(klass, 0), used, dropped, "type rule"))

    # First, so every control rule that follows wins over it. Qt resolves two rules of equal
    # specificity by taking the later one, and the surface rule matches every widget there is.
    surface = []
    for sheet, used in bare.most_common():
        surface.append(f"/* the window itself: {used} form(s) carried this. First on purpose --\n"
                       f" * a later rule of equal specificity wins, and this one matches\n"
                       f" * everything. */\n{TOP_LEVEL_SELECTOR} {{\n{indent(sheet)}\n}}")

    return "\n\n".join(blocks[:1] + surface + blocks[1:]) + "\n", decisions


def strip(dry_run: bool) -> int:
    """Remove every styleSheet property from the forms."""
    removed = 0
    for path in sorted(FORMS.glob("*.ui")):
        tree = ET.parse(path)
        touched = False
        for widget in tree.iter("widget"):
            for prop in list(widget.findall("property")):
                if prop.get("name") == "styleSheet":
                    widget.remove(prop)
                    removed += 1
                    touched = True
        if touched and not dry_run:
            path.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                + ET.tostring(tree.getroot(), encoding="unicode") + "\n",
                encoding="utf-8")
    return removed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would happen and write nothing")
    arguments = parser.parse_args(argv)

    styled = collect()
    counted = population()
    text, decisions = build(styled, counted)

    print(f"{len(styled)} stylesheet(s) across {len({form for form, *_ in styled})} form(s)\n")
    print(f"{'class':18} {'in forms':>9} {'styled':>7} {'variants dropped':>17}  rule")
    for klass, total, used, dropped, how in sorted(decisions):
        print(f"{klass:18} {total:9d} {used:7d} {dropped:17d}  {how}")

    if arguments.dry_run:
        print(f"\nwould write {STYLESHEET} ({len(text.splitlines())} lines) "
              f"and strip {strip(dry_run=True)} properties")
        return 0

    STYLESHEET.write_text(text, encoding="utf-8")
    removed = strip(dry_run=False)
    print(f"\nwrote {STYLESHEET} ({len(text.splitlines())} lines)")
    print(f"removed {removed} styleSheet properties from {len(list(FORMS.glob('*.ui')))} forms")
    print("now run: python tools/regenerate_ui.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
