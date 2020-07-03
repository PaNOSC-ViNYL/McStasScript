import os
import io
import builtins
import unittest
import unittest.mock
import datetime

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.helper.formatting import bcolors


def setup_instr_no_path():
    """
    Sets up a instrument without a mcstas_path
    """
    return McStas_instr("test_instrument")


def setup_instr_root_path():
    """
    Sets up a instrument with root mcstas_path
    """
    return McStas_instr("test_instrument", mcstas_path="/")


def setup_instr_with_path():
    """
    Sets up a instrument with a valid mcstas_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    return McStas_instr("test_instrument", mcstas_path=dummy_path)

    os.chdir(current_work_dir)  # Return to previous workdir

def setup_instr_with_input_path():
    """
    Sets up a instrument with a valid mcstas_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
    input_path = os.path.join(THIS_DIR, "test_input_folder")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    return McStas_instr("test_instrument",
                        mcstas_path=dummy_path,
                        input_path=input_path)

    os.chdir(current_work_dir)  # Return to previous workdir

def setup_instr_with_input_path_relative():
    """
    Sets up a instrument with a valid mcstas_path, but it points to
    the dummy installation in the test folder.
    """

    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    return McStas_instr("test_instrument",
                        mcstas_path="dummy_mcstas",
                        input_path="test_input_folder")

    os.chdir(current_work_dir)  # Return to previous workdir


def setup_populated_instr():
    """
    Sets up a instrument with some features used and two components
    """
    instr = setup_instr_root_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    comp1 = instr.add_component("first_component", "test_for_reading")
    comp2 = instr.add_component("second_component", "test_for_reading")
    comp3 = instr.add_component("third_component", "test_for_reading")

    return instr

