import os
import unittest
import unittest.mock

from mcstasscript.helper.managed_mcrun import ManagedMcrun
from mcstasscript.helper.managed_mcrun import load_results
from mcstasscript.helper.managed_mcrun import load_metadata
from mcstasscript.helper.managed_mcrun import load_monitor
from mcstasscript.tests.helpers_for_tests import WorkInTestDir

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

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun")

        self.assertEqual(mcrun_obj.name_of_instrumentfile, "test.instr")

        expected_data_folder = os.path.join(THIS_DIR, "test_folder")
        self.assertEqual(mcrun_obj.data_folder_name, expected_data_folder)

        expected_executable_path = os.path.join(THIS_DIR, "dummy_mcstas")
        self.assertEqual(mcrun_obj.executable_path, expected_executable_path)

    def test_ManagedMcrun_init_defaults(self):
        """
        Check default values are set up correctly
        """
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun")

        self.assertEqual(mcrun_obj.mpi, None)
        self.assertEqual(mcrun_obj.ncount, 1000000)
        expected_run_path = os.path.join(THIS_DIR, ".")
        self.assertEqual(mcrun_obj.run_path, expected_run_path)

    def test_ManagedMcrun_init_set_values(self):
        """
        Check values given to ManagedMcrun are internalized

        run_path set to an existing folder in the test directory
        """
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable="mcrun",
                                     executable_path=executable_path,
                                     run_path="test_data_set",
                                     mpi=4,
                                     ncount=128)

        self.assertEqual(mcrun_obj.mpi, 4)
        self.assertEqual(mcrun_obj.ncount, 128)
        expected_run_path = os.path.join(THIS_DIR, "test_data_set")
        self.assertEqual(mcrun_obj.run_path, expected_run_path)

    def test_ManagedMcrun_init_set_parameters(self):
        """
        Check parameters can be given as dictionary
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        par_input = {"A_par": 5.1,
                     "int_par": 1,
                     "define_par": "Bike",
                     "string_par": "\"Car\""}

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="",
                                     parameters=par_input)

        self.assertEqual(mcrun_obj.parameters["A_par"], 5.1)
        self.assertEqual(mcrun_obj.parameters["int_par"], 1)
        self.assertEqual(mcrun_obj.parameters["define_par"], "Bike")
        self.assertEqual(mcrun_obj.parameters["string_par"], "\"Car\"")

    def test_ManagedMcrun_init_set_custom_flags(self):
        """
        Check custom_flags can be given by user
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        custom_flag_input = "-p"
        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable="mcrun",
                                     executable_path=executable_path,
                                     custom_flags=custom_flag_input)

        self.assertEqual(mcrun_obj.custom_flags, custom_flag_input)

    def test_ManagedMcrun_init_no_folder_error(self):
        """
        An error should occur if no filename is given
        """
        with self.assertRaises(NameError):
            ManagedMcrun("test.instr", mcrun_path="")

    def test_ManagedMcrun_init_invalid_ncount_error(self):
        """
        An error should occur if negative ncount is given
        """
        with self.assertRaises(ValueError):
            ManagedMcrun("test.instr",
                         output_path="test_folder",
                         mcrun_path="",
                         ncount=-8)

    def test_ManagedMcrun_init_invalid_mpi_error(self):
        """
        An error should occur if negative mpi is given
        """
        with self.assertRaises(ValueError):
            ManagedMcrun("test.instr",
                         output_path="test_folder",
                         mcrun_path="",
                         mpi=-8)

    def test_ManagedMcrun_init_invalid_parameters_error(self):
        """
        An error should occur if parameters is given as non dict
        """
        with self.assertRaises(RuntimeError):
            ManagedMcrun("test.instr",
                         output_path="test_folder",
                         mcrun_path="",
                         parameters=[1, 2, 3])

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_basic(self, mock_sub):
        """
        Check a basic system call is correct
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",)

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        # a double space because of a missing option
        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'

        expected_call = (executable + " -c -n 1000000 "
                         + "-d " + expected_folder_path + "  test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_basic_path(self, mock_sub):
        """
        Check a basic system call is correct, with different path format
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas", "")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",)

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        # a double space because of a missing option
        expected_call = (executable + " -c -n 1000000 "
                         + "-d " + expected_folder_path + "  test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_no_standard(self, mock_sub):
        """
        Check a non standard system call is correct

        Here multiple options are used and ncount is a float that should
        be rounded by the class.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     mpi=7, seed=300,
                                     ncount=48.4,
                                     custom_flags="-fo")

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        # a double space because of a missing option
        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        expected_call = (executable + " -c -n 48 --mpi=7 --seed=300 "
                         + "-d " + expected_folder_path + " -fo test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_with_gravity(self, mock_sub):
        """
        Check a non standard system call is correct when including gravity

        Here multiple options are used and ncount is a float that should
        be rounded by the class.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     gravity=True,
                                     mpi=7, seed=300,
                                     ncount=48.4,
                                     custom_flags="-fo")

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        # a double space because of a missing option
        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        expected_call = (executable + " -c -g -n 48 --mpi=7 --seed=300 "
                         + "-d " + expected_folder_path + " -fo test.instr")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_parameters(self, mock_sub):
        """
        Check a run with parameters is correct
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     mpi=7,
                                     ncount=48.4,
                                     custom_flags="-fo",
                                     parameters={"A": 2,
                                                 "BC": "car",
                                                 "th": "\"toy\""})

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")
        # a double space because of a missing option
        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'

        expected_call = (executable + " -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_compile(self, mock_sub):
        """
        Check run with force_compile set to False works
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     mpi=7,
                                     ncount=48.4,
                                     force_compile=False,
                                     custom_flags="-fo",
                                     parameters={"A": 2,
                                                 "BC": "car",
                                                 "th": "\"toy\""})

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        # a double space because of a missing option
        expected_call = (executable + " -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_NeXus(self, mock_sub):
        """
        Check run with NeXus works
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     mpi=7,
                                     ncount=57.4,
                                     force_compile=False,
                                     NeXus=True,
                                     custom_flags="-fo",
                                     parameters={"A": 2,
                                                 "BC": "car",
                                                 "th": "\"toy\""})

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        # a double space because of a missing option
        expected_call = (executable + " --format=NeXus -n 57 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    @unittest.mock.patch("subprocess.run")
    def test_ManagedMcrun_run_simulation_openacc(self, mock_sub):
        """
        Check run with openacc works
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_folder",
                                     executable_path=executable_path,
                                     executable="mcrun",
                                     mpi=7,
                                     ncount=48.4,
                                     openacc=True,
                                     force_compile=False,
                                     custom_flags="-fo",
                                     parameters={"A": 2,
                                                 "BC": "car",
                                                 "th": "\"toy\""})

        mcrun_obj.run_simulation()

        expected_folder_path = os.path.join(THIS_DIR, "test_folder")

        executable = os.path.join(executable_path, "mcrun")
        executable = '"' + executable + '"'
        # a double space because of a missing option
        expected_call = (executable + " --openacc -n 48 --mpi=7 "
                         + "-d " + expected_folder_path + " -fo test.instr "
                         + "A=2 BC=car th=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-2, stdout=-1,
                                         universal_newlines=True,
                                         cwd=mcrun_obj.run_path)

    def test_ManagedMcrun_load_data_PSD4PI(self):
        """
        Use test_data_set to test load_data for PSD_4PI

        test_data_set contains three data files and some junk, the mccode.sim
        file contains names of the data files so only these are loaded.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            results = mcrun_obj.load_results()

        # Check three data objects are loaded
        self.assertEqual(len(results), 4)

        # Check properties of PSD_4PI data
        PSD_4PI = results[0]

        self.assertEqual(PSD_4PI.name, "PSD_4PI")
        self.assertEqual(PSD_4PI.metadata.dimension, [300, 300])
        self.assertEqual(PSD_4PI.metadata.limits, [-180, 180, -90, 90])
        self.assertEqual(PSD_4PI.metadata.xlabel, "Longitude [deg]")
        self.assertEqual(PSD_4PI.metadata.ylabel, "Latitude [deg]")
        self.assertEqual(PSD_4PI.metadata.title, "4PI PSD monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(PSD_4PI.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(PSD_4PI.metadata.parameters, expected_parameters)
        self.assertEqual(PSD_4PI.Ncount[4][1], 4)
        self.assertEqual(PSD_4PI.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(PSD_4PI.Error[4][1], 1.139482296E-10)

    def test_ManagedMcrun_load_data_PSD(self):
        """
        Use test_data_set to test load_data for PSD
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            results = mcrun_obj.load_results()

        # Check three data objects are loaded
        self.assertEqual(len(results), 4)

        # Check properties of PSD data
        PSD = results[1]

        self.assertEqual(PSD.name, "PSD")
        self.assertEqual(PSD.metadata.dimension, [200, 200])
        self.assertEqual(PSD.metadata.limits, [-5, 5, -5, 5])
        self.assertEqual(PSD.metadata.xlabel, "X position [cm]")
        self.assertEqual(PSD.metadata.ylabel, "Y position [cm]")
        self.assertEqual(PSD.metadata.title, "PSD monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(PSD.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(PSD.metadata.parameters, expected_parameters)
        self.assertEqual(PSD.Ncount[27][21], 9)
        self.assertEqual(PSD.Intensity[27][21], 2.623929371e-13)
        self.assertEqual(PSD.Error[27][21], 2.765467693e-13)

    def test_ManagedMcrun_load_data_L_mon(self):
        """
        Use test_data_set to test load_data for L_mon
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            results = mcrun_obj.load_results()

        # Check three data objects are loaded
        self.assertEqual(len(results), 4)

        # Check properties of L_mon
        L_mon = results[2]

        self.assertEqual(L_mon.name, "L_mon")
        self.assertEqual(L_mon.metadata.dimension, 150)
        self.assertEqual(L_mon.metadata.limits, [0.7, 1.3])
        self.assertEqual(L_mon.metadata.xlabel, "Wavelength [AA]")
        self.assertEqual(L_mon.metadata.ylabel, "Intensity")
        self.assertEqual(L_mon.metadata.title, "Wavelength monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(L_mon.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(L_mon.metadata.parameters, expected_parameters)
        self.assertEqual(L_mon.xaxis[53], 0.914)
        self.assertEqual(L_mon.Ncount[53], 37111)
        self.assertEqual(L_mon.Intensity[53], 6.990299315e-06)
        self.assertEqual(L_mon.Error[53], 6.215308587e-08)

    def test_ManagedMcrun_load_data_L_mon_direct(self):
        """
        Use test_data_set to test load_data for L_mon with direct path
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            load_path = os.path.join(THIS_DIR, "test_data_set")
            results = mcrun_obj.load_results(load_path)

        # Check properties of L_mon
        L_mon = results[2]

        self.assertEqual(L_mon.name, "L_mon")
        self.assertEqual(L_mon.metadata.dimension, 150)
        self.assertEqual(L_mon.metadata.limits, [0.7, 1.3])
        self.assertEqual(L_mon.metadata.xlabel, "Wavelength [AA]")
        self.assertEqual(L_mon.metadata.ylabel, "Intensity")
        self.assertEqual(L_mon.metadata.title, "Wavelength monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(L_mon.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(L_mon.metadata.parameters, expected_parameters)
        self.assertEqual(L_mon.xaxis[53], 0.914)
        self.assertEqual(L_mon.Ncount[53], 37111)
        self.assertEqual(L_mon.Intensity[53], 6.990299315e-06)
        self.assertEqual(L_mon.Error[53], 6.215308587e-08)

        self.assertFalse(hasattr(L_mon, 'Events'))

    def test_ManagedMcrun_load_data_Event(self):
        """
        Use test_data_set to test load_data for event data
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            load_path = os.path.join(THIS_DIR, "test_data_set")
            results = mcrun_obj.load_results(load_path)

        # Check properties of event data file
        mon = results[3]

        self.assertEqual(mon.name, "monitor")
        self.assertEqual(mon.metadata.dimension, [8, 12000])
        self.assertEqual(mon.metadata.limits, [1.0, 12000.0, 1.0, 8.0])
        self.assertEqual(mon.metadata.xlabel, "List of neutron events")
        self.assertEqual(mon.metadata.ylabel, "p x y z vx vy vz t")
        self.assertEqual(mon.metadata.title, "Intensity Position Position"
                + " Position Velocity Velocity Velocity"
                + " Time_Of_Flight Monitor (Square)")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(mon.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(mon.metadata.parameters, expected_parameters)
        self.assertEqual(mon.Events[12, 1], -0.006163896406)
        self.assertEqual(mon.Events[43, 4], 22.06193582)

        self.assertFalse(hasattr(mon, 'xaxis'))
        self.assertFalse(hasattr(mon, 'Error'))
        self.assertFalse(hasattr(mon, 'Ncount'))

    def test_ManagedMcrun_load_data_nonexisting(self):
        """
        If folder does not exists, a warning should be shown and None returned
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

        load_path = os.path.join(THIS_DIR, "non_existent_dataset")

        with self.assertWarns(Warning):
            result = mcrun_obj.load_results(load_path)

        self.assertIsNone(result)

    def test_ManagedMcrun_load_data_no_mcsim_file(self):
        """
        Check an error occurs when pointed to directory without mcsim file
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            mcrun_obj = ManagedMcrun("test.instr",
                                     output_path="test_data_set",
                                     executable_path=executable_path,
                                     mcrun_path="path")

            load_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with self.assertRaises(NameError):
            mcrun_obj.load_results(load_path)


class Test_load_functions(unittest.TestCase):
    """
    Testing the load functions in managed_mcrun.
    load_results loads all data in folder
    load_metadata loads all metadata in folder
    load_monitor loads one monitor given metadata and folder
    These are used in ManagedMcrun
    """
    def test_mcrun_load_data_PSD4PI(self):
        """
        Use test_data_set to test load_data for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = load_results("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(results), 4)

        PSD_4PI = results[0]

        self.assertEqual(PSD_4PI.name, "PSD_4PI")
        self.assertEqual(PSD_4PI.metadata.dimension, [300, 300])
        self.assertEqual(PSD_4PI.metadata.limits, [-180, 180, -90, 90])
        self.assertEqual(PSD_4PI.metadata.xlabel, "Longitude [deg]")
        self.assertEqual(PSD_4PI.metadata.ylabel, "Latitude [deg]")
        self.assertEqual(PSD_4PI.metadata.title, "4PI PSD monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(PSD_4PI.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(PSD_4PI.metadata.parameters, expected_parameters)
        self.assertEqual(PSD_4PI.Ncount[4][1], 4)
        self.assertEqual(PSD_4PI.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(PSD_4PI.Error[4][1], 1.139482296E-10)

    def test_mcrun_load_data_PSD(self):
        """
        Use test_data_set to test load_data for PSD
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        results = load_results("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(results), 4)

        PSD = results[1]

        self.assertEqual(PSD.name, "PSD")
        self.assertEqual(PSD.metadata.dimension, [200, 200])
        self.assertEqual(PSD.metadata.limits, [-5, 5, -5, 5])
        self.assertEqual(PSD.metadata.xlabel, "X position [cm]")
        self.assertEqual(PSD.metadata.ylabel, "Y position [cm]")
        self.assertEqual(PSD.metadata.title, "PSD monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(PSD.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(PSD.metadata.parameters, expected_parameters)
        self.assertEqual(PSD.Ncount[27][21], 9)
        self.assertEqual(PSD.Intensity[27][21], 2.623929371e-13)
        self.assertEqual(PSD.Error[27][21], 2.765467693e-13)

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
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(PSD_4PI.info["Parameters"], expected_parameters)
        self.assertEqual(PSD_4PI.parameters, expected_parameters)

    def test_mcrun_load_metadata_L_mon(self):
        """
        Use test_data_set to test load_metadata for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        metadata = load_metadata("test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(len(metadata), 4)

        L_mon = metadata[2]
        self.assertEqual(L_mon.dimension, 150)
        self.assertEqual(L_mon.limits, [0.7, 1.3])
        self.assertEqual(L_mon.xlabel, "Wavelength [AA]")
        self.assertEqual(L_mon.ylabel, "Intensity")
        self.assertEqual(L_mon.title, "Wavelength monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(L_mon.info["Parameters"], expected_parameters)
        self.assertEqual(L_mon.parameters, expected_parameters)

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
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(monitor.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(monitor.metadata.parameters, expected_parameters)
        self.assertEqual(monitor.Ncount[4][1], 4)
        self.assertEqual(monitor.Intensity[4][1], 1.537334562E-10)
        self.assertEqual(monitor.Error[4][1], 1.139482296E-10)

    def test_mcrun_load_monitor_L_mon(self):
        """
        Use test_data_set to test load_monitor for PSD_4PI
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        metadata = load_metadata("test_data_set")
        L_mon = metadata[2]
        monitor = load_monitor(L_mon, "test_data_set")

        os.chdir(current_work_dir)  # Reset work directory

        self.assertEqual(monitor.name, "L_mon")
        self.assertEqual(monitor.metadata.dimension, 150)
        self.assertEqual(monitor.metadata.limits, [0.7, 1.3])
        self.assertEqual(monitor.metadata.xlabel, "Wavelength [AA]")
        self.assertEqual(monitor.metadata.ylabel, "Intensity")
        self.assertEqual(monitor.metadata.title, "Wavelength monitor")
        expected_parameters = {"wavelength": 1.0}
        self.assertEqual(monitor.metadata.info["Parameters"], expected_parameters)
        self.assertEqual(monitor.metadata.parameters, expected_parameters)
        self.assertEqual(monitor.xaxis[53], 0.914)
        self.assertEqual(monitor.Ncount[53], 37111)
        self.assertEqual(monitor.Intensity[53], 6.990299315e-06)
        self.assertEqual(monitor.Error[53], 6.215308587e-08)

if __name__ == '__main__':
    unittest.main()
