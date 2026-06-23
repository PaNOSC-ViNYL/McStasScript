import os
import io
import unittest
import unittest.mock
import ipywidgets as widgets

import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg

from mcstasscript.jb_interface.simulation_interface import SimInterface
from mcstasscript.jb_interface.simulation_interface import ParameterWidget
from mcstasscript.jb_interface.widget_helpers import parameter_has_default
from mcstasscript.jb_interface.widget_helpers import get_parameter_default
from mcstasscript.interface.instr import McStas_instr
from mcstasscript.interface.instr import McXtrace_instr


def setup_instr_root_path_McStas():
    """
    Sets up a neutron instrument with root package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument", package_path="/")

    os.chdir(current_work_dir)

    return instrument

def setup_populated_instr_McStas():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_instr_root_path_McStas()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")

    return instr

def setup_instr_root_path_McXtrace():
    """
    Sets up a neutron instrument with root package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument", package_path="/")

    os.chdir(current_work_dir)

    return instrument

def setup_populated_instr_McXtrace():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_instr_root_path_McXtrace()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")

    return instr


class FakeChange:
    def __init__(self, new=None, old=None, name=None):
        self.new = new
        self.old = old
        self.name = name


class TestSimulationInterface(unittest.TestCase):
    """
    Tests of simulation interface
    """
    def test_initialization_McStas(self):
        """
        Checking that interface can initialize from instrument and retrieve the
        parameters that has a default value.
        """

        sim_interface = SimInterface(setup_populated_instr_McStas())
        self.assertEqual(sim_interface.parameters["has_default"], 37)

    def test_show_interface_McStas(self):
        """
        Ensure that show_interface runs without errors and returns widget
        """

        sim_interface = SimInterface(setup_populated_instr_McStas())
        widget = sim_interface.show_interface()

        self.assertIsInstance(widget, widgets.widgets.widget_box.VBox)

    def test_initialization_McXtrace(self):
        """
        Checking that interface can initialize from instrument and retrieve the
        parameters that has a default value.
        """

        sim_interface = SimInterface(setup_populated_instr_McXtrace())
        self.assertEqual(sim_interface.parameters["has_default"], 37)

    def test_show_interface_McXtrace(self):
        """
        Ensure that show_interface runs without errors and returns widget
        """

        sim_interface = SimInterface(setup_populated_instr_McXtrace())
        widget = sim_interface.show_interface()

        self.assertIsInstance(widget, widgets.widgets.widget_box.VBox)

    def test_update_ncount(self):
        """
        Check ncount can be set correctly
        """
        sim_interface = SimInterface(setup_populated_instr_McStas())
        sim_interface.show_interface()

        fake_change = FakeChange(new=100)
        sim_interface.update_ncount(fake_change)
        self.assertEqual(sim_interface.ncount, 100)

    def test_update_mpi(self):
        """
        Check mpi can be set correctly
        """
        sim_interface = SimInterface(setup_populated_instr_McStas())
        sim_interface.show_interface()

        fake_change = FakeChange(new=3)
        sim_interface.update_mpi(fake_change)
        self.assertEqual(sim_interface.mpi, 3)

        # Check input that wouldn't work is ignored
        fake_change = FakeChange(new="wrong input")
        sim_interface.update_mpi(fake_change)
        self.assertEqual(sim_interface.mpi, 3)

    def test_ParameterWidget(self):
        """
        Test that ParameterWidgets are initialized correctly

        This code is part of the initialization for the simulation interface,
        yet it is useful to have as its own test as if it fails its clear where
        the overall problem is.
        """

        instrument = setup_populated_instr_McStas()

        instrument.add_parameter("string", "choice", options=["A", "B", "Long"])

        parameters = {}
        # get default parameters from instrument
        for parameter in instrument.parameters:
            if parameter_has_default(parameter):
                parameters[parameter.name] = get_parameter_default(parameter)

        parameter_widgets = []
        parameterwidget_objects = []
        for parameter in instrument.parameters:
            par_widget = ParameterWidget(parameter, parameters)
            parameterwidget_objects.append(par_widget)
            parameter_widgets.append(par_widget.make_widget())

        self.assertEqual(parameterwidget_objects[0].name, "theta")
        self.assertEqual(parameterwidget_objects[0].default_value, None)
        # Parameter does not exist in parameter dict yet
        with self.assertRaises(KeyError):
            parameters[parameterwidget_objects[0].name]

        change = FakeChange(new=222)
        parameterwidget_objects[0].update(change)
        self.assertEqual(parameters[parameterwidget_objects[0].name], 222)

        self.assertEqual(parameterwidget_objects[1].name, "has_default")
        self.assertEqual(parameterwidget_objects[1].default_value, 37)
        self.assertEqual(parameters[parameterwidget_objects[1].name], 37)

        change = FakeChange(new=227)
        parameterwidget_objects[1].update(change)
        self.assertEqual(parameters[parameterwidget_objects[1].name], 227)

        self.assertEqual(parameterwidget_objects[2].name, "choice")
        self.assertEqual(parameterwidget_objects[2].default_value, None)
        with self.assertRaises(KeyError):
            parameters[parameterwidget_objects[2].name]

        change = FakeChange(new="test")
        parameterwidget_objects[2].update(change) # Should add necessary extra quotation marks
        self.assertEqual(parameters[parameterwidget_objects[2].name], "\"test\"")

