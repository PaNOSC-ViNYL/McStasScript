import io
import builtins
import unittest
import unittest.mock

from mcstasscript.helper.mcstas_objects import parameter_variable


class Test_parameter_variable(unittest.TestCase):
    """
    Tests the parameter_variable class that holds an input parameter
    for the instrument.

    """

    def test_parameter_variable_init_basic(self):
        """
        Smallest possible initialization
        """

        par = parameter_variable("test")
        self.assertEqual(par.name, "test")

    def test_parameter_variable_init_basic_type(self):
        """
        Initialization with a type
        """

        par = parameter_variable("double", "test")

        self.assertEqual(par.name, "test")
        self.assertEqual(par.type, "double ")  # space for easier writing

    def test_parameter_variable_init_basic_type_value(self):
        """
        Initialization with type and value
        """

        par = parameter_variable("double", "test", value=518)

        self.assertEqual(par.name, "test")
        self.assertEqual(par.type, "double ")  # space for easier writing
        self.assertEqual(par.value, 518)

    def test_parameter_variable_init_basic_type_value_comment(self):
        """
        Initialization with type, value and comment
        """

        par = parameter_variable("double", "test",
                                 value=518, comment="test comment /")

        self.assertEqual(par.name, "test")
        self.assertEqual(par.type, "double ")  # space for easier writing
        self.assertEqual(par.value, 518)
        self.assertEqual(par.comment, "// test comment /")

    def test_parameter_variable_init_basic_value_comment(self):
        """
        Initialization with value and comment
        """

        par = parameter_variable("test",
                                 value=518, comment="test comment /")

        self.assertEqual(par.name, "test")
        self.assertEqual(par.type, "")
        self.assertEqual(par.value, 518)
        self.assertEqual(par.comment, "// test comment /")

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_parameter_variable_write_basic(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument parameter section. The write file operation is
        mocked and check using a patch. Here a simple parameter is
        used.
        """

        par = parameter_variable("double", "test")
        with mock_f('test.txt', 'w') as m_fo:
            par.write_parameter(m_fo, "")

        expected_writes = [unittest.mock.call("double test"),
                           unittest.mock.call(""),
                           unittest.mock.call(""),
                           unittest.mock.call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_parameter_variable_write_complex_float(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument parameter section. The write file operation is
        mocked and check using a patch. Here a parameter with a value
        is used. (float value)
        """

        par = parameter_variable("double",
                                 "test",
                                 value=5.4,
                                 comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            par.write_parameter(m_fo, ")")

        expected_writes = [unittest.mock.call("double test"),
                           unittest.mock.call(" = 5.4"),
                           unittest.mock.call(")"),
                           unittest.mock.call("// test comment"),
                           unittest.mock.call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_parameter_variable_write_complex_int(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument parameter section. The write file operation is
        mocked and check using a patch. Here a parameter with a value
        is used. (integer value)
        """

        par = parameter_variable("double",
                                 "test",
                                 value=5,
                                 comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            par.write_parameter(m_fo, ")")

        expected_writes = [unittest.mock.call("double test"),
                           unittest.mock.call(" = 5"),
                           unittest.mock.call(")"),
                           unittest.mock.call("// test comment"),
                           unittest.mock.call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_parameter_variable_write_complex_string(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument parameter section. The write file operation is
        mocked and check using a patch. Here a parameter with a value
        is used. (string value)
        """

        par = parameter_variable("double",
                                 "test",
                                 value="\"Al\"",
                                 comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            par.write_parameter(m_fo, ",")

        expected_writes = [unittest.mock.call("double test"),
                           unittest.mock.call(" = \"Al\""),
                           unittest.mock.call(","),
                           unittest.mock.call("// test comment"),
                           unittest.mock.call("\n")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)


if __name__ == '__main__':
    unittest.main()
