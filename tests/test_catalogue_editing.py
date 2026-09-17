"""Editing the catalogues, and keeping them as JSON (C1).

A catalogue could be browsed and picked from, and changed only by editing a text file whose
format had nowhere to put a space telescope, an SEFD table or anything added later. Now the
managers add, edit and remove, and a catalogue is the same `Sources` or `Telescopes` a project
holds, written whole.

Converting found the reader wrong in two ways, and the shipped catalogues were converted with it
fixed: `$` -- the files' mark for "no name" -- was read as a name, 138 times, and a name with a
space in it was split into two names. `tests/fixtures/catalogs` keeps the `.dat` files as they
were, so that what was shipped stays checked against what it was converted from.
"""
import json
from pathlib import Path

import pytest

from pastrocore.paths import shipped_catalog, user_catalogs
from pastrocore.utils.catalogmanager import CatalogManager

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "catalogs"

#: Each shipped catalogue: the file stem, and which kind of catalogue it is.
SHIPPED = [("sources", "sources"), ("grav_lenses", "sources"), ("telescopes", "telescopes")]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A user directory of the test's own, so nothing is written into the real one."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))
    return tmp_path


@pytest.fixture
def core(project):
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    return ScheduleManipulator(project)


def own_copy(tmp_path, stem="sources"):
    """A catalogue of the user's own: the shipped one, copied where it may be written."""
    path = tmp_path / f"own_{stem}.json"
    path.write_text(shipped_catalog(f"{stem}.json").read_text(encoding="utf-8"), encoding="utf-8")
    return path


# --- the shipped catalogues, converted ------------------------------------------------------------

@pytest.mark.parametrize("stem,kind", SHIPPED)
def test_a_shipped_catalogue_reads_back_equal_to_the_dat_it_was_converted_from(stem, kind):
    """The exit criterion's last sentence, held rather than checked once."""
    dat = FIXTURES / f"{stem}.dat"
    from_dat, shipped = CatalogManager(), CatalogManager()
    from_dat.load(kind, str(dat))
    shipped.load(kind, str(shipped_catalog(f"{stem}.json")))

    lines = [line for line in dat.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.startswith("#")]
    assert len(shipped.catalog(kind)) == len(lines), "a line of the .dat did not reach the JSON"
    assert shipped.catalog(kind).to_dict() == from_dat.catalog(kind).to_dict()


def test_the_dat_files_are_not_shipped_any_more():
    """Two copies of one catalogue is one to edit and one that goes stale."""
    assert not list(shipped_catalog("sources.json").parent.glob("*.dat"))


def test_a_dollar_is_no_name(tmp_path):
    """`$` is how the files say there is no alternative name, and it was read as one."""
    catalog = tmp_path / "sources.dat"
    catalog.write_text("0003-003\t0003-003\t$\t00:06:22.1399\t-00:04:38.4575\n", encoding="utf-8")

    source = CatalogManager(source_file=str(catalog)).source_catalog.get("0003-003")

    assert source.alt_name is None
    shipped = CatalogManager(source_file=str(shipped_catalog("sources.json")))
    assert not [s.name for s in shipped.source_catalog.get_items() if "$" in (s.alt_name, s.name_J2000)]


def test_a_name_with_a_space_is_one_name(tmp_path):
    """The names are separated by tabs. Split on every space, `Mrk 1419` was a source called
    `Mrk` whose J2000 name was `1419` -- and here the position is separated by spaces, not a tab."""
    catalog = tmp_path / "sources.dat"
    catalog.write_text("Mrk 1419\tMrk 1419\tMrk 1419\t09:40:36.4      +03:34:37.0\n"
                       "G000.0+00.0 KPGT-1 $ 17:45:44.202 -28:59:56.498\n", encoding="utf-8")

    catalogs = CatalogManager(source_file=str(catalog))
    spaced = catalogs.source_catalog.get("Mrk 1419")
    plain = catalogs.source_catalog.get("G000.0+00.0")

    assert (spaced.name_J2000, spaced.alt_name) == ("Mrk 1419", "Mrk 1419")
    assert (spaced.ra_h, spaced.ra_m, spaced.ra_s, spaced.de_d) == (9.0, 40.0, 36.4, 3.0)
    assert (plain.name_J2000, plain.alt_name) == ("KPGT-1", None), "a line with no tab still reads"
    assert CatalogManager(source_file=str(shipped_catalog("sources.json"))).get_source("Mrk 1419")


# --- a catalogue is the container, whole ---------------------------------------------------------

