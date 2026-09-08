# formats/__init__.py
"""Contracts with software nobody here controls.

A module in here turns the model into a file some other program reads, and knows that program's
vocabulary and nothing else: no Qt, no manipulator, no request. What is here is a function of
an `Observation` -- given the same observation it writes the same bytes, which is what makes a
characterization test possible at all.

Each format is reached as its own operation on the manipulator, and the `Super` that does it is
the only thing that knows both this and the request. That is deliberate: `ScheduleData` writes
what a person wants to look at, and these write a contract with a correlator. Mixing them would
give one this module's vocabulary and give the other that module's tolerance for close enough.
"""


def build_observation(read: dict, *, code: str = None):
    """Turn what a format reader returned into an `Observation`.

    Args:
        read (dict): A reader's answer -- `code`, `telescopes`, `sources`, `bands`, `scans`.
        code (str): What to call the observation. The file's own experiment code by default.

    Returns:
        Tuple[Observation, List[str]]: What was built, and the scans this model would not hold.

    Raises:
        ValueError: If nothing usable was read.

    Notes:
        - **One builder for both formats**, because both readers answer in the same shape. A
          second one would be a second place for a scan to end up pointing at a source that is
          not in the observation.
        - What a reader passed over is passed over here too (V6): the hardware and the session
          are not this model's, an export leaves them for the station and the correlator to
          fill, and importing them would be carrying something nothing here can use or check.
        - **A scan this model refuses is named rather than forced in.**  is the
          case: two sub-arrays observing at the same moment in different bands, which is an
          ordinary thing to do and something the rule about overlapping active scans has no
          way to say. The ones that fit are imported and the rest are reported.
    """
    from astropy.time import Time

    from pastrocore.base.observation import Observation

    observation = Observation(code=code or read.get("code") or "IMPORTED")

    telescopes = observation.get_telescopes()
    for entry in read.get("telescopes", {}).values():
        if entry.get("kind") == "space":
            telescopes.create_space_telescope(code=entry["code"], name=entry.get("name"),
                                              orbit_file=entry.get("orbit_file"),
                                              use_kep=False)
        else:
            telescopes.create_telescope(
                code=entry["code"], name=entry.get("name"),
                x=entry.get("x", 0.0), y=entry.get("y", 0.0), z=entry.get("z", 0.0),
                vx=entry.get("vx", 0.0), vy=entry.get("vy", 0.0), vz=entry.get("vz", 0.0),
                mount_type=entry.get("mount_type", "AZIM"))

    sources = observation.get_sources()
    for entry in read.get("sources", {}).values():
        if "ra_degrees" in entry:
            # CFX states a position in degrees; the model keeps hours and arcseconds, and
            # already knows how to convert. Built at zero and then set, so the one conversion
            # in the model is the one used.
            source = sources.create_source(name=entry["name"])
            source = sources.get(entry["name"])
            source.set_ra_degrees(float(entry["ra_degrees"]))
            source.set_dec_degrees(float(entry["dec_degrees"]))
        else:
            sources.create_source(
                name=entry["name"], ra_h=entry["ra_h"], ra_m=entry["ra_m"],
                ra_s=entry["ra_s"], de_d=entry["de_d"], de_m=entry["de_m"], de_s=entry["de_s"])

    frequencies = observation.get_frequencies()
    for entry in read.get("bands", {}).values():
        frequencies.create_if(name=entry["name"], frequency=entry["frequency"],
                              bandwidth=entry["bandwidth"],
                              polarizations=entry.get("polarizations") or None,
                              sidebands=entry.get("sidebands") or None)

    from msb_arch import InvariantError

    scans, refused = observation.get_scans(), []
    by_code = {telescope.get_code(): telescope for telescope in telescopes.get_items()}
    for entry in read.get("scans", []):
        source = sources.get(entry["source"]) if entry.get("source") else None
        on_it = [by_code[code] for code in entry.get("telescopes", []) if code in by_code]
        bands = [frequencies.get(name) for name in entry.get("bands", [])
                 if frequencies.get(name) is not None]
        if not on_it:
            continue
        try:
            scans.create_scan(name=entry["name"], start=entry["start"],
                              duration=float(entry["duration"]), source=source,
                              telescopes=on_it, frequencies=bands, observation=observation)
        except InvariantError as e:
            refused.append(f"{entry['name']}: {e}")

    if not scans.get_items():
        raise ValueError("Nothing was read that this model can hold: no scan survived")
    return observation, refused
