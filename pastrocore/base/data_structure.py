# base/data_structure.py
from typing import Dict, List, Type, Optional
from astropy.time import Time
import numpy as np
import pandas as pd

class CalculatedDataStructure:
    """Schema definition for calculated data DataFrames."""
    SCHEMAS = {
        "times": {
            "columns": ["source_name", "scan_name", "time"],
            "metadata": {
                "time_step": float,
                "time_threshold": float,
                "start_time": Time,
                "end_time": Time,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "interpolated_orbits": {
            "columns": ["time", "scan_name", "telescope_code", "x", "y", "z"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "telescope_positions": {
            "columns": ["time", "scan_name", "telescope_code", "x", "y", "z"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "source_visibility": {
            "columns": ["time", "source_name", "scan_name", "telescope_code", "visibility"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "uv_coverage": {
            "columns": ["time", "source_name", "scan_name", "baseline", "u", "v", "w"],
            "metadata": {
                "time_step": float,
                "scan_count": int
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "beam_pattern": {
            "columns": ["telescope_code", "theta", "pattern"],
            "metadata": {
                "telescope_count": int,
                "frequency_agnostic": bool,
                "scale_instruction": str
            },
            "converters": {}
        },
        "time_on_source": {
            "columns": ["source_name", "scan_name", "telescope_code", "start", "end", "duration"],
            "metadata": {},
            "converters": {
                "start": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x),
                "end": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "az_el": {
            "columns": ["time", "source_name", "scan_name", "telescope_code", "az", "el"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str,
                "visibility_store_key": str
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "sun_angles": {
            "columns": ["time", "source_name", "scan_name", "telescope_code", "angle"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "position_store_key": str,
                "visibility_store_key": str
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "baseline_projections": {
            "columns": ["time", "source_name", "scan_name", "baseline", "projection"],
            "metadata": {},
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x)
            }
        },
        "mollweide_tracks": {
            "columns": ["time", "scan_name", "telescope_code", "lon", "lat"],
            "metadata": {
                "time_step": float,
                "scan_count": int,
                "sources": dict
            },
            "converters": {
                "time": lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and pd.notna(x) else (x.isot if isinstance(x, Time) and pd.notna(x) else x),
                "sources": lambda x: {k: np.array(v) for k, v in x.items()}
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
        """Return converters for specific columns or metadata for a given calculated data key."""
        schema = cls.SCHEMAS.get(key)
        return schema["converters"] if schema else None