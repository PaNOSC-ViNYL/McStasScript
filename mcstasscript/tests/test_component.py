import io
import unittest
import unittest.mock

from mcstasscript.helper.mcstas_objects import Component
from mcstasscript.helper.formatting import bcolors
from mcstasscript.helper.exceptions import McStasError


def setup_Component_all_keywords():
    """
    Sets up a Component by using all initialize keywords
    """

    return Component("test_component",
                     "Arm",
                     AT=[0.124, 183.9, 157],
                     AT_RELATIVE="home",
                     ROTATED=[482, 1240.2, 0.185],
                     ROTATED_RELATIVE="etc",
                     WHEN="1==2",
                     EXTEND="nscat = 8;",
                     GROUP="developers",
                     JUMP="myself 37",
                     SPLIT=7,
                     comment="test comment")


def setup_Component_relative():
    """
    Sets up a Component with the relative keyword used
    """
    return Component("test_component",
                     "Arm",
                     AT=[0.124, 183.9, 157],
                     ROTATED=[482, 1240.2, 0.185],
                     RELATIVE="source",
                     WHEN="1==2",
                     EXTEND="nscat = 8;",
                     GROUP="developers",
                     JUMP="myself 37",
                     SPLIT=7,
                     comment="test comment")


def setup_Component_with_parameters():
    """
    Sets up a Component with parameters and all options used.

    """
    comp = setup_Component_all_keywords()

    comp._unfreeze()
    # Need to set up attribute parameters
    comp.new_par1 = 1.5
    comp.new_par2 = 3
    comp.new_par3 = None
    comp.this_par = "test_val"
    comp.that_par = "\"txt_string\""
    # also need to categorize them as when created
    comp.parameter_names = ["new_par1", "new_par2", "new_par3",
                            "this_par", "that_par"]
    comp.parameter_defaults = {"new_par1": 5.1,
                               "new_par2": 9,
                               "new_par3": None,
                               "this_par": "conga",
                               "that_par": "\"txt\""}
    comp.parameter_comments = {"new_par1": "This is important",
                               "new_par2": "This is less important",
                               "this_par": "!",
                               "that_par": ""}
    comp.parameter_types = {"new_par1": "double",
                            "new_par2": "int",
                            "this_par": "",
                            "that_par": "string"}
    comp.parameter_units = {"new_par1": "m",
                            "new_par2": "AA",
                            "this_par": "",
                            "that_par": "1"}
    comp.line_limit = 117
    comp._freeze()

    return comp


