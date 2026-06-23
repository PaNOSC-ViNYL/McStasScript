import os
import os.path
import io
import unittest
import unittest.mock
import datetime

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.interface.instr import McXtrace_instr

from mcstasscript.tests.helpers_for_tests import WorkInTestDir

run_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.')

def setup_instr_no_path():
    """
    Sets up a neutron instrument without a package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument")

    os.chdir(current_work_dir)

    return instrument


def setup_x_ray_instr_no_path():
    """
    Sets up a X-ray instrument without a package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McXtrace_instr("test_instrument")

    os.chdir(current_work_dir)

    return instrument


def setup_instr_root_path():
    """
    Sets up a neutron instrument with root package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument", package_path="/")

    os.chdir(current_work_dir)

    return instrument


def setup_x_ray_instr_root_path():
    """
    Sets up a X-ray instrument with root package_path
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McXtrace_instr("test_instrument", package_path="/")

    os.chdir(current_work_dir)

    return instrument


def setup_instr_with_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument", package_path=dummy_path)

    os.chdir(current_work_dir)  # Return to previous workdir

    return instrument


def setup_x_ray_instr_with_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McXtrace_instr("test_instrument", package_path=dummy_path)

    os.chdir(current_work_dir)  # Return to previous workdir

    return instrument


def setup_instr_with_input_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder. In addition the input_path
    is set to a folder in the test directory using an absolute path.
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
    input_path = os.path.join(THIS_DIR, "test_input_folder")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument",
                              package_path=dummy_path,
                              input_path=input_path)

    os.chdir(current_work_dir)  # Return to previous workdir

    return instrument


def setup_instr_with_input_path_relative():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder. In addition the input_path
    is set to a folder in the test directory using a relative path.
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    instrument = McStas_instr("test_instrument",
                              package_path="dummy_mcstas",
                              input_path="test_input_folder")

    os.chdir(current_work_dir)  # Return to previous workdir

    return instrument


def setup_populated_instr():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_instr_root_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")

    return instr


def setup_populated_instr_with_dummy_path():
    """
    Sets up a neutron instrument with some features used and three components

    Here uses the dummy mcstas installation as path and sets required
    parameters so that a run is possible.
    """
    instr = setup_instr_with_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    comp1 = instr.add_component("first_component", "test_for_reading")
    comp1.gauss = 1.2
    comp1.test_string = "a_string"
    comp2 = instr.add_component("second_component", "test_for_reading")
    comp2.gauss = 1.4
    comp2.test_string = "b_string"
    comp3 = instr.add_component("third_component", "test_for_reading")
    comp3.gauss = 1.6
    comp3.test_string = "c_string"

    return instr


def setup_populated_x_ray_instr():
    """
    Sets up a X-ray instrument with some features used and three components
    """
    instr = setup_x_ray_instr_root_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")

    return instr


def setup_populated_x_ray_instr_with_dummy_path():
    """
    Sets up a x-ray instrument with some features used and three components

    Here uses the dummy mcstas installation as path and sets required
    parameters so that a run is possible.
    """
    instr = setup_x_ray_instr_with_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    comp1 = instr.add_component("first_component", "test_for_reading")
    comp1.gauss = 1.2
    comp1.test_string = "a_string"
    comp2 = instr.add_component("second_component", "test_for_reading")
    comp2.gauss = 1.4
    comp2.test_string = "b_string"
    comp3 = instr.add_component("third_component", "test_for_reading")
    comp3.gauss = 1.6
    comp3.test_string = "c_string"

    return instr


def setup_populated_with_some_options_instr():
    """
    Sets up a neutron instrument with some features used and two components
    """
    instr = setup_instr_root_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    comp1 = instr.add_component("first_component", "test_for_reading")
    comp1.set_AT([0, 0, 1])
    comp1.set_GROUP("Starters")
    comp2 = instr.add_component("second_component", "test_for_reading")
    comp2.set_AT([0, 0, 2], RELATIVE="first_component")
    comp2.set_ROTATED([0, 30, 0])
    comp2.set_WHEN("1==1")
    comp2.yheight = 1.23
    instr.add_component("third_component", "test_for_reading")

    return instr


class TestDumpAndLoad(unittest.TestCase):
    def test_dump_simple(self):
        """
        Test a simple instrument can be dumped using with environment
        """
        my_instrument = setup_populated_instr_with_dummy_path()

        with WorkInTestDir() as handler:
            dump_name = "test_McStasScript_dump.dmp"

            if os.path.isfile(dump_name):
                os.remove(dump_name)

            # Ensure dump file does not exist
            self.assertFalse(os.path.isfile(dump_name))

            # Write dump file
            my_instrument.dump(dump_name)

            # Check it was written
            self.assertTrue(os.path.isfile(dump_name))

            # Delete dump file
            os.remove(dump_name)

    def test_load_simple(self):
        """
        Test a simple instrument can be loaded from dump
        """
        my_instrument = setup_populated_instr_with_dummy_path()
        my_instrument.add_parameter("check", comment="for testing")

        with WorkInTestDir() as handler:
            dump_name = "test_McStasScript_dump.dmp"
            my_instrument.dump(dump_name)

            loaded_instrument = McStas_instr.from_dump(dump_name)
            os.remove(dump_name)

            self.assertTrue(loaded_instrument, McStas_instr)
            self.assertTrue(loaded_instrument.name, my_instrument.name)

            self.assertEqual(len(loaded_instrument.component_list), 3)
            self.assertEqual(loaded_instrument.component_list[0].name, "first_component")
            self.assertEqual(loaded_instrument.component_list[2].name, "third_component")
            self.assertEqual(loaded_instrument.parameters["check"].name, "check")
            self.assertEqual(loaded_instrument.parameters["check"].comment, "for testing")
            self.assertEqual(loaded_instrument.parameters["has_default"].value, 37)

