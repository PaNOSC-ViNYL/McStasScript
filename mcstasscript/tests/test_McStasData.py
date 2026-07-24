import unittest
import numpy as np

from mcstasscript.data.data import McStasData
from mcstasscript.data.data import McStasDataBinned
from mcstasscript.data.data import McStasDataEvent
from mcstasscript.data.data import McStasMetaData


def set_dummy_MetaDataBinned_1d():
    """
    Sets up simple McStasMetaData object with dimension, 1d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "component for 1d"
    meta_data.dimension = 50

    return meta_data


def set_dummy_McStasDataBinned_1d():
    """
    Sets up simple McStasData object, 1d case
    """
    meta_data = set_dummy_MetaDataBinned_1d()

    intensity = np.arange(20)
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasDataBinned(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaDataBinned_2d():
    """
    Sets up simple McStasMetaData object with dimensions, 2d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "test a component"
    meta_data.dimension = [50, 100]

    return meta_data


def set_dummy_McStasDataBinned_2d():
    """
    Sets up simple McStasData object, 2d case
    """
    meta_data = set_dummy_MetaDataBinned_2d()

    intensity = np.arange(20).reshape(4, 5)
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasDataBinned(meta_data, intensity, error, ncount)


class TestMcStasData(unittest.TestCase):
    """
    Various tests of McStasData class
    """

    def test_McStasDataBinned_init_1d(self):
        """
        Test that newly created McStasMetaData has correct names, 1d case
        """

        data = set_dummy_McStasDataBinned_1d()

        self.assertEqual(data.name, "component for 1d")
        self.assertEqual(data.metadata.component_name, "component for 1d")

    def test_McStasDataBinned_init_values(self):
        """
        Test that newly created McStasDataBinned has expected data, 1d case
        Here checking a single data point
        """

        data = set_dummy_McStasDataBinned_1d()

        self.assertEqual(data.Intensity[3], 3)
        self.assertEqual(data.Error[3], 1.5)
        self.assertEqual(data.Ncount[3], 6)
        self.assertEqual(data.xaxis[3], 15.0)

    def test_McStasDataBinned_init_values_full(self):
        """
        Test that newly created McStasDataBinned has expected data, 1d case
        """

        data = set_dummy_McStasDataBinned_1d()

        intensity = np.arange(20)
        error = 0.5 * np.arange(20)
        ncount = 2 * np.arange(20)
        axis = np.arange(20) * 5.0

        for index in range(len(data.Intensity)):
            self.assertEqual(data.Intensity[index], intensity[index])
            self.assertEqual(data.Error[index], error[index])
            self.assertEqual(data.Ncount[index], ncount[index])
            self.assertEqual(data.xaxis[index], axis[index])

    def test_McStasDataBinned_init_2d_names(self):
        """
        Test that newly created McStasMetaData has correct names, 1d case
        """

        data = set_dummy_McStasDataBinned_2d()

        self.assertEqual(data.name, "test a component")
        self.assertEqual(data.metadata.component_name, "test a component")

    def test_McStasDataBinned_init_2d_values(self):
        """
        Test that newly created McStasDataBinned has expected data, 2d case
        Here checking a single point
        """

        data = set_dummy_McStasDataBinned_2d()

        self.assertEqual(data.Intensity[2][3], 13)
        self.assertEqual(data.Error[2][3], 6.5)
        self.assertEqual(data.Ncount[2][3], 26)

    def test_McStasDataBinned_init_2d_values_full(self):
        """
        Test that newly created McStasDataBinned has expected data, 2d case
        Here checking a entire dataset
        """

        data = set_dummy_McStasDataBinned_2d()

        intensity = np.arange(20).reshape(4, 5)
        error = 0.5 * np.arange(20).reshape(4, 5)
        ncount = 2 * np.arange(20).reshape(4, 5)

        shape = np.shape(data.Intensity)

        for index1 in range(shape[0]):
            for index2 in range(shape[1]):

                self.assertEqual(data.Intensity[index1][index2],
                                 intensity[index1][index2])
                self.assertEqual(data.Error[index1][index2],
                                 error[index1][index2])
                self.assertEqual(data.Ncount[index1][index2],
                                 ncount[index1][index2])

    def test_McStasDataBinned_set_info_title(self):
        """
        Test that title can be set
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_title("title_test")
        self.assertEqual(data.metadata.title, "title_test")

    def test_McStasDataBinned_set_xlabel(self):
        """
        Test that xlabel can be set
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_xlabel("xlabel test")
        self.assertEqual(data.metadata.xlabel, "xlabel test")

    def test_McStasDataBinned_set_ylabel(self):
        """
        Test that ylabel can be set
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_ylabel("ylabel test")
        self.assertEqual(data.metadata.ylabel, "ylabel test")

    def test_McStasDataBinned_set_log(self):
        """
        Test that log setting has correct type regardless of how it is given
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_plot_options(log=True)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertTrue(data.plot_options.log)

        data.set_plot_options(log=0)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertFalse(data.plot_options.log)

        data.set_plot_options(log=1)
        self.assertIsInstance(data.plot_options.log, bool)
        self.assertTrue(data.plot_options.log)

    def test_McStasDataBinned_set_show_colorbar(self):
        """
        Test that log setting has correct type regardless of how it is given
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_plot_options(show_colorbar=True)
        self.assertIsInstance(data.plot_options.show_colorbar, bool)
        self.assertTrue(data.plot_options.show_colorbar)

        data.set_plot_options(show_colorbar=0)
        self.assertIsInstance(data.plot_options.show_colorbar, bool)
        self.assertFalse(data.plot_options.show_colorbar)

        data.set_plot_options(show_colorbar=1)
        self.assertIsInstance(data.plot_options.show_colorbar, bool)
        self.assertTrue(data.plot_options.show_colorbar)

    def test_McStasDataBinned_set_orders_of_mag(self):
        """
        Test that orders_og_mag can be set correctly
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_plot_options(orders_of_mag=5.2)
        self.assertEqual(data.plot_options.orders_of_mag, 5.2)

    def test_McStasDataBinned_set_colormap(self):
        """
        Test that colormap can be set correctly
        """
        data = set_dummy_McStasDataBinned_2d()
        data.set_plot_options(colormap="hot")
        self.assertIs(data.plot_options.colormap, "hot")


if __name__ == '__main__':
    unittest.main()