def test_a_catalogue_keeps_whatever_a_telescope_has(tmp_path, core):
    """What the `.dat` format had nowhere to put: a spacecraft, a table, a pointing limit."""
    from pastrocore.base.spacetelescope import SpaceTelescope
    from pastrocore.base.telescope import Telescope

    catalogs = CatalogManager()
    catalogs.telescope_catalog.add(Telescope(code="AA", name="Alpha", x=1.0, y=2.0, z=3.0,
                                             diameter=32.0, sefd_table=[(4800.0, 5200.0, 350.0)],
                                             elevation_range=(7.0, 88.0)))
    catalogs.telescope_catalog.add(SpaceTelescope(code="RA", name="RadioAstron"))
    path = catalogs.save("telescopes", str(tmp_path / "mine.json"), core)

    read = CatalogManager(telescope_file=path)

    assert read.telescope_catalog.to_dict() == catalogs.telescope_catalog.to_dict()
    assert isinstance(read.telescope_catalog.get("RadioAstron"), SpaceTelescope)
    assert read.telescope_catalog.get("Alpha").sefd_table == [(4800.0, 5200.0, 350.0)]


def test_a_file_of_the_other_kind_is_refused_by_name():
    """Read field for field it would be an empty catalogue, or an error about a coordinate."""
    with pytest.raises(ValueError, match="Telescopes"):
        CatalogManager(source_file=str(shipped_catalog("telescopes.json")))


def test_an_edit_is_unsaved_until_it_is_saved(tmp_path, core):
    from pastrocore.base.sources import Source

    catalogs = CatalogManager(source_file=str(own_copy(tmp_path)))
    assert not catalogs.is_modified("sources"), "a catalogue just read holds nothing unsaved"

    core.configure(catalogs.source_catalog, add=Source(name="J1234+5678", ra_h=12.0))
    assert catalogs.is_modified("sources")

    catalogs.save("sources", catalogs.path("sources"), core)
    assert not catalogs.is_modified("sources")
    assert "J1234+5678" in json.loads(Path(catalogs.path("sources")).read_text(encoding="utf-8"))["items"]
    assert core.journal().entries[-1]["operation"] == "save", "the save was not asked of the orchestrator"


def test_discarding_puts_back_what_the_file_holds(tmp_path, core):
    catalogs = CatalogManager(source_file=str(own_copy(tmp_path)))
    first = catalogs.source_catalog.get_items()[0].name
    core.configure(catalogs.source_catalog, remove=first)

    catalogs.revert("sources")

    assert catalogs.source_catalog.has_item(first)
    assert not catalogs.is_modified("sources")


def test_where_a_catalogue_is_saved(home):
    """Save writes the user's own JSON in place. The shipped catalogue is never written -- an
    upgrade replaces it, and an install may not be writable -- and a `.dat` becomes JSON, so
    both are saved under a name the user chooses, starting somewhere sensible."""
    own = own_copy(home)
    dat = home / "old" / "sources.dat"
    dat.parent.mkdir()
    dat.write_text((FIXTURES / "sources.dat").read_text(encoding="utf-8"), encoding="utf-8")

    shipped = CatalogManager(source_file=str(shipped_catalog("sources.json")))
    assert shipped.save_path("sources") is None
    assert Path(shipped.suggested_path("sources")) == user_catalogs() / "sources.json"

    from_dat = CatalogManager(source_file=str(dat))
    assert from_dat.save_path("sources") is None
    assert Path(from_dat.suggested_path("sources")) == dat.with_suffix(".json")

    assert Path(CatalogManager(source_file=str(own)).save_path("sources")) == own

    assert CatalogManager().save_path("telescopes") is None
    assert Path(CatalogManager().suggested_path("telescopes")) == user_catalogs() / "telescopes.json"


def test_a_setting_naming_a_shipped_dat_is_repaired_once(home, monkeypatch, caplog):
    """Everyone upgrading has the shipped `sources.dat` in their settings, and it is gone. That is
    a leftover, not a choice: corrected in the file, not warned about at every start."""
    import logging

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.paths import settings_file

    monkeypatch.chdir(home)
    PAstroCoreMainWindow._write_settings({
        "sources_catalog_path": str(shipped_catalog("sources.dat")),
        "telescopes_catalog_path": str(shipped_catalog("telescopes.dat"))})

    with caplog.at_level(logging.WARNING):
        settings = PAstroCoreMainWindow.load_settings()

    assert Path(settings["sources_catalog_path"]) == shipped_catalog("sources.json")
    stored = json.loads(settings_file().read_text(encoding="utf-8"))
    assert Path(stored["telescopes_catalog_path"]) == shipped_catalog("telescopes.json")
    assert "is not there" not in caplog.text


# --- the managers ----------------------------------------------------------------------------------

