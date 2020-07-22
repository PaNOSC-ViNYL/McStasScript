import os
import unittest


import numpy as np

from mcstasscript.interface.functions import name_search
from mcstasscript.interface.functions import name_plot_options
from mcstasscript.interface.functions import load_data
from mcstasscript.data.data import McStasData
from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasPlotOptions


def set_dummy_MetaData_1d(name):
    meta_data = McStasMetaData()
    meta_data.component_name = name
    meta_data.dimension = 50
    meta_data.filename = name + ".dat"

    return meta_data


def set_dummy_McStasData_1d(name):
    meta_data = set_dummy_MetaData_1d(name)

    intensity = np.arange(20)
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasData(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaData_2d(name):
    meta_data = McStasMetaData()
    meta_data.component_name = name
    meta_data.dimension = [50, 100]
    meta_data.filename = name + ".dat"

    return meta_data


def set_dummy_McStasData_2d(name):
    meta_data = set_dummy_MetaData_2d(name)

    intensity = np.arange(20).reshape(4, 5)
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasData(meta_data, intensity, error, ncount)


def setup_McStasData_array():

    data_list = []

    data_list.append(set_dummy_McStasData_1d("A_1d_thing"))
    data_list.append(set_dummy_McStasData_2d("A_2d_thing"))
    data_list.append(set_dummy_McStasData_1d("Another_1d_thing"))
    data_list.append(set_dummy_McStasData_2d("Another_2d_thing"))
    data_list.append(set_dummy_McStasData_2d("A_third_2d_thing"))

    hero_object = set_dummy_McStasData_2d("Hero")
    hero_object.metadata.dimension = 123
    hero_object.plot_options.colormap = "very hot"

    data_list.append(hero_object)

    data_list.append(set_dummy_McStasData_2d("After_hero_2d"))
    data_list.append(set_dummy_McStasData_2d("Last_object_2d"))

    return data_list


def setup_McStasData_array_repeat():

    data_list = []

    data_list.append(set_dummy_McStasData_1d("A_1d_thing"))
    data_list.append(set_dummy_McStasData_2d("A_2d_thing"))
    data_list.append(set_dummy_McStasData_1d("Another_1d_thing"))
    data_list.append(set_dummy_McStasData_2d("Another_2d_thing"))
    data_list.append(set_dummy_McStasData_2d("Hero"))

    hero_object = set_dummy_McStasData_2d("Big_Hero")
    hero_object.metadata.dimension = 123
    hero_object.plot_options.colormap = "very hot"

    data_list.append(hero_object)

    data_list.append(set_dummy_McStasData_2d("After_hero_2d"))
    data_list.append(set_dummy_McStasData_2d("Last_object_2d"))

    return data_list


class Test_name_search(unittest.TestCase):
    """
    Test the utility function called name_search which finds and
    returns a McStasData set with a given name from a list of
    McStasData objects.
    """

    def test_name_search_read(self):
        """
        Test simple case
        """

        data_list = setup_McStasData_array()

        hero_object = name_search("Hero", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)
        
    def test_name_search_filename_read(self):
        """
        Test simple case
        """

        data_list = setup_McStasData_array()

        hero_object = name_search("Hero.dat", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)

    def test_name_search_read_repeat(self):
        """
        Test simple case with repeat name
        """

        data_list = setup_McStasData_array_repeat()

        hero_object = name_search("Big_Hero", data_list)

        self.assertEqual(hero_object.metadata.dimension, 123)
        
    def test_name_search_read_dubplicate(self):
        """
        Test simple case with duplicated name, should return list
        """

        data_list = setup_McStasData_array_repeat()
        
        hero_object = set_dummy_McStasData_2d("Big_Hero")
        hero_object.metadata.dimension = 321
        hero_object.plot_options.colormap = "very hot"

        data_list.append(hero_object)
        
        results = name_search("Big_Hero", data_list)

        self.assertEqual(len(results), 2)

        self.assertEqual(results[0].metadata.dimension, 123)
        self.assertEqual(results[1].metadata.dimension, 321)

    def test_name_search_read_error(self):
        """
        Test simple case
        """

        data_list = setup_McStasData_array()

        with self.assertRaises(NameError):
            hero_object = name_search("Hero8", data_list)

    def test_name_search_type_error_not_list(self):
        """
        Test simple case
        """

        data_list = set_dummy_McStasData_2d("Last_object_2d")

        with self.assertRaises(NameError):
            hero_object = name_search("Hero", data_list)

    def test_name_search_type_error_not_McStasData(self):
        """
        Test simple case
        """

        data_list = [1, 2, 3]

        with self.assertRaises(NameError):
            hero_object = name_search(1, data_list)


class Test_name_plot_options(unittest.TestCase):
    """
    Test the utility function called name_plot_options which sends
    keyword arguments to the set_plot_options method of the
    McStasData object in a given list that has the given name.

    """

    def test_name_plot_options_simple(self):
        """
        Test simple case
        """

        data_list = setup_McStasData_array()
        name_plot_options("Hero", data_list, colormap="very hot")
        hero_object = name_search("Hero", data_list)
        self.assertEqual(hero_object.plot_options.colormap, "very hot")
        
    def test_name_plot_options_duplicate(self):
        """
        Test case where several datasets are modified
        """

        data_list = setup_McStasData_array()
        
        hero_object = set_dummy_McStasData_2d("Hero")
        hero_object.metadata.dimension = 321
        hero_object.plot_options.colormap = "absurdly hot"

        data_list.append(hero_object)
        
        name_plot_options("Hero", data_list, colormap="cold")
        
        results = name_search("Hero", data_list)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].plot_options.colormap, "cold")
        self.assertEqual(results[1].plot_options.colormap, "cold")


class Test_load_data(unittest.TestCase):
    """
    Testing the load data function which calls ManagedMcrun, which was
    tested elsewhere. Since the load data is tested elsewhere, this
    function has just a single test to check the interface.
    """
    def test_crun_load_data_PSD4PI(self):
        """
        Use test_data_set to test load_data for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = load_data("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(results), 3)

        PSD_4PI = results[0]

        self.assertEqual(PSD_4PI.name, "PSD_4PI")
        self.assertEqual(PSD_4PI.metadata.dimension, [300, 300])
        self.assertEqual(PSD_4PI.metadata.limits, [-180, 180, -90, 90])
        self.assertEqual(PSD_4PI.metadata.xlabel, "Longitude [deg]")
        self.assertEqual(PSD_4PI.metadata.ylabel, "Lattitude [deg]")
        self.assertEqual(PSD_4PI.metadata.title, "4PI PSD monitor")
        self.assertEqual(PSD_4PI.Ncount[4][1], 4)
        self.assertEqual(PSD_4PI.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(PSD_4PI.Error[4][1], 1.139482296E-10)


if __name__ == '__main__':
    unittest.main()
