# /main_scheduler_gui.py
import sys
from PySide6.QtWidgets import QApplication
from unit_scheduling.gui.main_window import MainWindow
from unit_scheduling.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger
from typing import Optional

def run_gui(project: Optional[ScheduleProject] = None) -> None:
    """Launch the pAstroCORE GUI application.

    Args:
        project (Optional[ScheduleProject]): The initial ScheduleProject to load into the GUI.
            If None, a default project is created.

    Notes:
        - Initializes the QApplication and MainWindow.
        - Sets up the main event loop.
    """
    logger.info("Starting pAstroCORE GUI application")
    app = QApplication(sys.argv)
    
    # сreate the main window with an optional project
    window = MainWindow(project)
    window.show()
    
    # start the event loop
    exit_code = app.exec()
    logger.info(f"pAstroCORE GUI application closed with exit code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    # Example: Optionally pass a pre-configured project
    # project = ScheduleProject(name="ExampleProject")
    # run_gui(project)
    run_gui()  # launch with default project