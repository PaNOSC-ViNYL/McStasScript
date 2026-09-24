import unittest

from mcstasscript.helper.check_mccode_version import _parse_version


class TestParseVersion(unittest.TestCase):

    def test_stable_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32"), (3, 4, 32))

    def test_suffixed_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32a0"), (3, 4, 32))

    def test_parenthesized_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32 (git)"), (3, 4, 32))

    def test_two_component_version(self):
        self.assertEqual(_parse_version(b"McXtrace version 1.2"), (1, 2, 0))

    def test_suffixed_minor(self):
        self.assertEqual(_parse_version(b"McStas version 3.4b1.32"), (3, 4, 32))


if __name__ == "__main__":
    unittest.main()
