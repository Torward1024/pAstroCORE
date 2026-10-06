"""Write the fixture project out as a directory, for something to open.

Usage:
    python tools/write_fixture.py <directory>

Notes:
    - A build is checked by opening a project, and the project has to be on disk before the
      build is started. This is what puts it there, in CI and by hand alike.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "test_project.pastro"


def main():
    if len(sys.argv) != 2:
        sys.exit("one argument: where to write the project")
    sys.path.insert(0, str(ROOT))
    from pastrocore.super.schedule_project import ScheduleProject

    into = pathlib.Path(sys.argv[1]).resolve()
    ScheduleProject.from_dict(
        json.loads(FIXTURE.read_text(encoding="utf-8"))).to_directory(str(into))
    print(into)


if __name__ == "__main__":
    main()
