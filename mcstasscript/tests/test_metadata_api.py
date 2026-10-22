import io
import os
import unittest
import unittest.mock

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.tests.helpers_for_tests import WorkInTestDir


def _make_instr():
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
    with WorkInTestDir():
        instr = McStas_instr("TestInstr",
                             package_path=dummy_path,
                             checks=False)
    instr.add_component("Origin", "test_for_reading")
    instr.add_component("Sample", "test_for_reading")
    return instr


class TestInstrMetadataAPI(unittest.TestCase):

    def setUp(self):
        self.instr = _make_instr()
        origin = self.instr.get_component("Origin")
        origin.add_METADATA("stored", "txt", "some text")
        origin.add_METADATA("info", "JSON", '{"a": 1}')
        sample = self.instr.get_component("Sample")
        sample.add_METADATA("note", "txt", "hello")

    def test_get_METADATA_all(self):
        result = self.instr.get_METADATA()
        self.assertEqual(result, {
            "Origin": {
                "stored": {"type": "txt", "value": "some text"},
                "info": {"type": "JSON", "value": '{"a": 1}'},
            },
            "Sample": {
                "note": {"type": "txt", "value": "hello"},
            },
        })

    def test_get_METADATA_component(self):
        result = self.instr.get_METADATA("Origin")
        self.assertEqual(result, {
            "Origin": {
                "stored": {"type": "txt", "value": "some text"},
                "info": {"type": "JSON", "value": '{"a": 1}'},
            },
        })

    def test_get_METADATA_specific_block(self):
        result = self.instr.get_METADATA("Origin", "stored")
        self.assertEqual(result, {
            "Origin": {
                "stored": {"type": "txt", "value": "some text"},
            },
        })

    def test_get_METADATA_specific_block_json(self):
        result = self.instr.get_METADATA("Origin", "info")
        self.assertEqual(result["Origin"]["info"]["type"], "JSON")
        self.assertEqual(result["Origin"]["info"]["value"], '{"a": 1}')

    def test_get_METADATA_component_not_found(self):
        with self.assertRaises(NameError):
            self.instr.get_METADATA("Nonexistent")

    def test_get_METADATA_name_not_found(self):
        with self.assertRaises(KeyError):
            self.instr.get_METADATA("Origin", "nonexistent")

    def test_get_METADATA_name_without_component(self):
        with self.assertRaises(ValueError):
            self.instr.get_METADATA(metadata_name="stored")

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_METADATA(self, mock_stdout):
        self.instr.show_METADATA()
        output = mock_stdout.getvalue()
        self.assertIn("Origin:", output)
        self.assertIn("  stored (txt):", output)
        self.assertIn("    some text", output)
        self.assertIn("  info (JSON):", output)
        self.assertIn("Sample:", output)

    def test_show_METADATA_empty(self):
        instr = _make_instr()
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            instr.show_METADATA()
        self.assertEqual(output.getvalue(), "No METADATA blocks defined.\n")

    def test_metadata_type(self):
        self.assertEqual(self.instr.metadata_type("Origin", "stored"), "txt")
        self.assertEqual(self.instr.metadata_type("Sample", "note"), "txt")

    def test_metadata_data(self):
        self.assertEqual(self.instr.metadata_data("Origin", "stored"),
                         "some text")
        self.assertEqual(self.instr.metadata_data("Sample", "note"),
                         "hello")

    def test_metadata_type_not_found(self):
        with self.assertRaises(KeyError):
            self.instr.metadata_type("Origin", "nonexistent")

    def test_metadata_data_not_found(self):
        with self.assertRaises(NameError):
            self.instr.metadata_data("Nonexistent", "stored")


if __name__ == "__main__":
    unittest.main()
