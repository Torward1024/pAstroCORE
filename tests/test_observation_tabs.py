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
    observation = project.observations()[0]
    core = ScheduleManipulator(project)
    if catalogs is not None:
        return widget_class(observation, core, catalogs), observation
    return widget_class(observation, core), observation


@pytest.fixture
def catalogs():
    from pastrocore.paths import existing_or_shipped
    from pastrocore.utils.catalogmanager import CatalogManager

    return CatalogManager(existing_or_shipped("", "sources.dat"),
                          existing_or_shipped("", "telescopes.dat"))


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
