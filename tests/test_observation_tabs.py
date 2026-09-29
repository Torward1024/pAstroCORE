"""The four tabs an observation is edited in, driven rather than imported.

Frequencies, scans, sources and telescopes. Between them they are 1822 lines and they carry the
same nine operations under four different nouns -- activate one, activate all, deactivate one,
deactivate all, drop the active, drop the inactive, clear, remove, and refresh the table.

This exists **before** those are folded into one place. It is the rule this project learned the
hard way twice: build the check before the change. What is asserted is not appearance but that
each operation reaches the model and that the table then shows what the model holds.
"""
import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator

#: Each tab, by the container it edits and the noun its methods are spelled with.
TABS = [
    ("p_tab_frequencies", "FrequenciesTab", "get_frequencies", "frequencies"),
    ("p_tab_scans", "ScansTab", "get_scans", "scans"),
    ("p_tab_sources", "SourcesTab", "get_sources", "sources"),
    ("p_tab_telescopes", "TelescopesTab", "get_telescopes", "telescopes"),
]


def build(module_name, class_name, project, catalogs=None):
    """Return a tab of one kind, built the way the window builds it."""
    import importlib

    widget_class = getattr(importlib.import_module(f"pastrocore.gui.{module_name}"), class_name)
    observation = project.get_observations()[0]
    core = ScheduleManipulator(project)
    if catalogs is not None:
        return widget_class(observation, core, catalogs), observation
    return widget_class(observation, core), observation


@pytest.fixture
def catalogs():
    from pastrocore.paths import existing_or_shipped
    from pastrocore.utils.catalogmanager import CatalogManager

    return CatalogManager(existing_or_shipped("", "sources.json"),
                          existing_or_shipped("", "telescopes.json"))


@pytest.fixture
def tab(request, project, catalogs, qt_application):
    """One of the four, with the observation it edits."""
    module_name, class_name, container, noun = request.param
    needs_catalog = module_name in ("p_tab_sources", "p_tab_telescopes")
    widget, observation = build(module_name, class_name, project,
                                catalogs if needs_catalog else None)
    yield widget, observation, container, noun
    widget.close()
    widget.deleteLater()


def held(observation, container):
    """What the observation holds, and how much of it is active."""
    items = getattr(observation, container)().get_items()
    return len(items), sum(1 for item in items if item.isactive)


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_a_tab_shows_what_the_observation_holds(tab):
    """The floor: it builds against a real observation and its table has the rows."""
    widget, observation, container, _noun = tab
    count, _active = held(observation, container)

    assert widget.model.rowCount() == count, "the table does not show what is there"


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_the_number_column_is_wide_enough_for_its_own_heading(tab, qt_application):
    """U1: the tables start with a row number and a dot, and both were sized to their contents
    after every refill -- so the number column came out one digit wide and Qt drew the sort
    arrow over the `#`. The heading read as a stray mark."""
    from PySide6.QtWidgets import QHeaderView

    widget, _observation, _container, _noun = tab
    table = widget.ui.table
    header = table.horizontalHeader()
    needed = header.fontMetrics().horizontalAdvance("#") + 28   # the arrow and the padding

    assert header.sectionSize(0) >= needed, "the sort arrow sits on top of the heading"
    assert header.sectionSize(1) <= 32, "the state column is a dot, not a column"
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Fixed


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_deactivating_and_activating_everything_reaches_the_model(tab):
    """Two of the eight methods that are the same in all four files. What is checked is the
    model, not the table -- a tab that redrew without changing anything would pass otherwise."""
    widget, observation, container, noun = tab

    getattr(widget, f"deactivate_all_{noun}")()
    count, active = held(observation, container)
    assert active == 0, f"{active} of {count} still active after deactivating all"

    getattr(widget, f"activate_all_{noun}")()
    count, active = held(observation, container)
    assert active == count, f"only {active} of {count} active after activating all"


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_dropping_the_inactive_leaves_the_active(tab):
    """`drop_inactive` and `drop_active` are one method with a word changed, four times over."""
    widget, observation, container, noun = tab

    getattr(widget, f"activate_all_{noun}")()
    before, _active = held(observation, container)

    getattr(widget, f"drop_inactive_{noun}")()
    after, active = held(observation, container)

    assert after == before, "everything was active, so nothing should have gone"
    assert active == after


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_dropping_the_active_empties_what_was_active(tab):
    widget, observation, container, noun = tab

    getattr(widget, f"activate_all_{noun}")()
    getattr(widget, f"drop_active_{noun}")()
    count, _active = held(observation, container)

    assert count == 0, f"{count} left after dropping every active {noun[:-1]}"
    assert widget.model.rowCount() == 0, "the table still shows rows the model no longer holds"


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_clearing_empties_the_container_and_the_table(tab):
    widget, observation, container, noun = tab

    getattr(widget, f"clear_{noun}")()
    count, _active = held(observation, container)

    assert count == 0
    assert widget.model.rowCount() == 0


