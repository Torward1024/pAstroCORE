# /unit_scheduling/cli/cli_interface.py
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory

from unit_scheduling.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger
import logging.handlers
import queue
import threading
import json
from typing import Dict, Any, List, Optional

class CLIInterface:
    """CLI interface for pAstroCORE with Vim-like commands and three-pane layout."""
    def __init__(self, manipulator: ScheduleManipulator):
        self.manipulator = manipulator
        self.output_text = f"pAstroCORE CLI - Project: {manipulator.get_managing_object().get_name()}\n"
        self.output_area = Window(
            content=FormattedTextControl(text=lambda: self.output_text),
            height=20,
            wrap_lines=True
        )
        self.log_text = ""
        self.log_area = Window(
            content=FormattedTextControl(text=lambda: self.log_text),
            width=40,
            wrap_lines=True
        )
        self.history = InMemoryHistory()
        self.input_area = TextArea(
            height=3,
            prompt="> ",
            multiline=False,
            accept_handler=self._execute_command,
            history=self.history
        )
        self.log_queue = queue.Queue()
        self.app = None
        self._setup_logging()
        self._setup_completer()
        self._start_log_listener()
        logger.info("CLI Interface initialized")

    def _setup_logging(self):
        """Configure logging to redirect to the log area."""
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        logger.handlers = [queue_handler]
        logger.setLevel(logging.INFO)

    def _setup_completer(self):
        """Set up nested autocompletion based on command structure and project data."""
        project = self.manipulator.get_managing_object()
        project_names = {f'"{project.get_name()}"'}
        observation_names = {f'"{obs.get_observation_code()}"' for obs in project.get_items()}
        operations = self.manipulator.get_supported_operations()
        methods = set()
        for cls in self.manipulator._base_classes:
            methods.update(self.manipulator.get_methods_for_type(cls).keys())

        completer_dict = {
            "show": {"project": project_names, "observation": observation_names},
            "save": None,
            "load": None,
            "help": {"show", "save", "load", "exit", "quit"} | set(operations),
            "exit": None,
            "quit": None
        }
        for op in operations:
            set_methods = {m.split("set_")[1]: {"VALUE"} for m in methods if m.startswith("set_")}
            get_methods = {m.split("get_")[1]: None for m in methods if m.startswith("get_")}
            completer_dict[op] = {
                "project": project_names,
                "observation": observation_names,
                "set": set_methods,
                "get": get_methods
            }
        self.input_area.completer = NestedCompleter.from_nested_dict(completer_dict)

    def _start_log_listener(self):
        """Start a thread to listen for log messages and update the log area."""
        def log_listener():
            while True:
                try:
                    record = self.log_queue.get()
                    if record is None:
                        break
                    msg = f"{record.levelname}: {record.message}\n"
                    self.log_text += msg
                    if self.app:
                        self.app.invalidate()
                except Exception as e:
                    self.log_text += f"Log error: {str(e)}\n"
                    if self.app:
                        self.app.invalidate()
        thread = threading.Thread(target=log_listener, daemon=True)
        thread.start()

    def _execute_command(self, buffer):
        """Execute a command entered by the user."""
        command = buffer.text.strip()
        if command.lower() in ["exit", "quit"]:
            self.log_queue.put(None)
            self.app.exit()
            return False
        self._parse_and_execute(command)
        if self.app:
            self.app.invalidate()
        self.input_area.text = ""
        return True

    def _parse_and_execute(self, command: str):
        """Parse and execute the command."""
        tokens = command.split()
        if not tokens:
            return

        cmd = tokens[0].lower()
        if cmd in self.manipulator.get_supported_operations():
            self._execute_operation(cmd, tokens[1:])
        elif cmd == "show":
            self._handle_show(tokens[1:])
        elif cmd == "save":
            self._handle_save(tokens[1:])
        elif cmd == "load":
            self._handle_load(tokens[1:])
        elif cmd == "help":
            self._handle_help(tokens[1:])
        else:
            self.output_text += f"Unknown command: {command}\n"
            logger.error(f"Unknown command: {command}")

    def _get_object(self, obj_type: str, obj_name: str) -> Optional[Any]:
        """Retrieve an object by type and name."""
        obj_name = obj_name.strip('"')
        project = self.manipulator.get_managing_object()
        if obj_type == "project" and project.get_name() == obj_name:
            return project
        elif obj_type == "observation":
            for obs in project.get_items():
                if obs.get_observation_code() == obj_name:
                    return obs
        return None

    def _parse_attributes(self, tokens: List[str], obj_type: str) -> Dict[str, Any]:
        """Parse attributes from tokens into a request-compatible dictionary."""
        attributes = {}
        sub_attributes = {}
        i = 0
        while i < len(tokens):
            token = tokens[i].lower()
            if token == "set":
                i += 1
                if i >= len(tokens):
                    break
                param_name = tokens[i]
                i += 1
                value = tokens[i].strip('"') if i < len(tokens) else None
                if value:
                    attributes["method"] = "set_name"
                    sub_attributes[param_name] = value
                break
            elif token == "get":
                i += 1
                if i >= len(tokens):
                    break
                param_name = tokens[i]
                attributes["method"] = f"get_{param_name}"
                break
            i += 1
        if sub_attributes:
            attributes["attributes"] = sub_attributes
        return attributes

    def _execute_operation(self, operation: str, tokens: List[str]):
        """Execute an operation on an object."""
        if len(tokens) < 2:
            self.output_text += f"Usage: {operation} <type> 'name' [attributes]\n"
            return
        obj_type = tokens[0].lower()
        obj_name = tokens[1]
        if not (obj_name.startswith('"') and obj_name.endswith('"')):
            self.output_text += "Object name must be in quotes, e.g., 'TestProject'\n"
            return
        obj = self._get_object(obj_type, obj_name)
        if not obj:
            self.output_text += f"{obj_type.capitalize()} '{obj_name.strip('\"')}' not found\n"
            return

        attributes = self._parse_attributes(tokens[2:], obj_type)
        request = {
            "operation": operation,
            "obj": obj,
            "method": "_configure_project" if obj_type == "project" else "_configure_observation"
        }
        if attributes:
            request["attributes"] = attributes
        try:
            result = self.manipulator.process_request(request)
            self.output_text += f"{operation.capitalize()} result: {result}\n"
            logger.info(f"Executed {operation} on {obj_type} '{obj_name}': {result}")
        except Exception as e:
            self.output_text += f"Error: {str(e)}\n"
            logger.error(f"Failed to execute {operation}: {str(e)}")

    def _handle_show(self, tokens: List[str]):
        """Handle the 'show' command to display objects."""
        if len(tokens) < 2 or tokens[0].lower() not in ["project", "observation"]:
            self.output_text += "Usage: show project|observation 'name'\n"
            return
        obj_type, obj_name = tokens[0].lower(), tokens[1]
        if not (obj_name.startswith('"') and obj_name.endswith('"')):
            self.output_text += "Object name must be in quotes, e.g., 'TestProject'\n"
            return
        obj = self._get_object(obj_type, obj_name)
        if obj:
            self.output_text += f"{repr(obj)}\n{json.dumps(obj.to_dict(), indent=2)}\n"
        else:
            self.output_text += f"{obj_type.capitalize()} '{obj_name.strip('\"')}' not found\n"

    def _handle_save(self, tokens: List[str]):
        """Handle the 'save' command to save the project to a file."""
        if len(tokens) < 1:
            self.output_text += "Usage: save 'filename'\n"
            return
        filename = tokens[0]
        if not (filename.startswith('"') and filename.endswith('"')):
            self.output_text += "Filename must be in quotes, e.g., 'test.json'\n"
            return
        filename = filename.strip('"')
        project = self.manipulator.get_managing_object()
        try:
            with open(filename, 'w') as f:
                json.dump(project.to_dict(), f, indent=2)
            self.output_text += f"Project saved to '{filename}'\n"
            logger.info(f"Project saved to {filename}")
        except Exception as e:
            self.output_text += f"Error saving project: {str(e)}\n"
            logger.error(f"Failed to save project: {str(e)}")

    def _handle_load(self, tokens: List[str]):
        """Handle the 'load' command to load a project from a file."""
        if len(tokens) < 1:
            self.output_text += "Usage: load 'filename'\n"
            return
        filename = tokens[0]
        if not (filename.startswith('"') and filename.endswith('"')):
            self.output_text += "Filename must be in quotes, e.g., 'test.json'\n"
            return
        filename = filename.strip('"')
        from main import load_project_from_file  # Avoid circular import
        project = load_project_from_file(filename)
        if project:
            self.manipulator.set_managing_object(project)
            self.output_text += f"Loaded project '{project.get_name()}' from '{filename}'\n"
            logger.info(f"Loaded project from {filename}")
            self._setup_completer()  # Update completer with new project data
        else:
            self.output_text += f"Failed to load project from '{filename}'\n"

    def _handle_help(self, tokens: List[str]):
        """Handle the 'help' command to display usage instructions."""
        help_text = "pAstroCORE CLI Help\n==================\n\n"
        if not tokens:
            help_text += (
                "This CLI provides a Vim-like interface for managing astronomical scheduling projects.\n"
                "Commands are case-insensitive, object names are case-sensitive and must be quoted.\n"
                "Use Tab for autocompletion, Up/Down for history, Ctrl+C to exit.\n\n"
                "Available Commands:\n"
                "  help [command]      - Show this help or detailed help for a command.\n"
                "  show <type> 'name' - Display details of a project or observation.\n"
                "  save 'filename'    - Save the current project to a JSON file.\n"
                "  load 'filename'    - Load a project from a JSON file.\n"
                "  <operation> <type> 'name' [attributes] - Execute an operation.\n"
                "  exit/quit           - Exit the CLI.\n\n"
                "Supported Types:\n"
                "  project, observation\n\n"
                "Supported Operations:\n"
                f"  {', '.join(self.manipulator.get_supported_operations())}\n"
            )
        else:
            cmd = tokens[0].lower()
            if cmd == "show":
                help_text += (
                    "Command: show\n"
                    "Usage: show <type> 'name'\n"
                    "Description: Displays details of a project or observation.\n"
                    "Examples:\n"
                    "  > show project 'TestProject'\n"
                    "  > show observation 'OBS001'\n"
                )
            elif cmd == "save":
                help_text += (
                    "Command: save\n"
                    "Usage: save 'filename'\n"
                    "Description: Saves the project to a JSON file.\n"
                    "Examples:\n"
                    "  > save 'test.json'\n"
                )
            elif cmd == "load":
                help_text += (
                    "Command: load\n"
                    "Usage: load 'filename'\n"
                    "Description: Loads a project from a JSON file.\n"
                    "Examples:\n"
                    "  > load 'test.json'\n"
                )
            elif cmd in self.manipulator.get_supported_operations():
                help_text += (
                    f"Command: {cmd}\n"
                    f"Usage: {cmd} <type> 'name' [set|get <param> 'value']\n"
                    f"Description: Performs '{cmd}' on an object.\n"
                    "Examples:\n"
                    f"  > {cmd} project 'TestProject' set name 'NewName'\n"
                    f"  > {cmd} observation 'OBS001' get observation_code\n"
                )
            elif cmd in ["exit", "quit"]:
                help_text += (
                    f"Command: {cmd}\n"
                    f"Usage: {cmd}\n"
                    "Description: Exits the CLI.\n"
                )
            else:
                help_text += f"Unknown command '{cmd}'. Use 'help' for available commands.\n"
        self.output_text += help_text + "\n"

    def run(self):
        """Run the CLI application with history navigation."""
        layout = Layout(
            VSplit([
                HSplit([
                    self.output_area,
                    self.input_area,
                ]),
                self.log_area,
            ])
        )
        bindings = KeyBindings()

        @bindings.add("up")
        def _(event):
            if self.input_area.buffer.history:
                self.input_area.buffer.history_backward()
                event.app.invalidate()

        @bindings.add("down")
        def _(event):
            if self.input_area.buffer.history:
                self.input_area.buffer.history_forward()
                event.app.invalidate()

        @bindings.add("c-c")
        def _(event):
            self.log_queue.put(None)
            event.app.exit()

        self.app = Application(layout=layout, key_bindings=bindings, full_screen=True)
        self.app.run()