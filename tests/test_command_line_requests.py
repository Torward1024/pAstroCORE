"""Every operation from a terminal, as one request (L4).

`pastrocore-cli ask <project> <operation> <address> key=value` sends what the window sends, and
`pastrocore-cli shell` takes the same lines one after another with completion. Neither holds a
command table: the operations, their handlers, the methods an object has and what is inside an
address are all asked of the orchestrator -- so a check here that walks the orchestrator's own
catalogue is a check that nothing is missing.
"""
import json

import pytest

import conftest
from pastrocore import cli, cli_request
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


@pytest.fixture
def saved(tmp_path):
    """The fixture project, on disk, where a command line would find it."""
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    destination = tmp_path / "survey.pastro"
    project.save(str(destination))
    return destination


@pytest.fixture
def core(project):
    return ScheduleManipulator(project, journal_limit=5000)


def run(*arguments, capsys):
    """Run one command and return its exit code and everything it put on the screen -- the log
    goes to stderr, and a refusal said twice is said on both."""
    code = cli.main(["--quiet", *[str(argument) for argument in arguments]])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def everything(core, address="project"):
    """Every address in the project, found by asking what is at each one."""
    found = [address]
    for entry in core.inspect(obj=core.get_managing_object(), method="contents", address=address):
        found.extend(everything(core, f"{address}/{entry['segment']}"))
    return found


# --- addresses ----------------------------------------------------------------------------------

def test_every_part_of_a_project_has_an_address_that_finds_it_again(core):
    """The round trip, over everything the project holds -- found by walking, not listed."""
    root = core.get_managing_object()
    addresses = everything(core)
    assert len(addresses) > 8, "the walk found almost nothing, so this checks almost nothing"

    for address in addresses:
        found = core.inspect(obj=root, method="locate", address=address)
        given = core.inspect(obj=root, method="address", object=found)
        again = core.inspect(obj=root, method="locate", address=given)
        assert again is found, f"{address} -> {given} names something else"


def test_an_item_is_found_by_its_name_its_code_or_its_position(core):
    root = core.get_managing_object()
    by_code = core.inspect(obj=root, method="locate", address="OBS_DEFAULT/telescopes/ALMA")

    assert core.inspect(obj=root, method="locate",
                        address=f"OBS_DEFAULT/telescopes/{by_code.name}") is by_code
    assert core.inspect(obj=root, method="locate", address="OBS_DEFAULT/telescopes/#1") is by_code
    assert core.inspect(obj=root, method="address", object=by_code) == "OBS_DEFAULT/telescopes/ALMA"


def test_a_misspelt_address_says_what_was_meant_and_what_is_there(core):
    answer = core.inspect(obj=core.get_managing_object(), method="locate",
                          address="OBS_DEFAULT/telescops", raise_on_error=False)

    assert not answer.ok
    assert "did you mean 'telescopes'" in answer.error and "sources" in answer.error


def test_inspect_is_offered_only_what_reads(core):
    from msb_arch.super.builtins import Inspector

    root = core.get_managing_object()
    reading = core.inspect(obj=root, method="offers", operation="inspect", address="OBS_DEFAULT/sources")
    changing = core.inspect(obj=root, method="offers", operation="configure", address="OBS_DEFAULT/sources")

    assert "get_items" in reading["methods"] and all(Inspector.reads(m) for m in reading["methods"])
    assert "deactivate_item" in changing["methods"]


def test_every_handler_of_every_operation_can_be_asked(core):
    """The exit criterion's first sentence, walked rather than listed: each handler the
    orchestrator describes passes the check a typed request goes through."""
    described = core.describe_operations()
    assert {"inspect", "configure", "compute", "calculate", "visualize", "export", "save"} <= set(described)

    for operation, handlers in described.items():
        for handler in handlers:
            cli_request.check(core, operation, "project", {"method": handler})


def test_a_released_project_is_not_saved_over_its_directory(saved):
    """`compute release` is a request like any other, and a command line saves after a change.
    Saving what was released would write an empty project and delete its results."""
    project = ScheduleProject.open(str(saved))
    project.release()

    with pytest.raises(ValueError, match="released"):
        project.save(str(saved))
    assert ScheduleProject.open(str(saved)).get_observations(), "the directory was emptied"


# --- ask ----------------------------------------------------------------------------------------

