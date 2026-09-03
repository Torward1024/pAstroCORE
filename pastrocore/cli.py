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
import zipfile
from pathlib import Path
from typing import List, Optional

from msb_arch.utils.logging_setup import logger

from pastrocore import __version__
from pastrocore.super.schedule_data import ScheduleData
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


def _open(path: str) -> ScheduleProject:
    """Open a project directory, refusing anything that is not one.

    Raises:
        SystemExit: With a message rather than a traceback -- a mistyped path is a mistake, not
            a crash.
    """
    # A package is a project too, as far as reading it goes. Accepting one here means every
    # command works on what a colleague sent without unpacking it first.
    if Path(path).is_file() and zipfile.is_zipfile(path):
        # An empty project to send the request against: a package carries its own, and a
        # request needs something to be about even when the handler ignores it.
        opening = ScheduleProject(name="opening")
        return ScheduleManipulator(opening, journal_limit=None).load(
            obj=opening, method="package", path=path)
    if not ScheduleProject.is_directory_project(path):
        raise SystemExit(f"'{path}' is not a pAstroCORE project (a folder holding project.json, "
                         f"or a {ScheduleData.ARCHIVE_SUFFIX} package)")
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


def _slice(pairs: Optional[List[str]]) -> dict:
    """Turn `--where telescope_code=ALMA time=61262:61263` into a filter.

    Notes:
        - `a=b` is a value, `a=b,c` is a set of them, and `a=x:y` is a range with either end
          allowed to be empty. Nothing here knows which columns exist -- the analyzer refuses
          one it does not have, and `analyze describe` is what lists them.
    """
    where = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"'{pair}' is not a filter; write column=value")
        column, value = pair.split("=", 1)
        if ":" in value:
            low, _, high = value.partition(":")
            where[column] = {"from": float(low) if low else None,
                             "to": float(high) if high else None}
        elif "," in value:
            where[column] = value.split(",")
        else:
            where[column] = value
    return where


def analyze(arguments) -> int:
    """Ask something of results that have already been calculated."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)

    asked = {"key": arguments.key, "where": _slice(arguments.where)}
    if arguments.what == "summary":
        asked.update(columns=arguments.columns, group_by=arguments.group_by)
    elif arguments.what == "windows":
        asked.update(gaps=arguments.gaps)
    elif arguments.what == "coverage":
        asked.update(at_least=arguments.at_least)
    if arguments.what == "describe":
        asked = {"key": arguments.key}

    answer = manipulator.analyze(obj=project, method=arguments.what, raise_on_error=False,
                                 **asked)
    if not answer.ok:
        print(f"  {answer.error}")
        return 1

    result = answer.value
    if arguments.what == "describe":
        for key, entry in sorted(result.items()):
            print(f"{key}  ({entry['rows']} row(s))")
            print(f"  numbers    {', '.join(entry['numeric']) or '-'}")
            print(f"  categories {', '.join(entry['categorical']) or '-'}")
            if entry["boolean"]:
                print(f"  true/false {', '.join(entry['boolean'])}")
            for column, values in sorted(entry.get("values", {}).items()):
                shown = ", ".join(values[:6]) + (" ..." if len(values) > 6 else "")
                print(f"    {column}: {shown}")
        return 0 if result else 1

    if not result:
        print("  nothing to report; has it been calculated?")
        return 1

    if arguments.what == "summary":
        for row in result:
            labels = " ".join(f"{value}" for key, value in row.items()
                              if key not in ("observation", "column") and not _is_statistic(key))
            print(f"{row['observation']}  {labels}  {row['column']}")
            print(f"    count {row['count']}   min {row['min']:.6g}   max {row['max']:.6g}")
            print(f"    mean {row['mean']:.6g}   median {row['median']:.6g}   "
                  f"std {row['std']:.6g}   range {row['range']:.6g}")
            if row.get("min_iso"):
                print(f"    {row['min_iso'][:19]} to {row['max_iso'][:19]}")
        return 0

    total = sum(row["duration"] for row in result)
    longest = max(result, key=lambda row: row["duration"])
    for row in result:
        labels = " ".join(str(value) for key, value in row.items()
                          if key in ("source_name", "target_code", "telescope_code", "baseline"))
        print(f"{row['observation']}  {labels:24} {row['start_iso'][:19]} to "
              f"{row['end_iso'][:19]}   {row['duration'] / 60:8.1f} min")
    print("")
    print(f"{len(result)} interval(s), {total / 60:.1f} min in total, "
          f"longest {longest['duration'] / 60:.1f} min")
    return 0


def _is_statistic(name: str) -> bool:
    return name in ("count", "min", "max", "mean", "median", "std", "range",
                    "min_iso", "max_iso")


def package(arguments) -> int:
    """Pack a project into one file, to send or to attach to a bug report."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)

    answer = manipulator.export(obj=project, method="package", path=arguments.destination,
                                results=not arguments.model_only,
                                overwrite=arguments.force, raise_on_error=False)
    if not answer.ok:
        print(f"  {answer.error}")
        return 1

    report = answer.value
    kilobytes = report["bytes"] / 1024
    print(f"{report['path']}")
    print(f"  {report['files']} file(s), {kilobytes:,.1f} KB"
          + ("" if report["results"] else ", model only"))
    return 0


