# cli.py
"""pAstroCORE from a terminal.

The second caller of the backend, and the reason it was built the way it was: everything the
window does is a request, so this parses arguments, sends the same requests and prints what
comes back. **Nothing here imports the interface, and nothing imports Qt** -- a test asserts
both, because a command line that has to reach into a dialog is the window with the pixels
removed rather than a second caller.

It holds no knowledge about calculations. What can be run, what each needs, what order they go
in and what a run did are all asked of the orchestrator, exactly as the dialogs ask.

    pastrocore-cli info survey.pastro
    pastrocore-cli calculations
    pastrocore-cli run survey.pastro --only uv_coverage --force
    pastrocore-cli export survey.pastro pictures/ --pictures
    pastrocore-cli replay survey.pastro session.json
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from msb_arch.utils.logging_setup import logger

from pastrocore import __version__
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


def _open(path: str) -> ScheduleProject:
    """Open a project directory, refusing anything that is not one.

    Raises:
        SystemExit: With a message rather than a traceback -- a mistyped path is a mistake, not
            a crash.
    """
    if not ScheduleProject.is_directory_project(path):
        raise SystemExit(f"'{path}' is not a pAstroCORE project (a folder holding project.json)")
    return ScheduleProject.open(path)


def _catalogue(manipulator) -> List[dict]:
    """What this application can calculate, asked rather than listed."""
    return manipulator.compute(obj=manipulator.get_managing_object(), method="catalogue",
                               raise_on_error=False).value or []


def _wanted(manipulator, only: Optional[List[str]]) -> List[str]:
    """Return the calculations to run, refusing one nobody offers."""
    catalogue = _catalogue(manipulator)
    offered = {entry["key"] for entry in catalogue if entry["offer"]}
    if not only:
        return sorted(offered)

    unknown = [key for key in only if key not in {entry["key"] for entry in catalogue}]
    if unknown:
        raise SystemExit(f"no such calculation: {', '.join(unknown)}\n"
                         f"try: pastrocore-cli calculations")
    return list(only)


def info(arguments) -> int:
    """Print what a project holds, and what of it is stale."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)

    print(f"{project.name}  ({arguments.project})")
    for observation in project.observations():
        held = manipulator.export(obj=observation, method="available",
                                  raise_on_error=False).value or []
        stale = set(manipulator.compute(obj=observation, method="stale",
                                        raise_on_error=False).value or [])
        print(f"\n  {observation.code}  [{observation.observation_type}]")
        print(f"    {len(observation.get_telescopes().get_items())} telescope(s), "
              f"{len(observation.get_sources().get_items())} source(s), "
              f"{len(observation.get_scans().get_items())} scan(s), "
              f"{len(observation.get_frequencies().get_items())} frequency band(s)")
        if held:
            for key in held:
                print(f"    - {key}{'  (stale)' if key in stale else ''}")
        else:
            print("    - nothing calculated yet")
    return 0


def calculations(arguments) -> int:
    """Print what can be calculated, and what each one needs."""
    manipulator = ScheduleManipulator(ScheduleProject(name="listing"), journal_limit=None)
    catalogue = _catalogue(manipulator)

    print("Calculations")
    for entry in sorted(catalogue, key=lambda item: item["key"]):
        if not entry["offer"]:
            continue
        needs = f"  needs {', '.join(entry['requires'])}" if entry["requires"] else ""
        target = "  (needs a target)" if entry["needs_target"] else ""
        print(f"  {entry['key']:24} {entry['label']}{target}{needs}")

    print("\nSteps (run for you, never asked for by name)")
    for entry in sorted(catalogue, key=lambda item: item["key"]):
        if entry["offer"]:
            continue
        print(f"  {entry['key']:24} {entry['label']}")
    return 0


