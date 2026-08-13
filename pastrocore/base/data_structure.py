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
            "depends_on": ("telescopes", "frequencies"),
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