import unittest
import unittest.mock
import io

from mcstasscript.jb_interface.widget_helpers import HiddenPrints
from mcstasscript.jb_interface.widget_helpers import parameter_has_default
from mcstasscript.jb_interface.widget_helpers import get_parameter_default
from mcstasscript.helper.mcstas_objects import provide_parameter


class TestWidgetHelpers(unittest.TestCase):
    """
    Tests of widget helpers
    """

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_HiddenPrints(self, mock_stdout):
        """
        Checks HiddenPrints suppress output to stdout
        """

        print("test")

        output = mock_stdout.getvalue()
        self.assertEqual(output, "test\n")

        with HiddenPrints():
            print("Hello")

        output = mock_stdout.getvalue()
        self.assertEqual(output, "test\n")

    def test_parameter_has_default_false(self):
        """
        Check for parameter that does not have default, should be false
        """

        par = provide_parameter("test")
        self.assertFalse(parameter_has_default(par))

    def test_parameter_has_default_true(self):
        """
        Check for parameter that has default, should be true
        """

        par = provide_parameter("test", value=8)
        self.assertTrue(parameter_has_default(par))

    def test_get_parameter_default_string(self):
        """
        Get the default for string parameter
        """

        par = provide_parameter("string", "test", value="variable")
        self.assertEqual(get_parameter_default(par), "variable")

    def test_get_parameter_default_double_specified(self):
        """
        Get the default for specified double parameter
        """

        par = provide_parameter("double", "test", value=5.5)
        self.assertEqual(get_parameter_default(par), 5.5)

    def test_get_parameter_default_double(self):
        """
        Get the default for parameter that was double by default
        """

        par = provide_parameter("test", value=5.7)
        self.assertEqual(get_parameter_default(par), 5.7)

    def test_get_parameter_default_int(self):
        """
        Get default value from integer value, should be rounded
        """

        par = provide_parameter("int", "test", value=5.7)
        self.assertEqual(get_parameter_default(par), 5)


