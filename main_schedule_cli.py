# /main.py
import argparse
import json
from typing import Optional
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling.cli.cli_interface import CLIInterface
from common.utils.logging_setup import logger

def load_project_from_file(file_path: str) -> Optional[ScheduleProject]:
    """Load a ScheduleProject from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Optional[ScheduleProject]: Loaded project or None if loading fails.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        project = ScheduleProject.from_dict(data)
        logger.info(f"Loaded project '{project.get_name()}' from {file_path}")
        return project
    except Exception as e:
        logger.error(f"Failed to load project from {file_path}: {str(e)}")
        return None

def main():
    """Main entry point for the pAstroCORE application."""
    parser = argparse.ArgumentParser(description="pAstroCORE: Radio Astronomy Scheduling Tool")
    parser.add_argument(
        "--project-file",
        type=str,
        help="Path to a JSON file containing a ScheduleProject",
        default=None
    )
    parser.add_argument(
        "--project-name",
        type=str,
        help="Name for a new project if no file is provided",
        default="DefaultProject"
    )
    args = parser.parse_args()

    # Initialize project
    if args.project_file:
        project = load_project_from_file(args.project_file)
        if not project:
            logger.warning("Failed to load project from file, creating a new one")
            project = ScheduleProject(name=args.project_name)
    else:
        project = ScheduleProject(name=args.project_name)
        logger.info(f"Created new project '{project.get_name()}'")

    # Initialize manipulator
    manipulator = ScheduleManipulator(project=project)

    # Run CLI interface
    cli = CLIInterface(manipulator)
    cli.run()

if __name__ == "__main__":
    main()