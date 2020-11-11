import os
import io
import unittest
import unittest.mock

from mcstasscript.helper.component_reader import ComponentInfo
from mcstasscript.helper.component_reader import ComponentReader


def setup_component_reader():
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    component_reader = ComponentReader(mcstas_path=dummy_path)

    os.chdir(current_work_dir)  # Reset work directory

    return component_reader

def setup_component_reader_input_path():
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
    input_path = os.path.join(THIS_DIR, "test_input_folder")

    current_work_dir = os.getcwd()
    os.chdir(THIS_DIR)  # Set work directory to test folder

    component_reader = ComponentReader(mcstas_path=dummy_path,
                                       input_path=input_path)

    os.chdir(current_work_dir)  # Reset work directory

    return component_reader


class TestComponentReader(unittest.TestCase):
    """
    Testing the ComponenReader class. As this class reads information
    from McStas, a dummy McStas install is made in the test folder to
    avoid the test results changeing with updates of McStas.
    """

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_overwrite_message(self, mock_stdout):
        """
        Test that ComponentReader reports overwritten components
        """

        component_reader = setup_component_reader()

        message = ("The following components are found in the work_directory "
                   + "/ input_path:\n     test_for_reading.comp\n"
                   + "These definitions will be used instead of the "
                   + "installed versions.\n")

        self.assertEqual(mock_stdout.getvalue(), message)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_overwrite_message_input(self, mock_stdout):
        """
        Test that ComponentReader reports overwritten components
        """

        component_reader = setup_component_reader_input_path()

        message = ("The following components are found in the work_directory "
                   + "/ input_path:\n     test_for_structure.comp\n"
                   + "These definitions will be used instead of the "
                   + "installed versions.\n")

        self.assertEqual(mock_stdout.getvalue(), message)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_filenames(self, mock_stdout):
        """
        Test that ComponentReader initializes component names correctly
        """

        component_reader = setup_component_reader()

        n_components_found = len(component_reader.component_path)
        self.assertEqual(n_components_found, 3)
        self.assertIn("test_for_reading", component_reader.component_path)
        self.assertIn("test_for_structure", component_reader.component_path)
        self.assertIn("test_for_structure2", component_reader.component_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_component_paths(self, mock_stdout):
        """
        Test that ComponentReader stores correct absolute paths to
        the components found in the McStas installation
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")

        component_reader = setup_component_reader()

        n_components_found = len(component_reader.component_path)
        self.assertEqual(n_components_found, 3)

        expected_path = os.path.join(THIS_DIR, "test_for_reading.comp")
        self.assertIn("test_for_reading", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_reading"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_reading"],
                         "Work directory")

        expected_path = os.path.join(dummy_path, "misc",
                                     "test_for_structure.comp")
        self.assertIn("test_for_structure", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_structure"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_structure"],
                         "misc")

        expected_path = os.path.join(dummy_path, "sources",
                                     "test_for_structure2.comp")
        self.assertIn("test_for_structure2", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_structure2"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_structure2"],
                         "sources")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_component_paths_input(self, mock_stdout):
        """
        Test that ComponentReader stores correct absolute paths to
        the components found in the McStas installation.
        This version uses custom input_path
        """

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
        input_path = os.path.join(THIS_DIR, "test_input_folder")

        component_reader = setup_component_reader_input_path()

        n_components_found = len(component_reader.component_path)
        self.assertEqual(n_components_found, 3)

        expected_path = os.path.join(dummy_path, "misc",
                                     "test_for_reading.comp")
        self.assertIn("test_for_reading", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_reading"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_reading"],
                         "misc")

        expected_path = os.path.join(input_path, "test_for_structure.comp")
        self.assertIn("test_for_structure", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_structure"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_structure"],
                         "Work directory")


        expected_path = os.path.join(dummy_path, "sources",
                                     "test_for_structure2.comp")
        self.assertIn("test_for_structure2", component_reader.component_path)
        self.assertEqual(component_reader.component_path["test_for_structure2"],
                         expected_path)
        self.assertEqual(component_reader.component_category["test_for_structure2"],
                         "sources")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_init_categories(self, mock_stdout):
        """
        Test that ComponentReader initializes categories correctly
        """

        component_reader = setup_component_reader()

        n_categories_found = len(component_reader.component_category)
        self.assertEqual(n_categories_found, 3)
        """
        Categories stored in a dict, so n_categories is the same as the
        number of components read. Here it happens to be the number of
        categories as well because of the dummy installation.
        """
        category = component_reader.component_category["test_for_reading"]
        self.assertEqual(category, "Work directory")
        category = component_reader.component_category["test_for_structure"]
        self.assertEqual(category, "misc")
        category = component_reader.component_category["test_for_structure2"]
        self.assertEqual(category, "sources")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_show_categories(self, mock_stdout):
        """
        This method prints to console, check it prints the categories
        in the dummy installation correctly.

        """
        component_reader = setup_component_reader()

        component_reader.show_categories()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(len(output), 7)
        self.assertIn(" sources", output)
        self.assertIn(" Work directory", output)
        self.assertIn(" misc", output)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_show_categories_ordered(self, mock_stdout):
        """
        Check that the print to console is ordered as usual. This test
        may be implementation dependent as python dictionaries are not
        ordered.

        """

        component_reader = setup_component_reader()

        component_reader.show_categories()

        output = mock_stdout.getvalue()
        output = output.split("\n")

        # Ignoring message about overwritten components, starting from 3
        self.assertEqual(output[3], " sources")
        self.assertEqual(output[4], " Work directory")
        self.assertEqual(output[5], " misc")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_show_components_short(self, mock_stdout):
        """
        Here we attempt to show components in the misc category.  In
        the dummy install, there are two components in this folder, but
        one of these is overwritten by the version in the current
        work directory.

        """

        component_reader = setup_component_reader()

        component_reader.show_components_in_category("misc", line_length=100)

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(len(output), 5)
        self.assertIn(" test_for_structure", output)
        # Check overwritten component is not in the output
        self.assertNotIn(" test_for_reading", output)

    """
    # This test not as important, but could be finished later
    @unittest.mock.patch("sys.stdout", new_callable = io.StringIO)
    def test_ComponentReader_show_components_long(self, mock_stdout):

        component_reader = setup_component_reader()

        #  Add elements directly to component_readers library
        # generate list
        # add list

        #component_reader.component_category[]

        component_reader.show_components_in_category("misc", line_length=100)

        output = mock_stdout.getvalue()
        output = output.split("\n")

        self.assertEqual(len(output), 3)
        self.assertIn(" test_for_structure", output)
    """

    # test load_all_components
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_load_all_components(self, mock_stdout):
        """
        Load all components in the dummy install, but only one has any
        content.  The method is currently not necessary, as components
        are now loaded individually when needed.

        """

        component_reader = setup_component_reader()

        CompInfo_dict = component_reader.load_all_components()

        comp_name = "test_for_reading"
        name = CompInfo_dict[comp_name].name
        self.assertEqual(name, comp_name)

        parameter_names = CompInfo_dict[comp_name].parameter_names
        self.assertIn("target_index", parameter_names)
        parameter_types = CompInfo_dict[comp_name].parameter_types
        self.assertIn("target_index", parameter_types)
        parameter_defaults = CompInfo_dict[comp_name].parameter_defaults
        self.assertIn("target_index", parameter_defaults)

        type_str = CompInfo_dict[comp_name].parameter_types["target_index"]
        self.assertEqual(type_str, "int")

        comp_name = "test_for_structure"
        name = CompInfo_dict[comp_name].name
        self.assertEqual(name, comp_name)
        # test_for_structure is an empty file, so no conentet to check

        comp_name = "test_for_structure2"
        name = CompInfo_dict[comp_name].name
        self.assertEqual(name, comp_name)
        # test_for_structure2 is an empty file, so no conentet to check

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_name_error(self, mock_stdout):
        """
        read_name should throw an error when searching for a component
        that is not present in the installation.
        """

        component_reader = setup_component_reader()

        with self.assertRaises(NameError):
            CompInfo = component_reader.read_name("no_such_comp")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_name_success(self, mock_stdout):
        """
        Read component simply calls read_component_file, but here
        the output is checked against what is in the dummy file.

        """

        component_reader = setup_component_reader()

        CompInfo = component_reader.read_name("test_for_reading")

        self.assertEqual(CompInfo.name, "test_for_reading")
        self.assertEqual(CompInfo.category, "Work directory")
        self.assertIn("dist", CompInfo.parameter_names)
        self.assertIn("dist", CompInfo.parameter_defaults)
        self.assertIn("dist", CompInfo.parameter_types)
        self.assertEqual(CompInfo.parameter_types["dist"], "double")
        self.assertIn("dist", CompInfo.parameter_comments)
        self.assertIn("dist", CompInfo.parameter_units)
        self.assertEqual(CompInfo.parameter_units["dist"], "m")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_find_components_names(self, mock_stdout):
        """
        Test that ComponentReader initializes component names correctly
        """

        component_reader = setup_component_reader()

        component_reader.component_path = {}
        component_reader.component_category = {}

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas", "misc")
        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder
        component_reader._find_components(dummy_path)
        os.chdir(current_work_dir)  # Return to original work directory

        n_components_found = len(component_reader.component_path)
        self.assertEqual(n_components_found, 2)
        self.assertIn("test_for_reading", component_reader.component_path)
        self.assertIn("test_for_structure", component_reader.component_path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_find_components_categories(self, mock_stdout):
        """
        Test that ComponentReader initializes component categories correctly
        """

        component_reader = setup_component_reader()

        component_reader.component_path = {}
        component_reader.component_category = {}

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        dummy_path = os.path.join(THIS_DIR, "dummy_mcstas", "misc")
        current_work_dir = os.getcwd()
        os.chdir(THIS_DIR)  # Set work directory to test folder
        component_reader._find_components(dummy_path)
        os.chdir(current_work_dir)  # Return to original work directory

        n_categories_found = len(component_reader.component_category)
        self.assertEqual(n_categories_found, 2)

        category = component_reader.component_category["test_for_reading"]
        self.assertEqual(category, "misc")
        category = component_reader.component_category["test_for_structure"]
        self.assertEqual(category, "misc")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_component_category(self, mock_stdout):
        """
        Check that the correct category is returned.

        Can't run this test with overwritten component test_for_reading.
        read_component will report tests as category, but this is
        overwritten by read_name in normal use.
        """
        component_reader = setup_component_reader()

        path_for_test = component_reader.component_path["test_for_structure"]
        CompInfo = component_reader.read_component_file(path_for_test)

        exp_cat = component_reader.component_category["test_for_structure"]
        self.assertEqual(CompInfo.category, exp_cat)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_component_standard(self, mock_stdout):
        """
        Test that a normal parameter is read correctly when reading a
        component file.
        Has default, is double type, has comment, has unit
        """

        component_reader = setup_component_reader()

        path_for_test = component_reader.component_path["test_for_reading"]
        CompInfo = component_reader.read_component_file(path_for_test)

        self.assertIn("xwidth", CompInfo.parameter_names)

        self.assertIn("xwidth", CompInfo.parameter_defaults)
        self.assertEqual(CompInfo.parameter_defaults["xwidth"], 0.0)

        self.assertIn("xwidth", CompInfo.parameter_types)
        self.assertEqual(CompInfo.parameter_types["xwidth"], "double")

        self.assertIn("xwidth", CompInfo.parameter_comments)
        comment = "Width of rectangle test comment"
        self.assertEqual(CompInfo.parameter_comments["xwidth"], comment)

        self.assertIn("xwidth", CompInfo.parameter_units)
        self.assertEqual(CompInfo.parameter_units["xwidth"], "m")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_component_required(self, mock_stdout):
        """
        Test that a required parameter is read correctly when reading a
        component file.
        Has no default, is double type, has no comment, has no unit
        """

        component_reader = setup_component_reader()

        path_for_test = component_reader.component_path["test_for_reading"]
        CompInfo = component_reader.read_component_file(path_for_test)

        self.assertIn("gauss", CompInfo.parameter_names)

        self.assertIn("gauss", CompInfo.parameter_defaults)
        self.assertIsNone(CompInfo.parameter_defaults["gauss"])

        self.assertIn("gauss", CompInfo.parameter_types)
        self.assertEqual(CompInfo.parameter_types["gauss"], "double")

        self.assertNotIn("gauss", CompInfo.parameter_comments)

        self.assertNotIn("gauss", CompInfo.parameter_units)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_component_int(self, mock_stdout):
        """
        Test that a integer parameter is read correctly when reading a
        component file.
        Has default, is int type (comments and unit checked already)
        """

        component_reader = setup_component_reader()

        path_for_test = component_reader.component_path["test_for_reading"]
        CompInfo = component_reader.read_component_file(path_for_test)

        self.assertIn("flux", CompInfo.parameter_names)

        self.assertIn("flux", CompInfo.parameter_defaults)
        self.assertEqual(CompInfo.parameter_defaults["flux"], 1)

        self.assertIn("flux", CompInfo.parameter_types)
        self.assertEqual(CompInfo.parameter_types["flux"], "int")

        self.assertIn("flux", CompInfo.parameter_comments)
        # Have already tested comments are read

        self.assertIn("flux", CompInfo.parameter_units)
        # Have already tested units are read

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_read_component_string(self, mock_stdout):
        """
        Test that a string parameter is read correctly when reading a
        component file.
        Has no default, is string type (comments and unit checked already)
        """

        component_reader = setup_component_reader()

        path_for_test = component_reader.component_path["test_for_reading"]
        CompInfo = component_reader.read_component_file(path_for_test)

        self.assertIn("test_string", CompInfo.parameter_names)

        self.assertIn("test_string", CompInfo.parameter_defaults)
        self.assertIsNone(CompInfo.parameter_defaults["test_string"])

        self.assertIn("test_string", CompInfo.parameter_types)
        self.assertEqual(CompInfo.parameter_types["test_string"], "string")

        self.assertNotIn("test_string", CompInfo.parameter_comments)
        # Have already tested comments are read

        self.assertNotIn("test_string", CompInfo.parameter_units)
        # Have already tested units are read

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_line_start_long(self, mock_stdout):
        """
        Helper function that should return true when certain string is
        the start of another string.

        """

        component_reader = setup_component_reader()

        test_string = "monkey wants banana"

        return_val = component_reader.line_starts_with(test_string, "mo")
        self.assertIsInstance(return_val, bool)
        self.assertTrue(return_val)

        return_val = component_reader.line_starts_with(test_string, "on")
        self.assertIsInstance(return_val, bool)
        self.assertFalse(return_val)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_ComponentReader_line_start_short(self, mock_stdout):
        """
        Helper function that should return true when certain string is
        the start of another string. Here checked with short test_string

        """

        component_reader = setup_component_reader()

        test_string = "m"

        return_val = component_reader.line_starts_with(test_string, "m")
        self.assertIsInstance(return_val, bool)
        self.assertTrue(return_val)

        return_val = component_reader.line_starts_with(test_string, "mo")
        self.assertIsInstance(return_val, bool)
        self.assertFalse(return_val)

        return_val = component_reader.line_starts_with(test_string, "on")
        self.assertIsInstance(return_val, bool)
        self.assertFalse(return_val)


if __name__ == '__main__':
    unittest.main()
