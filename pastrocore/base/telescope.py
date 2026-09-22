# base/telescope.py
from copy import deepcopy
from msb_arch.base.baseentity import BaseEntity
from msb_arch.utils.validation import check_type, check_positive
from msb_arch import InvariantError, Positive, Predicate, invariant
from msb_arch.utils.logging_setup import logger
import numpy as np
from typing import Annotated, Any, Dict, List, Optional, Tuple
from enum import Enum
import uuid

# Constants, exact where SI defines them. The speed of light was 3e8, which moved a Ruze loss at
# 86 GHz by a tenth of a percent -- small, and still a number that did not need to be wrong.
SPEED_OF_LIGHT = 299792458.0  # m/s
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K
JANSKY = 1e-26  # W m^-2 Hz^-1

#: One row of a telescope's measured tables: the lowest and highest frequency it applies to, in
#: MHz, and the value measured there.
Row = Tuple[float, float, float]


class MountType(Enum):
    EQUATORIAL = "EQUA"
    AZIMUTHAL = "AZIM"
    SPACE = "NONE"

def _rises(bounds) -> bool:
    """Report whether a pair of bounds is the right way round."""
    return (isinstance(bounds, (tuple, list)) and len(bounds) == 2
            and bounds[0] <= bounds[1])


def _rows(table: Optional[Any]) -> List[Row]:
    """Return a table as rows, accepting the `{frequency: value}` form tables had before E1.

    Notes:
        - A value measured at one frequency, written the old way, applies at that frequency and
          nowhere else: no range is made up for it. Widening it is a decision about a receiver,
          and the editor is where that is made.
    """
    if not table:
        return []
    if isinstance(table, dict):
        return [(float(f), float(f), value) for f, value in table.items()]
    return [tuple(row) for row in table]


