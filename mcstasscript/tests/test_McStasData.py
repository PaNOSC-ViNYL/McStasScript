import unittest
import numpy as np

from mcstasscript.data.data import McStasData
from mcstasscript.data.data import McStasMetaData


def set_dummy_MetaData_1d():
    meta_data = McStasMetaData()
    meta_data.component_name = "component for 1d"
    meta_data.dimension = 50

    return meta_data


def set_dummy_McStasData_1d():
    meta_data = set_dummy_MetaData_1d()

    intensity = np.arange(20)
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasData(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaData_2d():
    meta_data = McStasMetaData()
    meta_data.component_name = "test a component"
    meta_data.dimension = [50, 100]

    return meta_data


def set_dummy_McStasData_2d():
    meta_data = set_dummy_MetaData_2d()

    intensity = np.arange(20).reshape(4, 5)
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasData(meta_data, intensity, error, ncount)


class TestMcStasData(unittest.TestCase):
    """
    Various test of McStasData class
    """

    def test_McStasData_init_1d(self):
        """
        Test that newly created McStasMetaData has correct type
        """

        data = set_dummy_McStasData_1d()

        self.assertEqual(data.name, "component for 1d")
        self.assertEqual(data.metadata.component_name, "component for 1d")

    def test_McStasData_init_values(self):
        """
        Test that newly created McStasMetaData has correct type
        """

        data = set_dummy_McStasData_1d()

        self.assertEqual(data.Intensity[3], 3)
        self.assertEqual(data.Error[3], 1.5)
        self.assertEqual(data.Ncount[3], 6)
        self.assertEqual(data.xaxis[3], 15.0)

    def test_McStasData_init_2d_names(self):
        """
        Test that newly created McStasMetaData has correct type
        """

        data = set_dummy_McStasData_2d()

        self.assertEqual(data.name, "test a component")
        self.assertEqual(data.metadata.component_name, "test a component")

    def test_McStasData_init_2d_values(self):
        """
        Test that newly created McStasMetaData has correct type
        """

        data = set_dummy_McStasData_2d()

        self.assertEqual(data.Intensity[2][3], 13)
        self.assertEqual(data.Error[2][3], 6.5)
        self.assertEqual(data.Ncount[2][3], 26)

    def test_McStasData_set_info_title(self):
        """
        Test that title can be set
        """
        data = set_dummy_McStasData_2d()
        data.set_title("title_test")
        self.assertEqual(data.metadata.title, "title_test")

    def test_McStasData_set_xlabel(self):
        """
        Test that xlabel can be set
        """
        data = set_dummy_McStasData_2d()
        data.set_xlabel("xlabel test")
        self.assertEqual(data.metadata.xlabel, "xlabel test")

    def test_McStasData_set_ylabel(self):
        """
        Test that ylabel can be set
        """
        data = set_dummy_McStasData_2d()
        data.set_ylabel("ylabel test")
        self.assertEqual(data.metadata.ylabel, "ylabel test")

    def test_McStasData_set_log(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        data = set_dummy_McStasData_2d()
        data.set_plot_options(log=True)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertTrue(data.plot_options.log)

        data.set_plot_options(log=0)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertFalse(data.plot_options.log)

        data.set_plot_options(log=1)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertTrue(data.plot_options.log)

    def test_McStasData_set_orders_of_mag(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        data = set_dummy_McStasData_2d()
        data.set_plot_options(orders_of_mag=5.2)
        self.assertEqual(data.plot_options.orders_of_mag, 5.2)

    def test_McStasData_set_colormap(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        data = set_dummy_McStasData_2d()
        data.set_plot_options(colormap="hot")
        self.assertIs(data.plot_options.colormap, "hot")


if __name__ == '__main__':
    unittest.main()
