# base/data_structure.py
from typing import Dict, List, Type, Optional
import numpy as np
import polars as pl

class CalculatedDataStructure:
    """Schema definition for calculated data Polars DataFrames."""
    SCHEMAS = {
        "times": {
            "label": "Time Arrays",
            # The one calculation whose handler and store key differ: `_calculate_time_arrays`
            # files its result under `times`. Stated here so the catalogue, which knows only
            # handler names, can find this entry -- rather than special-cased where it is read.
            "handler": "time_arrays",
            "intermediate": True,
            # Sampled per *active source* -- one block each, and a `source_name` column to say
            # which -- so a source going inactive changes the answer. It said `("scans",)`, and
            # the result stayed "current" while holding rows for a source no longer observed.
            # Every calculation below it inherits the mistake, since they all start here.
            "depends_on": ("scans", "sources"),
            "columns": ["source_name", "scan_name", "time"],
            "metadata": {
                "time_step": float,
                "time_threshold": float,
                "start_time": float,
                "end_time": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None,
                "start_time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None,
                "end_time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "source_name": pl.String,
                "scan_name": pl.String,
                "time": pl.Float64
            }
        },
        "interpolated_orbits": {
            "intermediate": True,
            # A question for the observation, asked by name: without a spacecraft placed from an
            # orbit file there is nothing to interpolate, and the step is left out of a plan.
            "only_if": "has_orbit_file_telescopes",
            "depends_on": ("telescopes", "scans"),
            "columns": ["time", "scan_name", "telescope_code", "x", "y", "z"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "x": pl.Float64,
                "y": pl.Float64,
                "z": pl.Float64
            }
        },
        "telescope_positions": {
            "intermediate": True,
            "depends_on": ("telescopes", "scans"),
            "columns": ["time", "scan_name", "telescope_code", "x", "y", "z"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "x": pl.Float64,
                "y": pl.Float64,
                "z": pl.Float64
            }
        },
        "source_visibility": {
            "intermediate": True,
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["time", "source_name", "scan_name", "telescope_code", "visibility"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "visibility": pl.Boolean
            }
        },
        "uv_coverage": {
            "label": "UV Coverage",
            "depends_on": ("telescopes", "sources", "scans", "frequencies"),
            "columns": ["time", "source_name", "scan_name", "baseline", "u", "v", "w"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "baseline": pl.String,
                "u": pl.Float64,
                "v": pl.Float64,
                "w": pl.Float64
            }
        },
        "beam_pattern": {
            # Not frequencies: one curve per dish, given a frequency when it is drawn. Declaring
            # them marked the beam stale whenever a band was edited, and nothing had changed.
            "depends_on": ("telescopes",),
            "columns": ["telescope_code", "theta", "pattern"],
            "metadata": {
                "telescope_count": int,
                "scale_instruction": str
            },
            "converters": {},
            "deserialization_converters": {},
            "dtypes": {
                "telescope_code": pl.String,
                "theta": pl.Float64,
                "pattern": pl.Float64
            }
        },
        "time_on_source": {
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["source_name", "scan_name", "telescope_code", "start", "end", "duration"],
            "metadata": {},
            "converters": {
                "start": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None,
                "end": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "source_name": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "start": pl.Float64,
                "end": pl.Float64,
                "duration": pl.Float64
            }
        },
        "telescope_az_el": {
            "label": "Space Telescope Pointing",
            "depends_on": ("telescopes", "scans"),
            "columns": ["time", "target_code", "scan_name", "telescope_code", "az", "el", "range"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "target_code": str,
                "position_store_key": str,
                "orbit_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "target_code": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "az": pl.Float64,
                "el": pl.Float64,
                "range": pl.Float64
            }
        },
        "telescope_visibility": {
            "label": "Space Telescope Visibility",
            "depends_on": ("telescopes", "scans"),
            "columns": ["time", "target_code", "scan_name", "telescope_code", "visibility"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "target_code": str,
                "az_el_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "target_code": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "visibility": pl.Boolean
            }
        },
        "az_el": {
            "label": "Az/El",
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["time", "source_name", "scan_name", "telescope_code", "az", "el"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str,
                "visibility_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "az": pl.Float64,
                "el": pl.Float64
            }
        },
        "sun_angles": {
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["time", "source_name", "scan_name", "telescope_code", "angle"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str,
                "visibility_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "angle": pl.Float64
            }
        },
        "baseline_projections": {
            "depends_on": ("telescopes", "sources", "scans", "frequencies"),
            "columns": ["time", "source_name", "scan_name", "baseline", "projection"],
            "metadata": {},
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "baseline": pl.String,
                "projection": pl.Float64
            }
        },
        "mollweide_tracks": {
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["time", "scan_name", "telescope_code", "lon", "lat"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "sources": dict
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None,
                "sources": lambda x: {k: np.array(v).tolist() for k, v in x.items()} if isinstance(x, dict) else {}
            },
            "deserialization_converters": {
                "sources": lambda x: {k: np.array(v) for k, v in x.items()} if isinstance(x, dict) else {}
            },
            "dtypes": {
                "time": pl.Float64,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "lon": pl.Float64,
                "lat": pl.Float64
            }  
        },
        "parallactic_angle": {
            "depends_on": ("telescopes", "sources", "scans"),
            "columns": ["time", "source_name", "scan_name", "telescope_code", "parallactic_angle"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str,
                "visibility_store_key": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "source_name": pl.String,
                "scan_name": pl.String,
                "telescope_code": pl.String,
                "parallactic_angle": pl.Float64
            }
        },
        "sefd": {
            # E1. Not scans or sources: a station's SEFD in a band depends on the station and the
            # band and on nothing else.
            "label": "SEFD",
            "depends_on": ("telescopes", "frequencies"),
            "columns": ["telescope_code", "if_name", "frequency", "bandwidth", "sefd", "origin",
                        "tsys", "effective_area", "efficiency", "basis", "reason", "filled"],
            "metadata": {
                "filled": int
            },
            "converters": {},
            "deserialization_converters": {},
            "dtypes": {
                "telescope_code": pl.String,
                "if_name": pl.String,
                "frequency": pl.Float64,
                "bandwidth": pl.Float64,
                "sefd": pl.Float64,
                "origin": pl.String,
                "tsys": pl.Float64,
                "effective_area": pl.Float64,
                "efficiency": pl.Float64,
                "basis": pl.String,
                "reason": pl.String,
                "filled": pl.Boolean
            }
        },
        "sefd_track": {
            # E1. A station's SEFD at every sample of the time grid, from where the source stands:
            # one row per sample, station and band. The weather and the gain curves it was worked
            # out with are parameters, not the stations', so they are recorded here.
            "label": "SEFD Track",
            "depends_on": ("telescopes", "sources", "scans", "frequencies"),
            "columns": ["time", "scan_name", "source_name", "telescope_code", "if_name", "frequency",
                        "elevation", "airmass", "opacity", "attenuation", "tsys", "gain",
                        "sefd_zenith", "sefd", "basis", "reason"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "opacity": list,
                "t_atm": float,
                "gain_curve": dict,
                "assumption": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "scan_name": pl.String,
                "source_name": pl.String,
                "telescope_code": pl.String,
                "if_name": pl.String,
                "frequency": pl.Float64,
                "elevation": pl.Float64,
                "airmass": pl.Float64,
                "opacity": pl.Float64,
                "attenuation": pl.Float64,
                "tsys": pl.Float64,
                "gain": pl.Float64,
                "sefd_zenith": pl.Float64,
                "sefd": pl.Float64,
                "basis": pl.String,
                "reason": pl.String
            }
        },
        "baseline_sensitivity": {
            # E1. One row per scan, baseline and band, and one with `if_name` "all" for the bands
            # together. `time` is the scan's start, so the analyzer can find runs of detection.
            "label": "Baseline Sensitivity",
            "depends_on": ("telescopes", "sources", "scans", "frequencies"),
            "columns": ["time", "scan_name", "source_name", "baseline", "if_name", "frequency",
                        "bandwidth", "scan_duration", "duration", "sefd_1", "sefd_2", "noise_1s",
                        "noise", "flux", "flux_basis", "snr", "detected", "min_duration", "reason"],
            "metadata": {
                "threshold": float,
                "bits": int,
                "recording_efficiency": float,
                "opacity": list,
                "t_atm": float,
                "gain_curve": dict,
                "time_step": float,
                "scan_count": int,
                "assumption": str
            },
            "converters": {
                "time": lambda x: float(x) if isinstance(x, (int, float)) and x is not None else None
            },
            "deserialization_converters": {},
            "dtypes": {
                "time": pl.Float64,
                "scan_name": pl.String,
                "source_name": pl.String,
                "baseline": pl.String,
                "if_name": pl.String,
                "frequency": pl.Float64,
                "bandwidth": pl.Float64,
                "scan_duration": pl.Float64,
                "duration": pl.Float64,
                "sefd_1": pl.Float64,
                "sefd_2": pl.Float64,
                "noise_1s": pl.Float64,
                "noise": pl.Float64,
                "flux": pl.Float64,
                "flux_basis": pl.String,
                "snr": pl.Float64,
                "detected": pl.Boolean,
                "min_duration": pl.Float64,
                "reason": pl.String
            }
        }
    }

    @classmethod
    def get_columns(cls, key: str) -> Optional[List[str]]:
        """Return expected columns for a given calculated data key."""
        schema = cls.SCHEMAS.get(key)
        return schema["columns"] if schema else None

    @classmethod
    def get_metadata_types(cls, key: str) -> Optional[Dict[str, Type]]:
        """Return expected metadata types for a given calculated data key."""
        schema = cls.SCHEMAS.get(key)
        return schema["metadata"] if schema else None

    @classmethod
    def get_converters(cls, key: str) -> Optional[Dict[str, callable]]:
        """Return converters for specific columns or metadata for serialization."""
        schema = cls.SCHEMAS.get(key)
        return schema["converters"] if schema else None

    @classmethod
    def get_deserialization_converters(cls, key: str) -> Optional[Dict[str, callable]]:
        """Return converters for specific columns or metadata for deserialization."""
        schema = cls.SCHEMAS.get(key)
        return schema["deserialization_converters"] if schema else None

    @classmethod
    def is_intermediate(cls, key: str) -> bool:
        """Report whether a result exists for other calculations rather than for a user.

        Args:
            key (str): The result's store key.

        Returns:
            bool: True for a step nobody asks for by name -- times, positions, orbits,
                visibility. False for everything else, so a calculation added without saying
                otherwise is offered.

        Notes:
            - Declared rather than derived. It cannot be worked out from the graph: `uv_coverage`
              is needed by baseline projections *and* asked for by name, while `source_visibility`
              is only ever a step. One is a leaf, the other is not, and both are required by
              something -- the difference is intent, and intent has to be stated.
        """
        return bool(cls.entry_for(key).get("intermediate", False))

    @classmethod
    def condition_for(cls, key: str) -> Optional[str]:
        """Return the question an observation must answer yes to for this result to exist.

        Args:
            key (str): The result's store key, or its handler's name.

        Returns:
            Optional[str]: The name of an `Observation` method taking no arguments, or None for
                a result every observation can have.

        Notes:
            - Declared beside the result, like everything else about it, and asked of the model
              through a request -- so what makes a calculation pointless is a fact about the
              observation, not a list kept by whoever plans the run.
        """
        return cls.entry_for(key).get("only_if")

    @classmethod
    def uses_time_step(cls, key: str) -> bool:
        """Report whether a calculation is sampled over time.

        Args:
            key (str): The result's store key or its handler's name.

        Returns:
            bool: True when the result's metadata records a `time_step`, which is what a
                calculation sampled over a grid records and one that is not does not.

        Notes:
            - Read from what the schema already declares rather than from a name. The dialog
              used to ask whether "Beam Pattern" was selected, which is the one calculation
              that happens not to be sampled -- a fact about that calculation, spelled as a
              comparison against its title.
        """
        return "time_step" in (cls.entry_for(key).get("metadata") or {})

    @classmethod
    def store_key_for(cls, key: str) -> str:
        """Return the key a calculation's result is filed under.

        Args:
            key (str): A store key or a handler name -- the catalogue speaks the second.

        Returns:
            str: The store key. The same string back, for every calculation whose handler is
                named after its result.

        Notes:
            - `_calculate_time_arrays` files under `times`, and it is the only one where the
              two differ. A caller that passed the handler's name as `store_key` stored the
              result where nothing reads it, and the model said so on every save:
              `Unknown calculated_data key 'time_arrays'`.
        """
        if key in cls.SCHEMAS:
            return key
        for name, candidate in cls.SCHEMAS.items():
            if candidate.get("handler") == key:
                return name
        return key

    @classmethod
    def entry_for(cls, key: str) -> dict:
        """Return a result's schema, found by its store key or by its handler's name.

        Args:
            key (str): Either spelling.

        Returns:
            dict: The entry, or an empty one.

        Notes:
            - The catalogue knows handlers, results are filed under store keys, and for one
              calculation the two differ. Resolving it here means nothing that reads the schema
              has to know which spelling it was handed.
        """
        entry = cls.SCHEMAS.get(key)
        if entry is not None:
            return entry
        for candidate in cls.SCHEMAS.values():
            if candidate.get("handler") == key:
                return candidate
        return {}

    @classmethod
    def get_dependencies(cls, key: str) -> tuple:
        """Return the parts of an observation a result is computed from.

        Args:
            key (str): The result's store key.

        Returns:
            tuple: Names from "telescopes", "sources", "scans", "frequencies". Everything, for
                a key that does not declare them -- safe, and merely coarse.

        Notes:
            - Declared here rather than in a table of its own, because this is the one place a
              new calculation already has to register: it cannot produce a frame without
              dtypes. A separate table would be the file somebody forgets, and forgetting it
              fails quietly by making a result look permanently fresh or permanently stale.
            - The granularity of staleness is exactly this: editing a scan does not make a beam
              pattern stale, and changing a frequency does not move azimuth and elevation.
        """
        schema = cls.SCHEMAS.get(key)
        if not schema or "depends_on" not in schema:
            return ("telescopes", "sources", "scans", "frequencies")
        return tuple(schema["depends_on"])

    @classmethod
    def get_dtypes(cls, key: str) -> Optional[Dict[str, pl.DataType]]:
        """Return expected data types for columns in a given calculated data key."""
        schema = cls.SCHEMAS.get(key)
        return schema["dtypes"] if schema else None