def setup_populated_with_some_options_instr():
    """
    Sets up a instrument with some features used and two components
    """
    instr = setup_instr_root_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    comp1 = instr.add_component("first_component", "test_for_reading")
    comp1.set_AT([0,0,1])
    comp1.set_GROUP("Starters")
    comp2 = instr.add_component("second_component", "test_for_reading")
    comp2.set_AT([0,0,2], RELATIVE="first_component")
    comp2.set_ROTATED([0,30,0])
    comp2.set_WHEN("1==1")
    comp2.yheight=1.23
    comp3 = instr.add_component("third_component", "test_for_reading")

    return instr


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
        my_instrument = McStas_instr("test_instrument",
                                     author="Mads",
                                     origin="DMSC",
                                     mcrun_path="/path/to/mcrun",
                                     mcstas_path="/path/to/mcstas")

        self.assertEqual(my_instrument.author, "Mads")
        self.assertEqual(my_instrument.origin, "DMSC")
        self.assertEqual(my_instrument.mcrun_path, "/path/to/mcrun")
        self.assertEqual(my_instrument.mcstas_path, "/path/to/mcstas")

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

        self.assertEqual(my_instrument.mcrun_path, correct_mcrun_path)
        self.assertEqual(my_instrument.mcstas_path, correct_mcstas_path)
        self.assertEqual(my_instrument.line_limit, correct_n_of_characters)

    def test_simple_add_parameter(self):
        """
        This is just an interface to a function that is tested
        elsewhere, so only a basic test is performed here.
        """
        instr = setup_instr_root_path()

        instr.add_parameter("double", "theta", comment="test par")

        self.assertEqual(instr.parameter_list[0].name, "theta")
        self.assertEqual(instr.parameter_list[0].comment, "// test par")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_parameters(self, mock_stdout):
        """
        Testing that parameters are displayed correctly
        """
        instr = setup_instr_root_path()

        instr.add_parameter("double", "theta", comment="test par")
        instr.add_parameter("single", "theta", comment="test par")
        instr.add_parameter("float", "theta", value=8, comment="test par")
        instr.add_parameter("int", "slits", comment="test par")
        instr.add_parameter("string", "ref",
                            value="string", comment="new string")

        instr.show_parameters(line_length=300)

        output = mock_stdout.getvalue().split("\n")

        self.assertEqual(output[0], "double  theta             // test par")
        self.assertEqual(output[1], "single  theta             // test par")
        self.assertEqual(output[2], "float   theta  =  8       // test par")
        self.assertEqual(output[3], "int     slits             // test par")
        self.assertEqual(output[4], "string  ref    =  string  // new string")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_parameters_line_break(self, mock_stdout):
        """
        Testing that parameters are displayed correctly

        Here multiple lines are used for a long comment that was
        dynamically broken up.
        """
        instr = setup_instr_root_path()

        instr.add_parameter("double", "theta", comment="test par")
        instr.add_parameter("single", "theta", comment="test par")
        instr.add_parameter("float", "theta", value=8, comment="test par")
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

        self.assertEqual(output[0], "double  theta             // test par")
        self.assertEqual(output[1], "single  theta             // test par")
        self.assertEqual(output[2], "float   theta  =  8       // test par")
        self.assertEqual(output[3], "int     slits             // test par")
        self.assertEqual(output[4], "string  ref    =  string  // new string")
        comment_line = "This is a very long comment meant for testing "
        self.assertEqual(output[5], "double  value  =  37      // "
                                    + comment_line)
        comment_line = "the dynamic line breaking that is used in this "
        self.assertEqual(output[6], "                             "
                                    + comment_line)
        comment_line = "method. It needs to have many lines in order to "
        self.assertEqual(output[7], "                             "
                                    + comment_line)
        comment_line = "ensure it really works. "
        self.assertEqual(output[8], "                             "
                                    + comment_line)

    def test_simple_add_declare_parameter(self):
        """
        This is just an interface to a function that is tested
        elsewhere, so only a basic test is performed here.
        """
        instr = setup_instr_root_path()

        instr.add_declare_var("double", "two_theta", comment="test par")

        self.assertEqual(instr.declare_list[0].name, "two_theta")
        self.assertEqual(instr.declare_list[0].comment, " // test par")
        
    def test_simple_append_declare(self):
        """
        The declare lines are held as a string. This method
        appends that string.
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
        The declare lines are held as a string. This method
        appends that string.
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
        appends that string.
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
        The initialize section is held as a string. This method
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
        The initialize section is held as a string. This method
        appends that string.
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
        The initialize section is held as a string. This method
        appends that string.
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
        The initialize section is held as a string. This method
        appends that string.
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
    def test_show_components_simple(self, mock_stdout):
        """
        Simple test of show components to show categories
        """
        instr = setup_instr_with_path()

        instr.show_components()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work_directory / input_path:")
        self.assertEqual(output[1], "     test_for_reading.comp")
        self.assertEqual(output[2], "These definitions will be used "
                                    +"instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " sources")
        self.assertEqual(output[5], " Work directory")
        self.assertEqual(output[6], " misc")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_folder(self, mock_stdout):
        """
        Simple test of show components to show categories
        """
        instr = setup_instr_with_path()

        instr.show_components("Work directory")

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work_directory / input_path:")
        self.assertEqual(output[1], "     test_for_reading.comp")
        self.assertEqual(output[2], "These definitions will be used "
                         + "instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are all components in the Work directory "
                         + "category.")
        self.assertEqual(output[4], " test_for_reading")
        self.assertEqual(output[5], "")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_input_path_simple(self, mock_stdout):
        """
        Simple test of input_path being recoignized and passed
        to component_reader so PSDlin_monitor is overwritten
        """
        instr = setup_instr_with_input_path()

        instr.show_components()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work_directory / input_path:")
        self.assertEqual(output[1], "     test_for_structure.comp")
        self.assertEqual(output[2], "These definitions will be used "
                                    +"instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " sources")
        self.assertEqual(output[5], " misc")
        self.assertEqual(output[6], " Work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_components_input_path_simple(self, mock_stdout):
        """
        Simple test of input_path being recoignized and passed
        to component_reader so PSDlin_monitor is overwritten
        Here dummy_mcstas and input_path is set using relative
        paths instead of absolute paths.
        """
        instr = setup_instr_with_input_path_relative()

        instr.show_components()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0],
                         "The following components are found in the "
                         + "work_directory / input_path:")
        self.assertEqual(output[1], "     test_for_structure.comp")
        self.assertEqual(output[2], "These definitions will be used "
                                    +"instead of the installed versions.")
        self.assertEqual(output[3],
                         "Here are the available component categories:")
        self.assertEqual(output[4], " sources")
        self.assertEqual(output[5], " misc")
        self.assertEqual(output[6], " Work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_component_help(self, mock_stdout):
        """
        Simple test of component help
        """
        instr = setup_instr_with_path()

        instr.component_help("test_for_reading", line_length=90)
        # This call creates a dummy component and calls its
        # show_parameter method which has been tested. Here we
        # need to ensure the call is succesful, not test all
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
        _create_component_instance will make a dynamic subclass of
        component with the information from the component files read
        from disk.  The subclasses is saved in a dict for reuse in
        case the same component type is requested again.
        """

        instr = setup_instr_with_path()

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
        self.assertEqual(comp.category, "Work directory")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_create_component_instance_simple_error(self, mock_stdout):
        """
        _create_component_instance will make a dynamic subclass of
        component with the information from the component files read
        from disk.  The subclasses is saved in a dict for reuse in
        case the same component type is requested again.
        """

        instr = setup_instr_with_path()

        with self.assertRaises(NameError):
            comp = instr._create_component_instance("test_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_create_component_instance_complex(self, mock_stdout):
        """
        _create_component_instance will make a dynamic subclass of
        component with the information from the component files read
        from disk.  The subclasses is saved in a dict for reuse in
        case the same component type is requested again.
        """

        instr = setup_instr_with_path()

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
        self.assertEqual(comp.category, "Work directory")

        # The keyword arguments of the call should be passed to the
        # new instance of the component. This is checked by reading
        # the relative attributes which were set to home in the call
        self.assertEqual(comp.AT_relative, "RELATIVE home")
        self.assertEqual(comp.ROTATED_relative, "RELATIVE home")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple(self, mock_stdout):
        """
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
    def test_add_component_simple_keyword(self, mock_stdout):
        """
        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_instr_with_path()

        comp = instr.add_component("test_component",
                                   "test_for_reading",
                                   WHEN="1<2")

        self.assertEqual(len(instr.component_list), 1)
        self.assertEqual(instr.component_list[0].name, "test_component")
        self.assertEqual(instr.component_list[0].component_name,
                         "test_for_reading")

        self.assertEqual(instr.component_list[0].WHEN, "WHEN (1<2)")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_before(self, mock_stdout):
        """
        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_populated_instr()

        comp = instr.add_component("test_component",
                                   "test_for_reading",
                                   before="first_component")

        self.assertEqual(len(instr.component_list), 4)
        self.assertEqual(instr.component_list[0].name, "test_component")
        self.assertEqual(instr.component_list[3].name, "third_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_after(self, mock_stdout):
        """
        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_populated_instr()

        comp = instr.add_component("test_component",
                                   "test_for_reading",
                                   after="first_component")

        self.assertEqual(len(instr.component_list), 4)
        self.assertEqual(instr.component_list[1].name, "test_component")
        self.assertEqual(instr.component_list[3].name, "third_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_after_error(self, mock_stdout):
        """
        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            comp = instr.add_component("test_component",
                                       "test_for_reading",
                                       after="non_exsistent_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_before_error(self, mock_stdout):
        """
        The add_component method adds a new component object to the
        instrument and keeps track of its location within the
        sequence of components.  Normally a new component is added to
        the end of the sequence, but the before and after keywords can
        be used to select another location. Here keyword passing is
        tested.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            comp = instr.add_component("test_component",
                                       "test_for_reading",
                                       before="non_exsistent_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_add_component_simple_double_naming_error(self, mock_stdout):
        """
        This tests checks that an error occurs when giving the new
        component a name which has already been used.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            comp = instr.add_component("first_component", "test_for_reading")
            
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_copy_component_simple(self, mock_stdout):
        """
        Checks that a component can be copied
        """

        instr = setup_populated_with_some_options_instr()
        
        comp = instr.copy_component("copy_of_second_comp", "second_component")

        self.assertEqual(comp.name, "copy_of_second_comp")
        self.assertEqual(comp.yheight, 1.23)
        self.assertEqual(comp.AT_data[0], 0)
        self.assertEqual(comp.AT_data[1], 0)
        self.assertEqual(comp.AT_data[2], 2)
        
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_copy_component_keywords(self, mock_stdout):
        """
        Checks that a component can be copied and that keyword
        arguments given under copy operation is sucessfully 
        applied to the new component. A check is also made to 
        ensure that the original component was not modified.
        """

        instr = setup_populated_with_some_options_instr()

        comp = instr.copy_component("copy_of_second_comp", "second_component",
                                    AT=[1,2,3], SPLIT=10)

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
        

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_component_simple(self, mock_stdout):
        """
        get_component retrieves a component with a given name for
        easier manipulation.
        """

        instr = setup_populated_instr()

        comp = instr.get_component("second_component")

        self.assertEqual(comp.name, "second_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_component_simple_error(self, mock_stdout):
        """
        get_component retrieves a component with a given name for
        easier manipulation.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            comp = instr.get_component("non_existing_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_last_component_simple(self, mock_stdout):
        """
        get_component retrieves the last component for easier
        manipulation.
        """

        instr = setup_populated_instr()

        comp = instr.get_last_component()

        self.assertEqual(comp.name, "third_component")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_parameter(self, mock_stdout):
        """
        Set component parameter passes a dict from instrument level
        to a contained component with the given name. It uses the
        get_component method.
        """

        instr = setup_populated_instr()

        instr.set_component_parameter("second_component",
                                      {"radius": 5.8,
                                       "dist": "text"})

        comp = instr.get_component("second_component")

        self.assertEqual(comp.radius, 5.8)
        self.assertEqual(comp.dist, "text")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_parameter_error(self, mock_stdout):
        """
        Set component parameter passes a dict from instrument level
        to a contained component with the given name. It uses the
        get_component method.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.set_component_parameter("second_component",
                                          {"non_exsistant_par": 5.8,
                                           "dist": "text"})

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_AT(self, mock_stdout):
        """
        set_component_AT passes the argument to the similar method
        in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_AT("second_component",
                               [1, 2, 3.2], RELATIVE="home")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.AT_data, [1, 2, 3.2])
        self.assertEqual(comp.AT_relative, "RELATIVE home")
        self.assertEqual(comp.ROTATED_relative, "ABSOLUTE")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_ROTATED(self, mock_stdout):
        """
        set_component_ROTATED passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_ROTATED("second_component",
                                    [1, 2, 3.2], RELATIVE="home")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.ROTATED_data, [1, 2, 3.2])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE home")
        self.assertEqual(comp.AT_relative, "ABSOLUTE")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_RELATIVE(self, mock_stdout):
        """
        set_component_RELATIVE passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_RELATIVE("second_component", "home")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.ROTATED_data, [0, 0, 0])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE home")
        self.assertEqual(comp.AT_relative, "RELATIVE home")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_WHEN(self, mock_stdout):
        """
        set_component_WHEN passes the argument to the similar method
        in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_WHEN("second_component", "2>1")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.WHEN, "WHEN (2>1)")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_append_component_EXTEND(self, mock_stdout):
        """
        append_component_EXTEND passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.append_component_EXTEND("second_component", "line1")
        instr.append_component_EXTEND("second_component", "line2")

        comp = instr.get_component("second_component")

        output = comp.EXTEND.split("\n")

        self.assertEqual(output[0], "line1")
        self.assertEqual(output[1], "line2")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_GROUP(self, mock_stdout):
        """
        set_component_GROUP passes the argument to the similar method
        in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_GROUP("second_component", "developers")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.GROUP, "developers")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_JUMP(self, mock_stdout):
        """
        set_component_JUMP passes the argument to the similar method
        in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_JUMP("second_component", "myself 8")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.JUMP, "myself 8")
        
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_SPLIT(self, mock_stdout):
        """
        set_component_SPLIT passes the argument to the similar method
        in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_SPLIT("second_component", 3)

        comp = instr.get_component("second_component")

        self.assertEqual(comp.SPLIT, 3)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_component_comment(self, mock_stdout):
        """
        set_component_comment passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_comment("second_component", "test comment")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.comment, "test comment")
        
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_c_code_before(self, mock_stdout):
        """
        set_component_c_code_before passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_c_code_before("second_component", "%include before.instr")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.c_code_before, "%include before.instr")
        
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_set_c_code_after(self, mock_stdout):
        """
        set_component_c_code_after passes the argument to the similar
        method in the component class.
        """

        instr = setup_populated_instr()

        instr.set_component_c_code_after("second_component", "%include after.instr")

        comp = instr.get_component("second_component")

        self.assertEqual(comp.c_code_after, "%include after.instr")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_print_component(self, mock_stdout):
        """
        print_component calls the print_long method in the component
        class.
        """

        instr = setup_populated_instr()
        instr.set_component_parameter("second_component",
                                      {"dist": 5})

        instr.print_component("second_component")

        output = mock_stdout.getvalue().split("\n")

        self.assertEqual(output[0],
                         "COMPONENT second_component = test_for_reading")

        par_name = bcolors.BOLD + "dist" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "5" + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[1], "  " + par_name + " = " + value + " [m]")

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

        self.assertEqual(output[4], "AT [0, 0, 0] ABSOLUTE")
        # Rotation not printed since it was never specified
        #self.assertEqual(output[5], "ROTATED [0, 0, 0] ABSOLUTE")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_print_component_short(self, mock_stdout):
        """
        print_component_short calls the print_short method in the
        component class.
        """

        instr = setup_populated_instr()
        instr.set_component_AT("second_component",
                               [-1, 2, 3.4], RELATIVE="home")

        instr.print_component_short("second_component")

        output = mock_stdout.getvalue().split("\n")

        expected = ("second_component = test_for_reading "
                    + "\tAT [-1, 2, 3.4] RELATIVE home "
                    + "ROTATED [0, 0, 0] RELATIVE home")

        self.assertEqual(output[0], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_print_components_simple(self, mock_stdout):
        """
        print_components calls the print_short method in the component
        class for each component and aligns the data for display
        """

        instr = setup_populated_instr()

        instr.print_components(line_length=300)

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
    def test_print_components_complex(self, mock_stdout):
        """
        print_components calls the print_short method in the component
        class for each component and aligns the data for display
        """

        instr = setup_populated_instr()

        instr.set_component_AT("first_component",
                               [-0.1, 12, "dist"],
                               RELATIVE="home")
        instr.set_component_ROTATED("second_component",
                                    [-4, 0.001, "theta"],
                                    RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.print_components(line_length=300)

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
    def test_print_components_complex_2lines(self, mock_stdout):
        """
        print_components calls the print_short method in the component
        class for each component and aligns the data for display

        This version of the tests forces two lines of output.
        """

        instr = setup_populated_instr()

        instr.set_component_AT("first_component",
                               [-0.1, 12, "dist"],
                               RELATIVE="home")
        instr.set_component_ROTATED("second_component",
                                    [-4, 0.001, "theta"],
                                    RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.print_components(line_length=80)

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
    def test_print_components_complex_3lines(self, mock_stdout):
        """
        print_components calls the print_short method in the component
        class for each component and aligns the data for display

        This version of the tests forces three lines of output.
        """

        instr = setup_populated_instr()

        instr.set_component_AT("first_component",
                               [-0.1, 12, "dist"],
                               RELATIVE="home")
        instr.set_component_ROTATED("second_component",
                                    [-4, 0.001, "theta"],
                                    RELATIVE="etc")
        comp = instr.get_last_component()
        comp.component_name = "test_name"

        instr.print_components(line_length=1)  # Three lines maximum

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

        expected = ("  AT      (-0.1, 12, dist) RELATIVE home")
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

        expected = ("  AT      (0, 0, 0) ABSOLUTE ")
        self.assertEqual(output[3], expected)

        expected = ("  ROTATED (-4, 0.001, theta) RELATIVE etc")
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

        expected = ("  AT      (0, 0, 0) ABSOLUTE")
        self.assertEqual(output[6], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_write_c_files_simple(self, mock_f, mock_stdout):
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
        instr.write_c_files()

        mock_f.assert_any_call("./generated_includes/"
                               + "test_instrument_declare.c", "w")
        mock_f.assert_any_call("./generated_includes/"
                               + "test_instrument_declare.c", "a")
        mock_f.assert_any_call("./generated_includes/"
                               + "test_instrument_initialize.c", "w")
        mock_f.assert_any_call("./generated_includes/"
                               + "test_instrument_trace.c", "w")
        mock_f.assert_any_call("./generated_includes/"
                               + "test_instrument_component_trace.c", "w")

        # This does not check that the right thing is written to the
        # right file. Can be improved by splitting the method into
        # several for easier testing. Acceptable since it is rarely
        # used.
        handle = mock_f()
        call = unittest.mock.call
        wrts = [
         call("// declare section for test_instrument \n"),
         #call(""),
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

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_write_full_instrument_simple(self, mock_f, mock_stdout):
        """
        The write_full_instrument methods writes the information
        contained in the instrument instance to a file with McStas
        syntax.

        The test includes a time stamp in the written and expected
        data that has an accuracy of 1 second.  It is unlikey to fail
        due to this, but it can happen.
        """

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
         my_call("* Software Center\n"),
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
         my_call("*"*80 + "/\n"),
         my_call("\n"),
         my_call("DEFINE INSTRUMENT test_instrument ("),
         my_call("\n"),
         my_call("double theta"),
         my_call(","),
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
         #my_call(""),
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

        mock_f.assert_called_with("./test_instrument.instr", "w")
        handle = mock_f()
        handle.write.assert_has_calls(wrts, any_order=False)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_run_full_instrument_required_par_error(self, mock_stdout):
        """
        The populated instr has a required parameter, and when not
        given it should raise an error.
        """

        instr = setup_populated_instr()

        with self.assertRaises(NameError):
            instr.run_full_instrument("test_instrument.instr",
                                      foldername="test_data_set",
                                      mcrun_path="path")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_basic(self, mock_sub,
                                       mock_f, mock_stdout,):
        """
        Check a simple run performs the correct system call.  Here
        the target directory is set to the test data set so that some
        data is loaded even though the system call is not executed.
        """

        instr = setup_populated_instr()
        instr.run_full_instrument("test_instrument.instr",
                                  foldername="test_data_set",
                                  mcrun_path="path",
                                  parameters={"theta": 1})

        expected_path = os.path.join("path","mcrun")

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_data_set")

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 1000000 "
                         + "-d " + expected_folder_path
                         + "  test_instrument.instr"
                         + " has_default=37 theta=1")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_complex(self, mock_sub,
                                         mock_f, mock_stdout,):
        """
        Check a complex run performs the correct system call.  Here
        the target directory is set to the test data set so that some
        data is loaded even though the system call is not executed.
        """

        instr = setup_populated_instr()
        instr.run_full_instrument("test_instrument.instr",
                                  foldername="test_data_set",
                                  mcrun_path="path",
                                  mpi=7,
                                  ncount=48.4,
                                  custom_flags="-fo",
                                  parameters={"A": 2,
                                              "BC": "car",
                                              "theta": "\"toy\""})

        expected_path = os.path.join("path","mcrun")

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_data_set")

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path
                         + " -fo test_instrument.instr "
                         + "has_default=37 A=2 BC=car theta=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    @unittest.mock.patch("subprocess.run")
    def test_run_full_instrument_overwrite_default(self, mock_sub,
                                                   mock_f, mock_stdout,):
        """
        Check that default parameters are overwritten by given
        parameters.
        """

        instr = setup_populated_instr()
        instr.run_full_instrument("test_instrument.instr",
                                  foldername="test_data_set",
                                  mcrun_path="path",
                                  mpi=7,
                                  ncount=48.4,
                                  custom_flags="-fo",
                                  parameters={"A": 2,
                                              "BC": "car",
                                              "theta": "\"toy\"",
                                              "has_default": 10})
        
        expected_path = os.path.join("path","mcrun")

        current_directory = os.getcwd()
        expected_folder_path = os.path.join(current_directory, "test_data_set")

        # a double space because of a missing option
        expected_call = (expected_path + " -c -n 48 --mpi=7 "
                         + "-d " + expected_folder_path
                         + " -fo test_instrument.instr "
                         + "has_default=10 A=2 BC=car theta=\"toy\"")

        mock_sub.assert_called_once_with(expected_call,
                                         shell=True,
                                         stderr=-1, stdout=-1,
                                         universal_newlines=True)


if __name__ == '__main__':
    unittest.main()