def affected(arguments) -> int:
    """Say which results editing something of a given type would make wrong."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)

    answer = manipulator.compute(obj=project, method="affected", type=arguments.type,
                                 raise_on_error=False)
    if not answer.ok:
        print(f"  {answer.error}")
        return 1

    report = answer.value or {}
    print(f"Editing a {report['type']} reaches: {', '.join(report['parts']) or 'nothing'}")
    print("")
    print(f"{len(report['calculations'])} calculation(s) read those parts:")
    for key in report["calculations"]:
        print(f"  {key}")

    stored = report.get("stored") or []
    print("")
    if not stored:
        print("None of them has been calculated, so nothing would go stale.")
        return 0
    print(f"{len(stored)} of them have been calculated and would go stale:")
    for key in stored:
        print(f"  {key}")
    return 0


def check(arguments) -> int:
    """Read a session and say what is wrong with it, without running anything."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project, journal_limit=None)

    report = manipulator.compute(obj=project, method="check", path=arguments.session,
                                 raise_on_error=False).value or {}
    for problem in report.get("problems", []):
        print(f"  problem  {problem}")
    for note in report.get("warnings", []):
        print(f"  warning  {note}")

    steps = report.get("steps", 0)
    problems = report.get("problems") or []
    warnings = report.get("warnings") or []
    if problems:
        print("")
        print(f"{len(problems)} problem(s) in {steps} step(s); this session will not be replayed")
        return 1
    print("")
    print(f"{steps} step(s), no problems"
          + (f", {len(warnings)} warning(s)" if warnings else ""))
    return 0

def replay(arguments) -> int:
    """Run a recorded session again, against this project."""
    project = _open(arguments.project)
    manipulator = ScheduleManipulator(project)

    outcome = manipulator.compute(obj=project, method="replay", path=arguments.session,
                                  raise_on_error=False).value or {}
    # Checked whole before anything ran, so a refusal is the whole list rather than the first
    # thing that broke halfway through.
    if outcome.get("problems"):
        for problem in outcome["problems"]:
            print(f"  problem  {problem}")
        print("")
        print(f"refused: {len(outcome['problems'])} problem(s), nothing was run")
        return 1
    for note in outcome.get("warnings", []):
        print(f"  warning  {note}")
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

    asked = commands.add_parser(
        "analyze", help="ask something of results that have already been calculated")
    asked.add_argument("project")
    asked.add_argument("what", choices=["describe", "summary", "windows", "coverage"],
                       help="describe: what can be asked; summary: the numbers; "
                            "windows: runs of a true/false column; coverage: across stations")
    asked.add_argument("--key", metavar="CALCULATION",
                       help="which result; every one for describe")
    asked.add_argument("--columns", nargs="+", metavar="COLUMN",
                       help="summary: which numeric columns; all of them by default")
    asked.add_argument("--group-by", nargs="+", metavar="COLUMN", dest="group_by",
                       help="summary: break the answer down by these")
    asked.add_argument("--where", nargs="+", metavar="COLUMN=VALUE",
                       help="slice: a value, a,b,c for several, or x:y for a range")
    asked.add_argument("--gaps", action="store_true",
                       help="windows: the runs of false rather than of true")
    asked.add_argument("--at-least", type=int, default=1, dest="at_least",
                       help="coverage: how many stations at once (1)")
    asked.set_defaults(run=analyze)

    packed = commands.add_parser("package", help="pack a project into one file, to send")
    packed.add_argument("project")
    packed.add_argument("destination")
    packed.add_argument("--model-only", action="store_true", dest="model_only",
                        help="leave the results out; a few KB that reproduce the configuration")
    packed.add_argument("--force", action="store_true", help="replace a file that is there")
    packed.set_defaults(run=package)

    spoiled = commands.add_parser(
        "affected", help="which results editing something of a type would make wrong")
    spoiled.add_argument("project")
    spoiled.add_argument("type", help="Telescope, SpaceTelescope, Source, Scan, IF, ...")
    spoiled.set_defaults(run=affected)

    checked = commands.add_parser(
        "check", help="say what is wrong with a session, without running it")
    checked.add_argument("project")
    checked.add_argument("session")
    checked.set_defaults(run=check)

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