def test_a_read_prints_addresses_and_leaves_the_project_alone(saved, capsys):
    model = saved / "project.json"
    before = model.stat().st_mtime_ns

    code, printed = run("ask", saved, "inspect", "OBS_DEFAULT/telescopes", "get_items", capsys=capsys)

    assert code == 0
    assert "Telescope OBS_DEFAULT/telescopes/ALMA" in printed
    assert "saved" not in printed and model.stat().st_mtime_ns == before


def test_a_change_is_saved_and_a_dry_run_is_not(saved, capsys):
    code, printed = run("ask", saved, "configure", "OBS_DEFAULT/sources",
                        "deactivate_item=1228+126", "--dry-run", capsys=capsys)
    assert code == 0 and "saved" not in printed
    assert ScheduleProject.open(str(saved)).get_observations()[0].get_sources().get("1228+126").isactive

    code, printed = run("ask", saved, "configure", "OBS_DEFAULT/sources",
                        "deactivate_item=1228+126", capsys=capsys)
    assert code == 0 and "saved" in printed
    reopened = ScheduleProject.open(str(saved))
    assert reopened.get_observations()[0].get_sources().get("1228+126").isactive is False


def test_an_address_in_a_value_passes_the_object_there(saved, capsys):
    """`targets` wants observations, and a terminal can only type their codes."""
    code, printed = run("ask", saved, "compute", "project", "method=clear",
                        'targets=["@OBS_DEFAULT"]', "--json", capsys=capsys)

    assert code == 0, printed
    assert json.loads(printed) == {"cleared": ["OBS_DEFAULT"]}


def test_a_table_is_shown_by_its_size_and_first_rows_and_given_whole_as_json(saved, capsys):
    """A result is thousands of rows. Printed whole it scrolls the question off the screen; a script
    asking for JSON wants every one."""
    run("ask", saved, "compute", "project", "method=run", 'calculations=["az_el"]',
        'targets=["@OBS_DEFAULT"]', "time_step=60", "force=true", capsys=capsys)

    code, printed = run("ask", saved, "inspect", "OBS_DEFAULT",
                        "get_calculated_data_by_key=az_el", capsys=capsys)
    assert code == 0
    assert "rows: 576" in printed and "first 10:" in printed
    assert printed.count("telescope_code: ") == 10, "more rows were printed than were meant"

    code, printed = run("ask", saved, "inspect", "OBS_DEFAULT",
                        "get_calculated_data_by_key=az_el", "--json", capsys=capsys)
    assert len(json.loads(printed)["data"]["rows"]) == 576


@pytest.mark.parametrize("words,said", [
    (["inspekt", "project", "get_observations"], "did you mean 'inspect'"),
    (["inspect", "OBS_DEFAULT/telescops", "get_items"], "did you mean 'telescopes'"),
    (["compute", "project", "method=rn"], "did you mean 'run'"),
    (["inspect", "OBS_DEFAULT/sources", "deactivate_item=1228+126"], "configure OBS_DEFAULT/sources"),
    (["inspect", "OBS_DEFAULT/sources", "get_itms"], "did you mean 'get_items'"),
    (["configure", "OBS_DEFAULT/sources"], "Name what to configure"),
])
def test_a_request_that_cannot_work_is_refused_with_what_was_meant(saved, capsys, caplog, words, said):
    import logging

    model = saved / "project.json"
    before = model.read_bytes()

    with caplog.at_level(logging.ERROR, logger="msb_arch"):
        code, printed = run("ask", saved, *words, capsys=capsys)

    assert code == 2, printed
    assert said in printed
    logged = [record.getMessage() for record in caplog.records if record.name == "msb_arch"]
    assert not logged, f"the refusal was said twice, once by the log: {logged}"
    assert model.read_bytes() == before


def test_a_package_is_refused_before_a_change_is_sent(saved, tmp_path, capsys):
    package = tmp_path / "sent.pastroz"
    cli.main(["--quiet", "package", str(saved), str(package)])
    capsys.readouterr()

    code, printed = run("ask", package, "configure", "OBS_DEFAULT/sources",
                        "deactivate_item=1228+126", capsys=capsys)
    assert code == 2 and "package" in printed

    code, printed = run("ask", package, "inspect", "OBS_DEFAULT", "get_observation_code", capsys=capsys)
    assert code == 0 and "OBS_DEFAULT" in printed, "a package can still be read"


