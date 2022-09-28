import unittest
import numpy as np
import copy

from mcstasscript.data.data import McStasDataBinned
from mcstasscript.data.data import McStasMetaData
from mcstasscript.jb_interface.simulation_interface import add_data

def set_dummy_MetaDataBinned_1d():
    """
    Sets up simple McStasMetaData object with dimension, 1d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "component for 1d"
    meta_data.filename = "data.dat"
    meta_data.dimension = 50

    meta_data.info = {"Ncount" : 40}

    return meta_data


def set_dummy_McStasDataBinned_1d():
    """
    Sets up simple McStasData object, 1d case
    """
    meta_data = set_dummy_MetaDataBinned_1d()

    intensity = np.ones(20)
    error = np.ones(20)
    ncount = np.ones(20)
    axis = np.arange(20)*5.0

    return McStasDataBinned(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaDataBinned_2d():
    """
    Sets up simple McStasMetaData object with dimensions, 2d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "test a component"
    meta_data.filename = "data.dat"
    meta_data.dimension = [50, 100]

    meta_data.info = {"Ncount": 40}

    return meta_data


def set_dummy_McStasDataBinned_2d():
    """
    Sets up simple McStasData object, 2d case
    """
    meta_data = set_dummy_MetaDataBinned_2d()

    intensity = np.ones(20).reshape(4, 5)
    error = np.ones(20).reshape(4, 5)
    ncount = np.ones(20).reshape(4, 5)

    return McStasDataBinned(meta_data, intensity, error, ncount)

