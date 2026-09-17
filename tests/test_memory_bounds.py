"""What a long session may hold on to, and what it may not (M1).

Reported from use: memory climbing through a session -- 260 MB to 327 MB by the status bar -- as
dialogs and plots are opened and closed, and never coming back down.

Measured: nothing grows without a bound. What grows is three caches, and they are named here so
that the next person watching the number climb knows what they are looking at:

- **matplotlib's text metrics**, an `lru_cache(4096)`. Every tab brings a new renderer, so every tab
  fills it with new keys -- about 400 `FontProperties` per round of work -- until it is full.
- **the request journal**, capped by the `session_limit` setting (5000). Entries are plain data: the
  objects a request named are recorded by name, so nothing in the model is pinned by being asked
  about.
- **the results in hand**, capped by the residency budget, which is a share of what the machine has
  free. That one is the point of the design, not an accident.

What this holds, then, is the part that has no bound of its own: widgets, figures and tabs must go
when they are closed, and the journal must not exceed what it was told.
"""
import gc

import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator


def settle(application):
    """Let Qt delete what was asked to go, and Python collect what nothing holds."""
    from PySide6.QtCore import QEvent

    for _ in range(3):
        application.processEvents()
        application.sendPostedEvents(None, QEvent.DeferredDelete)
        application.processEvents()
    gc.collect()


def alive(kind):
    return sum(1 for obj in gc.get_objects() if isinstance(obj, kind))


@pytest.fixture
def drawn(project):
    """A project with something to plot, and the orchestrator to ask."""
    core = ScheduleManipulator(project)
    project.hold_results_in_scratch()
    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["uv_coverage", "az_el"], time_step=600.0, recalculate=True)
    return core, project.get_observations()[0]


def test_opening_and_closing_a_plot_leaves_no_tab_and_no_figure_behind(qt_application, drawn):
    """A tab holds a figure, and a figure holds the arrays a day's sampling makes. Ten of them
    opened and closed must leave none of it."""
    from matplotlib.figure import Figure

    from pastrocore.gui.p_tab_vis_az_el import AzElVisualizationTab
    from pastrocore.gui.p_tab_vis_base import VisualizationTab

    core, observation = drawn
    settle(qt_application)
    figures = alive(Figure)

    for _ in range(10):
        tab = AzElVisualizationTab(core, observation)
        tab.resize(800, 600)
        tab.show()
        qt_application.processEvents()
        tab.close()
        tab.deleteLater()
        settle(qt_application)
    # The loop's own variable is a reference like any other, and holding it would make the last
    # tab look like a leak -- which is exactly how this check first read.
    del tab
    settle(qt_application)

    assert alive(VisualizationTab) == 0, "a closed tab is still alive"
    assert alive(Figure) <= figures, "a closed tab left its figure behind"


def test_the_visualization_dialog_closes_the_tabs_it_opened(qt_application, project, drawn):
    """`removeTab` does not send a close event and a child is destroyed without one, so a tab's own
    teardown never ran: neither closing a plot's tab nor closing the dialog freed what it held."""
    from matplotlib.figure import Figure

    from pastrocore.gui.p_dialog_visualize import VisualizationDialog
    from pastrocore.gui.p_tab_vis_base import VisualizationTab

    core, _ = drawn
    settle(qt_application)
    figures = alive(Figure)

    for _ in range(3):
        dialog = VisualizationDialog(core)
        dialog.show()
        qt_application.processEvents()
        kinds = dialog.ui.comboBoxVisualizationType
        assert kinds.count(), "the dialog offered nothing to plot"
        for index in range(min(kinds.count(), 3)):
            kinds.setCurrentIndex(index)
            qt_application.processEvents()
            dialog.ui.pushButtonVisualize.click()
            qt_application.processEvents()
        assert dialog.ui.tabWidget.count(), "no tab was opened to close"
        dialog.done(0)
        dialog.deleteLater()
        settle(qt_application)
    settle(qt_application)

    assert alive(VisualizationTab) == 0, "the dialog left its tabs alive"
    assert alive(Figure) <= figures, "the dialog left a figure behind"


def test_the_journal_stops_at_the_size_it_was_given(project):
    """It records every request, which is what makes a session replayable -- and what would make it
    grow all day if the limit were not held to. Entries are plain data: what a request named is
    recorded by name, so asking about an object does not keep it alive."""
    core = ScheduleManipulator(project, journal_limit=20)
    observation = project.get_observations()[0]

    for _ in range(60):
        core.inspect(obj=observation, get_observation_code=None)

    journal = core.journal()
    assert journal is not None and len(journal) == 20
    recorded = journal.entries[-1]
    assert isinstance(recorded["attributes"], dict)
    assert all(isinstance(value, (str, int, float, bool, list, dict, type(None)))
               for value in recorded["attributes"].values()), recorded["attributes"]


def test_a_plot_request_pins_nothing_it_was_given(qt_application, drawn):
    """The figure a tab draws into travels in the request. A journal that held it would keep every
    figure of the session -- the failure this whole recording design exists to avoid."""
    from matplotlib.figure import Figure

    core, observation = drawn
    figure = Figure()
    core.visualize(obj=observation, plot_type="uv_coverage", figure=figure, show=False,
                   return_figure=True, raise_on_error=False)

    journal = core.journal()
    if journal is None:
        pytest.skip("this orchestrator records nothing")
    held = journal.entries[-1]["attributes"].get("figure")
    assert not isinstance(held, Figure), "the journal is holding the figure it was told about"