class TestComponent(unittest.TestCase):
    """
    Components are the building blocks used to create an instrument in
    the McStas meta language. They describe spatially seperated parts
    of the neutron scattering instrument. Here the class component is
    tested.
    """

    def test_Component_basic_init(self):
        """
        Testing basic initialization

        """

        comp = Component("test_component", "Arm")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")

    def test_Component_basic_init_defaults(self):
        """
        Testing basic initialization sets the correct defaults
        """

        comp = Component("test_component", "Arm")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [0, 0, 0])
        self.assertEqual(comp.AT_relative, "ABSOLUTE")
        self.assertEqual(comp.ROTATED_data, [0, 0, 0])
        self.assertEqual(comp.ROTATED_relative, "ABSOLUTE")
        self.assertEqual(comp.WHEN, "")
        self.assertEqual(comp.EXTEND, "")
        self.assertEqual(comp.GROUP, "")
        self.assertEqual(comp.JUMP, "")
        self.assertEqual(comp.comment, "")

    def test_Component_init_complex_call(self):
        """
        Testing keywords set attributes correctly
        """

        comp = setup_Component_all_keywords()

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [0.124, 183.9, 157])
        self.assertEqual(comp.AT_relative, "RELATIVE home")
        self.assertEqual(comp.ROTATED_data, [482, 1240.2, 0.185])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE etc")
        self.assertEqual(comp.WHEN, "WHEN (1==2)")
        self.assertEqual(comp.EXTEND, "nscat = 8;\n")
        self.assertEqual(comp.GROUP, "developers")
        self.assertEqual(comp.JUMP, "myself 37")
        self.assertEqual(comp.SPLIT, 7)
        self.assertEqual(comp.comment, "test comment")

    def test_Component_init_complex_call_relative(self):
        """
        Tests the relative keyword overwrites AT_relative and
        ROTATED_relative
        """
        comp = setup_Component_relative()

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [0.124, 183.9, 157])
        self.assertEqual(comp.AT_relative, "RELATIVE source")
        self.assertEqual(comp.ROTATED_data, [482, 1240.2, 0.185])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE source")
        self.assertEqual(comp.WHEN, "WHEN (1==2)")
        self.assertEqual(comp.EXTEND, "nscat = 8;\n")
        self.assertEqual(comp.GROUP, "developers")
        self.assertEqual(comp.JUMP, "myself 37")
        self.assertEqual(comp.SPLIT, 7)
        self.assertEqual(comp.comment, "test comment")

    def test_Component_basic_init_set_AT(self):
        """
        Testing set_AT method
        """
        comp = Component("test_component", "Arm")

        comp.set_AT([12.124, 214.0, 2], RELATIVE="monochromator")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [12.124, 214.0, 2])
        self.assertEqual(comp.AT_relative, "RELATIVE monochromator")

    def test_Component_freeze(self):
        """
        Testing frozen Component cant have new attributes, and that
        _unfreeze / _freeze works correctly.
        """
        comp = Component("test_component", "Arm")

        with self.assertRaises(AttributeError):
            comp.new_parameter = 5

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")

        comp._unfreeze()
        comp.new_parameter = 5

        self.assertEqual(comp.new_parameter, 5)

        comp._freeze()
        with self.assertRaises(AttributeError):
            comp.another_parameter = 5

    def test_Component_basic_init_set_AT_Component(self):
        """
        Testing set_AT method using Component object and method
        """

        prev_component = Component("relative_base", "Arm")
        comp = Component("test_component", "Arm")

        comp.set_AT([12.124, 214.0, 2], RELATIVE=prev_component)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [12.124, 214.0, 2])
        self.assertEqual(comp.AT_relative, "RELATIVE relative_base")

    def test_Component_basic_init_set_AT_Component_keyword(self):
        """
        Testing set_AT method using Component object and keyword argument
        """

        prev_component = Component("relative_base", "Arm")
        comp = Component("test_component", "Arm",
                         AT=[1, 2, 3.0], AT_RELATIVE=prev_component)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [1, 2, 3.0])
        self.assertEqual(comp.AT_relative, "RELATIVE relative_base")

    def test_Component_basic_init_set_ROTATED(self):
        """
        Testing set_ROTATED method med relative as string
        """

        comp = Component("test_component", "Arm")

        comp.set_ROTATED([1204.8, 8490.1, 129], RELATIVE="analyzer")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.ROTATED_data, [1204.8, 8490.1, 129])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE analyzer")

    def test_Component_basic_init_set_ROTATED_Component(self):
        """
        Testing set_ROTATED method with relative as Component object
        """

        prev_component = Component("relative_base", "Arm")
        comp = Component("test_component", "Arm")

        comp.set_ROTATED([1204.8, 8490.1, 129], RELATIVE=prev_component)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.ROTATED_data, [1204.8, 8490.1, 129])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE relative_base")

    def test_Component_basic_init_set_ROTATED_Component_keyword(self):
        """
        Testing setting ROTATION with keyword and Component object input
        """

        prev_component = Component("relative_base", "Arm")
        comp = Component("test_component", "Arm",
                         ROTATED=[1, 2, 3.0], ROTATED_RELATIVE=prev_component)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.ROTATED_data, [1, 2, 3.0])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE relative_base")

    def test_Component_basic_init_set_RELATIVE(self):
        """
        Testing set_RELATIVE method with string
        """

        comp = Component("test_component", "Arm")

        comp.set_RELATIVE("sample")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_relative, "RELATIVE sample")
        self.assertEqual(comp.ROTATED_relative, "RELATIVE sample")

    def test_Component_basic_object_ref_init_set_RELATIVE(self):
        """
        Testing set_RELATIVE method with Component object input
        """

        prev_component = Component("relative_base", "Arm")
        comp = Component("test_component", "Arm")

        comp.set_RELATIVE(prev_component)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_relative, "RELATIVE relative_base")
        self.assertEqual(comp.ROTATED_relative, "RELATIVE relative_base")

    def test_component_basic_init_set_parameters(self):
        """
        Testing set_parameters method. Need to set some attribute
        parameters manually to test this.
        """

        comp = Component("test_component", "Arm")

        # Need to add some parameters to this bare component
        # Parameters are usually added by McStas_Instr
        comp._unfreeze()
        comp.new_par1 = 1
        comp.new_par2 = 3
        comp.this_par = 1492.2

        comp.set_parameters({"new_par1": 37.0,
                             "new_par2": 12.0,
                             "this_par": 1})

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.new_par1, 37.0)
        self.assertEqual(comp.new_par2, 12.0)
        self.assertEqual(comp.this_par, 1)

        with self.assertRaises(NameError):
            comp.set_parameters({"new_par3": 37.0})

    def test_Component_basic_init_set_WHEN(self):
        """
        Testing WHEN method
        """

        comp = Component("test_component", "Arm")

        comp.set_WHEN("1 != 2")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.WHEN, "WHEN (1 != 2)")

    def test_Component_basic_init_set_GROUP(self):
        """
        Testing set_GROUP method
        """

        comp = Component("test_component", "Arm")

        comp.set_GROUP("test group")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.GROUP, "test group")

    def test_Component_basic_init_set_JUMP(self):
        """
        Testing set_JUMP method
        """

        comp = Component("test_component", "Arm")

        comp.set_JUMP("test jump")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.JUMP, "test jump")

    def test_Component_basic_init_set_SPLIT(self):
        """
        Testing set_SPLIT method
        """

        comp = Component("test_component", "Arm")

        comp.set_SPLIT(500)

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.SPLIT, 500)

    def test_Component_basic_init_set_EXTEND(self):
        """
        Testing set_EXTEND method
        """

        comp = Component("test_component", "Arm")

        comp.append_EXTEND("test code")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.EXTEND, "test code\n")

        comp.append_EXTEND("new code")

        self.assertEqual(comp.EXTEND, "test code\nnew code\n")

    def test_Component_basic_init_set_comment(self):
        """
        Testing set_comment method
        """
        comp = Component("test_component", "Arm")

        comp.set_comment("test comment")

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.comment, "test comment")

    def test_Component_basic_new_attribute_error(self):
        """
        The Component class is frozen after initialize in order to
        prevent the user accidentilly misspelling an attribute name,
        or at least be able to report an error when they do so.
        """

        comp = Component("test_component", "Arm")
        with self.assertRaises(AttributeError):
            comp.new_attribute = 1

        # If unfreeze does not work, this would cause an error
        comp._unfreeze()
        comp.new_attribute = 1

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_to_file_simple(self, mock_f):
        """
        Testing that a Component can be written to file with the
        expected output. Here with simple input.
        """

        comp = Component("test_component", "Arm")

        comp._unfreeze()
        # Need to set up attribute parameters
        # Also need to categorize them as when created
        comp.parameter_names = []
        comp.parameter_defaults = {}
        comp.parameter_types = {}
        comp._freeze()

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call("COMPONENT test_component = Arm("),
                           my_call(")\n"),
                           my_call("AT (0,0,0)"),
                           my_call(" ABSOLUTE\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_to_file_simple_search(self, mock_f):
        """
        Testing that a Component can be written to file with the
        expected output. Here with simple input and search.
        """

        comp = Component("test_component", "Arm")
        comp.add_search("A search_statement")
        comp.add_search("Another search_statement", SHELL=True)
        comp.add_search('"One with double quotes"')

        comp._unfreeze()
        # Need to set up attribute parameters
        # Also need to categorize them as when created
        comp.parameter_names = []
        comp.parameter_defaults = {}
        comp.parameter_types = {}
        comp._freeze()

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call('SEARCH "A search_statement"\n'),
                           my_call('SEARCH SHELL "Another search_statement"\n'),
                           my_call('SEARCH "One with double quotes"\n'),
                           my_call("COMPONENT test_component = Arm("),
                           my_call(")\n"),
                           my_call("AT (0,0,0)"),
                           my_call(" ABSOLUTE\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_to_file_include(self, mock_f):
        """
        Testing that a Component can be written to file with the
        expected output. Here with simple input.
        """
        comp = Component("test_component", "Arm",
                         c_code_before="%include \"test.instr\"")

        comp.set_c_code_after("%include \"after.instr\"")

        comp._unfreeze()
        # Need to set up attribute parameters
        # Also need to categorize them as when created
        comp.parameter_names = []
        comp.parameter_defaults = {}
        comp.parameter_types = {}
        comp._freeze()

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call("%include \"test.instr\" // From"
                                   + " component named test_component\n"),
                           my_call("\n"),
                           my_call("COMPONENT test_component = Arm("),
                           my_call(")\n"),
                           my_call("AT (0,0,0)"),
                           my_call(" ABSOLUTE\n"),
                           my_call("\n"),
                           my_call("%include \"after.instr\" // From"
                                   + " component named test_component\n"),
                           my_call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_to_file_complex(self, mock_f):
        """
        Testing that a Component can be written to file with the
        expected output. Here with complex input.
        """

        comp = setup_Component_with_parameters()

        # This setup has a required parameter.
        # If this parameter is not set, an error should be returned,
        # this will be tested in the next test.

        comp.new_par3 = "1.25"

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call("SPLIT 7 "),
                           my_call("COMPONENT test_component = Arm("),
                           my_call("\n"),
                           my_call(" new_par1 = 1.5"),
                           my_call(","),
                           my_call(" new_par2 = 3"),
                           my_call(","),
                           my_call("\n"),
                           my_call(" new_par3 = 1.25"),
                           my_call(","),
                           my_call(" this_par = test_val"),
                           my_call(","),
                           my_call("\n"),
                           my_call(" that_par = \"txt_string\""),
                           my_call(")\n"),
                           my_call("WHEN (1==2)\n"),
                           my_call("AT (0.124,183.9,157)"),
                           my_call(" RELATIVE home\n"),
                           my_call("ROTATED (482,1240.2,0.185)"),
                           my_call(" RELATIVE etc\n"),
                           my_call("GROUP developers\n"),
                           my_call("EXTEND %{\n"),
                           my_call("nscat = 8;\n"),
                           my_call("%}\n"),
                           my_call("JUMP myself 37\n"),
                           my_call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_to_file_complex_SPLIT_string(self, mock_f):
        """
        Testing that a Component can be written to file with the
        expected output. Here with complex input, and a string as
        given for split.
        """

        comp = setup_Component_with_parameters()
        comp.set_SPLIT("VAR")

        # This setup has a required parameter.
        # If this parameter is not set, an error should be returned,
        # this will be tested in the next test.

        comp.new_par3 = "1.25"

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call("SPLIT VAR "),
                           my_call("COMPONENT test_component = Arm("),
                           my_call("\n"),
                           my_call(" new_par1 = 1.5"),
                           my_call(","),
                           my_call(" new_par2 = 3"),
                           my_call(","),
                           my_call("\n"),
                           my_call(" new_par3 = 1.25"),
                           my_call(","),
                           my_call(" this_par = test_val"),
                           my_call(","),
                           my_call("\n"),
                           my_call(" that_par = \"txt_string\""),
                           my_call(")\n"),
                           my_call("WHEN (1==2)\n"),
                           my_call("AT (0.124,183.9,157)"),
                           my_call(" RELATIVE home\n"),
                           my_call("ROTATED (482,1240.2,0.185)"),
                           my_call(" RELATIVE etc\n"),
                           my_call("GROUP developers\n"),
                           my_call("EXTEND %{\n"),
                           my_call("nscat = 8;\n"),
                           my_call("%}\n"),
                           my_call("JUMP myself 37\n"),
                           my_call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_Component_write_Component_required_parameter_error(self, mock_f):
        """
        Test an error occurs if the Component is asked to write to disk
        without a required parameter.
        """

        comp = setup_Component_with_parameters()

        # new_par3 unset and has no default so an error will be raised

        with self.assertRaises(NameError):
            with mock_f('test.txt', 'w') as m_fo:
                comp.write_component(m_fo)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_Component_print_long(self, mock_stdout):
        """
        Test print to console on the current state of the Component.
        Using a mocked stdout to catch the print statements.
        """

        comp = setup_Component_with_parameters()
        comp.append_EXTEND("second extend line;")

        comp.print_long()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0], "// test comment")
        self.assertEqual(output[1], "SPLIT 7 COMPONENT test_component = Arm(")

        par_name = bcolors.BOLD + "new_par1" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "1.5" + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[2], "  " + par_name + " = " + value + ", // [m]")

        par_name = bcolors.BOLD + "new_par2" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "3" + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[3], "  " + par_name + " = " + value + ", // [AA]")

        par_name = bcolors.BOLD + "new_par3" + bcolors.ENDC
        warning = (bcolors.FAIL
                   + " : Required parameter not yet specified"
                   + bcolors.ENDC)
        self.assertEqual(output[4], "  " + par_name + warning)

        par_name = bcolors.BOLD + "this_par" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "test_val" + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[5], "  " + par_name + " = " + value + ", // []")

        par_name = bcolors.BOLD + "that_par" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "\"txt_string\"" + bcolors.ENDC + bcolors.ENDC)
        # No comma after last parameter
        self.assertEqual(output[6], "  " + par_name + " = " + value + " // [1]")

        self.assertEqual(output[7], ") WHEN (1==2)")

        self.assertEqual(output[8], "AT (0.124, 183.9, 157) RELATIVE home")
        self.assertEqual(output[9],
                         "ROTATED (482, 1240.2, 0.185) RELATIVE etc")
        self.assertEqual(output[10], "GROUP developers")
        self.assertEqual(output[11], "EXTEND %{")
        self.assertEqual(output[12], "nscat = 8;")
        self.assertEqual(output[13], "second extend line;")
        self.assertEqual(output[14], "%}")
        self.assertEqual(output[15], "JUMP myself 37")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_Component_print_short_standard(self, mock_stdout):
        """
        Test print_short that prints name, type and location of the
        Component to the console.
        """

        comp = setup_Component_with_parameters()

        comp.print_short()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        expected = ("test_component = Arm "
                    + "\tAT [0.124, 183.9, 157] RELATIVE home "
                    + "ROTATED [482, 1240.2, 0.185] RELATIVE etc")

        self.assertEqual(output[0], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_Component_print_short_longest_name(self, mock_stdout):
        """
        Test print_short that prints name, type and location of the
        Component to the console. Here with specified longest_name.
        """

        comp = setup_Component_with_parameters()

        comp.print_short(longest_name=15)

        output = mock_stdout.getvalue()
        output = output.split("\n")

        expected = ("test_component    Arm "
                    + "\tAT [0.124, 183.9, 157] RELATIVE home "
                    + "ROTATED [482, 1240.2, 0.185] RELATIVE etc")

        self.assertEqual(output[0], expected)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_Component_show_parameters(self, mock_stdout):
        """
        Test print_short that prints name, type and location of the
        Component to the console. An extra parameter was added.
        This test also checks for specific formatting.
        """

        comp = setup_Component_with_parameters()

        comp._unfreeze()

        # This is now not set by the user, but has default
        # This results in different formatting in show_parameters
        comp.new_par2 = None

        comp._freeze()

        comp.show_parameters()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0], " ___ Help Arm " + "_"*103)

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

        self.assertEqual(output[1], legend)

        par_name = bcolors.BOLD + "new_par1" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "1.5" + bcolors.ENDC + bcolors.ENDC)
        comment = "// This is important"
        self.assertEqual(output[2],
                         par_name + " = " + value + " [m] " + comment)

        par_name = bcolors.BOLD + "new_par2" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKBLUE
                 + "9" + bcolors.ENDC + bcolors.ENDC)
        comment = "// This is less important"
        self.assertEqual(output[3],
                         par_name + " = " + value + " [AA] " + comment)

        par_name = (bcolors.UNDERLINE + bcolors.BOLD
                    + "new_par3"
                    + bcolors.ENDC + bcolors.ENDC)
        self.assertEqual(output[4], par_name)

        par_name = bcolors.BOLD + "this_par" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "test_val" + bcolors.ENDC + bcolors.ENDC)
        comment = "// !"
        self.assertEqual(output[5],
                         par_name + " = " + value + " [] " + comment)

        par_name = bcolors.BOLD + "that_par" + bcolors.ENDC
        value = (bcolors.BOLD + bcolors.OKGREEN
                 + "\"txt_string\"" + bcolors.ENDC + bcolors.ENDC)
        comment = ""
        self.assertEqual(output[6],
                         par_name + " = " + value + " [1]" + comment)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_Component_show_parameters_simple(self, mock_stdout):
        """
        Test print_short that prints name, type and location of the
        Component to the console.  No formatting used in simple
        version.
        """

        comp = setup_Component_with_parameters()

        comp._unfreeze()

        # This is now not set by the user, but has default
        # This results in different formatting in show_parameters
        comp.new_par2 = None

        comp._freeze()

        comp.show_parameters_simple()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(output[0], "---- Help Arm -----")

        par_name = "new_par1"
        value = "1.5"
        comment = "// This is important"
        self.assertEqual(output[1],
                         par_name + " = " + value + " [m] " + comment)

        par_name = "new_par2"
        value = "9"
        comment = "// This is less important"
        self.assertEqual(output[2],
                         par_name + " = " + value + " [AA] " + comment)

        par_name = "new_par3"
        self.assertEqual(output[3], par_name)

        par_name = "this_par"
        value = "test_val"
        comment = "// !"
        self.assertEqual(output[4],
                         par_name + " = " + value + " [] " + comment)

        par_name = "that_par"
        value = "\"txt_string\""
        comment = ""
        self.assertEqual(output[5],
                         par_name + " = " + value + " [1]" + comment)

    def test_component_error_check(self):

        comp = setup_Component_with_parameters()

        # Currently no ilegal parameters
        comp.check_parameters([])

        # Introduce illegal parameter
        comp.new_par1 = "wrong"
        with self.assertRaises(McStasError):
            comp.check_parameters([])

        # Check no error is raised when on whitelist
        comp.check_parameters(["wrong"])


if __name__ == '__main__':
    unittest.main()
