import unittest
from types import SimpleNamespace

from mcstasscript.geometry_viewer.mcdisplay import _format_parameter


class TestMcdisplay(unittest.TestCase):
    def test_format_string_parameter_removes_c_literal_quotes(self):
        parameter = SimpleNamespace(
            name="sample_choice",
            type="string",
            value='"sample_Si"',
        )

        self.assertEqual(_format_parameter(parameter), "sample_choice=sample_Si")

    def test_format_unquoted_string_parameter_unchanged(self):
        parameter = SimpleNamespace(
            name="sample_choice",
            type="string",
            value="sample_Si",
        )

        self.assertEqual(_format_parameter(parameter), "sample_choice=sample_Si")

    def test_format_non_string_parameter_unchanged(self):
        parameter = SimpleNamespace(name="l_min", type="double", value=0.5)

        self.assertEqual(_format_parameter(parameter), "l_min=0.5")

    def test_format_string_parameter_preserves_shell_special_characters(self):
        """String values remain one argv item when shell=False is used."""
        parameter = SimpleNamespace(
            name="sample_choice",
            type="string",
            value='"sample path;$"',
        )

        self.assertEqual(_format_parameter(parameter), "sample_choice=sample path;$")


if __name__ == "__main__":
    unittest.main()
