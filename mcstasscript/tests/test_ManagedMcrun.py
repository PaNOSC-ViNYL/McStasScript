import os
import io
import unittest
import numpy as np

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasData
from mcstasscript.helper.managed_mcrun import ManagedMcrun


class TestManagedMcrun(unittest.TestCase):
    """
    Testing the ManagedMcrun class that sets up McStas runs, runs the
    simulation and loads the data.

    Here the simulation is not actually performed, this will be done in
    integration tests. The surrounding plumbing and data loading is
    tested.
    """

    def test_ManagedMcrun_init_simple(self):
        """
        Check shortest possible initialization works
        """
        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="test_path")

        self.assertEqual(mcrun_obj.name_of_instrumentfile, "test.instr")
        self.assertEqual(mcrun_obj.data_folder_name, "test_folder")
        self.assertEqual(mcrun_obj.mcrun_path, "test_path")

    def test_ManagedMcrun_init_defaults(self):
        """
        Check default values are set up correctly
        """
        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="")

        self.assertEqual(mcrun_obj.mpi, None)
        self.assertEqual(mcrun_obj.ncount, 1000000)
        self.assertEqual(mcrun_obj.run_path, ".")

    def test_ManagedMcrun_init_set_values(self):
        """
        Check default values are set up correctly
        """
        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="",
                                 run_path="test",
                                 mpi=4,
                                 ncount=128)

        self.assertEqual(mcrun_obj.mpi, 4)
        self.assertEqual(mcrun_obj.ncount, 128)
        self.assertEqual(mcrun_obj.run_path, "test")

    def test_ManagedMcrun_init_set_parameters(self):
        """
        Check default values are set up correctly
        """

        par_input = {"A_par": 5.1,
                     "int_par": 1,
                     "define_par": "Bike",
                     "string_par": "\"Car\""}

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="",
                                 parameters=par_input)

        self.assertEqual(mcrun_obj.parameters["A_par"], 5.1)
        self.assertEqual(mcrun_obj.parameters["int_par"], 1)
        self.assertEqual(mcrun_obj.parameters["define_par"], "Bike")
        self.assertEqual(mcrun_obj.parameters["string_par"], "\"Car\"")

    def test_ManagedMcrun_init_set_custom_flags(self):
        """
        Check default values are set up correctly
        """

        custom_flag_input = "-p"

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="",
                                 custom_flags=custom_flag_input)

        self.assertEqual(mcrun_obj.custom_flags, custom_flag_input)

    def test_ManagedMcrun_init_no_folder_error(self):
        """
        An error should occur if no filename is given
        """
        with self.assertRaises(NameError):
            mcrun_obj = ManagedMcrun("test.instr", mcrun_path="")

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_basic(self, mock_sub):
        """
        Check a basic system call is correct
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="path")

        mcrun_obj.run_simulation()

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_folder")

        # a double space because of a missing option
        expected_call = ("path/mcrun -c -n 1000000 "
                         + "-d " + expected_folder_path + "  test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_basic_path(self, mock_sub):
        """
        Check a basic system call is correct, with different path format
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="path/")

        mcrun_obj.run_simulation()

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_folder")

        # a double space because of a missing option
        expected_call = ("path/mcrun -c -n 1000000 "
                         + "-d " + expected_folder_path + "  test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_no_standard(self, mock_sub):
        """
        Check a non standard system call is correct
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="path",
                                 mpi=7,
                                 ncount=48.4,
                                 custom_flags="-fo")

        mcrun_obj.run_simulation()

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_folder")

        # a double space because of a missing option
        expected_call = ("path/mcrun -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_parameters(self, mock_sub):
        """
        Check a run with parameters is correct
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="path",
                                 mpi=7,
                                 ncount=48.4,
                                 custom_flags="-fo",
                                 parameters={"A": 2,
                                             "BC": "car",
                                             "th": "\"toy\""})

        mcrun_obj.run_simulation()

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_folder")
        # a double space because of a missing option
        expected_call = ("path/mcrun -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_compile(self, mock_sub):
        """
        Check a run with parameters is correct
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_folder",
                                 mcrun_path="path",
                                 mpi=7,
                                 ncount=48.4,
                                 force_compile=False,
                                 custom_flags="-fo",
                                 parameters={"A": 2,
                                             "BC": "car",
                                             "th": "\"toy\""})

        mcrun_obj.run_simulation()

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_folder")

        # a double space because of a missing option
        expected_call = ("path/mcrun -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    def test_ManagedMcrun_load_data_PSD4PI(self):
        """
        Use test_data_set to test load_data for PSD_4PI
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = mcrun_obj.load_results()

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

    def test_ManagedMcrun_load_data_PSD(self):
        """
        Use test_data_set to test load_data for PSD
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = mcrun_obj.load_results()

        os.chdir(current_work_dir)  # Reset work directory

        # Check other properties

        PSD = results[1]

        self.assertEqual(PSD.name, "PSD")
        self.assertEqual(PSD.metadata.dimension, [200, 200])
        self.assertEqual(PSD.metadata.limits, [-5, 5, -5, 5])
        self.assertEqual(PSD.metadata.xlabel, "X position [cm]")
        self.assertEqual(PSD.metadata.ylabel, "Y position [cm]")
        self.assertEqual(PSD.metadata.title, "PSD monitor")
        self.assertEqual(PSD.Ncount[27][21], 9)
        self.assertEqual(PSD.Intensity[27][21], 2.623929371e-13)
        self.assertEqual(PSD.Error[27][21], 2.765467693e-13)

    def test_ManagedMcrun_load_data_L_mon(self):
        """
        Use test_data_set to test load_data for L_mon
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = mcrun_obj.load_results()

        os.chdir(current_work_dir)  # Reset work directory

        # Check other properties

        L_mon = results[2]

        self.assertEqual(L_mon.name, "L_mon")
        self.assertEqual(L_mon.metadata.dimension, 150)
        self.assertEqual(L_mon.metadata.limits, [0.7, 1.3])
        self.assertEqual(L_mon.metadata.xlabel, "Wavelength [AA]")
        self.assertEqual(L_mon.metadata.ylabel, "Intensity")
        self.assertEqual(L_mon.metadata.title, "Wavelength monitor")
        self.assertEqual(L_mon.xaxis[53], 0.914)
        self.assertEqual(L_mon.Ncount[53], 37111)
        self.assertEqual(L_mon.Intensity[53], 6.990299315e-06)
        self.assertEqual(L_mon.Error[53], 6.215308587e-08)

    def test_ManagedMcrun_load_data_L_mon_direct(self):
        """
        Use test_data_set to test load_data for L_mon with direct path
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        load_path = os.path.join(THIS_DIR, "test_data_set")
        results = mcrun_obj.load_results(load_path)

        os.chdir(current_work_dir)  # Reset work directory

        # Check other properties

        L_mon = results[2]

        self.assertEqual(L_mon.name, "L_mon")
        self.assertEqual(L_mon.metadata.dimension, 150)
        self.assertEqual(L_mon.metadata.limits, [0.7, 1.3])
        self.assertEqual(L_mon.metadata.xlabel, "Wavelength [AA]")
        self.assertEqual(L_mon.metadata.ylabel, "Intensity")
        self.assertEqual(L_mon.metadata.title, "Wavelength monitor")
        self.assertEqual(L_mon.xaxis[53], 0.914)
        self.assertEqual(L_mon.Ncount[53], 37111)
        self.assertEqual(L_mon.Intensity[53], 6.990299315e-06)
        self.assertEqual(L_mon.Error[53], 6.215308587e-08)

    def test_ManagedMcrun_load_data_L_mon_direct_error(self):
        """
        Check an error occurs when directory has no mccode.sim
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        load_path = os.path.join(THIS_DIR, "non_exsistent_dataset")
        with self.assertRaises(NameError):
            results = mcrun_obj.load_results(load_path)

        os.chdir(current_work_dir)  # Reset work directory

    def test_ManagedMcrun_load_data_L_mon_empty_error(self):
        """
        Check an error occurs when pointed to empty directory
        """

        mcrun_obj = ManagedMcrun("test.instr",
                                 foldername="test_data_set",
                                 mcrun_path="path")

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        load_path = os.path.join(THIS_DIR, "/dummy_mcstas")
        with self.assertRaises(NameError):
            results = mcrun_obj.load_results(load_path)

        os.chdir(current_work_dir)  # Reset work directory


if __name__ == '__main__':
    unittest.main()
