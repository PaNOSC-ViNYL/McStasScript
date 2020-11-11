import io
import os
import unittest
import unittest.mock

from mcstasscript.interface import instr, functions, plotter


def setup_simple_instrument():
    Instr = instr.McStas_instr("integration_test_simple")

    source = Instr.add_component("source", "Source_div")

    source.xwidth = 0.03
    source.yheight = 0.01
    source.focus_aw = 0.01
    source.focus_ah = 0.01
    source.E0 = 81.81
    source.dE = 1.0
    source.flux = 1E10

    PSD = Instr.add_component("PSD_1D", "PSDlin_monitor")

    PSD.set_AT([0, 0, 1], RELATIVE="source")
    PSD.xwidth = 0.1
    PSD.nx = 100
    PSD.yheight = 0.03
    PSD.filename = "\"PSD.dat\""
    PSD.restore_neutron = 1

    return Instr

def setup_simple_instrument_input_path():
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(THIS_DIR, "test_input_folder")

    Instr = instr.McStas_instr("integration_test_simple_input",
                               input_path=input_path)

    source = Instr.add_component("source", "Source_div")

    source.xwidth = 0.03
    source.yheight = 0.01
    source.focus_aw = 0.01
    source.focus_ah = 0.01
    source.E0 = 81.81
    source.dE = 1.0
    source.flux = 1E10

    PSD = Instr.add_component("PSD_1D", "PSDlin_monitor")

    PSD.set_AT([0, 0, 1], RELATIVE="source")
    PSD.xwidth = 0.1
    PSD.nx = 100
    PSD.yheight = 0.03
    PSD.filename = "\"PSD.dat\""
    PSD.restore_neutron = 1

    return Instr


def setup_simple_slit_instrument():
    Instr = instr.McStas_instr("integration_test_simple")

    source = Instr.add_component("source", "Source_div")
    source.xwidth = 0.1
    source.yheight = 0.01
    source.focus_aw = 0.01
    source.focus_ah = 0.01
    source.E0 = 81.81
    source.dE = 1.0
    source.flux = 1E10

    Instr.add_parameter("slit_offset", value=0)

    Slit = Instr.add_component("slit", "Slit")
    Slit.set_AT(["slit_offset", 0, 0.5], RELATIVE="source")
    Slit.xwidth = 0.01
    Slit.yheight = 0.03

    PSD = Instr.add_component("PSD_1D", "PSDlin_monitor")
    PSD.set_AT([0, 0, 1], RELATIVE="source")
    PSD.xwidth = 0.1
    PSD.nx = 100
    PSD.yheight = 0.03
    PSD.filename = "\"PSD.dat\""
    PSD.restore_neutron = 1

    return Instr


class TestSimpleInstrument(unittest.TestCase):
    """
    Integration test of a full instrument with McStas simulation
    performed by the system. The configuration file needs to be set up
    correctly in order for these tests to succeed.
    """

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_simple_instrument(self, mock_stdout):
        """
        Test that an instrument can run and that the results matches
        expectations. Here beam in small area in the middle of the
        detector.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_simple_instrument()

        data = Instr.run_full_instrument(foldername="integration_test_simple",
                                         ncount=1E6, mpi=1,
                                         increment_folder_name=True)

        os.chdir(CURRENT_DIR)

        intensity_data = data[0].Intensity
        # beam should be on pixel 35 to 65

        sum_outside_beam = (sum(intensity_data[0:34])
                            + sum(intensity_data[66:99]))
        sum_inside_beam = sum(intensity_data[35:65])

        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_simple_instrument_input(self, mock_stdout):
        """
        Test that an instrument can run and that the results matches
        expectations. Here beam in small area in the middle of the
        detector.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_simple_instrument_input_path()

        data = Instr.run_full_instrument(foldername="integration_test_simple_input",
                                         ncount=1E6, mpi=1,
                                         increment_folder_name=True)

        os.chdir(CURRENT_DIR)

        intensity_data = data[0].Intensity
        # beam should be on pixel 35 to 65

        sum_outside_beam = (sum(intensity_data[0:34])
                            + sum(intensity_data[66:99]))
        sum_inside_beam = sum(intensity_data[35:65])

        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

        # Check component from input_folder read
        self.assertEqual(data[0].metadata.xlabel, "Test")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_simple_instrument_mpi(self, mock_stdout):
        """
        Test that an instrument can run and that the results matches
        expectations. Here beam in small area in the middle of the
        detector. Running with mpi, 2 cores.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_simple_instrument()

        data = Instr.run_full_instrument(foldername="integration_test_mpi",
                                         ncount=1E6, mpi=2,
                                         increment_folder_name=True)

        os.chdir(CURRENT_DIR)

        intensity_data = data[0].Intensity
        # beam should be on pixel 35 to 65

        sum_outside_beam = (sum(intensity_data[0:34])
                            + sum(intensity_data[66:99]))
        sum_inside_beam = sum(intensity_data[35:65])

        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_slit_instrument(self, mock_stdout):
        """
        Test parameters can be controlled through McStasScript.  Here
        a slit is can be moved, but the default value of 0 should be
        used.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_simple_slit_instrument()

        data = Instr.run_full_instrument(foldername="integration_test_slit",
                                         ncount=2E6, mpi=2,
                                         increment_folder_name=True)

        os.chdir(CURRENT_DIR)

        intensity_data = data[0].Intensity
        # beam should be on pixel 45 to 55

        sum_outside_beam = (sum(intensity_data[0:44])
                            + sum(intensity_data[56:99]))
        sum_inside_beam = sum(intensity_data[45:55])
        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_slit_moved_instrument(self, mock_stdout):
        """
        Test parameters can be controlled through McStasScript.  Here
        a slit is moved to one side and the result is verified.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_simple_slit_instrument()

        data = Instr.run_full_instrument(foldername="integration_test_slit",
                                         ncount=2E6, mpi=2,
                                         increment_folder_name=True,
                                         parameters={"slit_offset": 0.03})

        os.chdir(CURRENT_DIR)

        intensity_data = data[0].Intensity
        # beam should be on pixel 75 to 85

        sum_outside_beam = (sum(intensity_data[0:74])
                            + sum(intensity_data[86:99]))
        sum_inside_beam = sum(intensity_data[75:85])

        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

if __name__ == '__main__':
    unittest.main()