@pytest.mark.parametrize("tab", TABS, indirect=True, ids=[entry[1] for entry in TABS])
def test_refreshing_after_the_model_changed_shows_the_change(tab):
    """`update` is the one method of the nine that is genuinely different in each tab -- 6%
    alike across the four -- because each shows different columns. It still has to do this."""
    widget, observation, container, _noun = tab
    before = widget.model.rowCount()

    getattr(observation, container)().remove_all()
    widget.update()

    assert widget.model.rowCount() == 0, (
        f"the table still shows {widget.model.rowCount()} of {before} rows")


def test_the_number_column_sorts_as_a_number(qt_application):
    """`#` runs past nine, and as text 10 comes before 9. The comparison that keeps it in order
    is the proxy's, and it was written twice: the other copy sat on a `QStandardItemModel`
    subclass every one of these tables was built on -- which has no `lessThan` to override, so
    Qt never called it once. This holds the one that works while the one that never did goes."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    from pastrocore.gui.p_custom_model import CustomSortFilterProxyModel

    model = QStandardItemModel()
    for number in range(12, 0, -1):
        first = QStandardItem(str(number))
        first.setData(number, Qt.UserRole + 1)
        model.appendRow([first])
    proxy = CustomSortFilterProxyModel()
    proxy.setSourceModel(model)
    proxy.sort(0, Qt.AscendingOrder)
    shown = [proxy.data(proxy.index(row, 0)) for row in range(proxy.rowCount())]

    assert shown == [str(number) for number in range(1, 13)], f"sorted as text: {shown}"


def test_the_sources_table_writes_a_position_the_way_the_source_does(project, catalogs,
                                                                     qt_application):
    """A source just south of the equator is south of it, and 59.97 seconds is the next minute.

    Both were found once already -- `dec_degrees` reads the sign with `copysign` because the
    only field that can carry it holds `-0.0`, and `get_*_parts` round the whole position
    rather than its seconds on their own -- and the catalogue dialog asks the source for the
    answer. This table formatted the stored fields itself.
    """
    from PySide6.QtCore import Qt

    widget, observation = build("p_tab_sources", "SourcesTab", project, catalogs)
    try:
        source = observation.get_sources().get_items()[0]
        source.set_dec_degrees(-0.5)
        source.set_ra_degrees(15.0 * (12 + 34 / 60 + 59.97 / 3600))
        widget.update()
        row = next(index for index in range(widget.model.rowCount())
                   if widget.model.item(index, 0).data(Qt.UserRole) == source.name)

        assert widget.model.item(row, 6).text() == "-00:30:00.0", "drawn north of the equator"
        assert widget.model.item(row, 5).text() == "12:35:00.0", "59.97 seconds is a minute"
    finally:
        widget.close()
        widget.deleteLater()


def test_the_search_box_takes_a_name_rather_than_a_pattern(project, catalogs, qt_application):
    """801 of the 1633 names in the shipped source catalogue hold a `+`, and a `+` in a regular
    expression is not a plus: `0010+405` reads as `001`, one or more `0`, then `405`, and
    matches the row it was copied from in no way at all. The catalogue's own search is a
    substring, which is what a box labelled "Search sources..." is."""
    from pastrocore.base.sources import Source

    widget, observation = build("p_tab_sources", "SourcesTab", project, catalogs)
    try:
        observation.get_sources().add(Source(name="0010+405", ra_h=0, ra_m=10, ra_s=0.0,
                                             de_d=40, de_m=5, de_s=0.0))
        widget.update()
        widget.search_changed("0010+405")

        assert widget.proxy_model.rowCount() == 1, (
            f"searching for a source by its own name found {widget.proxy_model.rowCount()} rows")
    finally:
        widget.close()
        widget.deleteLater()


def test_the_frequencies_search_finds_a_band_by_the_sidebands_it_shows(project, qt_application):
    """The sidebands column joins them with a `+`, so a band recording both is listed as `U+L`
    -- and that is the one string in the table the search could never find."""
    widget, observation = build("p_tab_frequencies", "FrequenciesTab", project)
    try:
        band = observation.get_frequencies().get_items()[0]
        band.set_sidebands(["U", "L"])
        widget.update()
        widget.search_changed("U+L")

        assert widget.proxy_model.rowCount() == 1, (
            f"searching for what the table shows found {widget.proxy_model.rowCount()} rows")
    finally:
        widget.close()
        widget.deleteLater()


def test_adding_a_frequency_announces_the_one_it_added(project, qt_application, monkeypatch):
    """The name it emitted and logged was made up on the spot -- `freq_` and a fresh uuid --
    while the band that arrived carries the `if_` name its editor gave it. Nothing was ever
    called what the log said had been added."""
    from PySide6.QtWidgets import QDialog

    from pastrocore.base.frequencies import IF
    from pastrocore.gui import p_tab_frequencies

    added = IF(name="if_the_band_that_was_added", frequency=8213.0, bandwidth=8.0,
               polarizations=["RCP"], isactive=True)

    class Editor:
        def __init__(self, *arguments, **keywords):
            pass

        def exec(self):
            return QDialog.Accepted

        def get_if_object(self):
            return added

    monkeypatch.setattr(p_tab_frequencies, "IFEditorDialog", Editor)
    widget, observation = build("p_tab_frequencies", "FrequenciesTab", project)
    try:
        announced = []
        widget.data_updated.connect(lambda name, _active, _what: announced.append(name))
        widget.add_frequency()
        held_now = [band.name for band in observation.get_frequencies().get_items()]

        assert added.name in held_now, "the band the editor made is not the one that arrived"
        assert announced == [added.name], f"it announced {announced}, and added {added.name}"
    finally:
        widget.close()
        widget.deleteLater()


def test_removing_an_observation_closes_its_tab_without_complaining(project, qt_application,
                                                                    monkeypatch):
    """The tab closes itself when the observation it edits is gone, which is right, and is how
    "Drop Inactive" and a removal from the project table reach an open tab. It read the code
    for its own log line *after* the cleanup had set the observation to `None`, so what the
    user got instead was a critical dialog reading "'NoneType' object has no attribute
    'get_observation_code'"."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.gui.p_tab_observation import ObservationTab

    complaints = []
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *arguments, **keywords: complaints.append(arguments[2])))

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    observation = project.get_observations()[0]
    tab = ObservationTab(observation, window.manipulator, window.catalog_manager, window)
    window.ui.tabContainer.addTab(tab, "obs")
    try:
        project.remove_item(observation.name)
        tab.update_tab()

        assert not complaints, f"closing the tab said: {complaints}"
        assert window.ui.tabContainer.indexOf(tab) == -1, "the tab is still there"
    finally:
        window.status.close()
        window.close()
        window.deleteLater()
        qt_application.processEvents()


