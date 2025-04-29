import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import unittest
import numpy as np
from pastrocore.base.sources import Source
from pastrocore.base.frequencies import IF
from unit_modeller.base.model import Model, Models

import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt5Agg for interactive display; try 'TkAgg' if Qt5Agg fails
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from astropy.coordinates import Angle
import astropy.units as u

class TestModel(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.resolution = 16
        self.test_file_single = "test_data_single.txt"
        self.test_file_complex = "test_data_complex.txt"
        
        # Create test data files
        np.savetxt(self.test_file_single, np.ones(256), fmt="%.6f")
        np.savetxt(self.test_file_complex, np.column_stack((np.ones(256), np.zeros(256))), fmt="%.6f")
        
        self.source1 = Source(name="Src1")
        self.source2 = Source(name="Src2")
        self.freq1 = IF(name="IF1", frequency=1000.0, bandwidth=16.0)
        self.freq2 = IF(name="IF2", frequency=2000.0, bandwidth=16.0)
        self.data = np.ones((self.resolution, self.resolution), dtype=np.complex128)
        
        self.model_params = {
            "code": "M1",
            "name": "TestModel",
            "source": self.source1,
            "frequency": self.freq1,
            "vis_width": 0.01,
            "resolution": self.resolution,
            "data": self.data
        }

    def tearDown(self):
        """Clean up test files."""
        for file in [self.test_file_single, self.test_file_complex]:
            if os.path.exists(file):
                os.remove(file)

    def test_model_creation_valid(self):
        """Test successful model creation with valid parameters."""
        model = Model(**self.model_params)
        self.assertEqual(model.code, "M1")
        self.assertEqual(model.name, "TestModel")
        self.assertEqual(model.source, self.source1)
        self.assertEqual(model.frequency, self.freq1)
        self.assertEqual(model.vis_width, 0.01)
        self.assertEqual(model.resolution, self.resolution)
        np.testing.assert_array_equal(model.data, self.data)
        self.assertTrue(np.issubdtype(model.data.dtype, np.complexfloating))

    def test_model_missing_required_field(self):
        """Test model creation fails with missing required fields."""
        required_fields = ['code', 'name', 'source', 'frequency', 'vis_width']
        for field in required_fields:
            with self.subTest(field=field):
                invalid_params = self.model_params.copy()
                invalid_params[field] = None
                with self.assertRaises(ValueError):
                    Model(**invalid_params)

    def test_model_invalid_data_type(self):
        """Test model creation fails with invalid data type."""
        invalid_params = self.model_params.copy()
        invalid_params["data"] = [1, 2, 3]  # Not np.ndarray
        with self.assertRaises(TypeError):
            Model(**invalid_params)

    def test_model_invalid_data_shape(self):
        """Test model creation fails with incorrect data shape."""
        invalid_params = self.model_params.copy()
        invalid_params["data"] = np.ones((self.resolution, self.resolution - 1))
        with self.assertRaises(ValueError):
            Model(**invalid_params)

    def test_model_data_conversion(self):
        """Test automatic conversion of float data to complex."""
        float_data = np.ones((self.resolution, self.resolution), dtype=np.float64)
        params = self.model_params.copy()
        params["data"] = float_data
        model = Model(**params)
        self.assertTrue(np.issubdtype(model.data.dtype, np.complexfloating))
        np.testing.assert_array_equal(model.data, float_data.astype(np.complex128))

    def test_load_from_file_single_column(self):
        """Test loading data from single-column file."""
        model = Model(
            code="M1",
            name="TestModel",
            source=self.source1,
            frequency=self.freq1,
            vis_width=0.01
        )
        model.load_from_file(self.test_file_single)
        self.assertEqual(model.resolution, self.resolution)
        self.assertEqual(model.data.shape, (self.resolution, self.resolution))
        np.testing.assert_array_equal(model.data, np.ones((self.resolution, self.resolution), dtype=np.complex128))

    def test_load_from_file_complex(self):
        """Test loading data from complex (two-column) file."""
        model = Model(
            code="M1",
            name="TestModel",
            source=self.source1,
            frequency=self.freq1,
            vis_width=0.01
        )
        model.load_from_file(self.test_file_complex)
        self.assertEqual(model.resolution, self.resolution)
        self.assertEqual(model.data.shape, (self.resolution, self.resolution))
        np.testing.assert_array_equal(model.data, np.ones((self.resolution, self.resolution), dtype=np.complex128))

    def test_load_from_file_non_square(self):
        """Test loading fails with non-square data."""
        model = Model(
            code="M1",
            name="TestModel",
            source=self.source1,
            frequency=self.freq1,
            vis_width=0.01
        )
        invalid_file = "invalid.txt"
        np.savetxt(invalid_file, np.ones(200))  # Not a square
        with self.assertRaises(ValueError):
            model.load_from_file(invalid_file)
        if os.path.exists(invalid_file):
            os.remove(invalid_file)

    def test_load_from_file_invalid_columns(self):
        """Test loading fails with invalid number of columns."""
        model = Model(
            code="M1",
            name="TestModel",
            source=self.source1,
            frequency=self.freq1,
            vis_width=0.01
        )
        invalid_file = "invalid_columns.txt"
        np.savetxt(invalid_file, np.ones((256, 3)))  # Three columns
        with self.assertRaises(ValueError):
            model.load_from_file(invalid_file)
        if os.path.exists(invalid_file):
            os.remove(invalid_file)

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        model = Model(**self.model_params)
        model_dict = model.to_dict()
        restored_model = Model.from_dict(model_dict)
        self.assertEqual(model.code, restored_model.code)
        self.assertEqual(model_dict["type"], "Model")
        self.assertEqual(model_dict["code"], "M1")
        np.testing.assert_array_equal(restored_model.data, self.data)

    def test_model_clone(self):
        """Test model cloning creates identical copy."""
        model = Model(**self.model_params)
        cloned = model.clone()
        self.assertEqual(model.code, cloned.code)
        self.assertIsNot(model, cloned)
        np.testing.assert_array_equal(model.data, cloned.data)

    def test_model_visualization(self):
        """Test model visualization as a 2D color map."""
        # Create a model with varied data for better visualization
        x = np.linspace(-self.model_params["vis_width"]/2, self.model_params["vis_width"]/2, self.resolution)
        X, Y = np.meshgrid(x, x)
        amplitude = np.exp(-(X**2 + Y**2) / (2 * (self.model_params["vis_width"]/4)**2))
        model_params = self.model_params.copy()
        model_params["data"] = amplitude.astype(np.complex128)
        model = Model(**model_params)

        # Create plot
        fig, ax = plt.subplots()
        extent = [-model.vis_width/2, model.vis_width/2, -model.vis_width/2, model.vis_width/2]
        im = ax.imshow(np.abs(model.data), extent=extent, origin='lower', cmap='viridis')
        plt.colorbar(im, ax=ax, label='Amplitude')

        # Format RA (x-axis) in hour:min:sec
        def ra_formatter(x, pos):
            # Convert offset in radians to hours
            offset = Angle(x * u.radian).to(u.hourangle)
            return offset.to_string(unit=u.hourangle, sep=':')

        # Format Dec (y-axis) in deg:min:sec
        def dec_formatter(y, pos):
            # Convert offset in radians to degrees
            offset = Angle(y * u.radian).to(u.degree)
            return offset.to_string(unit=u.degree, sep=':')

        ax.xaxis.set_major_formatter(FuncFormatter(ra_formatter))
        ax.yaxis.set_major_formatter(FuncFormatter(dec_formatter))
        
        ax.set_xlabel('RA offset (hms)')
        ax.set_ylabel('Dec offset (dms)')
        ax.set_title(f'Model Amplitude Map (Source: {model.source.name})')
        
        # Debug: Confirm plot is being displayed
        print("Displaying visualization plot")
        plt.show()

class TestModelsContainer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for Models container."""
        self.source1 = Source(name="Src1")
        self.source2 = Source(name="Src2")
        self.freq1 = IF(name="IF1", frequency=1000.0, bandwidth=16.0)
        self.freq2 = IF(name="IF2", frequency=2000.0, bandwidth=16.0)
        self.resolution = 16
        self.data = np.ones((self.resolution, self.resolution), dtype=np.complex128)
        
        self.model1 = Model(
            code="M1",
            name="Model1",
            source=self.source1,
            frequency=self.freq1,
            vis_width=0.01,
            resolution=self.resolution,
            data=self.data
        )
        self.model2 = Model(
            code="M2",
            name="Model2",
            source=self.source1,
            frequency=self.freq2,
            vis_width=0.01,
            resolution=self.resolution,
            data=self.data
        )
        self.model3 = Model(
            code="M3",
            name="Model3",
            source=self.source2,
            frequency=self.freq1,
            vis_width=0.01,
            resolution=self.resolution,
            data=self.data
        )
        self.models = Models(
            name="ModelCollection",
            items={m.name: m for m in [self.model1, self.model2, self.model3]}
        )

    def test_models_container_operations(self):
        """Test basic container operations."""
        self.assertEqual(len(self.models), 3)
        self.assertEqual(self.models.get("Model1").code, self.model1.code)
        self.assertTrue(self.models.has_item("Model2"))
        self.assertEqual(len(self.models.get_items()), 3)
        
        # Test add
        new_model = Model(
            code="M4",
            name="Model4",
            source=self.source2,
            frequency=self.freq2,
            vis_width=0.01,
            resolution=self.resolution,
            data=self.data
        )
        self.models.add(new_model)
        self.assertEqual(len(self.models), 4)
        
        # Test remove
        self.models.remove("Model4")
        self.assertEqual(len(self.models), 3)

    def test_get_by_source_name(self):
        """Test filtering models by source name."""
        filtered = self.models.get_by_value({"source": self.source1})
        self.assertEqual(len(filtered), 2)
        self.assertEqual({m.name for m in filtered}, {"Model1", "Model2"})

    def test_get_by_frequency(self):
        """Test filtering models by frequency."""
        filtered = self.models.get_by_value({"frequency": self.freq1})
        self.assertEqual(len(filtered), 2)
        self.assertEqual({m.name for m in filtered}, {"Model1", "Model3"})

    def test_models_serialization(self):
        """Test container serialization and deserialization."""
        models_dict = self.models.to_dict()
        restored_models = Models.from_dict(models_dict)
        self.assertEqual(len(restored_models), len(self.models))
        for name in self.models.get_all():
            self.assertEqual(self.models.get(name).code, restored_models.get(name).code)

    def test_models_clone(self):
        """Test container cloning."""
        cloned = self.models.clone()
        self.assertEqual(len(cloned), len(self.models))
        for name in self.models.get_all():
            self.assertEqual(self.models.get(name).code, cloned.get(name).code)
        self.assertIsNot(self.models, cloned)

    def test_invalid_attribute_filter(self):
        """Test filtering with invalid attribute raises AttributeError."""
        with self.assertRaises(AttributeError):
            self.models.get_by_value({"invalid_attr": "value"})

    def test_active_inactive_filtering(self):
        """Test filtering active and inactive models."""
        self.model2.deactivate()
        active = self.models.get_active_items()
        inactive = self.models.get_inactive_items()
        self.assertEqual(len(active), 2)
        self.assertEqual(len(inactive), 1)
        self.assertEqual(inactive[0].name, "Model2")

if __name__ == '__main__':
    unittest.main()