# /pAstroCORE/main_gui.py
import sys
import os

# Add the root directory (pAstroCORE) to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)

from PySide6.QtWidgets import QApplication
from unit_scheduling_2.gui.main_window import MainWindow
from unit_scheduling_2.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling_2.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        manipulator = ScheduleManipulator(ScheduleProject(name="TestProject"))
        window = MainWindow(manipulator)
        window.show()
        logger.info("Started pAstroCORE application")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        raise