@pytest.fixture
def sources_manager(qt_application, tmp_path, core):
    """The sources manager, on a catalogue of the user's own."""
    from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog

    catalogs = CatalogManager(source_file=str(own_copy(tmp_path)))
    dialog = SourcesCatalogDialog(catalogs, core)
    yield dialog
    dialog.hide()
    dialog.deleteLater()


def shown_names(dialog):
    return [dialog.model.item(row, 0).text() for row in range(dialog.model.rowCount())
            if not dialog.ui.catalogTable.isRowHidden(row)]


@pytest.mark.parametrize("class_name,space", [("SourcesCatalogDialog", False),
                                              ("TelescopesCatalogDialog", True)])
def test_the_manager_edits_and_the_picker_picks(qt_application, core, class_name, space):
    import pastrocore.gui.p_dialog_sources_catalog as sources
    import pastrocore.gui.p_dialog_telescopes_catalog as telescopes

    dialog_class = getattr(sources, class_name, None) or getattr(telescopes, class_name)
    catalogs = CatalogManager(str(shipped_catalog("sources.json")),
                              str(shipped_catalog("telescopes.json")))
    manager = dialog_class(catalogs, core)
    picker = dialog_class(catalogs, core, allow_selection=True)
    try:
        for button in ("addButton", "editButton", "removeButton", "saveButton", "saveAsButton"):
            assert not getattr(manager.ui, button).isHidden(), f"the manager has no {button}"
            assert getattr(picker.ui, button).isHidden(), f"the picker offers {button}"
        assert manager.ui.addSelectedButton.isHidden() and not picker.ui.addSelectedButton.isHidden()
        assert manager.ui.addSpaceButton.isHidden() is not space
    finally:
        manager.deleteLater()
        picker.deleteLater()


def test_a_source_is_added_from_its_editor(sources_manager, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog

    def filled(editor):
        editor.ui.nameEdit.setText("J1234+5678")
        editor.ui.raHEdit.setValue(12.0)
        return QDialog.Accepted

    monkeypatch.setattr(SourceEditorDialog, "exec", filled)
    before = sources_manager.model.rowCount()

    sources_manager.ui.addButton.click()

    catalogue = sources_manager.catalogue()
    assert catalogue.get("J1234+5678").ra_h == 12.0
    assert sources_manager.model.rowCount() == before + 1
    assert sources_manager.isWindowModified(), "the window does not say there are unsaved edits"


def test_an_edit_changes_the_catalogue_and_a_cancelled_one_does_not(sources_manager, monkeypatch):
    """The editor writes into the object it was given before its checks run. Given the catalogue's
    own object, an edit it wrote and then cancelled stayed in the catalogue."""
    from PySide6.QtWidgets import QDialog

    from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog

    name = sources_manager.model.item(0, 0).text()
    sources_manager.show_entry(name)

    def cancelled_after_writing(editor):
        editor.ui.altNameEdit.setText("HALF WAY")
        editor.get_source_object()
        return QDialog.Rejected

    monkeypatch.setattr(SourceEditorDialog, "exec", cancelled_after_writing)
    sources_manager.ui.editButton.click()
    assert sources_manager.catalogue().get(name).alt_name != "HALF WAY"
    assert not sources_manager.isWindowModified()

    def edited(editor):
        editor.ui.altNameEdit.setText("EDITED")
        return QDialog.Accepted

    monkeypatch.setattr(SourceEditorDialog, "exec", edited)
    sources_manager.ui.editButton.click()
    assert sources_manager.catalogue().get(name).alt_name == "EDITED"
    assert "EDITED" in [sources_manager.model.item(row, 2).text()
                        for row in range(sources_manager.model.rowCount())]


def test_selected_sources_are_removed_once_asked(sources_manager, monkeypatch):
    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QMessageBox

    names = [sources_manager.model.item(row, 0).text() for row in (0, 1)]
    selection = sources_manager.ui.catalogTable.selectionModel()
    for row in (0, 1):
        selection.select(sources_manager.model.index(row, 0),
                         QItemSelectionModel.Select | QItemSelectionModel.Rows)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    sources_manager.ui.removeButton.click()

    assert not any(sources_manager.catalogue().has_item(name) for name in names)
    assert not set(names) & set(shown_names(sources_manager))


def test_a_search_asks_the_catalogue_nothing(sources_manager, core, monkeypatch):
    """Rebuilding the table on each key pressed asked for every source and both halves of every
    position again: more than a thousand requests a keystroke, all of them in the journal.

    Counted at the orchestrator rather than by the journal's length: the journal is a sliding
    window, and one already full stays the same length however much is asked -- which is how
    this check first passed on the rebuilding version.
    """
    asked = []
    requested = core.inspect
    monkeypatch.setattr(core, "inspect", lambda *args, **kwargs: asked.append(kwargs)
                        or requested(*args, **kwargs))

    sources_manager.ui.search.setText("mrk 14")

    assert shown_names(sources_manager) == ["Mrk 1419"]
    assert not asked, f"a search made {len(asked)} requests"


def test_a_shipped_catalogue_is_saved_under_a_new_name_and_followed(
        qt_application, home, core, monkeypatch):
    """Save on the shipped catalogue asks where, adds `.json` to a name without it, leaves the
    shipped file alone, and says where it went so the settings can follow."""
    from PySide6.QtWidgets import QFileDialog

    from pastrocore.base.sources import Source
    from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog

    shipped_before = shipped_catalog("sources.json").read_bytes()
    catalogs = CatalogManager(source_file=str(shipped_catalog("sources.json")))
    core.configure(catalogs.source_catalog, add=Source(name="J1234+5678"))
    dialog = SourcesCatalogDialog(catalogs, core)
    asked, said = [], []
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda parent, title, start, filter: asked.append(start)
                        or (str(home / "mine"), filter))
    dialog.catalog_saved.connect(lambda kind, path: said.append((kind, path)))
    try:
        dialog.ui.saveButton.click()

        written = home / "mine.json"
        assert asked == [str(user_catalogs() / "sources.json")]
        assert said == [("sources", str(written))]
        assert "J1234+5678" in json.loads(written.read_text(encoding="utf-8"))["items"]
        assert shipped_catalog("sources.json").read_bytes() == shipped_before
        assert not dialog.isWindowModified() and "mine.json" in dialog.windowTitle()
    finally:
        dialog.deleteLater()


