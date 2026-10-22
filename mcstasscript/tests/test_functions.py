import os
import unittest


import numpy as np

from mcstasscript.interface.functions import name_search
from mcstasscript.interface.functions import name_plot_options
from mcstasscript.interface.functions import load_data
from mcstasscript.interface.functions import load_metadata
from mcstasscript.interface.functions import load_monitor
from mcstasscript.data.data import McStasDataBinned
from mcstasscript.data.data import McStasMetaData


def set_dummy_MetaDataBinned_1d(name):
    """
    Sets up a dummy MetaData object for a 1d dataset

    Parameters
    ----------

    name : str
        base for filename, .dat will be appended
    """

    meta_data = McStasMetaData()
    meta_data.component_name = name
    meta_data.dimension = 50
    meta_data.filename = name + ".dat"

    return meta_data


def set_dummy_McStasDataBinned_1d(name):
    """
    Sets up a dummy McStasData object for a 1d dataset

    Parameters
    ----------

    name : str
        base for filename, .dat will be appended
    """
    meta_data = set_dummy_MetaDataBinned_1d(name)

    intensity = np.arange(20)
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasDataBinned(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaDataBinned_2d(name):
    """
    Sets up a dummy MetaData object for a 2d dataset

    Parameters
    ----------

    name : str
        base for filename, .dat will be appended
    """
    meta_data = McStasMetaData()
    meta_data.component_name = name
    meta_data.dimension = [50, 100]
    meta_data.filename = name + ".dat"

    return meta_data


def set_dummy_McStasDataBinned_2d(name):
    """
    Sets up a dummy McStasData object for a 2d dataset

    Parameters
    ----------

    name : str
        base for filename, .dat will be appended
    """

    meta_data = set_dummy_MetaDataBinned_2d(name)

    intensity = np.arange(20).reshape(4, 5)
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasDataBinned(meta_data, intensity, error, ncount)


def setup_McStasData_array():
    """
    Sets up an list of McStasData objects, similar to simulation output
    """

    data_list = []

    data_list.append(set_dummy_McStasDataBinned_1d("A_1d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("A_2d_thing"))
    data_list.append(set_dummy_McStasDataBinned_1d("Another_1d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("Another_2d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("A_third_2d_thing"))

    hero_object = set_dummy_McStasDataBinned_2d("Hero")
    hero_object.metadata.dimension = 123
    hero_object.plot_options.colormap = "very hot"

    data_list.append(hero_object)

    data_list.append(set_dummy_McStasDataBinned_2d("After_hero_2d"))
    data_list.append(set_dummy_McStasDataBinned_2d("Last_object_2d"))

    return data_list


def setup_McStasData_array_repeat():
    """
    Sets up an list of McStasData objects, similar to simulation output

    Have Hero twice in naming, testing search capability
    """

    data_list = []

    data_list.append(set_dummy_McStasDataBinned_1d("A_1d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("A_2d_thing"))
    data_list.append(set_dummy_McStasDataBinned_1d("Another_1d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("Another_2d_thing"))
    data_list.append(set_dummy_McStasDataBinned_2d("Hero"))

    hero_object = set_dummy_McStasDataBinned_2d("Big_Hero")
    hero_object.metadata.dimension = 123
    hero_object.plot_options.colormap = "very hot"

    data_list.append(hero_object)

    data_list.append(set_dummy_McStasDataBinned_2d("After_hero_2d"))
    data_list.append(set_dummy_McStasDataBinned_2d("Last_object_2d"))

    return data_list


class Test_name_search(unittest.TestCase):
    """
    Test the utility function called name_search which finds and
    returns a McStasData set with a given name from a list of
    McStasData objects.
    """

    def test_name_search_read(self):
        """
        Test that Hero object can be found and check the unique dimension

        Here the name is used
        """

        data_list = setup_McStasData_array()

        hero_object = name_search("Hero", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)

    def test_name_search_filename_read(self):
        """
        Test that Hero object can be found and check the unique dimension

        Here the name of the datafile is used
        """

        data_list = setup_McStasData_array()

        hero_object = name_search("Hero.dat", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)

    def test_name_search_read_repeat(self):
        """
        Test that Hero object can be found and check the unique dimension
        Here the used data set has two monitors with Hero in the name

        Here the name of the monitor is used
        """

        data_list = setup_McStasData_array_repeat()

        hero_object = name_search("Big_Hero", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)

    def test_name_search_read_duplicate(self):
        """
        Test simple case with duplicated name, search should return list
        """

        data_list = setup_McStasData_array_repeat()

        # Adds another dataset with a name already in the data_list
        hero_object = set_dummy_McStasDataBinned_2d("Big_Hero")
        hero_object.metadata.dimension = 321
        hero_object.plot_options.colormap = "very hot"

        data_list.append(hero_object)

        # Now two McStasData objects match the Big_Hero name
        results = name_search("Big_Hero", data_list)

        self.assertEqual(type(results), list)
        # Check two results are returned
        self.assertEqual(len(results), 2)

        # Check they have the correct dimensions
        self.assertEqual(results[0].metadata.dimension, 123)
        self.assertEqual(results[1].metadata.dimension, 321)

    def test_name_search_read_error(self):
        """
        Check an NameError is returned when no match is found
        """

        data_list = setup_McStasData_array()

        with self.assertRaises(NameError):
            name_search("Hero8", data_list)

    def test_name_search_type_error_not_list(self):
        """
        Check error is given even when data list is just single object
        """

        data_list = set_dummy_McStasDataBinned_2d("Last_object_2d")

        with self.assertRaises(RuntimeError):
            name_search("Hero", data_list)

    def test_name_search_type_error_not_McStasData(self):
        """
        Checks that an error is returned if the given dataset contains
        non McStasData objects
        """

        data_list = [1, 2, 3]

        with self.assertRaises(RuntimeError):
            name_search(1, data_list)


class Test_name_plot_options(unittest.TestCase):
    """
    Test the utility function called name_plot_options which sends
    keyword arguments to the set_plot_options method of the
    McStasData object in a given list that has the given name.

    """

    def test_name_plot_options_simple(self):
        """
        Check set_plot_options can modify given attribute
        """

        data_list = setup_McStasData_array()
        name_plot_options("Hero", data_list, colormap="Oranges")
        hero_object = name_search("Hero", data_list)
        self.assertEqual(hero_object.plot_options.colormap, "Oranges")

    def test_name_plot_options_duplicate(self):
        """
        Test case where several McStasData objects are modified since
        the internal name_search finds multiple matches
        """

        data_list = setup_McStasData_array()

        hero_object = set_dummy_McStasDataBinned_2d("Hero")
        hero_object.metadata.dimension = 321
        hero_object.plot_options.colormap = "absurdly hot"

        data_list.append(hero_object)

        name_plot_options("Hero", data_list, colormap="Blues")

        results = name_search("Hero", data_list)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].plot_options.colormap, "Blues")
        self.assertEqual(results[1].plot_options.colormap, "Blues")


class Test_load_data(unittest.TestCase):
    """
    Testing the load data function which calls ManagedMcrun, which was
    tested elsewhere. Since the load data is tested elsewhere, this
    function has just a single test to check the interface.
    """
    def test_mcrun_load_data_PSD4PI(self):
        """
        Use test_data_set to test load_data for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = load_data("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(results), 4)

        PSD_4PI = results[0]

        self.assertEqual(PSD_4PI.name, "PSD_4PI")
        self.assertEqual(PSD_4PI.metadata.dimension, [300, 300])
        self.assertEqual(PSD_4PI.metadata.limits, [-180, 180, -90, 90])
        self.assertEqual(PSD_4PI.metadata.xlabel, "Longitude [deg]")
        self.assertEqual(PSD_4PI.metadata.ylabel, "Latitude [deg]")
        self.assertEqual(PSD_4PI.metadata.title, "4PI PSD monitor")
        self.assertEqual(PSD_4PI.Ncount[4][1], 4)
        self.assertEqual(PSD_4PI.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(PSD_4PI.Error[4][1], 1.139482296E-10)


class Test_load_metadata(unittest.TestCase):
    """
    Testing the load metadata function which calls ManagedMcrun, which
    was tested elsewhere. Since the load metadata is tested elsewhere,
    this function has just a single test to check the interface.
    """
    def test_mcrun_load_metadata_PSD4PI(self):
        """
        Use test_data_set to test load_metadata for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        metadata = load_metadata("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(metadata), 4)

        PSD_4PI = metadata[0]
        self.assertEqual(PSD_4PI.dimension, [300, 300])
        self.assertEqual(PSD_4PI.limits, [-180, 180, -90, 90])
        self.assertEqual(PSD_4PI.xlabel, "Longitude [deg]")
        self.assertEqual(PSD_4PI.ylabel, "Latitude [deg]")
        self.assertEqual(PSD_4PI.title, "4PI PSD monitor")

class Test_load_monitor(unittest.TestCase):
    """
    Testing the load monitor function which calls ManagedMcrun, which
    was tested elsewhere. Since the load monitor is tested elsewhere, this
    function has just a single test to check the interface.
    """
    def test_mcrun_load_monitor_PSD4PI(self):
        """
        Use test_data_set to test load_monitor for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        metadata = load_metadata("test_data_set")
        PSD_4PI = metadata[0]
        monitor = load_monitor(PSD_4PI, "test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(monitor.name, "PSD_4PI")
        self.assertEqual(monitor.metadata.dimension, [300, 300])
        self.assertEqual(monitor.metadata.limits, [-180, 180, -90, 90])
        self.assertEqual(monitor.metadata.xlabel, "Longitude [deg]")
        self.assertEqual(monitor.metadata.ylabel, "Latitude [deg]")
        self.assertEqual(monitor.metadata.title, "4PI PSD monitor")
        self.assertEqual(monitor.Ncount[4][1], 4)
        self.assertEqual(monitor.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(monitor.Error[4][1], 1.139482296E-10)


if __name__ == '__main__':
    unittest.main()
