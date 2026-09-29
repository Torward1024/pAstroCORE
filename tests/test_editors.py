"""The forms an entity is edited in: a source, a band, a station, a scan.

What is asserted is that what comes out of a form is what was put into it and what the user
then typed -- nothing rounded on the way through, nothing written before it was accepted, and
nothing asked for and then ignored.
"""
import pytest

pytest.importorskip("PySide6")

from pastrocore.super.schedule_manipulator import ScheduleManipulator


# --- the source editor ------------------------------------------------------------------

def test_a_flux_table_survives_being_opened_and_saved(qt_application):
    """It was shown to two decimals and read back from what was shown, so opening a source and
    pressing Save rewrote its spectrum: 12.345 Jy became 12.35, and anything under 5 mJy became
    0.00, which the form then refused as not positive. The same rounding was found and taken
    out of the coordinate fields of this very dialog."""
    from pastrocore.base.sources import Source
    from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog

    measured = {1666.0: 0.0034, 4996.0: 12.345}
    dialog = SourceEditorDialog(source_obj=Source(name="S", flux_table=dict(measured)))
    try:
        assert dialog.get_source_object().flux_table == measured
    finally:
        dialog.deleteLater()


def test_a_flat_spectrum_is_not_the_same_as_no_spectrum(qt_application):
    """A spectral index of zero is a flat spectrum, which is what most VLBI calibrators have.
    The form read zero as "not given" and stored `None`, and `None` is what stops a flux being
    reached at all outside the frequencies it was measured at."""
    from pastrocore.base.sources import Source
    from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog

    flat = SourceEditorDialog(source_obj=Source(name="FLAT", spectral_index=0.0))
    unknown = SourceEditorDialog(source_obj=Source(name="UNKNOWN", spectral_index=None))
    try:
        assert flat.get_source_object().spectral_index == 0.0, "a flat spectrum was thrown away"
        assert unknown.get_source_object().spectral_index is None, "a spectrum was invented"
    finally:
        flat.deleteLater()
        unknown.deleteLater()


# --- the two station editors ------------------------------------------------------------

def ground(name="TT"):
    from pastrocore.base.telescope import Telescope

    return Telescope(code="AA", name=name, x=1.0, y=2.0, z=3.0, diameter=25.0)


def space(name="SS"):
    from astropy.time import Time

    from pastrocore.base.spacetelescope import SpaceTelescope

    return SpaceTelescope(code="SA", name=name, diameter=10.0, use_kep=True,
                          kepler_elements={"a": 2.0e7, "e": 0.1, "i": 51.0, "raan": 0.0,
                                           "argp": 0.0, "nu": 0.0, "mu": 3.986004418e14,
                                           "epoch": Time("2026-01-01T00:00:00", scale="utc")})


def editor_for(telescope):
    from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
    from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog
    from pastrocore.base.spacetelescope import SpaceTelescope

    if isinstance(telescope, SpaceTelescope):
        return SpaceTelescopeEditorDialog(telescope=telescope)
    return TelescopeEditorDialog(telescope=telescope)


@pytest.mark.parametrize("build", [ground, space], ids=["Telescope", "SpaceTelescope"])
def test_an_edit_the_editor_refuses_never_reaches_the_station(build, qt_application, monkeypatch):
    """It wrote first and checked afterwards. The station a form is handed is the one the
    observation holds, so a code the form itself rejects was already on it: the dialog said no,
    the tab did nothing because nothing was accepted, and the station was called `BAD CODE`
    from then on -- through Cancel, through a save, and into a written schedule."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    said = []
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *arguments, **keywords: said.append(arguments[2])))

    telescope = build()
    was = telescope.get_code()
    dialog = editor_for(telescope)
    try:
        dialog.ui.codeEdit.setReadOnly(False)
        dialog.ui.codeEdit.setText("BAD CODE")
        dialog.accept()

        assert said, "a code with a space in it was taken"
        assert dialog.result() != QDialog.Accepted
        assert telescope.get_code() == was, f"it is called '{telescope.get_code()}' now"
    finally:
        dialog.deleteLater()


@pytest.mark.parametrize("build", [ground, space], ids=["Telescope", "SpaceTelescope"])
def test_a_range_the_model_accepts_is_not_refused_by_the_form(build, qt_application, monkeypatch):
    """A pointing range runs low to high, and `_rises` reads that as `low <= high`: a mount
    fixed at one elevation is the model's to allow. The forms said `>=` and refused it, which
    is one rule written twice and already saying two things."""
    from PySide6.QtWidgets import QMessageBox

    said = []
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *arguments, **keywords: said.append(arguments[2])))

    dialog = editor_for(build())
    try:
        low, high = (("elevationMinEdit", "elevationMaxEdit")
                     if hasattr(dialog.ui, "elevationMinEdit") else ("pitchMinEdit", "pitchMaxEdit"))
        getattr(dialog.ui, low).setValue(45.0)
        getattr(dialog.ui, high).setValue(45.0)
        dialog.accept()

        assert not said, f"the form refused what the model allows: {said}"
    finally:
        dialog.deleteLater()


# --- the scan editor --------------------------------------------------------------------

@pytest.fixture
def scan_editor(project, qt_application):
    """The scan editor on the fixture observation's first scan."""
    from pastrocore.gui.p_dialog_edit_scan import ScanEditorDialog

    observation = project.get_observations()[0]
    scan = observation.get_scans().get_items()[0]
    dialog = ScanEditorDialog(observation, ScheduleManipulator(project), scan=scan)
    yield dialog, scan
    dialog.deleteLater()


def test_moving_a_scans_start_does_not_change_how_long_it_is(scan_editor):
    """Three fields, two of which are free: moving the start moves the end, and the length
    stays. It recomputed the length from the end instead -- correcting a start by an hour took
    an hour off the scan, and correcting it by more than its length left a scan of one second.
    """
    dialog, scan = scan_editor
    lasted = dialog.ui.durationEdit.text()

    dialog.ui.startTimeEdit.setDateTime(dialog.ui.startTimeEdit.dateTime().addSecs(3600))

    assert dialog.ui.durationEdit.text() == lasted, (
        f"a scan of {lasted} s became one of {dialog.ui.durationEdit.text()} s")
    assert dialog.get_scan_object().duration == scan.duration


def test_a_scan_the_user_unticked_is_saved_inactive(scan_editor):
    """"Active in this observation" was a box a user could tick, and what it said was thrown
    away: the saved value was recomputed from whether the scan *could* be active. Untick it,
    press Save, and the scan comes back active."""
    dialog, _scan = scan_editor
    assert dialog.ui.chk_active.isChecked(), "this scan can be active, so the box should be on"

    dialog.ui.chk_active.setChecked(False)

    assert dialog.get_scan_object().isactive is False, "the box was asked and then ignored"


def test_a_scan_that_cannot_be_active_cannot_be_ticked(scan_editor):
    """The other half: the box may not offer what the model would refuse. A scan with no
    telescope is not activatable, and `activate_scan` says so -- the form should not let it be
    ticked in the first place."""
    dialog, _scan = scan_editor
    dialog.clear_all_telescopes()

    assert not dialog.ui.chk_active.isChecked(), "it is ticked with no telescope selected"
    assert not dialog.ui.chk_active.isEnabled(), "and it can still be ticked"
