import io
import os
import time
import unittest
import unittest.mock
import matplotlib as plt

from mcstasscript.interface import instr, functions, plotter


def setup_complex_instrument():
    """
    Sets up guide system with two guides that are placed next to one
    another with separate entrances but converge at the end.

    It attempts to use as McStas keywords and features as possible.
    """
    Instr = instr.McStas_instr("integration_test_complex",
                               author="test_suite",
                               origin="integration tests")

    Instr.add_parameter("guide_width", value=0.03)
    Instr.add_parameter("guide_length", value=8.0)

    source = Instr.add_component("source", "Source_simple")
    source.xwidth = 0.1
    source.yheight = 0.01
    source.dist = 1.5
    source.focus_xw = "3*guide_width"
    source.focus_yh = 0.05
    source.E0 = 5.0
    source.dE = 1.0
    source.flux = 1E10

    Instr.add_declare_var("int", "guide_choice")
    Instr.add_declare_var("double", "source_to_guide_end")
    Instr.append_initialize("source_to_guide_end = 1.5 + guide_length;")

    after_guide = Instr.add_component("after_guide", "Arm",
                                      AT=[0, 0, "source_to_guide_end"],
                                      RELATIVE="source")
    after_guide.append_EXTEND("guide_choice = -1;")

    # Add first slit with component methods
    slit1 = Instr.add_component("slit1", "Slit")
    slit1.set_AT(["1.3*guide_width", 0, 1.5], RELATIVE="source")
    slit1.xwidth = "guide_width"
    slit1.yheight = 0.05
    slit1.append_EXTEND("if (SCATTERED) {")
    slit1.append_EXTEND("  guide_choice = 1;")
    slit1.append_EXTEND("}")
    slit1.set_GROUP("entrance_slits")

    # Add second slit with instr methods
    Instr.add_component("slit2", "Slit")
    Instr.set_component_AT("slit2", ["-1.3*guide_width", 0, 1.5])
    Instr.set_component_RELATIVE("slit2", "source")
    Instr.set_component_parameter("slit2", {"xwidth": "guide_width",
                                            "yheight": 0.05})
    Instr.append_component_EXTEND("slit2", "if (SCATTERED) {")
    Instr.append_component_EXTEND("slit2", "  guide_choice = 2;")
    Instr.append_component_EXTEND("slit2", "}")
    Instr.set_component_GROUP("slit2", "entrance_slits")

    select1 = Instr.add_component("select1", "Arm", RELATIVE="after_guide")
    select1.set_JUMP("select2 WHEN guide_choice == 2")

    guide1 = Instr.add_component("guide1", "Guide_gravity")
    guide1.set_AT([0, 0, 0.1], RELATIVE="slit1")
    guide1.set_ROTATED([0, "-RAD2DEG*atan(0.5*guide_width/guide_length)", 0],
                       RELATIVE="slit1")
    guide1.w1 = "guide_width"
    guide1.w2 = "1.3*guide_width"
    guide1.h1 = 0.05
    guide1.h2 = 0.05
    guide1.l = "guide_length"
    guide1.m = 4
    guide1.G = -9.82

    select2 = Instr.add_component("select2", "Arm", RELATIVE="after_guide")
    select2.set_JUMP("done WHEN guide_choice == 1")

    guide2 = Instr.add_component("guide2", "Guide_gravity")
    guide2.set_AT([0, 0, 0.1], RELATIVE="slit2")
    guide2.set_ROTATED([0, "RAD2DEG*atan(0.5*guide_width/guide_length)", 0],
                       RELATIVE="slit2")
    guide2.w1 = "guide_width"
    guide2.w2 = "1.3*guide_width"
    guide2.h1 = 0.05
    guide2.h2 = 0.05
    guide2.l = "guide_length"
    guide2.m = 4
    guide2.G = -9.82
    
    guide2.set_SPLIT = 2

    done = Instr.add_component("done", "Arm", RELATIVE="after_guide")

    PSD1 = Instr.add_component("PSD_1D_1", "PSDlin_monitor")
    PSD1.set_AT([0, 0, 0.2], RELATIVE="after_guide")
    PSD1.xwidth = 0.1
    PSD1.nx = 100
    PSD1.yheight = 0.03
    PSD1.filename = "\"PSD1.dat\""
    PSD1.restore_neutron = 1
    PSD1.set_WHEN("guide_choice == 1")

    PSD2 = Instr.add_component("PSD_1D_2", "PSDlin_monitor")
    PSD2.set_AT([0, 0, 0.2], RELATIVE="after_guide")
    PSD2.xwidth = 0.1
    PSD2.nx = 100
    PSD2.yheight = 0.03
    PSD2.filename = "\"PSD2.dat\""
    PSD2.restore_neutron = 1
    PSD2.set_WHEN("guide_choice == 2")

    PSD = Instr.add_component("PSD_1D", "PSDlin_monitor")
    PSD.set_AT([0, 0, 0.2], RELATIVE="after_guide")
    PSD.xwidth = 0.1
    PSD.nx = 100
    PSD.yheight = 0.03
    PSD.filename = "\"PSD_all.dat\""
    PSD.restore_neutron = 1

    Instr.append_finally("guide_choice = -1;")

    return Instr


class TestComplexInstrument(unittest.TestCase):
    """
    Integration test of a full instrument with McStas simulation
    performed by the system. The configuration file needs to be set up
    correctly in order for these tests to succeed.
    """
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_complex_instrument(self, mock_stdout):
        """
        Test parameters can be controlled through McStasScript.  Here
        a slit is moved to one side and the result is verified.
        """
        CURRENT_DIR = os.getcwd()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(THIS_DIR)

        Instr = setup_complex_instrument()

        data = Instr.run_full_instrument(foldername="integration_test_complex",
                                         ncount=2E6, mpi=2,
                                         increment_folder_name=True,
                                         parameters={"guide_width": 0.03,
                                                     "guide_length": 8.0})

        os.chdir(CURRENT_DIR)

        intensity_data_pos = functions.name_search("PSD_1D_1", data).Intensity
        sum_outside_beam = sum(intensity_data_pos[0:50])
        sum_inside_beam = sum(intensity_data_pos[51:99])
        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

        intensity_data_neg = functions.name_search("PSD_1D_2", data).Intensity
        sum_outside_beam = sum(intensity_data_neg[51:99])
        sum_inside_beam = sum(intensity_data_neg[0:50])
        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

        intensity_data_all = functions.name_search("PSD_1D", data).Intensity
        sum_outside_beam = sum(intensity_data_all[49:51])
        sum_inside_beam = (sum(intensity_data_all[0:45])
                           + sum(intensity_data_all[56:99]))
        self.assertTrue(1000*sum_outside_beam < sum_inside_beam)

        # Could have the plot window up for some short time
        # Need to use plt.draw instead of plt.show in plotter
        # plotter.make_sub_plot(data)
        # time.sleep(10)
        # plt.close()

if __name__ == '__main__':
    unittest.main()