def test_renaming_an_observation_onto_a_taken_code_is_refused(project, qt_application,
                                                              monkeypatch):
    """The form wrote the new code onto the observation, where no rule about the project could
    see it: the rename was taken, the window said nothing, and the project was saved holding
    two observations with one code -- which the rule refuses on the way back in. The file
    could not be opened again."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.base.observation import Observation
    from pastrocore.gui.p_tab_observation import ObservationTab
    from pastrocore.super.schedule_project import ScheduleProject

    complaints = []
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *arguments, **keywords: complaints.append(arguments[2])))

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    project.add_item(Observation(name="obs_the_other_one", code="TAKEN"))
    observation = project.get_observations()[0]
    mine = observation.code
    tab = ObservationTab(observation, window.manipulator, window.catalog_manager, window)
    window.ui.tabContainer.addTab(tab, "obs")
    try:
        tab.ui.obs_name_edit.setReadOnly(False)
        tab.ui.obs_name_edit.setText("TAKEN")
        tab.obs_name_confirmed()

        assert complaints, "the rename was taken in silence"
        assert observation.code == mine, f"it is now called '{observation.code}'"
        assert ScheduleProject.from_dict(project.to_dict()) == project, "it cannot be reopened"
    finally:
        window.status.close()
        window.close()
        window.deleteLater()
        qt_application.processEvents()


def test_a_closed_observation_tab_lets_go_of_what_its_four_were_editing(project, qt_application):
    """Each of the four has a `_cleanup` that drops the observation, the orchestrator and the
    project. The tab that owns them disconnected each one and called `deleteLater`, which
    destroys the widget and leaves the Python object holding all three -- so nothing ever
    called the method written for exactly this."""
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.gui.p_tab_observation import ObservationTab

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    tab = ObservationTab(project.get_observations()[0], window.manipulator,
                         window.catalog_manager, window)
    window.ui.tabContainer.addTab(tab, "obs")
    four = [tab.frequencies_tab, tab.sources_tab, tab.telescopes_tab, tab.scans_tab]
    try:
        tab.close_tab()
        holding = [type(one).__name__ for one in four
                   if one.observation is not None or one.manipulator is not None]

        assert not holding, f"{', '.join(holding)} still hold the observation they edited"
    finally:
        window.status.close()
        window.close()
        window.deleteLater()
        qt_application.processEvents()


def test_the_scans_tab_stops_listening_when_it_is_cleaned(project, catalogs, qt_application):
    """It meant to take back the three connections it made, and asked `self.sender()` for who
    to take them back from -- which is who emitted the signal being handled, and nothing is
    being handled during a cleanup. So all three stayed, and the next change to a source drove
    a tab that had let go of its model and its orchestrator through both of them."""
    from PySide6.QtCore import QMetaMethod

    from pastrocore.gui.p_tab_scans import ScansTab

    sources, observation = build("p_tab_sources", "SourcesTab", project, catalogs)
    telescopes, _ = build("p_tab_telescopes", "TelescopesTab", project, catalogs)
    frequencies, _ = build("p_tab_frequencies", "FrequenciesTab", project)
    scans = ScansTab(observation, ScheduleManipulator(project), telescopes_tab=telescopes,
                     frequencies_tab=frequencies, sources_tab=sources)
    try:
        # Built the way the window builds them but on their own, so the scans tab is the only
        # thing listening to the three: what is left afterwards is what it failed to take back.
        scans._cleanup()
        still = [type(tab).__name__ for tab in (sources, telescopes, frequencies)
                 if tab.isSignalConnected(QMetaMethod.fromSignal(tab.data_updated))]

        assert not still, f"a cleaned tab is still listening to {', '.join(still)}"
    finally:
        for widget in (scans, frequencies, telescopes, sources):
            widget.close()
            widget.deleteLater()
