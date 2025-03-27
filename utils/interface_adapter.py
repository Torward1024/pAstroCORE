# utils/interface_adapter.py
from typing import Any, Dict, Callable, Optional, Union
from base.project import Project
from base.observation import Observation
from utils.logging_setup import logger

class InterfaceAdapter:
    """Adapt various interface inputs to Manipulator attributes.

    Attributes:
        converters (Dict[str, Callable[[Any], Dict[str, Any]]]): Registered converters for operation/target pairs.

    Methods:
        register_converter: Register a custom converter for a specific operation and target.
        convert: Convert raw input data into attributes dictionary using the appropriate converter.
        register_default_converters: Register built-in converters for all operations and targets.
    """
    def __init__(self):
        """Initialize the InterfaceAdapter."""
        self.converters: Dict[str, Callable[[Any], Dict[str, Any]]] = {}
        self.register_default_converters()
        logger.info("Initialized InterfaceAdapter with default converters")

    def register_converter(self, operation: str, target: str, converter: Callable[[Any], Dict[str, Any]]) -> None:
        """Register a converter for a specific operation and target."""
        key = f"{operation}/{target}"
        self.converters[key] = converter
        logger.debug(f"Registered converter for {key}")

    def convert(self, operation: str, target: str, raw_data: Any) -> Dict[str, Any]:
        """Convert raw input data into attributes dictionary."""
        key = f"{operation}/{target}"
        converter = self.converters.get(key)
        if not converter:
            logger.error(f"No converter registered for {key}")
            raise ValueError(f"No converter registered for {operation}/{target}")
        
        try:
            attributes = converter(raw_data)
            if not isinstance(attributes, dict):
                logger.error(f"Converter for {key} returned non-dict: {type(attributes)}")
                raise ValueError(f"Converter must return a dictionary, got {type(attributes)}")
            logger.debug(f"Converted raw data for {key}: {attributes}")
            return attributes
        except Exception as e:
            logger.error(f"Failed to convert data for {key}: {str(e)}")
            raise ValueError(f"Conversion failed: {str(e)}")

    def register_default_converters(self) -> None:
        """Register default converters for all operations and targets."""
        # Configure operations
        self.register_converter("configure", "project", self._configure_project_converter)
        self.register_converter("configure", "observation", self._configure_observation_converter)
        self.register_converter("configure", "telescope", self._configure_telescope_converter)
        self.register_converter("configure", "telescopes", self._configure_telescopes_converter)
        self.register_converter("configure", "source", self._configure_source_converter)
        self.register_converter("configure", "sources", self._configure_sources_converter)
        self.register_converter("configure", "frequency", self._configure_frequency_converter)
        self.register_converter("configure", "frequencies", self._configure_frequencies_converter)
        self.register_converter("configure", "scan", self._configure_scan_converter)
        self.register_converter("configure", "scans", self._configure_scans_converter)

        # Inspect operations
        self.register_converter("inspect", "project", self._inspect_project_converter)
        self.register_converter("inspect", "observation", self._inspect_observation_converter)
        self.register_converter("inspect", "telescope", self._inspect_telescope_converter)
        self.register_converter("inspect", "telescopes", self._inspect_telescopes_converter)
        self.register_converter("inspect", "source", self._inspect_source_converter)
        self.register_converter("inspect", "sources", self._inspect_sources_converter)
        self.register_converter("inspect", "frequency", self._inspect_frequency_converter)
        self.register_converter("inspect", "frequencies", self._inspect_frequencies_converter)
        self.register_converter("inspect", "scan", self._inspect_scan_converter)
        self.register_converter("inspect", "scans", self._inspect_scans_converter)

        # Calculate operations
        self.register_converter("calculate", "project", self._calculate_project_converter)
        self.register_converter("calculate", "observation", self._calculate_observation_converter)

    # --- Configure Converters ---
    def _configure_project_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["set_name"] = {"name": str(raw_data[0])}
            if len(raw_data) > 1 and isinstance(raw_data[1], int):
                attributes["observation_index"] = int(raw_data[1])
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["set_name"] = {"name": str(data.get("name", "UnnamedProject"))}
            if "observation_index" in data:
                attributes["observation_index"] = int(data["observation_index"])
        else:
            raise ValueError(f"Unsupported data type for project configuration: {type(raw_data)}")
        return attributes

    def _configure_observation_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["observation_index"] = int(raw_data[0])
            if len(raw_data) > 1:
                attributes["set_observation_code"] = {"code": str(raw_data[1])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["observation_index"] = int(data.get("index", 0))
            if "code" in data:
                attributes["set_observation_code"] = {"code": str(data["code"])}
        else:
            raise ValueError(f"Unsupported data type for observation configuration: {type(raw_data)}")
        return attributes

    def _configure_telescope_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 2:
            attributes["telescope_index"] = int(raw_data[0])
            attributes["set_name"] = {"name": str(raw_data[1])}
            if len(raw_data) > 2:
                attributes["set_code"] = {"code": str(raw_data[2])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["telescope_index"] = int(data.get("index", 0))
            attributes["set_name"] = {"name": str(data.get("name", "UnnamedTelescope"))}
            if "code" in data:
                attributes["set_code"] = {"code": str(data["code"])}
        else:
            raise ValueError(f"Unsupported data type for telescope configuration: {type(raw_data)}")
        return attributes

    def _configure_telescopes_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["add_telescope"] = {"name": str(raw_data[0])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["add_telescope"] = {"name": str(data.get("name", "UnnamedTelescope"))}
        else:
            raise ValueError(f"Unsupported data type for telescopes configuration: {type(raw_data)}")
        return attributes

    def _configure_source_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 2:
            attributes["source_index"] = int(raw_data[0])
            attributes["set_name"] = {"name": str(raw_data[1])}
            if len(raw_data) > 2:
                attributes["set_ra"] = {"ra_h": float(raw_data[2])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["source_index"] = int(data.get("index", 0))
            attributes["set_name"] = {"name": str(data.get("name", "UnnamedSource"))}
            if "ra" in data:
                attributes["set_ra"] = {"ra_h": float(data["ra"])}
        else:
            raise ValueError(f"Unsupported data type for source configuration: {type(raw_data)}")
        return attributes

    def _configure_sources_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["add_source"] = {"name": str(raw_data[0])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["add_source"] = {"name": str(data.get("name", "UnnamedSource"))}
        else:
            raise ValueError(f"Unsupported data type for sources configuration: {type(raw_data)}")
        return attributes

    def _configure_frequency_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 2:
            attributes["if_index"] = int(raw_data[0])
            attributes["set_frequency"] = {"freq": float(raw_data[1])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["if_index"] = int(data.get("index", 0))
            attributes["set_frequency"] = {"freq": float(data.get("freq", 0.0))}
        else:
            raise ValueError(f"Unsupported data type for frequency configuration: {type(raw_data)}")
        return attributes

    def _configure_frequencies_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["add_IF"] = {"freq": float(raw_data[0])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["add_IF"] = {"freq": float(data.get("freq", 0.0))}
        else:
            raise ValueError(f"Unsupported data type for frequencies configuration: {type(raw_data)}")
        return attributes

    def _configure_scan_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 2:
            attributes["scan_index"] = int(raw_data[0])
            attributes["set_start"] = {"start": float(raw_data[1])}
            if len(raw_data) > 2:
                attributes["set_duration"] = {"duration": float(raw_data[2])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["scan_index"] = int(data.get("index", 0))
            attributes["set_start"] = {"start": float(data.get("start", 0.0))}
            if "duration" in data:
                attributes["set_duration"] = {"duration": float(data["duration"])}
        else:
            raise ValueError(f"Unsupported data type for scan configuration: {type(raw_data)}")
        return attributes

    def _configure_scans_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["add_scan"] = {"start": float(raw_data[0])}
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["add_scan"] = {"start": float(data.get("start", 0.0))}
        else:
            raise ValueError(f"Unsupported data type for scans configuration: {type(raw_data)}")
        return attributes

    # --- Inspect Converters ---
    def _inspect_project_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            if len(raw_data) == 1:
                attributes["get_name"] = None
            else:
                attributes["observation_index"] = int(raw_data[0])
                attributes["get_observation_code"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            if "index" in data:
                attributes["observation_index"] = int(data["index"])
                attributes["get_observation_code"] = None
            else:
                attributes["get_name"] = None
        else:
            raise ValueError(f"Unsupported data type for project inspection: {type(raw_data)}")
        return attributes

    def _inspect_observation_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["observation_index"] = int(raw_data[0])
            attributes["get_observation_code"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["observation_index"] = int(data.get("index", 0))
            attributes["get_observation_code"] = None
        else:
            raise ValueError(f"Unsupported data type for observation inspection: {type(raw_data)}")
        return attributes

    def _inspect_telescope_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["telescope_index"] = int(raw_data[0])
            attributes["get_name"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["telescope_index"] = int(data.get("index", 0))
            attributes["get_name"] = None
        else:
            raise ValueError(f"Unsupported data type for telescope inspection: {type(raw_data)}")
        return attributes

    def _inspect_telescopes_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["get_all_telescopes"] = None
        elif hasattr(raw_data, "__dict__"):
            attributes["get_all_telescopes"] = None
        else:
            raise ValueError(f"Unsupported data type for telescopes inspection: {type(raw_data)}")
        return attributes

    def _inspect_source_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["source_index"] = int(raw_data[0])
            attributes["get_name"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["source_index"] = int(data.get("index", 0))
            attributes["get_name"] = None
        else:
            raise ValueError(f"Unsupported data type for source inspection: {type(raw_data)}")
        return attributes

    def _inspect_sources_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["get_all_sources"] = None
        elif hasattr(raw_data, "__dict__"):
            attributes["get_all_sources"] = None
        else:
            raise ValueError(f"Unsupported data type for sources inspection: {type(raw_data)}")
        return attributes

    def _inspect_frequency_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["if_index"] = int(raw_data[0])
            attributes["get_frequency"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["if_index"] = int(data.get("index", 0))
            attributes["get_frequency"] = None
        else:
            raise ValueError(f"Unsupported data type for frequency inspection: {type(raw_data)}")
        return attributes

    def _inspect_frequencies_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["get_all_IF"] = None
        elif hasattr(raw_data, "__dict__"):
            attributes["get_all_IF"] = None
        else:
            raise ValueError(f"Unsupported data type for frequencies inspection: {type(raw_data)}")
        return attributes

    def _inspect_scan_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["scan_index"] = int(raw_data[0])
            attributes["get_start"] = None
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["scan_index"] = int(data.get("index", 0))
            attributes["get_start"] = None
        else:
            raise ValueError(f"Unsupported data type for scan inspection: {type(raw_data)}")
        return attributes

    def _inspect_scans_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["get_all_scans"] = None
        elif hasattr(raw_data, "__dict__"):
            attributes["get_all_scans"] = None
        else:
            raise ValueError(f"Unsupported data type for scans inspection: {type(raw_data)}")
        return attributes

    # --- Calculate Converters ---
    def _calculate_project_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 1:
            attributes["type"] = str(raw_data[0])
            if len(raw_data) > 1:
                attributes["time_step"] = float(raw_data[1])
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["type"] = str(data.get("type", "telescope_positions"))
            if "time_step" in data:
                attributes["time_step"] = float(data["time_step"])
        else:
            raise ValueError(f"Unsupported data type for project calculation: {type(raw_data)}")
        return attributes

    def _calculate_observation_converter(self, raw_data: Any) -> Dict[str, Any]:
        attributes = {}
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, (list, tuple)) and len(raw_data) >= 2:
            attributes["observation_index"] = int(raw_data[0])
            attributes["type"] = str(raw_data[1])
            if len(raw_data) > 2:
                attributes["time_step"] = float(raw_data[2])
        elif hasattr(raw_data, "__dict__"):
            data = raw_data.__dict__
            attributes["observation_index"] = int(data.get("index", 0))
            attributes["type"] = str(data.get("type", "telescope_positions"))
            if "time_step" in data:
                attributes["time_step"] = float(data["time_step"])
        else:
            raise ValueError(f"Unsupported data type for observation calculation: {type(raw_data)}")
        return attributes

    def __repr__(self) -> str:
        """String representation of InterfaceAdapter."""
        return f"InterfaceAdapter(converters={len(self.converters)})"