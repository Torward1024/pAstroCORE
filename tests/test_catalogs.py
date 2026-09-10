"""The catalogues the application ships, read the way its own API says to read them.

`CatalogManager` parses two files and offers five ways to look inside them. Every one of the
five called `get_all_sources()` or `get_all_telescopes()` -- names the containers have not had
for as long as the containers have been `Sources` and `Telescopes`. Nothing in the application
calls those five, so nothing raised, and the class kept a public interface where every lookup
was an `AttributeError` waiting for its first caller. One of them had even been fixed once, for
a different defect, without the fix ever being run.

These tests are cheap insurance of the dullest kind: call each method, on the real shipped
files, and require an answer.
"""
import pytest

from pastrocore.paths import shipped_catalog
from pastrocore.utils.catalogmanager import CatalogManager


@pytest.fixture(scope="module")
def catalogs():
    """The catalogues as the application loads them at start-up."""
    return CatalogManager(source_file=str(shipped_catalog("sources.dat")),
                          telescope_file=str(shipped_catalog("telescopes.dat")))


def test_the_shipped_catalogues_are_not_empty(catalogs):
    """A parser that silently produced nothing would make every test below vacuous."""
    assert len(catalogs.source_catalog) > 0, "the shipped sources parsed to nothing"
    assert len(catalogs.telescope_catalog) > 0, "the shipped telescopes parsed to nothing"


def test_a_source_is_found_by_the_name_it_is_filed_under(catalogs):
    first = catalogs.source_catalog.get_items()[0]

    assert catalogs.get_source(first.name) is first
    assert catalogs.get_source("no such source") is None


def test_a_source_is_found_by_its_J2000_name_too(catalogs):
    """Both names are how a catalogue is actually searched; only one is the key."""
    named = next((source for source in catalogs.source_catalog.get_items()
                  if source.name_J2000), None)
    if named is None:
        pytest.skip("the shipped catalogue records no J2000 names")

    assert catalogs.get_source(named.name_J2000) is named


def test_a_telescope_is_found_by_its_code(catalogs):
    first = catalogs.telescope_catalog.get_items()[0]

    assert catalogs.get_telescope(first.get_code()) is first
    assert catalogs.get_telescope("no such telescope") is None


@pytest.mark.parametrize("bounds", [(0.0, 360.0), (0.0, 90.0)])
def test_sources_are_found_in_a_range_of_right_ascension(catalogs, bounds):
    low, high = bounds
    found = catalogs.get_sources_by_ra_range(low, high)

    assert all(low <= source.ra_degrees <= high for source in found)
    if (low, high) == (0.0, 360.0):
        assert len(found) == len(catalogs.source_catalog), "every source has an RA"


def test_sources_are_found_in_a_range_of_declination(catalogs):
    found = catalogs.get_sources_by_dec_range(-90.0, 90.0)

    assert len(found) == len(catalogs.source_catalog), "every source has a declination"


def test_telescopes_are_found_by_type(catalogs):
    """The ground stations and the spacecraft are asked for separately, and a spelling that is
    neither is refused rather than answered with everything."""
    ground = catalogs.get_telescopes_by_type("Telescope")
    space = catalogs.get_telescopes_by_type("SpaceTelescope")

    assert len(ground) + len(space) == len(catalogs.telescope_catalog)
    assert catalogs.get_telescopes_by_type("Antenna") == []


def test_a_telescope_line_without_a_diameter_is_skipped(tmp_path):
    """Six fields is a line that is too short, not a line that failed to parse.

    The guard read `< 6` while the diameter is the seventh field, so such a line reached the
    read and was reported as unparseable. Same outcome, wrong reason in the log -- and the log
    is all anyone has when a catalogue comes back smaller than it should.
    """
    catalog = tmp_path / "telescopes.dat"
    catalog.write_text("1 Sv Svetloe 2730173.0 1562442.7 5529969.1 32.0\n"
                       "2 Zc Zelenchuk 3451207.5 3060375.4 4391915.0\n", encoding="utf-8")

    catalogs = CatalogManager(telescope_file=str(catalog))

    assert [t.get_code() for t in catalogs.telescope_catalog.get_items()] == ["Sv"]