def test_the_users_own_catalogue_is_saved_in_place_without_asking(sources_manager, core, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    def asked(*args, **kwargs):
        raise AssertionError("Save asked where, for a catalogue that has its own file")

    monkeypatch.setattr(QFileDialog, "getSaveFileName", asked)
    first = sources_manager.model.item(0, 0).text()
    core.configure(sources_manager.catalogue(), remove=first)

    sources_manager.ui.saveButton.click()

    held = json.loads(Path(sources_manager.catalog_manager.path("sources")).read_text(encoding="utf-8"))
    assert first not in held["items"]


@pytest.mark.parametrize("answer", ["Cancel", "Discard", "Save"])
def test_closing_with_unsaved_edits_asks(sources_manager, core, monkeypatch, answer):
    from PySide6.QtWidgets import QMessageBox

    first = sources_manager.model.item(0, 0).text()
    core.configure(sources_manager.catalogue(), remove=first)
    sources_manager.refresh_title()
    questions = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *args, **kwargs: questions.append(args) or getattr(QMessageBox, answer))
    sources_manager.show()

    sources_manager.ui.closeButton.click()

    assert len(questions) == 1, "closing with unsaved edits did not ask"
    catalogs = sources_manager.catalog_manager
    if answer == "Cancel":
        assert sources_manager.isVisible() and catalogs.is_modified("sources")
        return
    assert not sources_manager.isVisible()
    assert not catalogs.is_modified("sources")
    assert catalogs.catalog("sources").has_item(first) is (answer == "Discard")
    held = json.loads(Path(catalogs.path("sources")).read_text(encoding="utf-8"))
    assert (first in held["items"]) is (answer == "Discard")


def test_the_picker_hands_over_the_entries_chosen(qt_application, core):
    from PySide6.QtCore import QItemSelectionModel

    from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog

    catalogs = CatalogManager(telescope_file=str(shipped_catalog("telescopes.json")))
    picker = TelescopesCatalogDialog(catalogs, core, allow_selection=True)
    handed = []
    picker.telescopes_selected.connect(handed.extend)
    try:
        picker.ui.search.setText("Svetloe")
        row = next(row for row in range(picker.model.rowCount())
                   if not picker.ui.catalogTable.isRowHidden(row))
        picker.ui.catalogTable.selectionModel().select(
            picker.model.index(row, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)

        picker.ui.addSelectedButton.click()

        assert [telescope.name for telescope in handed] == ["Svetloe"]
    finally:
        picker.deleteLater()


def test_the_window_reads_a_saved_catalogue_from_then_on(qt_application, home, project, monkeypatch):
    """A catalogue saved under a new name is what the next start reads."""
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    monkeypatch.chdir(home)
    saved = own_copy(home)
    monkeypatch.setattr(SourcesCatalogDialog, "exec",
                        lambda dialog: dialog.catalog_saved.emit("sources", str(saved)) or 0)
    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    try:
        window.open_source_catalog_manager()

        assert Path(PAstroCoreMainWindow.load_settings()["sources_catalog_path"]) == saved
    finally:
        window.status.close()
        window.close()
        window.deleteLater()
        qt_application.processEvents()
