import unittest
import os
import mcstasscript as ms
from mcstasscript.tests.helpers_for_tests import WorkInTestDir

from mcstasscript.tools.instrument_checker import has_component


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
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_name="second_component"))

    def test_simple_case_name_not_found(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="fourth_component"))

    def test_simple_case_type(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_type="test_for_reading"))

    def test_simple_case_type_not_found(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_type="Arm"))

    def test_case_both(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertTrue(has_component(instr, component_name="first_component",
                                      component_type="test_for_reading"))

    def test_case_both_not_found_name(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="",
                                       component_type="test_for_reading"))

    def test_case_both_not_found_type(self):
        """
        check component of given name
        """
        instr = setup_populated_instr()
        self.assertFalse(has_component(instr, component_name="first_component",
                                       component_type="Arm"))