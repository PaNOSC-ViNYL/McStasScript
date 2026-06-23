import unittest
import os
import mcstasscript as ms
from mcstasscript.tests.helpers_for_tests import WorkInTestDir

from mcstasscript.tools.instrument_checker import has_component, has_parameter, all_parameters_set


def setup_instr_with_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder.
    """

    with WorkInTestDir() as handler:
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
        instrument = ms.McStas_instr("test_instrument",
                                     package_path=dummy_path,
                                     executable_path=dummy_path)

    return instrument


def setup_populated_instr():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_instr_with_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_parameter("int", "n_pulses")

    instr.add_declare_var("double", "two_theta")

    instr.append_initialize("two_theta = 2.0*theta;")

    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")

    return instr


class TestToolInstrumentChecker(unittest.TestCase):
    """
    Various test of instrument_checker functions
    """

    def test_simple_case_name(self):
        """
        check has_component of given name
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_name="second_component"))

    def test_simple_case_name_not_found(self):
        """
        check has_component returns false when name is not there
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="fourth_component"))

    def test_simple_case_type(self):
        """
        check has_component can find component of given type
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_type="test_for_reading"))

    def test_simple_case_type_not_found(self):
        """
        check has_component returns false when component type is not found
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_type="Arm"))

    def test_case_both(self):
        """
        check has_component when given both name and component type
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_name="first_component",
                                      component_type="test_for_reading"))

    def test_case_both_not_found_name(self):
        """
        check has_component returns false when name not found but type is
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="",
                                       component_type="test_for_reading"))

    def test_case_both_not_found_type(self):
        """
        check has_component returns false when type not found but name is
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="first_component",
                                       component_type="Arm"))

    def test_parameter_found(self):
        """
        check has_parameter of given name
        """
        instr = setup_populated_instr()
        self.assertTrue(has_parameter(instr, parameter_name="theta"))

    def test_parameter_not_found(self):
        """
        check has_parameter returns false when of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_parameter(instr, parameter_name="bogus"))

    def test_parameter_found_with_type(self):
        """
        check has_parameter of given name and type
        """
        instr = setup_populated_instr()
        self.assertTrue(has_parameter(instr, parameter_name="n_pulses", parameter_type="int"))

    def test_parameter_found_with_type_default(self):
        """
        check has_parameter of given name and type (using default double)
        """
        instr = setup_populated_instr()
        self.assertTrue(has_parameter(instr, parameter_name="theta", parameter_type="double"))

    def test_parameter_found_with_wrong_type(self):
        """
        check has_parameter of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_parameter(instr, parameter_name="theta", parameter_type="int"))

    def test_all_parameters_set_not_set(self):
        """
        check all_parameters_set returns false when not all parameters are set of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(all_parameters_set(instr))

    def test_all_parameters_set_actually_set(self):
        """
        check all_parameters_set returns false when all parameters are set of given name
        """
        instr = setup_populated_instr()

        instr.set_parameters(theta=37, n_pulses=3)
        self.assertTrue(all_parameters_set(instr))