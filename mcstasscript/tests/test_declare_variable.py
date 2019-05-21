import io
import builtins
import unittest
import unittest.mock

from mcstasscript.helper.mcstas_objects import declare_variable


class Test_declare_variable(unittest.TestCase):
    """
    Tests the declare_variable class that holds a declared variable
    that will be written to the McStas declare section.

    """

    def test_declare_variable_init_basic_type(self):
        """
        Initialization with a type
        """

        var = declare_variable("double", "test")

        self.assertEqual(var.name, "test")
        self.assertEqual(var.type, "double")  # space for easier writing

    def test_declare_variable_init_basic_type_value(self):
        """
        Initialization with type and value
        """

        var = declare_variable("double", "test", value=518)

        self.assertEqual(var.name, "test")
        self.assertEqual(var.type, "double")  # space for easier writing
        self.assertEqual(var.value, 518)

    def test_declare_variable_init_basic_type_vector(self):
        """
        Initialization with type and value
        """

        var = declare_variable("double", "test",
                               array=6, value=[1, 2.2, 3, 3.3, 4, 4.4])

        self.assertEqual(var.name, "test")
        self.assertEqual(var.type, "double")  # space for easier writing
        self.assertEqual(var.vector, 6)
        self.assertEqual(var.value, [1, 2.2, 3, 3.3, 4, 4.4])

    def test_declare_variable_init_basic_type_value_comment(self):
        """
        Initialization with type, value and comment
        """

        var = declare_variable("double", "test",
                               value=518, comment="test comment /")

        self.assertEqual(var.name, "test")
        self.assertEqual(var.type, "double")  # Space for easier writing
        self.assertEqual(var.value, 518)
        self.assertEqual(var.comment, " // test comment /")

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_declare_variable_write_basic(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument declare section. The write file operation is
        mocked and check using a patch. Here a simple declare is
        used.
        """

        var = declare_variable("double", "test")
        with mock_f('test.txt', 'w') as m_fo:
            var.write_line(m_fo)

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_called_once_with("double test;")

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_declare_variable_write_complex_float(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument declare section. The write file operation is
        mocked and check using a patch. Here a declare with a value
        is used. (float value)
        """

        var = declare_variable("double",
                               "test",
                               value=5.4,
                               comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            var.write_line(m_fo)

        expected_write = "double test = 5.4; // test comment"

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_called_once_with(expected_write)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_declare_variable_write_complex_int(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument declare section. The write file operation is
        mocked and check using a patch. Here a declare with a value
        is used. (integer value)
        """

        var = declare_variable("double",
                               "test",
                               value=5,
                               comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            var.write_line(m_fo)

        expected_write = "double test = 5; // test comment"

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_called_once_with(expected_write)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_declare_variable_write_simple_array(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument declare section. The write file operation is
        mocked and check using a patch. Here an array is declared.
        """

        var = declare_variable("double",
                               "test",
                               array=29,
                               comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            var.write_line(m_fo)

        expected_write = "double test[29]; // test comment"

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_called_once_with(expected_write)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable=unittest.mock.mock_open)
    def test_declare_variable_write_complex_array(self, mock_f):
        """
        Testing that write to file is correct. Here a line is in a
        instrument declare section. The write file operation is
        mocked and check using a patch. Here an array is decalred and
        populated with the selected values.
        """

        var = declare_variable("double",
                               "test",
                               array=3,
                               value=[5, 4, 3.1],
                               comment="test comment")

        with mock_f('test.txt', 'w') as m_fo:
            var.write_line(m_fo)

        expected_writes = [unittest.mock.call("double test[3] = {"),
                           unittest.mock.call("5,"),
                           unittest.mock.call("4,"),
                           unittest.mock.call("3.1}; // test comment")]

        mock_f.assert_called_with('test.txt', 'w')
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)


if __name__ == '__main__':
    unittest.main()