def test_releasing_through_ask_says_it_did_not_save(saved, capsys):
    code, printed = run("ask", saved, "compute", "project", "method=release", capsys=capsys)

    assert code == 1 and "not saved" in printed
    assert ScheduleProject.open(str(saved)).get_observations()


# --- the shell ----------------------------------------------------------------------------------

@pytest.fixture
def shell(saved):
    from pastrocore.cli_shell import Shell

    return Shell(ScheduleManipulator(ScheduleProject.open(str(saved)), journal_limit=5000), str(saved))


def completions(shell, text):
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from pastrocore.cli_shell import ShellCompleter

    return [c.text for c in ShellCompleter(shell).get_completions(Document(text), CompleteEvent())]


def test_the_shell_completes_from_what_the_orchestrator_says(shell):
    assert {"inspect", "configure", "compute", "exit"} <= set(completions(shell, ""))
    assert completions(shell, "inspect OBS_DEFAULT/") == ["sources", "telescopes", "frequencies", "scans"]
    assert completions(shell, "inspect OBS_DEFAULT/telescopes/") == ["ALMA", "APEX"]
    assert "deactivate_item" not in completions(shell, "inspect OBS_DEFAULT/sources ")
    assert "deactivate_item" in completions(shell, "configure OBS_DEFAULT/sources de")
    assert completions(shell, "compute project method=") == ["clear", "release", "replay", "run"]
    assert "targets=" in completions(shell, "compute project method=run ")
    assert completions(shell, "compute project method=run targets=@OBS") == ["OBS_DEFAULT"]


def test_the_shell_saves_only_when_asked_and_asks_before_leaving(shell, saved):
    said = shell.handle("configure OBS_DEFAULT/sources deactivate_item=1228+126")
    assert shell.changed, said
    assert ScheduleProject.open(str(saved)).get_observations()[0].get_sources().get("1228+126").isactive

    assert shell.leave(lambda question: "cancel") is False
    assert shell.handle("save project") and not shell.changed
    reopened = ScheduleProject.open(str(saved))
    assert reopened.get_observations()[0].get_sources().get("1228+126").isactive is False
    assert shell.leave(lambda question: pytest.fail("asked with nothing to save")) is True


def test_a_mistake_in_the_shell_is_said_and_the_shell_goes_on(shell):
    assert "did you mean 'inspect'" in shell.handle("inspekt project get_observations")
    assert shell.handle("") == ""
    assert "compute" in shell.handle("help")
    assert "run" in shell.handle("help compute")
    assert shell.handle("exit") is None


def test_the_shell_reads_lines_until_it_is_left(saved, monkeypatch, capsys):
    """The loop itself, driven through a pipe as a terminal would drive it: a request, a mistake,
    a change, the question on leaving, and the answer."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from pastrocore import cli_shell

    monkeypatch.setenv("LOCALAPPDATA", str(saved.parent / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(saved.parent / "user"))
    core = ScheduleManipulator(ScheduleProject.open(str(saved)), journal_limit=5000)
    with create_pipe_input() as typed:
        typed.send_text("inspect OBS_DEFAULT get_observation_code\r"
                        "inspekt project get_observations\r"
                        "configure OBS_DEFAULT/sources deactivate_item=1228+126\r"
                        "exit\r"
                        "yes\r")
        code = cli_shell.run(core, str(saved), input=typed, output=DummyOutput())

    printed = capsys.readouterr().out
    assert code == 0
    assert "OBS_DEFAULT" in printed and "did you mean 'inspect'" in printed
    reopened = ScheduleProject.open(str(saved))
    assert reopened.get_observations()[0].get_sources().get("1228+126").isactive is False, (
        "answering yes on leaving did not save")


def test_what_the_shell_did_is_a_script_that_replays(shell, saved, tmp_path, capsys):
    """A script is a session file: what was typed is written out and runs again elsewhere."""
    session = tmp_path / "typed.json"
    shell.handle("configure OBS_DEFAULT/sources deactivate_item=1228+126")
    shell.handle(f"export project method=journal path={session}")

    code, printed = run("replay", saved, session, capsys=capsys)

    assert code == 0, printed
    reopened = ScheduleProject.open(str(saved))
    assert reopened.get_observations()[0].get_sources().get("1228+126").isactive is False
