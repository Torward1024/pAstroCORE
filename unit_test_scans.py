import unittest
from unittest.mock import Mock
from base.scans import Scan, Scans
from base.observation import Observation
from base.sources import Sources, Source
from base.telescopes import Telescopes, Telescope
from base.frequencies import Frequencies, IF
from datetime import datetime

class TestScans(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data before each test."""
        # Создаем минимальные объекты для Observation
        sources = Sources([Source(name="SRC1"), Source(name="SRC2")])
        telescopes = Telescopes([Telescope(code="TEL1"), Telescope(code="TEL2")])
        frequencies = Frequencies([IF(freq=1000.0), IF(freq=2000.0)])
        self.observation = Observation(
            observation_code="TEST_OBS",
            sources=sources,
            telescopes=telescopes,
            frequencies=frequencies
        )

        # Настраиваем тестовые данные для Scan
        self.scan1 = Scan(
            start=1000.0,
            duration=300.0,
            source_index=0,
            telescope_indices=[0, 1],
            frequency_indices=[0],
            is_off_source=False,
            isactive=True
        )
        self.scan2 = Scan(
            start=1500.0,
            duration=200.0,
            source_index=1,
            telescope_indices=[1],
            frequency_indices=[1],
            is_off_source=False,
            isactive=False
        )
        self.scans = Scans([self.scan1, self.scan2])

    def test_scan_init(self) -> None:
        """Test Scan initialization."""
        self.assertEqual(self.scan1.get_start(), 1000.0)
        self.assertEqual(self.scan1.get_end(), 1300.0)
        self.assertEqual(self.scan1.get_duration(), 300.0)
        self.assertEqual(self.scan1.get_source_index(), 0)
        self.assertEqual(self.scan1.get_telescope_indices(), [0, 1])
        self.assertEqual(self.scan1.get_frequency_indices(), [0])
        self.assertFalse(self.scan1.is_off_source)
        self.assertTrue(self.scan1.isactive)

    def test_scan_time_methods(self) -> None:
        """Test time-related methods."""
        self.assertAlmostEqual(self.scan1.get_MJD_starttime(), 40587.01157407407, places=5)  # 1000 / 86400 + 40587
        self.assertAlmostEqual(self.scan1.get_MJD_endtime(), 40587.0150462963, places=5)    # 1300 / 86400 + 40587
        self.assertEqual(self.scan1.get_start_datetime(), datetime.fromtimestamp(1000.0))
        self.assertEqual(self.scan1.get_end_datetime(), datetime.fromtimestamp(1300.0))

    def test_scan_setters(self) -> None:
        """Test Scan setters."""
        self.scan1.set_start(2000.0)
        self.assertEqual(self.scan1.get_start(), 2000.0)
        self.scan1.set_duration(600.0)
        self.assertEqual(self.scan1.get_duration(), 600.0)
        self.scan1.set_source_index(None, self.observation)
        self.assertIsNone(self.scan1.get_source_index())
        self.assertTrue(self.scan1.is_off_source)
        self.scan1.set_telescope_indices([0], self.observation)
        self.assertEqual(self.scan1.get_telescope_indices(), [0])
        self.scan1.set_frequency_indices([1], self.observation)
        self.assertEqual(self.scan1.get_frequency_indices(), [1])

    def test_scan_validation(self) -> None:
        """Test validation with Observation."""
        self.assertTrue(self.scan1.validate_with_observation(self.observation))
        invalid_scan = Scan(start=0.0, source_index=5, telescope_indices=[10], frequency_indices=[-1])
        self.assertFalse(invalid_scan.validate_with_observation(self.observation))

    def test_scans_init_and_add(self) -> None:
        """Test Scans initialization and scan addition."""
        self.assertEqual(len(self.scans), 2)
        self.assertEqual(self.scans.get_by_index(0).get_start(), 1000.0)
        new_scan = Scan(start=2000.0, duration=100.0, telescope_indices=[0])
        self.scans.add_scan(new_scan, self.observation)
        self.assertEqual(len(self.scans), 3)
        with self.assertRaises(ValueError):
            overlap_scan = Scan(start=1000.0, duration=400.0, telescope_indices=[0])
            self.scans.add_scan(overlap_scan, self.observation)  # Пересечение по времени и телескопам

    def test_scans_activation(self) -> None:
        """Test scan activation/deactivation."""
        self.scans.deactivate_scan(0)
        self.assertFalse(self.scans.get_by_index(0).isactive)
        self.assertEqual(len(self.scans.get_active_scans()), 0)
        self.scans.activate_scan(0)
        self.assertTrue(self.scans.get_by_index(0).isactive)
        self.scans.activate_all()
        self.assertEqual(len(self.scans.get_active_scans()), 2)

    def test_scans_serialization(self) -> None:
        """Test Scans to/from dict serialization."""
        scans_dict = self.scans.to_dict()
        self.assertEqual(len(scans_dict["data"]), 2)
        restored_scans = Scans.from_dict(scans_dict)
        self.assertEqual(restored_scans.get_by_index(0).get_start(), 1000.0)
        self.assertEqual(restored_scans.get_by_index(1).get_source_index(), 1)

if __name__ == "__main__":
    unittest.main()