class Test_add_data(unittest.TestCase):
    def test_1d_updates_correctly(self):
        """
        Test that adding 1d dataset modifies only the intended dataset
        """

        data1 = set_dummy_McStasDataBinned_1d()
        data1_original = copy.deepcopy(data1)

        data2 = set_dummy_McStasDataBinned_1d()
        data2_original = copy.deepcopy(data2)

        add_data([data1], [data2])

        # Data 2 should not be touched
        self.assertTrue(np.array_equal(data2.Intensity, data2_original.Intensity))
        self.assertTrue(np.array_equal(data2.Error, data2_original.Error))
        self.assertTrue(np.array_equal(data2.Ncount, data2_original.Ncount))

        # Data 1 Intensity should be unchanged, as data1 and data2 equal
        self.assertTrue(np.array_equal(data1.Intensity, data1_original.Intensity))
        # Data 1 should be updated
        self.assertFalse(np.array_equal(data1.Error, data1_original.Error))
        self.assertFalse(np.array_equal(data1.Ncount, data1_original.Ncount))

    def test_1d_updates_different(self):
        """
        Test that adding 1d datasets work as expected when different
        """
        data1 = set_dummy_McStasDataBinned_1d()
        data1.Intensity *= 2.0
        data1.Intensity[10:] *= 2.0
        data1.Error *= 1.5
        data1.Ncount *= 4.0
        data1.metadata.info["Ncount"] *= 4.0
        data1_original = copy.deepcopy(data1)

        data2 = set_dummy_McStasDataBinned_1d()
        data2.Intensity *= 3.0
        data2.Error *= 1.5
        data2_original = copy.deepcopy(data2)

        add_data([data1], [data2])

        # Data 2 should not be touched
        self.assertTrue(np.array_equal(data2.Intensity, data2_original.Intensity))
        self.assertTrue(np.array_equal(data2.Error, data2_original.Error))
        self.assertTrue(np.array_equal(data2.Ncount, data2_original.Ncount))

        # 4 times more weight on data1, intensity 2 and 3
        expected_low_intensity = 4/5*2.0 + 1/5*3.0
        # 4 times more weight on data1, intensity 4 and 3
        expected_high_intensity = 4/5*2.0*2.0 + 1/5*3.0
        expected_error = np.sqrt((4 / 5) ** 2 * 1.5 ** 2 + (1 / 5) ** 2 * 1.5 ** 2)

        for index in range(len(data1_original.Intensity)):
            if index < 10:
                self.assertEqual(data1.Intensity[index], expected_low_intensity)
            else:
                self.assertEqual(data1.Intensity[index], expected_high_intensity)

            self.assertEqual(data1.Error[index], expected_error)
            self.assertEqual(data1.Ncount[index], 5.0)

        self.assertEqual(data1.metadata.info["Ncount"], 40*4+40)

    def test_fail(self):
        """
        Test that adding datasets fail when they dont have the same monitors

        Both 1d and 2d cases included.
        """

        data11 = set_dummy_McStasDataBinned_1d()
        data11.name = "first monitor"
        data11.filename = "first_monitor.dat"
        data12 = set_dummy_McStasDataBinned_2d()
        data12.name = "second monitor"
        data12.filename = "second_monitor.dat"
        data13 = set_dummy_McStasDataBinned_1d()
        data13.name = "third monitor"
        data13.filename = "third_monitor.dat"

        data21 = set_dummy_McStasDataBinned_1d()
        data21.name = "first monitor"
        data21.filename = "first_monitor.dat"
        data22 = set_dummy_McStasDataBinned_2d()
        data22.name = "second monitor"
        data22.filename = "second_monitor.dat"
        data23 = set_dummy_McStasDataBinned_1d()
        data23.name = "third monitor"
        data23.filename = "third_monitor.dat"

        # Should succeed, monitors match
        add_data([data11, data12, data13], [data21, data22, data23])
        # Should succeed, all monitors needed to update first argument present
        add_data([data11, data12], [data21, data22, data23])

        # Should fail if a monitor is missing
        with self.assertRaises(NameError):
            add_data([data11, data12, data13], [data21, data22])

        data23.name = "different monitor"
        # Should fail if name mismatch
        with self.assertRaises(NameError):
            add_data([data11, data12, data13], [data21, data22, data23])

    def test_2d_updates_correctly(self):
        """
        Test that adding 1d dataset modifies only the intended dataset
        """

        data1 = set_dummy_McStasDataBinned_2d()
        data1_original = copy.deepcopy(data1)

        data2 = set_dummy_McStasDataBinned_2d()
        data2_original = copy.deepcopy(data2)

        add_data([data1], [data2])

        # Data 2 should not be touched
        self.assertTrue(np.array_equal(data2.Intensity, data2_original.Intensity))
        self.assertTrue(np.array_equal(data2.Error, data2_original.Error))
        self.assertTrue(np.array_equal(data2.Ncount, data2_original.Ncount))

        # Data 1 Intensity should be unchanged, as data1 and data2 equal
        self.assertTrue(np.array_equal(data1.Intensity, data1_original.Intensity))
        # Data 1 should be updated
        self.assertFalse(np.array_equal(data1.Error, data1_original.Error))
        self.assertFalse(np.array_equal(data1.Ncount, data1_original.Ncount))

    def test_2d_updates_different(self):
        """
        Test that adding 2d datasets work as expected when different
        """
        data1 = set_dummy_McStasDataBinned_2d()
        data1.Intensity *= 2.0
        data1.Intensity[1,:] *= 2.0
        data1.Error *= 1.5
        data1.Ncount *= 4.0
        data1.metadata.info["Ncount"] *= 4.0
        data1_original = copy.deepcopy(data1)

        data2 = set_dummy_McStasDataBinned_2d()
        data2.Intensity *= 3.0
        data2.Error *= 1.5
        data2_original = copy.deepcopy(data2)

        add_data([data1], [data2])

        # Data 2 should not be touched
        self.assertTrue(np.array_equal(data2.Intensity, data2_original.Intensity))
        self.assertTrue(np.array_equal(data2.Error, data2_original.Error))
        self.assertTrue(np.array_equal(data2.Ncount, data2_original.Ncount))

        # 4 times more weight on data1, intensity 2 and 3
        expected_low_intensity = 4/5*2.0 + 1/5*3.0
        # 4 times more weight on data1, intensity 4 and 3
        expected_high_intensity = 4/5*2.0*2.0 + 1/5*3.0
        expected_error = np.sqrt((4 / 5) ** 2 * 1.5 ** 2 + (1 / 5) ** 2 * 1.5 ** 2)

        for index1 in range(len(data1_original.Intensity[:,0])):
            for index2 in range(len(data1_original.Intensity[0, :])):

                if index1 == 1:
                    self.assertEqual(data1.Intensity[index1, index2], expected_high_intensity)
                else:
                    self.assertEqual(data1.Intensity[index1, index2], expected_low_intensity)

            self.assertEqual(data1.Error[index1, index2], expected_error)
            self.assertEqual(data1.Ncount[index1, index2], 5.0)

        self.assertEqual(data1.metadata.info["Ncount"], 40*4+40)