class Telescope(BaseEntity):
    """Class representing a ground-based telescope with ITRF coordinates, velocities, and SEFD properties.

    Notes:
        - **The measured tables are rows of `(f_min, f_max, value)`** (E1): what was measured, and the
          frequencies it holds for. A value applies to a band whose frequency lies in its range and
          to nothing else, so a system temperature measured for a C-band receiver is never taken as
          the one at 22 GHz. The ranges in one table do not overlap, so no frequency has two answers.
          Tables were `{frequency: value}` before, and read that way still (`SCHEMA_VERSION` 2).
    """
    SCHEMA_VERSION = 2

    code: str
    name: str
    type: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    diameter: Annotated[float, Positive()]
    sefd_table: List[Row]
    # Checked in `__init__` and nowhere else, so a range could be turned back to front later.
    # A station that can point nowhere is not visible as an error, only as an empty result.
    elevation_range: Annotated[Tuple[float, float], Predicate(_rises, "a range, low to high")]
    azimuth_range: Annotated[Tuple[float, float], Predicate(_rises, "a range, low to high")]
    mount_type: MountType
    surface_accuracy: Optional[float]
    surface_efficiency_table: List[Row]
    effective_area_table: List[Row]
    system_temperature_table: List[Row]

    def __init__(self, *, code: str = "TT", name: str = "TEMPTELESCOPE", type = "Telescope",
                 x: float = 0.0, y: float = 0.0, z: float = 0.0,
                 vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                 diameter: float = 1.0, sefd_table: Optional[List[Row]] = None,
                 elevation_range: Tuple[float, float] = (15.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 mount_type: str = "AZIM", isactive: bool = True,
                 surface_accuracy: Optional[float] = None,
                 surface_efficiency_table: Optional[List[Row]] = None,
                 effective_area_table: Optional[List[Row]] = None,
                 system_temperature_table: Optional[List[Row]] = None):
        """Initialize a Telescope with ITRF coordinates, velocities, and optional SEFD properties."""
        if name is None:
            name = f"tlsc_{uuid.uuid4().hex[:32]}"


        if isinstance(mount_type, str):
            try:
                mount_type = MountType(mount_type.upper())
            except ValueError:
                raise ValueError(f"Invalid mount_type: {mount_type}")
        elif not isinstance(mount_type, MountType):
            raise TypeError("mount_type must be a string or MountType")

        super().__init__(name=name, isactive=isactive,
                         code=code, type=type, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                         diameter=diameter, sefd_table=_rows(sefd_table),
                         elevation_range=elevation_range, azimuth_range=azimuth_range,
                         mount_type=mount_type, surface_accuracy=surface_accuracy,
                         surface_efficiency_table=_rows(surface_efficiency_table),
                         effective_area_table=_rows(effective_area_table),
                         system_temperature_table=_rows(system_temperature_table))
        logger.debug("Initialized Telescope '%s' at (%s, %s, %s) m, diameter=%s m", code, x, y, z, diameter)

    @classmethod
    def migrate(cls, data: dict, from_version: int) -> dict:
        """Bring a telescope written before E1 forward: `{frequency: value}` tables become rows."""
        if from_version < 2:
            data = dict(data)
            for table in cls.TABLES:
                if isinstance(data.get(table), dict):
                    data[table] = [[float(f), float(f), value] for f, value in data[table].items()]
        return data

    #: The tables of measured numbers a telescope carries, and what each value is. A table added
    #: later is guarded by adding it here, which is the point of naming them once.
    TABLES = {
        "sefd_table": "an SEFD, in janskys",
        "system_temperature_table": "a system temperature, in kelvin",
        "effective_area_table": "an effective area, in square metres",
        "surface_efficiency_table": "an aperture efficiency, a fraction",
    }

    @invariant("a telescope's tables hold positive values over ranges that do not overlap")
    def _tables_hold_positive_values(self) -> bool:
        """A dish with a negative SEFD is not a worse dish, it is a wrong answer.

        Raises:
            InvariantError: Naming the table, the range and the value.

        Notes:
            - `add_sefd` checked what it was given and `set` did not, so
              `set({"sefd_table": ...})` took a negative SEFD and `get_sefd` handed the minus
              one to whatever asked -- a sensitivity, an integration time, a beam. Four tables
              had the same hole, and so did a saved project carrying one back.
            - **Surface efficiency is a fraction**, so it is bounded above as well: an aperture
              cannot return more than it collects, and 1.4 there is a typo for 0.4 rather than
              a very good dish.
            - **A range runs low to high, and ranges in one table do not overlap.** Two rows
              covering one frequency would be two answers to one question. Ranges may touch; at
              the frequency they share, the lower row answers.
        """
        for table, what in self.TABLES.items():
            rows = sorted(getattr(self, table, None) or [])
            for low, high, value in rows:
                if not 0 < low <= high:
                    raise InvariantError(
                        f"Telescope '{self.code}': {table} has a range {low}-{high} MHz; a range "
                        f"runs from a positive frequency up")
                if not isinstance(value, (int, float)) or value <= 0:
                    raise InvariantError(
                        f"Telescope '{self.code}': {table} over {low}-{high} MHz is {value!r}; "
                        f"{what} must be positive")
                if table == "surface_efficiency_table" and value > 1:
                    raise InvariantError(
                        f"Telescope '{self.code}': surface efficiency over {low}-{high} MHz is "
                        f"{value!r}; it is a fraction, so it lies between 0 and 1")
            for (low, high, _), (next_low, next_high, _) in zip(rows, rows[1:]):
                if next_low < high:
                    raise InvariantError(
                        f"Telescope '{self.code}': {table} rows {low}-{high} and "
                        f"{next_low}-{next_high} MHz overlap, so a frequency between would have "
                        f"two values")

        if self.surface_accuracy is not None and (
                not isinstance(self.surface_accuracy, (int, float))
                or self.surface_accuracy <= 0):
            # An RMS surface error is a length. It reaches Ruze's formula squared, so a
            # negative one gives the same answer as its opposite -- which is worse than an
            # error, because the number is wrong and the result looks reasonable.
            raise InvariantError(
                f"Telescope '{self.code}': surface accuracy is {self.surface_accuracy!r}; "
                f"it is an RMS error in micrometres, so it is positive or not stated")
        return True

    def set(self, params: Dict[str, Any]) -> None:
        """Set entity attributes from a dictionary with type validation, handling mount_type.

        Notes:
            - A name is given at creation and kept: msb_arch refuses to rename an entity a
              container holds, because a container is keyed by the names of what it holds.
        """
        processed_params = params.copy()
        if "mount_type" in processed_params:
            mount_type = processed_params["mount_type"]
            if isinstance(mount_type, str):
                try:
                    processed_params["mount_type"] = MountType(mount_type.upper())
                except ValueError:
                    raise ValueError(f"Invalid mount_type: {mount_type}")
            elif not isinstance(mount_type, MountType):
                raise TypeError("mount_type must be a string or MountType")
        for table in self.TABLES:
            if table in processed_params:
                processed_params[table] = _rows(processed_params[table])
        super().set(processed_params)

    def add_sefd(self, frequency_min: float, frequency_max: float, sefd: float) -> None:
        """Add an SEFD measured over a range of frequencies, in MHz and Jy."""
        check_positive(sefd, "SEFD")
        self.set({"sefd_table": list(self.sefd_table) + [(float(frequency_min),
                                                           float(frequency_max), float(sefd))]})
        logger.debug("Added SEFD=%s Jy over %s-%s MHz to '%s'", sefd, frequency_min, frequency_max,
                     self.code)

    def remove_sefd(self, frequency: float) -> None:
        """Remove the SEFD row that covers a frequency, if there is one."""
        check_type(frequency, (int, float), "Frequency")
        row = self._covering(self.sefd_table, frequency)
        if row is not None:
            self.set({"sefd_table": [each for each in self.sefd_table if each != row]})
            logger.debug("Removed SEFD over %s-%s MHz from '%s'", row[0], row[1], self.code)

    def get_code(self) -> str:
        """Return the telescope's code.

        Returns:
            str: The unique code of the telescope.
        """
        return self.code

    def get_coordinates(self) -> Tuple[float, float, float]:
        """Return the telescope's ITRF coordinates.

        Returns:
            Tuple[float, float, float]: The (x, y, z) coordinates in meters.
        """
        return (self.x, self.y, self.z)

    def get_velocities(self) -> Tuple[float, float, float]:
        """Return the telescope's ITRF velocities.

        Returns:
            Tuple[float, float, float]: The (vx, vy, vz) velocities in meters.
        """
        return (self.vx, self.vy, self.vz)

    def get_elevation_range(self) -> Tuple[float,float]:
        """Return the telescope's elevation range.

        Returns:
            Tuple[float, float]: The minimum and maximum elevation angles in degrees.
        """
        return self.elevation_range

    def get_azimuth_range(self) -> Tuple[float,float]:
        """Return the telescope's azimuth range.

        Returns:
            Tuple[float, float]: The minimum and maximum azimuth angles in degrees.
        """
        return self.azimuth_range

    # --- sensitivity (E1) -------------------------------------------------------------------------

    @staticmethod
    def _covering(table: List[Row], frequency: float) -> Optional[Row]:
        """Return the row whose range holds a frequency; the lower one where two ranges touch."""
        for row in sorted(table or []):
            if row[0] <= frequency <= row[1]:
                return row
        return None

    def get_sefd(self, frequency: float) -> Optional[float]:
        """Return the SEFD measured for a frequency, in Jy, or None when no row covers it.

        Notes:
            - It returned the one point of a one-point table at any frequency at all, and
              interpolated between rows in a straight line -- a 22 GHz SEFD made out of an L-band
              and a Q-band measurement. A row now says what it holds for.
        """
        check_type(frequency, (int, float), "Frequency")
        row = self._covering(self.sefd_table, frequency)
        return row[2] if row else None

    def get_surface_efficiency(self, frequency: float) -> Optional[float]:
        """Return the aperture efficiency measured for a frequency, or None when no row covers it.

        Notes:
            - `surface_efficiency_table` holds what was measured of the whole aperture --
              illumination, spillover and blockage as well as the surface.
        """
        check_type(frequency, (int, float), "Frequency")
        row = self._covering(self.surface_efficiency_table, frequency)
        return row[2] if row else None

    def get_effective_area(self, frequency: float) -> Optional[float]:
        """Return the effective area measured for a frequency, in m^2, or None."""
        check_type(frequency, (int, float), "Frequency")
        row = self._covering(self.effective_area_table, frequency)
        return row[2] if row else None

    def get_system_temperature(self, frequency: float) -> Optional[float]:
        """Return the system temperature measured for a frequency, in K, or None."""
        check_type(frequency, (int, float), "Frequency")
        row = self._covering(self.system_temperature_table, frequency)
        return row[2] if row else None

    def get_geometric_area(self) -> float:
        """Return the area of the dish, in m^2."""
        return float(np.pi * (self.diameter / 2.0) ** 2)

    def get_ruze_efficiency(self, frequency: float) -> Optional[float]:
        """Return the fraction of the aperture the surface's roughness leaves, by Ruze's formula.

        Returns:
            Optional[float]: `exp(-(4 pi sigma / lambda)^2)`, with `surface_accuracy` in micrometres
                and the frequency in MHz; None when the surface accuracy is not stated.

        Notes:
            - Only the surface's part of the efficiency. What the illumination, the spillover and
              the blockage lose is not in it, and at long wavelengths this is close to one.
        """
        check_type(frequency, (int, float), "Frequency")
        check_positive(frequency, "Frequency")
        if self.surface_accuracy is None:
            return None
        wavelength = SPEED_OF_LIGHT / (frequency * 1e6)
        return float(np.exp(-(4.0 * np.pi * self.surface_accuracy * 1e-6 / wavelength) ** 2))

    def get_aperture_efficiency(self, frequency: float) -> Dict[str, Any]:
        """Return the aperture efficiency at a frequency, and what it was got from.

        Returns:
            Dict[str, Any]: `{"value": float | None, "basis": str | None, "reason": str | None}` --
                `basis` saying how the value was got, `reason` why there is none.

        Notes:
            - In this order, the first that answers:
              1. **Measured for this frequency** -- a `surface_efficiency_table` row covering it.
              2. **Measured elsewhere, carried by Ruze** -- with the surface accuracy known, the
                 efficiency of the row nearest in frequency, at the middle of its range, is split
                 into what the surface loses there and the rest, `eta0 = eta(nu1) / ruze(nu1)`,
                 and the rest is taken to hold at every frequency: `eta = eta0 * ruze(nu)`. That is
                 the physics of an aperture, and why a measurement at one frequency speaks for
                 another.
              3. **Ruze alone** -- nothing measured, the surface accuracy known. Only the surface's
                 losses, so it is higher than a real dish's efficiency and the SEFD it gives is
                 optimistic; the basis says so.
            - None, with the reason, when none of those can be made.
        """
        check_type(frequency, (int, float), "Frequency")
        measured = self._covering(self.surface_efficiency_table, frequency)
        if measured is not None:
            return {"value": measured[2],
                    "basis": f"measured over {measured[0]:g}-{measured[1]:g} MHz", "reason": None}

        ruze = self.get_ruze_efficiency(frequency)
        rows = list(self.surface_efficiency_table or [])
        if rows and ruze is not None:
            def middle(row: Row) -> float:
                return float(np.sqrt(row[0] * row[1]))

            nearest = min(rows, key=lambda row: abs(np.log(middle(row) / frequency)))
            there = middle(nearest)
            rest = nearest[2] / self.get_ruze_efficiency(there)
            if rest > 1.0:
                return {"value": None, "basis": None,
                        "reason": f"the efficiency measured at {there:g} MHz is more than a surface "
                                  f"of {self.surface_accuracy:g} um leaves there"}
            return {"value": rest * ruze,
                    "basis": f"measured at {there:g} MHz, carried by Ruze", "reason": None}
        if rows:
            return {"value": None, "basis": None,
                    "reason": f"no aperture efficiency covers {frequency:g} MHz, and no surface "
                              f"accuracy to carry one from another frequency"}
        if ruze is not None:
            return {"value": ruze, "basis": "Ruze only: surface losses, not illumination",
                    "reason": None}
        return {"value": None, "basis": None,
                "reason": "no aperture efficiency and no surface accuracy"}

    def get_sefd_estimate(self, frequency: float) -> Dict[str, Any]:
        """Return the SEFD at a frequency, and where the number came from.

        Returns:
            Dict[str, Any]: `{"sefd", "origin", "tsys", "effective_area", "efficiency", "basis",
                "reason"}` -- the SEFD in Jy; `origin` is `table`, `parameters` or `none`; the parts
                it was computed from when it was; and the reason when there is no SEFD.

        Notes:
            - **The SEFD table first.** Otherwise `SEFD = 2 k Tsys / A_eff`, in Jy, with `Tsys` from
              a row covering the frequency and `A_eff` from an effective-area row covering it, or
              from `get_aperture_efficiency` times the dish's area.
            - The old `calculate_sefd` left out the conversion to janskys, so it gave 1.8e-25 for a
              dish of 18 Jy, and took the efficiency from Ruze alone. Nothing called it.
        """
        check_type(frequency, (int, float), "Frequency")
        check_positive(frequency, "Frequency")
        answer = {"sefd": None, "origin": "none", "tsys": None, "effective_area": None,
                  "efficiency": None, "basis": None, "reason": None}

        row = self._covering(self.sefd_table, frequency)
        if row is not None:
            answer.update(sefd=row[2], origin="table",
                          basis=f"SEFD measured over {row[0]:g}-{row[1]:g} MHz")
            return answer

        tsys = self.get_system_temperature(frequency)
        if tsys is None:
            answer["reason"] = f"no SEFD and no system temperature covers {frequency:g} MHz"
            return answer
        answer["tsys"] = tsys

        area_row = self._covering(self.effective_area_table, frequency)
        if area_row is not None:
            area = area_row[2]
            answer.update(effective_area=area, efficiency=area / self.get_geometric_area(),
                          basis=f"effective area measured over {area_row[0]:g}-{area_row[1]:g} MHz")
        else:
            efficiency = self.get_aperture_efficiency(frequency)
            if efficiency["value"] is None:
                answer["reason"] = efficiency["reason"]
                return answer
            area = efficiency["value"] * self.get_geometric_area()
            answer.update(effective_area=area, efficiency=efficiency["value"],
                          basis=efficiency["basis"])

        answer.update(sefd=2.0 * BOLTZMANN_CONSTANT * tsys / area / JANSKY, origin="parameters")
        return answer

    def clear_sefd_table(self) -> None:
        """Clear all entries from the SEFD table."""
        self.set({"sefd_table": []})
        logger.debug("Cleared SEFD table for '%s'", self.code)

    def copy(self) -> 'Telescope':
        """Create a deep copy of the Telescope object."""
        return Telescope(
            code=self.code,
            name=self.name,
            type=self.type,
            x=self.x,
            y=self.y,
            z=self.z,
            vx=self.vx,
            vy=self.vy,
            vz=self.vz,
            diameter=self.diameter,
            sefd_table=deepcopy(self.sefd_table),
            elevation_range=self.elevation_range,
            azimuth_range=self.azimuth_range,
            mount_type=self.mount_type,
            isactive=self.isactive,
            surface_accuracy=self.surface_accuracy,
            surface_efficiency_table=deepcopy(self.surface_efficiency_table),
            effective_area_table=deepcopy(self.effective_area_table),
            system_temperature_table=deepcopy(self.system_temperature_table)
        )

    def to_dict(self) -> dict:
        """Convert the Telescope object to a dictionary for serialization."""
        # A copy: on an object that caches, `to_dict` returns the cache itself, and
        # writing to it corrupts what every later call reports -- which MSB 1.9.0
        # turned from silent into a refusal.
        data = dict(super().to_dict())
        data.update({
            "mount_type": self.mount_type.value,
            "elevation_range": list(self.elevation_range),
            "azimuth_range": list(self.azimuth_range),
            **{table: [list(row) for row in getattr(self, table)] for table in self.TABLES},
        })
        return data


    def __repr__(self) -> str:
        """Return a string representation of the Telescope object."""
        return (f"Telescope(code='{self.code}', name='{self.name}', "
                f"x={self.x}, y={self.y}, z={self.z}, "
                f"diameter={self.diameter}, isactive={self.isactive})")
