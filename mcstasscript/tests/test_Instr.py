import os
import os.path
import io
import unittest
import unittest.mock
import datetime

from libpyvinyl.Parameters.Collections import CalculatorParameters

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.interface.instr import McXtrace_instr
from mcstasscript.helper.formatting import bcolors
from mcstasscript.tests.helpers_for_tests import WorkInTestDir
from mcstasscript.helper.exceptions import McStasError
from mcstasscript.helper.mcstas_objects import Component
from mcstasscript.helper.beam_dump_database import BeamDump

run_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.')

class DummyComponent(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_parameters(self, *args, **kwargs):
        pass

def setup_instr_no_path():
    """
    Sets up a neutron instrument without a package_path
    """

    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument")

    return instrument


def setup_x_ray_instr_no_path():
    """
    Sets up a X-ray instrument without a package_path
    """

    with WorkInTestDir() as handler:
        instrument = McXtrace_instr("test_instrument")

    return instrument


def setup_instr_root_path():
    """
    Sets up a neutron instrument with root package_path
    """
    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument", package_path="/")

    return instrument


def setup_x_ray_instr_root_path():
    """
    Sets up a X-ray instrument with root package_path
    """
    with WorkInTestDir() as handler:
        instrument = McXtrace_instr("test_instrument", package_path="/")

    return instrument


def setup_instr_with_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder.
    """

    with WorkInTestDir() as handler:
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
        instrument = McStas_instr("test_instrument",
                                  package_path=dummy_path, executable_path=dummy_path)

    return instrument


def setup_x_ray_instr_with_path():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

    with WorkInTestDir() as handler:
        instrument = McXtrace_instr("test_instrument", package_path=dummy_path)

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

    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument",
                                  package_path=dummy_path,
                                  input_path=input_path)

    return instrument


def setup_instr_with_input_path_relative():
    """
    Sets up an instrument with a valid package_path, but it points to
    the dummy installation in the test folder. In addition the input_path
    is set to a folder in the test directory using a relative path.
    """

    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument",
                                  package_path="dummy_mcstas",
                                  input_path="test_input_folder")

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


def setup_populated_instr_with_dummy_MCPL_comps():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_populated_instr()

    instr.component_class_lib["MCPL_input"] = DummyComponent
    instr.component_class_lib["MCPL_output"] = DummyComponent

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


def insert_mock_dump(instr, component_name, run_name="Run", tag=0):
    dump = BeamDump("", {}, component_name, run_name, tag=tag)
    dump.file_present = lambda *_: True  # Overwrite file check

    instr.dump_database.data[component_name] = {}
    instr.dump_database.data[component_name][run_name] = {}
    instr.dump_database.data[component_name][run_name][tag] = dump


class TestMcStas_instr(unittest.TestCase):
    """
    Tests of the main class in McStasScript called McStas_instr.
    """

    def test_simple_initialize(self):
        """
        Test basic initialization runs
        """
        my_instrument = setup_instr_root_path()

        self.assertEqual(my_instrument.name, "test_instrument")

    def test_complex_initialize(self):
        """
        Tests all keywords work in initialization
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        my_instrument = McStas_instr("test_instrument",
                                     author="Mads",
                                     origin="DMSC",
                                     executable_path="./dummy_mcstas/contrib",
                                     package_path="./dummy_mcstas/misc")

        os.chdir(current_work_dir)

        self.assertEqual(my_instrument.author, "Mads")
        self.assertEqual(my_instrument.origin, "DMSC")
        self.assertEqual(my_instrument._run_settings["executable_path"],
                         "./dummy_mcstas/contrib")
        self.assertEqual(my_instrument._run_settings["package_path"],
                         "./dummy_mcstas/misc")

    def test_load_config_file(self):
        """
        Test that configuration file is read correctly. In order to have
        an independent test, the yaml file is read manually instead of
        using the yaml package.
        """
        # Load configuration file and read manually
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(THIS_DIR,
                                               "..", "configuration.yaml")

        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")

        f = open(configuration_file_name, "r")

        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("mcrun_path:"):
                parts = line.split(" ")
                correct_mcrun_path = parts[1]

            if line.startswith("mcstas_path:"):
                parts = line.split(" ")
                correct_mcstas_path = parts[1]

            if line.startswith("characters_per_line:"):
                parts = line.split(" ")
                correct_n_of_characters = int(parts[1])

        f.close()

        # Check the value matches what is loaded by initialization
        my_instrument = setup_instr_no_path()

        self.assertEqual(my_instrument._run_settings["executable_path"], correct_mcrun_path)
        self.assertEqual(my_instrument._run_settings["package_path"], correct_mcstas_path)
        self.assertEqual(my_instrument.line_limit, correct_n_of_characters)

    def test_load_config_file_x_ray(self):
        """
        Test that configuration file is read correctly. In order to have
        an independent test, the yaml file is read manually instead of
        using the yaml package.
        """
        # Load configuration file and read manually
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(THIS_DIR,
                                               "..", "configuration.yaml")

        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")

        f = open(configuration_file_name, "r")

        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("mxrun_path:"):
                parts = line.split(" ")
                correct_mxrun_path = parts[1]

            if line.startswith("mcxtrace_path:"):
                parts = line.split(" ")
                correct_mcxtrace_path = parts[1]

            if line.startswith("characters_per_line:"):
                parts = line.split(" ")
                correct_n_of_characters = int(parts[1])

        f.close()

        # Check the value matches what is loaded by initialization
        my_instrument = setup_x_ray_instr_no_path()

        self.assertEqual(my_instrument._run_settings["executable_path"], correct_mxrun_path)
        self.assertEqual(my_instrument._run_settings["package_path"], correct_mcxtrace_path)
        self.assertEqual(my_instrument.line_limit, correct_n_of_characters)

    def test_load_libpyvinyl_parameters(self):
        parameters = CalculatorParameters()
        int_par = parameters.new_parameter("int_parameter", comment="integer parameter")
        int_par.value = 3

        double_par = parameters.new_parameter("double_parameter", unit="meV")
        double_par.value = 3.0

        string_par = parameters.new_parameter("string_parameter")
        string_par.value = "hello world"

        secret_par = parameters.new_parameter("no_value_par")

        instr = McStas_instr("test_instr", parameters=parameters)

        self.assertEqual(int_par.type, "double")
        self.assertEqual(double_par.type, "double")
        self.assertEqual(string_par.type, "string")
        self.assertEqual(secret_par.type, None)

        instr.set_parameters(int_parameter=4)
        self.assertEqual(int_par.value, 4)

        int_par.value = 5
        self.assertEqual(instr.parameters["int_parameter"].value, 5)

    def test_simple_add_parameter(self):
        """
        This is just an interface to a function that is tested
        elsewhere, so only a basic test is performed here.

        ParameterVariable is tested in test_parameter_variable.
        """
        instr = setup_instr_root_path()

        parameter = instr.add_parameter("double", "theta", comment="test par")

        self.assertEqual(parameter.name, "theta")
        self.assertEqual(parameter.comment, "test par")
        self.assertTrue(parameter in instr.parameters.parameters.values())

    def test_user_var_block_add_parameter(self):
        """
        Checks that adding a parameter with a name already used for a
        user variable fails with NameError
        """
        instr = setup_instr_root_path()

        instr.add_user_var("double", "theta")

        with self.assertRaises(NameError):
            instr.add_parameter("double", "theta", comment="test par")


    def test_declare_var_block_add_parameter(self):
        """
        Checks that adding a parameter with a name already used for a
        declared variable fails with NameError
        """
        instr = setup_instr_root_path()

        instr.add_declare_var("double", "theta")

        with self.assertRaises(NameError):
            instr.add_parameter("double", "theta", comment="test par")

    def test_infer_name_add_parameter(self):
        """
        Test that name can be ommited when defining a parameter and that
        the python variable name is used in its place.
        """
        instr = setup_instr_root_path()

        theta = instr.add_parameter(type="double", comment="test par")

        self.assertEqual(theta.name, "theta")
        self.assertEqual(theta.comment, "test par")
        self.assertTrue(theta in instr.parameters.parameters.values())

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_parameters(self, mock_stdout):
        """
        Testing that parameters are displayed correctly
        """
        instr = setup_instr_root_path()

        instr.add_parameter("theta", comment="test par")
        instr.add_parameter("double", "par_double", comment="test par")
        instr.add_parameter("int", "int_par", value=8, comment="test par")
        instr.add_parameter("int", "slits", comment="test par")
        instr.add_parameter("string", "ref",
                            value="string", comment="new string")

        instr.show_parameters(line_length=300)

        output = mock_stdout.getvalue().split("\n")

        self.assertEqual(output[0], "       theta                 // test par")
        self.assertEqual(output[1], "double par_double            // test par")
        self.assertEqual(output[2], "int    int_par     = 8       // test par")
        self.assertEqual(output[3], "int    slits                 // test par")
        self.assertEqual(output[4], "string ref         = string  // new string")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_parameters_line_break(self, mock_stdout):
        """
        Testing that parameters are displayed correctly

        Here multiple lines are used for a long comment that was
        dynamically broken up.
        """
        instr = setup_instr_root_path()

        instr.add_parameter("theta", comment="test par")
        instr.add_parameter("double", "par_double", comment="test par")
        instr.add_parameter("int", "int_par", value=8, comment="test par")
        instr.add_parameter("int", "slits", comment="test par")
        instr.add_parameter("string", "ref",
                            value="string", comment="new string")

        longest_comment = ("This is a very long comment meant for "
                           + "testing the dynamic line breaking "
                           + "that is used in this method. It needs "
                           + "to have many lines in order to ensure "
                           + "it really works.")

        instr.add_parameter("double", "value",
                            value="37", comment=longest_comment)

        instr.show_parameters(line_length=80)

        output = mock_stdout.getvalue().split("\n")

        self.assertEqual(output[0], "       theta                 // test par")
        self.assertEqual(output[1], "double par_double            // test par")
        self.assertEqual(output[2], "int    int_par     = 8       // test par")
        self.assertEqual(output[3], "int    slits                 // test par")
        self.assertEqual(output[4], "string ref         = string  // new string")
        comment_line = "This is a very long comment meant for "
        self.assertEqual(output[5], "double value       = 37      // "
                                    + comment_line)
        comment_line = "testing the dynamic line breaking that is "
        self.assertEqual(output[6], " "*33 + comment_line)
        comment_line = "used in this method. It needs to have many "
        self.assertEqual(output[7], " "*33 + comment_line)
        comment_line = "lines in order to ensure it really works. "
        self.assertEqual(output[8], " "*33 + comment_line)

    def test_simple_add_declare_variable(self):
        """
        This is just an interface to a function that is tested
        elsewhere, so only a basic test is performed here.

        DeclareVariable is tested in test_declare_variable.
        """
        instr = setup_instr_root_path()

        instr.add_declare_var("double", "two_theta", comment="test par")

        self.assertEqual(instr.declare_list[0].name, "two_theta")
        self.assertEqual(instr.declare_list[0].comment, " // test par")

    def test_parameter_block_add_declare_variable(self):
        """
        Checks a NameError is raised when using declare variable of same
        name as instrument parameter.
        """
        instr = setup_instr_root_path()

        instr.add_parameter("two_theta")
        with self.assertRaises(NameError):
            instr.add_declare_var("double", "two_theta")

    def test_user_var_block_add_declare_variable(self):
        """
        Checks a NameError is raised when using declare variable of same
        name as declared variable.
        """
        instr = setup_instr_root_path()

        instr.add_user_var("double", "two_theta")
        with self.assertRaises(NameError):
            instr.add_declare_var("double", "two_theta")

    def test_infer_add_declare_variable(self):
        """
        Check that name can be inferred from python variable when
        adding a declared variable.
        """
        instr = setup_instr_root_path()

        two_theta = instr.add_declare_var("double", comment="test par")

        self.assertEqual(instr.declare_list[0].name, "two_theta")
        self.assertEqual(instr.declare_list[0].comment, " // test par")

    def test_simple_add_user_variable(self):
        """
        This is just an interface to a function that is tested
        elsewhere, so only a basic test is performed here.

        DeclareVariable is tested in test_declare_variable.
        """
        instr = setup_instr_root_path()

        user_var = instr.add_user_var("double", "two_theta_user", comment="test par")

        self.assertEqual(user_var.name, "two_theta_user")
        self.assertEqual(user_var.comment, " // test par")
        self.assertEqual(instr.user_var_list[0].name, "two_theta_user")
        self.assertEqual(instr.user_var_list[0].comment, " // test par")

        with self.assertRaises(ValueError):
            instr.add_user_var("double", "illegal", value=8)

    def test_declare_block_add_user_variable(self):
        """
        Checks a NameError is raised when using user variable of same
        name as declare variable already defined.
        """
        instr = setup_instr_root_path()

        instr.add_declare_var("double", "two_theta")
        with self.assertRaises(NameError):
            instr.add_user_var("double", "two_theta")

    def test_parameter_block_add_user_variable(self):
        """
        Checks a NameError is raised when using user variable of same
        name as parameter already defined.
        """
        instr = setup_instr_root_path()

        instr.add_parameter("two_theta")
        with self.assertRaises(NameError):
            instr.add_user_var("double", "two_theta")

    def test_simple_append_declare(self):
        """
        Appending to declare adds an object to the declare list, and the
        allowed types are either strings or DeclareVariable objects.
        Here only strings are added.
        """
        instr = setup_instr_root_path()

        instr.append_declare("First line of declare")
        instr.append_declare("Second line of declare")
        instr.append_declare("Third line of declare")

        self.assertEqual(instr.declare_list[0],
                         "First line of declare")
        self.assertEqual(instr.declare_list[1],
                         "Second line of declare")
        self.assertEqual(instr.declare_list[2],
                         "Third line of declare")

    def test_simple_append_declare_var_mix(self):
        """
        Appending to declare adds an object to the declare list, and the
        allowed types are either strings or DeclareVariable objects.
        Here a mix of strings and DeclareVariable objects are added.
        """
        instr = setup_instr_root_path()

        instr.append_declare("First line of declare")
        instr.add_declare_var("double", "two_theta", comment="test par")
        instr.append_declare("Third line of declare")

        self.assertEqual(instr.declare_list[0],
                         "First line of declare")
        self.assertEqual(instr.declare_list[1].name, "two_theta")
        self.assertEqual(instr.declare_list[1].comment, " // test par")
        self.assertEqual(instr.declare_list[2],
                         "Third line of declare")

    def test_simple_append_initialize(self):
        """
        The initialize section is held as a string. This method
        appends that string.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.initialize_section,
                         "// Start of initialize for generated "
                         + "test_instrument\n")

        instr.append_initialize("First line of initialize")
        instr.append_initialize("Second line of initialize")
        instr.append_initialize("Third line of initialize")

        self.assertEqual(instr.initialize_section,
                         "// Start of initialize for generated "
                         + "test_instrument\n"
                         + "First line of initialize\n"
                         + "Second line of initialize\n"
                         + "Third line of initialize\n")

    def test_simple_append_initialize_no_new_line(self):
        """
        The initialize section is held as a string. This method
        appends that string without making a new line.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.initialize_section,
                         "// Start of initialize for generated "
                         + "test_instrument\n")

        instr.append_initialize_no_new_line("A")
        instr.append_initialize_no_new_line("B")
        instr.append_initialize_no_new_line("CD")

        self.assertEqual(instr.initialize_section,
                         "// Start of initialize for generated "
                         + "test_instrument\n"
                         + "ABCD")

    def test_simple_append_finally(self):
        """
        The finally section is held as a string. This method
        appends that string.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.finally_section,
                         "// Start of finally for generated "
                         + "test_instrument\n")

        instr.append_finally("First line of finally")
        instr.append_finally("Second line of finally")
        instr.append_finally("Third line of finally")

        self.assertEqual(instr.finally_section,
                         "// Start of finally for generated "
                         + "test_instrument\n"
                         + "First line of finally\n"
                         + "Second line of finally\n"
                         + "Third line of finally\n")

    def test_simple_append_finally_no_new_line(self):
        """
        The finally section is held as a string. This method
        appends that string without making a new line.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.finally_section,
                         "// Start of finally for generated "
                         + "test_instrument\n")

        instr.append_finally_no_new_line("A")
        instr.append_finally_no_new_line("B")
        instr.append_finally_no_new_line("CD")

        self.assertEqual(instr.finally_section,
                         "// Start of finally for generated "
                         + "test_instrument\n"
                         + "ABCD")

    def test_simple_append_trace(self):
        """
        The trace section is held as a string. This method
        appends that string. Only used for writing c files, which is not
        the main way to use McStasScript.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.trace_section,
                         "// Start of trace section for generated "
                         + "test_instrument\n")

        instr.append_trace("First line of trace")
        instr.append_trace("Second line of trace")
        instr.append_trace("Third line of trace")

        self.assertEqual(instr.trace_section,
                         "// Start of trace section for generated "
                         + "test_instrument\n"
                         + "First line of trace\n"
                         + "Second line of trace\n"
                         + "Third line of trace\n")

    def test_simple_append_trace_no_new_line(self):
        """
        The trace section is held as a string. This method appends that string
        without making a new line. Only used for writing c files, which is not
        the main way to use McStasScript.
        """
        instr = setup_instr_root_path()

        self.assertEqual(instr.trace_section,
                         "// Start of trace section for generated "
                         + "test_instrument\n")

        instr.append_trace_no_new_line("A")
        instr.append_trace_no_new_line("B")
        instr.append_trace_no_new_line("CD")

        self.assertEqual(instr.trace_section,
                         "// Start of trace section for generated "
                         + "test_instrument\n"
                         + "ABCD")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_available_components_simple(self, mock_stdout):
        """
        Simple test of show components to show component categories
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        instr = setup_instr_with_path()

        instr.available_components()

        os.chdir(current_work_dir)

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work directory / input_path:")
        self.assertEqual(output[1], "     test_for_reading.comp")
        self.assertEqual(output[2], "These definitions will be used "
                         + "instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " misc")
        self.assertEqual(output[5], " sources")
        self.assertEqual(output[6], " work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_available_components_folder(self, mock_stdout):
        """
        Simple test of show components to show components in current work
        directory.
        """
        instr = setup_instr_with_path()

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        instr.available_components("work directory")

        os.chdir(current_work_dir)

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work directory / input_path:")
        self.assertEqual(output[1], "     test_for_reading.comp")
        self.assertEqual(output[2], "These definitions will be used "
                         + "instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are all components in the work directory "
                         + "category.")
        self.assertEqual(output[4], " test_for_reading")
        self.assertEqual(output[5], "")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_available_components_input_path_simple(self, mock_stdout):
        """
        Simple test of input_path being recognized and passed
        to component_reader so PSDlin_monitor is overwritten
        """
        instr = setup_instr_with_input_path()

        instr.available_components()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work directory / input_path:")
        self.assertEqual(output[1], "     test_for_structure.comp")
        self.assertEqual(output[2], "These definitions will be used "
                         + "instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " misc")
        self.assertEqual(output[5], " sources")
        self.assertEqual(output[6], " work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_available_components_input_path_custom(self, mock_stdout):
        """
        Simple test of input_path being recognized and passed
        to component_reader so PSDlin_monitor is overwritten
        Here dummy_mcstas and input_path are set using relative
        paths instead of absolute paths.
        """
        instr = setup_instr_with_input_path_relative()

        instr.available_components()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work directory / input_path:")
        self.assertEqual(output[1], "     test_for_structure.comp")
        self.assertEqual(output[2], "These definitions will be used "
                         + "instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " misc")
        self.assertEqual(output[5], " sources")
        self.assertEqual(output[6], " work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_component_help(self, mock_stdout):
        """
        Simple test of component help
        """
        instr = setup_instr_with_path()

        instr.component_help("test_for_reading", line_length=90)
        # This call creates a dummy component and calls its
        # show_parameter method which has been tested. Here we
        # need to ensure the call is successful, not test all
        # output from the call.

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[3], " ___ Help test_for_reading " + "_"*63)

        legend = ("|"
                  + bcolors.BOLD + "optional parameter" + bcolors.ENDC
                  + "|"
                  + bcolors.BOLD + bcolors.UNDERLINE
                  + "required parameter"
                  + bcolors.ENDC + bcolors.ENDC
                  + "|"
                  + bcolors.BOLD + bcolors.OKBLUE
                  + "default value"
                  + bcolors.ENDC + bcolors.ENDC
                  + "|"
                  + bcolors.BOLD + bcolors.OKGREEN
                  + "user specified value"
                  + bcolors.ENDC + bcolors.ENDC
                  + "|")

        self.assertEqual(output[4], legend)

        par_name = bcolors.BOLD + "radius" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKBLUE
                 + "0.1" + bcolors.ENDC + bcolors.ENDC)
        comment = ("// Radius of circle in (x,y,0) plane where "
                   + "neutrons are generated.")
        self.assertEqual(output[5],
                         par_name + " = " + value + " [m] " + comment)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_create_component_instance_simple(self, mock_stdout):
        """
        Tests successful use of _create_component_instance

        _create_component_instance will make a dynamic subclass of
        component with the information from the component files read
        from disk.  The subclass is saved in a dict for reuse in
        case the same component type is requested again.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        instr = setup_instr_with_path()

        os.chdir(current_work_dir)

        comp = instr._create_component_instance("test_component",
                                                "test_for_reading")

        self.assertEqual(comp.radius, None)
        self.assertIn("radius", comp.parameter_names)
        self.assertEqual(comp.parameter_defaults["radius"], 0.1)
        self.assertEqual(comp.parameter_types["radius"], "double")
        self.assertEqual(comp.parameter_units["radius"], "m")

        comment = ("Radius of circle in (x,y,0) plane where "
                   + "neutrons are generated.")
        self.assertEqual(comp.parameter_comments["radius"], comment)
        self.assertEqual(comp.category, "work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_create_component_instance_complex(self, mock_stdout):
        """
        Tests successful use of _create_component_instance while using
        keyword arguments in creation

        _create_component_instance will make a dynamic subclass of
        component with the information from the component files read
        from disk.  The subclasses is saved in a dict for reuse in
        case the same component type is requested again.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        instr = setup_instr_with_path()

        os.chdir(current_work_dir)

        # Setting relative to home, should be passed to component
        comp = instr._create_component_instance("test_component",
                                                "test_for_reading",
                                                RELATIVE="home")

        self.assertEqual(comp.radius, None)
        self.assertIn("radius", comp.parameter_names)
        self.assertEqual(comp.parameter_defaults["radius"], 0.1)
        self.assertEqual(comp.parameter_types["radius"], "double")
        self.assertEqual(comp.parameter_units["radius"], "m")

        comment = ("Radius of circle in (x,y,0) plane where "
                   + "neutrons are generated.")
        self.assertEqual(comp.parameter_comments["radius"], comment)
        self.assertEqual(comp.category, "work directory")

        # The keyword arguments of the call should be passed to the
        # new instance of the component. This is checked by reading
        # the relative attributes which were set to home in the call
        self.assertEqual(comp.AT_relative, "RELATIVE home")
        self.assertEqual(comp.ROTATED_relative, "RELATIVE home")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple(self, mock_stdout):
        """
        Testing add_component in simple case.

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location.
        """

        instr = setup_instr_with_path()

        comp = instr.add_component("test_component", "test_for_reading")

        self.assertEqual(len(instr.component_list), 1)
        self.assertEqual(instr.component_list[0].name, "test_component")

        # Test the resulting object functions as intended
        comp.set_GROUP("developers")
        self.assertEqual(instr.component_list[0].GROUP, "developers")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_infer_name(self, mock_stdout):
        """
        Testing add_component works when name is left out and inferred
        from the name of the python variable in the call.
        """

        instr = setup_instr_with_path()

        test_component = instr.add_component("test_for_reading")

        self.assertEqual(len(instr.component_list), 1)
        self.assertEqual(instr.component_list[0].name, "test_component")

        # Test the resulting object functions as intended
        test_component.set_GROUP("developers")
        self.assertEqual(instr.component_list[0].GROUP, "developers")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_keyword(self, mock_stdout):
        """
        Testing add_component with keyword argument for the component

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_instr_with_path()

        instr.add_component("test_component",
                            "test_for_reading",
                            WHEN="1<2")

        self.assertEqual(len(instr.component_list), 1)
        self.assertEqual(instr.component_list[0].name, "test_component")
        self.assertEqual(instr.component_list[0].component_name,
                         "test_for_reading")

        self.assertEqual(instr.component_list[0].WHEN, "WHEN (1<2)")

    def test_add_component_simple_before(self):
        """
        Testing add_component with before keyword argument for the method

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location, here before is tested.
        """

        instr = setup_populated_instr()

        instr.add_component("test_component",
                            "test_for_reading",
                            before="first_component")

        self.assertEqual(len(instr.component_list), 4)
        self.assertEqual(instr.component_list[0].name, "test_component")
        self.assertEqual(instr.component_list[3].name, "third_component")

    def test_add_component_simple_after(self):
        """
        Testing add_component with after keyword argument for the method

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location, here after is tested.
        """

        instr = setup_populated_instr()

        instr.add_component("test_component",
                            "test_for_reading",
                            after="first_component")

        self.assertEqual(len(instr.component_list), 4)
        self.assertEqual(instr.component_list[1].name, "test_component")
        self.assertEqual(instr.component_list[3].name, "third_component")

    def test_add_component_simple_after_error(self):
        """
        Checks add_component raises a NameError if after keyword specifies a
        non-existent component

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location, here before is tested.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.add_component("test_component",
                                "test_for_reading",
                                after="non_existent_component")

    def test_add_component_simple_before_error(self):
        """
        Checks add_component raises a NameError if before keyword specifies a
        non-existent component

        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location, here after is tested.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.add_component("test_component",
                                "test_for_reading",
                                before="non_existent_component")

    def test_add_component_simple_double_naming_error(self):
        """
        This tests checks that an error occurs when giving a new
        component a name which has already been used.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.add_component("first_component", "test_for_reading")

    def test_copy_component_simple(self):
        """
        Checks that a component can be copied using the name
        """

        instr = setup_populated_with_some_options_instr()

        comp = instr.copy_component("copy_of_second_comp", "second_component")

        self.assertEqual(comp.name, "copy_of_second_comp")
        self.assertEqual(comp.yheight, 1.23)
        self.assertEqual(comp.AT_data[0], 0)
        self.assertEqual(comp.AT_data[1], 0)
        self.assertEqual(comp.AT_data[2], 2)

    def test_infer_copy_component_simple(self):
        """
        Checks that a component can be copied using the name
        while giving the new instance name as the python variable
        """

        instr = setup_populated_with_some_options_instr()

        copy_of_second_comp = instr.copy_component("second_component")

        self.assertEqual(copy_of_second_comp.name, "copy_of_second_comp")
        self.assertEqual(copy_of_second_comp.yheight, 1.23)
        self.assertEqual(copy_of_second_comp.AT_data[0], 0)
        self.assertEqual(copy_of_second_comp.AT_data[1], 0)
        self.assertEqual(copy_of_second_comp.AT_data[2], 2)

    def test_copy_component_simple_fail(self):
        """
        Checks a NameError is raised if trying to copy a component that does
        not exist
        """

        instr = setup_populated_with_some_options_instr()

        with self.assertRaises(NameError):
            instr.copy_component("copy_of_second_comp", "unknown_component")

    def test_copy_component_simple_object(self):
        """
        Checks that a component can be copied using the object
        """

        instr = setup_populated_with_some_options_instr()

        comp = instr.get_component("second_component")

        comp = instr.copy_component("copy_of_second_comp", comp)

        self.assertEqual(comp.name, "copy_of_second_comp")
        self.assertEqual(comp.yheight, 1.23)
        self.assertEqual(comp.AT_data[0], 0)
        self.assertEqual(comp.AT_data[1], 0)
        self.assertEqual(comp.AT_data[2], 2)

    def test_copy_component_keywords(self):
        """
        Checks that a component can be copied and that keyword
        arguments given under copy operation is successfully
        applied to the new component. A check is also made to
        ensure that the original component was not modified.
        """

        instr = setup_populated_with_some_options_instr()

        comp = instr.copy_component("copy_of_second_comp", "second_component",
                                    AT=[1, 2, 3], SPLIT=10)

        self.assertEqual(comp.name, "copy_of_second_comp")
        self.assertEqual(comp.yheight, 1.23)
        self.assertEqual(comp.AT_data[0], 1)
        self.assertEqual(comp.AT_data[1], 2)
        self.assertEqual(comp.AT_data[2], 3)
        self.assertEqual(comp.SPLIT, 10)

        # ensure original component was not changed
        original = instr.get_component("second_component")
        self.assertEqual(original.name, "second_component")
        self.assertEqual(original.yheight, 1.23)
        self.assertEqual(original.AT_data[0], 0)
        self.assertEqual(original.AT_data[1], 0)
        self.assertEqual(original.AT_data[2], 2)
        self.assertEqual(original.SPLIT, 0)

    def test_remove_component(self):
        """
        Ensure a component can be removed
        """
        instr = setup_populated_instr()

        instr.remove_component("second_component")

        self.assertEqual(len(instr.component_list), 2)
        self.assertEqual(instr.component_list[0].name, "first_component")
        self.assertEqual(instr.component_list[1].name, "third_component")

    def test_move_component(self):
        """
        Ensure a component can be moved
        """
        instr = setup_populated_instr()

        instr.move_component("second_component", before="first_component")

        self.assertEqual(len(instr.component_list), 3)
        self.assertEqual(instr.component_list[0].name, "second_component")
        self.assertEqual(instr.component_list[1].name, "first_component")
        self.assertEqual(instr.component_list[2].name, "third_component")

    def test_RELATIVE_error(self):
        """
        Ensure check_for_errors finds impossible relative statement
        """

        instr = setup_populated_instr()

        second_component = instr.get_component("second_component")
        second_component.set_AT([0, 0, 0], RELATIVE="third_component")

        self.assertTrue(instr.has_errors())

        with self.assertRaises(McStasError):
            instr.check_for_errors()

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_RELATIVE_error_and_checks_false(self, mock_f):
        """
        Ensure check_for_errors finds impossible relative statement
        """

        instr = setup_populated_instr()

        second_component = instr.get_component("second_component")
        second_component.set_AT([0, 0, 0], RELATIVE="third_component")

        self.assertTrue(instr.has_errors())

        with self.assertRaises(McStasError):
            instr.write_full_instrument()

        instr.settings(checks=False)
        instr.write_full_instrument()

    def test_get_component_simple(self):
        """
        get_component retrieves a component with a given name for
        easier manipulation. Check it works as intended.
        """

        instr = setup_populated_instr()

        comp = instr.get_component("second_component")

        self.assertEqual(comp.name, "second_component")

    def test_get_component_simple_error(self):
        """
        get_component retrieves a component with a given name for
        easier manipulation. Check it fails when the component name
        doesn't correspond to a component in the instrument.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.get_component("non_existing_component")

    def test_get_last_component_simple(self):
        """
        Check get_last_component retrieves the last component
        """

        instr = setup_populated_instr()

        comp = instr.get_last_component()

        self.assertEqual(comp.name, "third_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_print_component(self, mock_stdout):
        """
        print_component calls the print_long method in the component
        class.
        """

        instr = setup_populated_instr()
        instr.get_component("second_component").set_parameters(dist=5)

        instr.print_component("second_component")

        output = mock_stdout.getvalue().split("\n")

        self.assertEqual(output[0],
                         "COMPONENT second_component = test_for_reading(")

        par_name = bcolors.BOLD + "dist" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "5" + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[1], "  " + par_name + " = " + value + " // [m]")

        par_name = bcolors.BOLD + "gauss" + bcolors.ENDC
        warning = (bcolors.FAIL
                   + " : Required parameter not yet specified"
                   + bcolors.ENDC)
        self.assertEqual(output[2], "  " + par_name + warning)

        par_name = bcolors.BOLD + "test_string" + bcolors.ENDC
        warning = (bcolors.FAIL
                   + " : Required parameter not yet specified"
                   + bcolors.ENDC)
        self.assertEqual(output[3], "  " + par_name + warning)

        self.assertEqual(output[4], ")")
        self.assertEqual(output[5], "AT (0, 0, 0) ABSOLUTE")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_print_component_short(self, mock_stdout):
        """
        print_component_short calls the print_short method in the
        component class.
        """

        instr = setup_populated_instr()
        instr.get_component("second_component").set_AT([-1, 2, 3.4],
                                                       RELATIVE="home")

        instr.print_component_short("second_component")

        output = mock_stdout.getvalue().split("\n")

        expected = ("second_component = test_for_reading "
                    + "\tAT [-1, 2, 3.4] RELATIVE home "
                    + "ROTATED [0, 0, 0] RELATIVE home")

        self.assertEqual(output[0], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_simple(self, mock_stdout):
        """
        Tests show_components for simple case

        show_components calls the print_short method in the component
        class for each component and aligns the data for display
        """

        instr = setup_populated_instr()

        instr.show_components(line_length=300)

        output = mock_stdout.getvalue().split("\n")

        expected = ("first_component  test_for_reading"
                    + " AT (0, 0, 0) ABSOLUTE")
        self.assertEqual(output[0], expected)

        expected = ("second_component test_for_reading"
                    + " AT (0, 0, 0) ABSOLUTE")
        self.assertEqual(output[1], expected)

        expected = ("third_component  test_for_reading"
                    + " AT (0, 0, 0) ABSOLUTE")
        self.assertEqual(output[2], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_complex(self, mock_stdout):
        """
        Tests show_components for complex case

        show_components calls the print_short method in the component
        class for each component and aligns the data for display
        """

        instr = setup_populated_instr()

        instr.get_component("first_component").set_AT([-0.1, 12, "dist"],
                                                      RELATIVE="home")
        instr.get_component("second_component").set_ROTATED([-4, 0.001, "theta"],
                                                            RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.show_components(line_length=300)

        output = mock_stdout.getvalue().split("\n")

        expected = ("first_component  test_for_reading"
                    + " AT (-0.1, 12, dist) RELATIVE home")
        self.assertEqual(output[0], expected)

        expected = ("second_component test_for_reading"
                    + " AT (0, 0, 0)        ABSOLUTE"
                    + "      ROTATED (-4, 0.001, theta) RELATIVE etc")
        self.assertEqual(output[1], expected)

        expected = ("third_component  test_name"
                    + "        AT (0, 0, 0)        ABSOLUTE     ")
        self.assertEqual(output[2], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_complex_2lines(self, mock_stdout):
        """
        show_components calls the print_short method in the component
        class for each component and aligns the data for display

        This version of the tests forces two lines of output.
        """

        instr = setup_populated_instr()

        instr.get_component("first_component").set_AT([-0.1, 12, "dist"],
                                                      RELATIVE="home")
        instr.get_component("second_component").set_ROTATED([-4, 0.001, "theta"],
                                                            RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.show_components(line_length=80)

        output = mock_stdout.getvalue().split("\n")

        expected = ("first_component  test_for_reading"
                    + " AT      (-0.1, 12, dist)   RELATIVE home")
        self.assertEqual(output[0], expected)

        expected = ("second_component test_for_reading"
                    + " AT      (0, 0, 0)          ABSOLUTE      ")
        self.assertEqual(output[1], expected)

        expected = ("                                 "
                    + " ROTATED (-4, 0.001, theta) RELATIVE etc")
        self.assertEqual(output[2], expected)

        expected = ("third_component  test_name       "
                    + " AT      (0, 0, 0)          ABSOLUTE     ")
        self.assertEqual(output[3], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_complex_3lines(self, mock_stdout):
        """
        show_components calls the print_short method in the component
        class for each component and aligns the data for display

        This version of the tests forces three lines of output.
        """

        instr = setup_populated_instr()

        instr.get_component("first_component").set_AT([-0.1, 12, "dist"],
                                                      RELATIVE="home")
        instr.get_component("second_component").set_ROTATED([-4, 0.001, "theta"],
                                                            RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.show_components(line_length=1)  # Three lines maximum

        output = mock_stdout.getvalue().split("\n")

        expected = (bcolors.BOLD
                    + "first_component"
                    + bcolors.ENDC
                    + "  "
                    + bcolors.BOLD
                    + "test_for_reading"
                    + bcolors.ENDC
                    + " ")
        self.assertEqual(output[0], expected)

        expected = "  AT      (-0.1, 12, dist) RELATIVE home"
        self.assertEqual(output[1], expected)

        expected = (bcolors.BOLD
                    + "second_component"
                    + bcolors.ENDC
                    + "  "
                    + bcolors.BOLD
                    + "test_for_reading"
                    + bcolors.ENDC
                    + " ")
        self.assertEqual(output[2], expected)

        expected = "  AT      (0, 0, 0) ABSOLUTE "
        self.assertEqual(output[3], expected)

        expected = "  ROTATED (-4, 0.001, theta) RELATIVE etc"
        self.assertEqual(output[4], expected)

        expected = (bcolors.BOLD
                    + "third_component"
                    + bcolors.ENDC
                    + "  "
                    + bcolors.BOLD
                    + "test_name"
                    + bcolors.ENDC
                    + " ")
        self.assertEqual(output[5], expected)

        expected = "  AT      (0, 0, 0) ABSOLUTE"
        self.assertEqual(output[6], expected)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_write_c_files_simple(self, mock_f):
        """
        Write_c_files writes the strings for declare, initialize,
        and trace to files that are then included in McStas files.
        This is an obsolete method, but may be repurposed later
        so that instrument parts can be created with the modern
        syntax.

        The generated includes file in the test directory is written
        by this test. It will fail if it does not have rights to
        create the directory.
        """

        instr = setup_populated_instr()

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        current_directory = os.getcwd()
        os.chdir(THIS_DIR)

        try:
            instr.write_c_files()
        finally:
            os.chdir(current_directory)

        base_path = os.path.join(".", "generated_includes")
        expected_path = os.path.join(base_path, "test_instrument_declare.c")
        mock_f.assert_any_call(expected_path, "w")
        mock_f.assert_any_call(expected_path, "a")

        expected_path = os.path.join(base_path, "test_instrument_initialize.c")
        mock_f.assert_any_call(expected_path, "w")

        expected_path = os.path.join(base_path, "test_instrument_trace.c")
        mock_f.assert_any_call(expected_path, "w")

        expected_path = os.path.join(base_path, "test_instrument_component_trace.c")
        mock_f.assert_any_call(expected_path, "w")

        # This does not check that the right thing is written to the
        # right file. Can be improved by splitting the method into
        # several for easier testing. Acceptable since it is rarely
        # used.
        handle = mock_f()
        call = unittest.mock.call
        wrts = [
         call("// declare section for test_instrument \n"),
         call("double two_theta;"),
         call("\n"),
         call("// Start of initialize for generated test_instrument\n"
              + "two_theta = 2.0*theta;\n"),
         call("// Start of trace section for generated test_instrument\n"),
         call("COMPONENT first_component = test_for_reading("),
         call(")\n"),
         call("AT (0,0,0)"),
         call(" ABSOLUTE\n"),
         call("\n"),
         call("COMPONENT second_component = test_for_reading("),
         call(")\n"),
         call("AT (0,0,0)"),
         call(" ABSOLUTE\n"),
         call("\n"),
         call("COMPONENT third_component = test_for_reading("),
         call(")\n"),
         call("AT (0,0,0)"),
         call(" ABSOLUTE\n"),
         call("\n")]

        handle.write.assert_has_calls(wrts, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    @unittest.mock.patch('datetime.datetime')
    def test_write_full_instrument_simple(self, mock_datetime, mock_f):
        """
        The write_full_instrument method write the information
        contained in the instrument instance to a file with McStas
        syntax.

        The test includes a time stamp in the written and expected
        data that has an accuracy of 1 second.  It is unlikely to fail
        due to this, but it can happen.
        """

        # Fix datetime for call
        fixed_datetime = datetime.datetime(2023, 12, 14, 12, 44, 21)
        mock_datetime.now.return_value = fixed_datetime

        instr = setup_populated_instr()
        instr.write_full_instrument()

        t_format = "%H:%M:%S on %B %d, %Y"

        my_call = unittest.mock.call
        wrts = [
         my_call("/" + 80*"*" + "\n"),
         my_call("* \n"),
         my_call("* McStas, neutron ray-tracing package\n"),
         my_call("*         Copyright (C) 1997-2008, All rights reserved\n"),
         my_call("*         Risoe National Laboratory, Roskilde, Denmark\n"),
         my_call("*         Institut Laue Langevin, Grenoble, France\n"),
         my_call("* \n"),
         my_call("* This file was written by McStasScript, which is a \n"),
         my_call("* python based McStas instrument generator written by \n"),
         my_call("* Mads Bertelsen in 2019 while employed at the \n"),
         my_call("* European Spallation Source Data Management and \n"),
         my_call("* Software Centre\n"),
         my_call("* \n"),
         my_call("* Instrument test_instrument\n"),
         my_call("* \n"),
         my_call("* %Identification\n"),
         my_call("* Written by: Python McStas Instrument Generator\n"),
         my_call("* Date: %s\n" % fixed_datetime.strftime(t_format)),
         my_call("* Origin: ESS DMSC\n"),
         my_call("* %INSTRUMENT_SITE: Generated_instruments\n"),
         my_call("* \n"),
         my_call("* \n"),
         my_call("* %Parameters\n"),
         my_call("* \n"),
         my_call("* %End \n"),
         my_call("*"*80 + "/\n"),
         my_call("\n"),
         my_call("DEFINE INSTRUMENT test_instrument ("),
         my_call("\n"),
         my_call("double theta"),
         my_call(", "),
         my_call(""),
         my_call("\n"),
         my_call("double has_default"),
         my_call(" = 37"),
         my_call(" "),
         my_call(""),
         my_call("\n"),
         my_call(")\n"),
         my_call("\n"),
         my_call("DECLARE \n%{\n"),
         my_call("double two_theta;"),
         my_call("\n"),
         my_call("%}\n\n"),
         my_call("INITIALIZE \n%{\n"),
         my_call("// Start of initialize for generated test_instrument\n"
                 + "two_theta = 2.0*theta;\n"),
         my_call("%}\n\n"),
         my_call("TRACE \n"),
         my_call("COMPONENT first_component = test_for_reading("),
         my_call(")\n"),
         my_call("AT (0,0,0)"),
         my_call(" ABSOLUTE\n"),
         my_call("\n"),
         my_call("COMPONENT second_component = test_for_reading("),
         my_call(")\n"),
         my_call("AT (0,0,0)"),
         my_call(" ABSOLUTE\n"),
         my_call("\n"),
         my_call("COMPONENT third_component = test_for_reading("),
         my_call(")\n"),
         my_call("AT (0,0,0)"),
         my_call(" ABSOLUTE\n"),
         my_call("\n"),
         my_call("FINALLY \n%{\n"),
         my_call("// Start of finally for generated test_instrument\n"),
         my_call("%}\n"),
         my_call("\nEND\n")]

        expected_path = os.path.join(".", "test_instrument.instr")
        mock_f.assert_called_with(expected_path, "w")
        handle = mock_f()
        handle.write.assert_has_calls(wrts, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_write_full_instrument_dependency(self, mock_f):
        """
        The write_full_instrument method write the information
        contained in the instrument instance to a file with McStas
        syntax. Here tested with the dependency section enabled.

        The test includes a time stamp in the written and expected
        data that has an accuracy of 1 second.  It is unlikely to fail
        due to this, but it can happen.
        """

        instr = setup_populated_instr()
        instr.set_dependency("-DMCPLPATH=GETPATH(data)")
        instr.write_full_instrument()

        t_format = "%H:%M:%S on %B %d, %Y"

        my_call = unittest.mock.call
        wrts = [
            my_call("/" + 80 * "*" + "\n"),
            my_call("* \n"),
            my_call("* McStas, neutron ray-tracing package\n"),
            my_call("*         Copyright (C) 1997-2008, All rights reserved\n"),
            my_call("*         Risoe National Laboratory, Roskilde, Denmark\n"),
            my_call("*         Institut Laue Langevin, Grenoble, France\n"),
            my_call("* \n"),
            my_call("* This file was written by McStasScript, which is a \n"),
            my_call("* python based McStas instrument generator written by \n"),
            my_call("* Mads Bertelsen in 2019 while employed at the \n"),
            my_call("* European Spallation Source Data Management and \n"),
            my_call("* Software Centre\n"),
            my_call("* \n"),
            my_call("* Instrument test_instrument\n"),
            my_call("* \n"),
            my_call("* %Identification\n"),
            my_call("* Written by: Python McStas Instrument Generator\n"),
            my_call("* Date: %s\n" % datetime.datetime.now().strftime(t_format)),
            my_call("* Origin: ESS DMSC\n"),
            my_call("* %INSTRUMENT_SITE: Generated_instruments\n"),
            my_call("* \n"),
            my_call("* \n"),
            my_call("* %Parameters\n"),
            my_call("* \n"),
            my_call("* %End \n"),
            my_call("*" * 80 + "/\n"),
            my_call("\n"),
            my_call("DEFINE INSTRUMENT test_instrument ("),
            my_call("\n"),
            my_call("double theta"),
            my_call(", "),
            my_call(""),
            my_call("\n"),
            my_call("double has_default"),
            my_call(" = 37"),
            my_call(" "),
            my_call(""),
            my_call("\n"),
            my_call(")\n"),
            my_call('DEPENDENCY "-DMCPLPATH=GETPATH(data)"\n'),
            my_call("\n"),
            my_call("DECLARE \n%{\n"),
            my_call("double two_theta;"),
            my_call("\n"),
            my_call("%}\n\n"),
            my_call("INITIALIZE \n%{\n"),
            my_call("// Start of initialize for generated test_instrument\n"
                    + "two_theta = 2.0*theta;\n"),
            my_call("%}\n\n"),
            my_call("TRACE \n"),
            my_call("COMPONENT first_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("COMPONENT second_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("COMPONENT third_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("FINALLY \n%{\n"),
            my_call("// Start of finally for generated test_instrument\n"),
            my_call("%}\n"),
            my_call("\nEND\n")]

        expected_path = os.path.join(".", "test_instrument.instr")
        mock_f.assert_called_with(expected_path, "w")
        handle = mock_f()
        handle.write.assert_has_calls(wrts, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_write_full_instrument_search(self, mock_f):
        """
        The write_full_instrument method write the information
        contained in the instrument instance to a file with McStas
        syntax. Here tested with the search section enabled.

        The test includes a time stamp in the written and expected
        data that has an accuracy of 1 second.  It is unlikely to fail
        due to this, but it can happen.
        """

        instr = setup_populated_instr()
        instr.add_search("first_search")
        instr.add_search("second search", SHELL=True)
        instr.write_full_instrument()

        t_format = "%H:%M:%S on %B %d, %Y"

        my_call = unittest.mock.call
        wrts = [
            my_call("/" + 80 * "*" + "\n"),
            my_call("* \n"),
            my_call("* McStas, neutron ray-tracing package\n"),
            my_call("*         Copyright (C) 1997-2008, All rights reserved\n"),
            my_call("*         Risoe National Laboratory, Roskilde, Denmark\n"),
            my_call("*         Institut Laue Langevin, Grenoble, France\n"),
            my_call("* \n"),
            my_call("* This file was written by McStasScript, which is a \n"),
            my_call("* python based McStas instrument generator written by \n"),
            my_call("* Mads Bertelsen in 2019 while employed at the \n"),
            my_call("* European Spallation Source Data Management and \n"),
            my_call("* Software Centre\n"),
            my_call("* \n"),
            my_call("* Instrument test_instrument\n"),
            my_call("* \n"),
            my_call("* %Identification\n"),
            my_call("* Written by: Python McStas Instrument Generator\n"),
            my_call("* Date: %s\n" % datetime.datetime.now().strftime(t_format)),
            my_call("* Origin: ESS DMSC\n"),
            my_call("* %INSTRUMENT_SITE: Generated_instruments\n"),
            my_call("* \n"),
            my_call("* \n"),
            my_call("* %Parameters\n"),
            my_call("* \n"),
            my_call("* %End \n"),
            my_call("*" * 80 + "/\n"),
            my_call("\n"),
            my_call("DEFINE INSTRUMENT test_instrument ("),
            my_call("\n"),
            my_call("double theta"),
            my_call(", "),
            my_call(""),
            my_call("\n"),
            my_call("double has_default"),
            my_call(" = 37"),
            my_call(" "),
            my_call(""),
            my_call("\n"),
            my_call(")\n"),
            my_call("\n"),
            my_call("DECLARE \n%{\n"),
            my_call("double two_theta;"),
            my_call("\n"),
            my_call("%}\n\n"),
            my_call("INITIALIZE \n%{\n"),
            my_call("// Start of initialize for generated test_instrument\n"
                    + "two_theta = 2.0*theta;\n"),
            my_call("%}\n\n"),
            my_call("TRACE \n"),
            my_call('SEARCH "first_search"\n'),
            my_call('SEARCH SHELL "second search"\n'),
            my_call("COMPONENT first_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("COMPONENT second_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("COMPONENT third_component = test_for_reading("),
            my_call(")\n"),
            my_call("AT (0,0,0)"),
            my_call(" ABSOLUTE\n"),
            my_call("\n"),
            my_call("FINALLY \n%{\n"),
            my_call("// Start of finally for generated test_instrument\n"),
            my_call("%}\n"),
            my_call("\nEND\n")]

        expected_path = os.path.join(".", "test_instrument.instr")
        mock_f.assert_called_with(expected_path, "w")
        handle = mock_f()
        handle.write.assert_has_calls(wrts, any_order=False)

    # mock sys.stdout to avoid printing to terminal
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_run_full_instrument_required_par_error(self, mock_stdout):
        """
        Tests run_full_instrument raises error when lacking required parameter

        The populated instr has a required parameter, and when not
        given it should raise an error.
        """
        instr = setup_populated_instr()

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with self.assertRaises(NameError):
            instr.run_full_instrument(output_path="test_data_set",
                                      increment_folder_name=False,
                                      executable_path=executable_path)

    def test_run_full_instrument_junk_par_error(self):
        """
        Check run_full_instrument raises a NameError if a unrecognized
        parameter is provided, here junk.
        """
        instr = setup_populated_instr()

        pars = {"theta": 2, "junk": "test"}

        with self.assertRaises(KeyError):
            instr.run_full_instrument(output_path="test_data_set",
                                      increment_folder_name=False,
                                      parameters=pars)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_x_ray_run_full_instrument_basic(self, mock_sub, mock_stdout):
        """
        Tests x-ray run_full_instrument

        Check a simple run performs the correct system call.  Here
        the output_path is set to a name that does not correspond to a
        existing file so no error is thrown.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_x_ray_instr_with_dummy_path()
            instr.run_full_instrument(output_path=new_folder_name,
                                      increment_folder_name=False,
                                      executable_path=executable_path,
                                      parameters={"theta": 1})

        expected_path = os.path.join(executable_path, "mxrun")
        expected_path = '"' + expected_path + '"'

        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 1000000 "
                         + "-d " + expected_folder_path
                         + "  test_instrument.instr"
                         + " theta=1 has_default=37")

        expected_run_path = os.path.join(THIS_DIR, ".")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    cwd=expected_run_path,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_run_backengine_existing_folder(self, mock_stdout):
        """
        Test neutron run of backengine fails if using existing folder
        for output_path and with increment_folder_name disabled.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            instr = setup_populated_instr_with_dummy_path()

            instr.set_parameters({"theta": 1})
            instr.settings(output_path="test_data_set",
                           increment_folder_name=False,
                           executable_path=executable_path)

            with self.assertRaises(NameError):
                instr.backengine()

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_run_backengine_basic(self, mock_sub, mock_stdout):
        """
        Test neutron run_full_instrument

        Check a simple run performs the correct system call. Here
        the output_path is set to a name that does not correspond to a
        existing file so no error is thrown.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_instr_with_dummy_path()

            instr.set_parameters({"theta": 1})
            instr.settings(output_path=new_folder_name,
                           increment_folder_name=True,
                           executable_path=executable_path)
            instr.backengine()

        expected_path = os.path.join(executable_path, "mcrun")
        expected_path = '"' + expected_path + '"'

        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 1000000 "
                         + "-d " + expected_folder_path
                         + "  test_instrument.instr"
                         + " theta=1 has_default=37")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True,
                                    cwd=run_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_run_backengine_complex_settings(self, mock_sub, mock_stdout):
        """
        Test settings are passed to backengine with complex settings

        Check run performs the correct system call with settings. Here
        the output_path is set to a name that does not correspond to a
        existing file so no error is thrown.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_instr_with_dummy_path()

            instr.set_parameters({"theta": 1})
            instr.settings(output_path=new_folder_name,
                           increment_folder_name=True,
                           executable_path=executable_path,
                           mpi=5, ncount=19373, openacc=True,
                           NeXus=True, force_compile=False,
                           seed=300, gravity=True, checks=False,
                           save_comp_pars=True)
            instr.backengine()

        expected_path = os.path.join(executable_path, "mcrun")
        expected_path = '"' + expected_path + '"'

        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -g --format=NeXus "
                         + "--openacc "
                         + "-n 19373 --mpi=5 --seed=300 "
                         + "-d " + expected_folder_path
                         + "  test_instrument.instr"
                         + " theta=1 has_default=37")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True,
                                    cwd=run_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_complex(self, mock_sub, mock_stdout):
        """
        Test neutron run_full_instrument in more complex case

        Check a complex run performs the correct system call. Here
        the output_path is set to a name that does not correspond to a
        existing file so no error is thrown.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_instr_with_dummy_path()

            # Add some extra parameters for testing
            instr.add_parameter("A")
            instr.add_parameter("BC")

            instr.run_full_instrument(output_path=new_folder_name,
                                      increment_folder_name=False,
                                      executable_path=executable_path,
                                      mpi=7,
                                      seed=300,
                                      ncount=48.4,
                                      gravity=True,
                                      custom_flags="-fo",
                                      parameters={"A": 2,
                                                  "BC": "car",
                                                  "theta": "\"toy\""})

        expected_path = os.path.join(executable_path, "mcrun")
        expected_path = '"' + expected_path + '"'
        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -c -g -n 48 --mpi=7 --seed=300 "
                         + "-d " + expected_folder_path
                         + " -fo test_instrument.instr "
                         + "theta=\"toy\" has_default=37 A=2 BC=car")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True,
                                    cwd=run_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_overwrite_default(self, mock_sub,
                                                   mock_stdout):
        """
        Check that default parameters are overwritten by given
        parameters in run_full_instrument.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_instr_with_dummy_path()

            # Add some extra parameters for testing
            instr.add_parameter("A")
            instr.add_parameter("BC")

            instr.run_full_instrument(output_path=new_folder_name,
                                      increment_folder_name=False,
                                      executable_path=executable_path,
                                      mpi=7,
                                      ncount=48.4,
                                      custom_flags="-fo",
                                      parameters={"A": 2,
                                                  "BC": "car",
                                                  "theta": "\"toy\"",
                                                  "has_default": 10})

        expected_path = os.path.join(executable_path, "mcrun")
        expected_path = '"' + expected_path + '"'
        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path
                         + " -fo test_instrument.instr "
                         + "theta=\"toy\" has_default=10 A=2 BC=car")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True,
                                    cwd=run_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_x_ray_basic(self, mock_sub, mock_stdout):
        """
        Test x-ray run_full_instrument

        Check a simple run performs the correct system call.  Here
        the output_path is set to a name that does not correspond to a
        existing file so no error is thrown.
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        with WorkInTestDir() as handler:
            new_folder_name = "folder_name_which_is_unused"
            if os.path.exists(new_folder_name):
                raise RuntimeError("Folder_name was supposed to not "
                                   + "exist before "
                                   + "test_run_backengine_basic")

            instr = setup_populated_x_ray_instr_with_dummy_path()

            instr.run_full_instrument(output_path=new_folder_name,
                                      increment_folder_name=False,
                                      executable_path=executable_path,
                                      parameters={"theta": 1})

        expected_path = os.path.join(executable_path, "mxrun")
        expected_path = '"' + expected_path + '"'
        expected_folder_path = os.path.join(THIS_DIR, new_folder_name)

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 1000000 "
                         + "-d " + expected_folder_path
                         + "  test_instrument.instr"
                         + " theta=1 has_default=37")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-2, stdout=-1,
                                    universal_newlines=True,
                                    cwd=run_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch("subprocess.run")
    def test_show_instrument_basic(self, mock_sub, mock_stdout):
        """
        Test show_instrument methods makes correct system calls
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(THIS_DIR, "dummy_mcstas")

        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder

        instr = setup_populated_instr_with_dummy_path()

        instr.set_parameters(theta=1.2)
        instr.show_instrument()

        os.chdir(current_work_dir)

        expected_path = os.path.join(executable_path, "bin", "mcdisplay-webgl")
        expected_path = '"' + expected_path + '"'
        expected_instr_path = os.path.join(THIS_DIR, "test_instrument.instr")

        # a double space because of a missing option
        expected_call = (expected_path
                         + " --dirname test_instrument_mcdisplay"
                         + " " + expected_instr_path
                         + "  theta=1.2 has_default=37")

        mock_sub.assert_called_with(expected_call,
                                    shell=True,
                                    stderr=-1, stdout=-1,
                                    universal_newlines=True,
                                    cwd=".")

    def test_show_dumps_works(self):
        """
        Ensures show_dumps runs
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()
        insert_mock_dump(instr, "second_component")

        instr.show_dumps()

    def test_show_dump_works(self):
        """
        Ensures show_dump runs and that db can get the stored dump
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()
        insert_mock_dump(instr, "second_component", run_name="custom_run", tag=31)

        instr.show_dump("second_component", "custom_run", 31)

        dump = instr.dump_database.get_dump("second_component", "custom_run", 31)
        self.assertEqual(dump.data["dump_point"], "second_component")
        self.assertEqual(dump.data["run_name"], "custom_run")
        self.assertEqual(dump.data["tag"], 31)

    def test_set_run_to_component(self):
        """
        Testing run_to method updates instr state correctly
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()

        second_component = instr.get_component("second_component")

        # Ensure remaining instrument can work
        third_component = instr.get_component("third_component")
        third_component.set_RELATIVE("second_component")

        instr.run_to(second_component)

        self.assertEqual(instr.run_from_ref, None)
        self.assertEqual(instr.run_to_ref, "second_component")
        self.assertEqual(instr.run_to_name, "Run")

        # Check filename added to parameters
        self.assertTrue("run_to_mcpl" in instr.parameters.parameters)
        self.assertEqual(instr.parameters.parameters["run_to_mcpl"].type, "string")

        instr.run_to("third_component", run_name="Test_name")
        self.assertEqual(instr.run_to_ref, "third_component")
        self.assertEqual(instr.run_to_name, "Test_name")

    def test_set_run_to_component_keywords(self):
        """
        Testing run_to method updates instr state with passed keywords
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()

        second_component = instr.get_component("second_component")

        # Ensure remaining instrument can work
        third_component = instr.get_component("third_component")
        third_component.set_RELATIVE("second_component")

        instr.run_to(second_component, test_keyword=58)

        self.assertIn("test_keyword", instr.run_to_component_parameters)
        self.assertEqual(instr.run_to_component_parameters["test_keyword"], 58)

    def test_set_run_to_nonexistant_component_fails(self):
        """
        Ensures run_to fails if the component doesn't exist
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()

        with self.assertRaises(ValueError):
            instr.run_to("component_that_does_not_exists")

    def test_set_run_to_component_with_ABSOLUTE_in_remaining_fails(self):
        """
        Ensures run_to fails if the remaining instrument refers to absolute
        """
        instr = setup_populated_instr_with_dummy_MCPL_comps()

        with self.assertRaises(McStasError):
            # Fails because the rest of the instrument has reference to ABSOLUTE
            instr.run_to("second_component")

    def test_set_run_to_component_with_early_ref_in_remaining_fails(self):
        """
        Ensures run_to fails if the remaining instrument refers to absolute
        """
        instr = setup_populated_instr_with_dummy_MCPL_comps()

        comp = instr.get_component("third_component")
        comp.set_RELATIVE("first_component")

        with self.assertRaises(McStasError):
            # Fails because the rest of the instrument has reference to component before split
            instr.run_to("second_component")

    def test_set_run_from_component(self):
        """
        Testing run_from method updates instr state correctly
        """
        instr = setup_populated_instr_with_dummy_MCPL_comps()

        insert_mock_dump(instr, "second_component")

        second_component = instr.get_component("second_component")

        # Ensure remaining instrument can work
        third_component = instr.get_component("third_component")
        third_component.set_RELATIVE("second_component")

        instr.run_from(second_component)

        self.assertEqual(instr.run_to_ref, None)
        self.assertEqual(instr.run_from_ref, "second_component")

        # Check filename added to parameters
        self.assertTrue("run_from_mcpl" in instr.parameters.parameters)
        self.assertEqual(instr.parameters.parameters["run_from_mcpl"].type, "string")

    def test_set_run_from_component_fails_if_no_dump(self):
        """
        Ensure run_from fails if there are no dumps at that location
        """
        instr = setup_populated_instr_with_dummy_MCPL_comps()

        with self.assertRaises(KeyError):
            instr.run_from("second_component")

        # Also fails if database is populated at a different component
        insert_mock_dump(instr, "second_component")

        with self.assertRaises(KeyError):
            instr.run_from("first_component")

    def test_set_run_from_component_keywords(self):
        """
        Testing run_to method updates instr state with passed keywords
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()

        insert_mock_dump(instr, "second_component")

        second_component = instr.get_component("second_component")

        # Ensure remaining instrument can work
        third_component = instr.get_component("third_component")
        third_component.set_RELATIVE("second_component")

        instr.run_from(second_component, test_keyword=37)

        self.assertIn("test_keyword", instr.run_from_component_parameters)
        self.assertEqual(instr.run_from_component_parameters["test_keyword"], 37)

    def test_set_run_from_and_run_to(self):
        """
        Ensure it is possible to use run_from and run_to, and that reset work
        """

        instr = setup_populated_instr_with_dummy_MCPL_comps()
        insert_mock_dump(instr, "second_component")
        third_component = instr.get_component("third_component")
        third_component.set_RELATIVE("second_component")

        instr.run_from("second_component")
        instr.run_to("third_component")

        self.assertEqual(instr.run_from_ref, "second_component")
        self.assertEqual(instr.run_to_ref, "third_component")

        instr.reset_run_points()

        self.assertEqual(instr.run_from_ref, None)
        self.assertEqual(instr.run_to_ref, None)

if __name__ == '__main__':
    unittest.main()