def run(arguments) -> int:
    """Run calculations and print what each step did."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project)
    wanted = _wanted(manipulator, arguments.only)

    outcome = manipulator.compute(
        obj=None, method="run", targets=project.observations(), calculations=wanted,
        time_step=arguments.time_step, force=arguments.force, concurrent=True,
        progress=lambda percent, message: print(f"  [{percent:3}%] {message}"))

    for row in outcome["report"]:
        mark = "ok " if row["outcome"] == "ok" else "FAILED"
        print(f"  {mark} {row['observation']:16} {row['label']:26} {row['seconds']:6.2f} s")

    summary = outcome["summary"]
    print(f"\n{summary['steps']} calculation(s) in {summary['seconds']:.2f} s"
          + (f", {summary['failed']} failed" if summary["failed"] else ""))

    project.save(arguments.project)
    if arguments.session:
        written = manipulator.export(obj=project, method="journal", path=arguments.session,
                                     raise_on_error=False).value
        if written:
            print(f"session of {written['steps']} request(s) written to {written['path']}")
    return 1 if summary["failed"] else 0


def export(arguments) -> int:
    """Write results out as text, pictures, or both."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)
    catalogue = _catalogue(manipulator)
    labels = {entry["key"]: entry["label"] for entry in catalogue}
    wanted = _wanted(manipulator, arguments.only)

    Path(arguments.destination).mkdir(parents=True, exist_ok=True)
    outcome = manipulator.export(
        obj=project, calc_types=[labels[key] for key in wanted],
        export_data=True, export_vis=arguments.pictures,
        export_path=str(arguments.destination), units="wavelengths",
        progress=lambda percent, message: print(f"  [{percent:3}%] {message}"),
        raise_on_error=False).value

    written = (outcome or {}).get("written") or []
    print(f"\n{len(written)} file(s) written to {arguments.destination}")
    return 0 if written else 1


def replay(arguments) -> int:
    """Run a recorded session again, against this project."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project)

    outcome = manipulator.compute(obj=project, method="replay", path=arguments.session,
                                  raise_on_error=False).value or {}
    print(f"{len(outcome.get('ran', []))} request(s) replayed")
    for name in outcome.get("failed", []):
        print(f"  FAILED {name}")
    for note in outcome.get("unresolved", []):
        print(f"  not in this project: {note}")

    project.save(arguments.project)
    return 1 if outcome.get("failed") or outcome.get("unresolved") else 0


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser.

    Notes:
        - One subcommand per thing a person wants, and each is one request. Nothing here
          decides anything a dialog does not also ask the orchestrator.
    """
    parser = argparse.ArgumentParser(
        prog="pastrocore-cli",
        description="pAstroCORE from a terminal. The window is `pastrocore`.")
    parser.add_argument("--version", action="version", version=f"pAstroCORE {__version__}")
    parser.add_argument("--quiet", action="store_true", help="log errors only")
    commands = parser.add_subparsers(dest="command", required=True)

    said = commands.add_parser("info", help="what a project holds, and what of it is stale")
    said.add_argument("project")
    said.set_defaults(run=info)

    listed = commands.add_parser("calculations", help="what can be calculated")
    listed.set_defaults(run=calculations)

    ran = commands.add_parser("run", help="calculate, for every observation in a project")
    ran.add_argument("project")
    ran.add_argument("--only", nargs="+", metavar="KEY",
                     help="calculations to run; everything offered by default")
    ran.add_argument("--time-step", type=float, default=600.0, dest="time_step",
                     help="seconds between sampled moments (600)")
    ran.add_argument("--force", action="store_true",
                     help="recompute what is current as well as what is stale")
    ran.add_argument("--session", metavar="FILE",
                     help="write the session to a file, to replay later")
    ran.set_defaults(run=run)

    written = commands.add_parser("export", help="write results out as text or pictures")
    written.add_argument("project")
    written.add_argument("destination")
    written.add_argument("--only", nargs="+", metavar="KEY")
    written.add_argument("--pictures", action="store_true", help="draw them as well")
    written.set_defaults(run=export)

    again = commands.add_parser("replay", help="run a recorded session against this project")
    again.add_argument("project")
    again.add_argument("session")
    again.set_defaults(run=replay)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Parse the arguments and run one command.

    Args:
        argv: What to parse. Defaults to the command line.

    Returns:
        int: What to exit with -- 0 when it worked.

    Notes:
        - A mistake is a message and a non-zero exit, not a traceback. Anything unexpected keeps
          its traceback, because that one is a defect rather than a typo.
    """
    parser = build_parser()
    arguments = parser.parse_args(argv)

    logging.basicConfig(level=logging.ERROR if arguments.quiet else logging.WARNING,
                        format="%(levelname)s %(message)s")
    logger.setLevel(logging.ERROR if arguments.quiet else logging.WARNING)

    try:
        return arguments.run(arguments)
    except SystemExit as refusal:
        print(refusal.code if isinstance(refusal.code, str) else "refused")
        return 2


if __name__ == "__main__":
    sys.exit(main())
