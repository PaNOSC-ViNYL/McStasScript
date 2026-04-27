import unittest

from mcstasscript.helper.formatting import is_legal_parameter
from mcstasscript.helper.formatting import is_legal_filename


class TestFormatting(unittest.TestCase):
    """
    Tests the formatting functions
    """
    def test_is_legal_parameter_simple(self):
        """
        Check a legal parameter is legal
        """
        test_name = "test_parameter_name1"
        self.assertTrue(is_legal_parameter(test_name))

    def test_is_legal_parameter_reject_space(self):
        """
        A space should make the parameter name illegal
        """
        test_name = "test_parameter name"
        self.assertFalse(is_legal_parameter(test_name))

    def test_is_legal_parameter_reject_first_number(self):
        """
        The first character being a number is ilegal
        """
        test_name = "2est_parameter_name"
        self.assertFalse(is_legal_parameter(test_name))

    def test_is_legal_parameter_reject_empty(self):
        """
        An empty string should not be a legal name
        """
        test_name = ""
        self.assertFalse(is_legal_parameter(test_name))

    def test_is_legal_filename_simple(self):
        """
        Test with a legal filename
        """
        test_name = "test_instrument1"
        self.assertTrue(is_legal_filename(test_name))

    def test_is_legal_filename_reject_forward_dash(self):
        """
        A dash should make the filename illegal
        """
        test_name = "test/instrument"
        self.assertFalse(is_legal_filename(test_name))

    def test_is_legal_filename_reject_backwards_dash(self):
        """
        A backwards dash should make the filename illegal
        """
        test_name = "test\\instrument"
        self.assertFalse(is_legal_filename(test_name))

    def test_is_legal_filename_rekect_space(self):
        """
        A space should make the filename illegal
        """
        test_name = "test instrument"
        self.assertFalse(is_legal_filename(test_name))


if __name__ == '__main__':
    unittest.main()
