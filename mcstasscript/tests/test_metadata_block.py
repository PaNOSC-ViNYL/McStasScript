import io
import re
import unittest

from mcstasscript.helper.mcstas_objects import Component, MetadataBlock, _quote_if_needed


class TestMetadataBlock(unittest.TestCase):

    def test_construction(self):
        block = MetadataBlock("mydata", "JSON", '{"key": "value"}')
        self.assertEqual(block.name, "mydata")
        self.assertEqual(block.type, "JSON")
        self.assertEqual(block.value, '{"key": "value"}')
        self.assertEqual(block.source, "instrument")

    def test_component_source(self):
        block = MetadataBlock("mydata", "JSON", "{}", source="component")
        self.assertEqual(block.source, "component")

    def test_repr(self):
        block = MetadataBlock("mydata", "JSON", '{"key": "value"}')
        r = repr(block)
        self.assertIn("MetadataBlock", r)
        self.assertIn("mydata", r)
        self.assertIn("JSON", r)
        self.assertIn("instrument", r)

    def test_str(self):
        block = MetadataBlock("mydata", "JSON", '{"key": "value"}')
        self.assertEqual(str(block), "METADATA JSON mydata")

    def test_multiline_value(self):
        value = "line1\nline2\nline3"
        block = MetadataBlock("txt", "text", value)
        self.assertEqual(block.value, "line1\nline2\nline3")


class TestComponentMetadata(unittest.TestCase):

    def setUp(self):
        self.comp = Component("Origin", "Progress_bar",
                              AT=[0, 0, 0], AT_RELATIVE="ABSOLUTE")

    def test_initial_metadata_list_empty(self):
        self.assertEqual(self.comp.metadata_list, [])

    def test_add_METADATA(self):
        self.comp.add_METADATA("stored", "txt", "some text")
        self.assertEqual(len(self.comp.metadata_list), 1)
        block = self.comp.metadata_list[0]
        self.assertEqual(block.name, "stored")
        self.assertEqual(block.type, "txt")
        self.assertEqual(block.value, "some text")
        self.assertEqual(block.source, "instrument")

    def test_add_multiple_METADATA(self):
        self.comp.add_METADATA("a", "JSON", '{"x": 1}')
        self.comp.add_METADATA("b", "txt", "hello")
        self.assertEqual(len(self.comp.metadata_list), 2)
        self.assertEqual(self.comp.metadata_list[0].name, "a")
        self.assertEqual(self.comp.metadata_list[1].name, "b")

    def test_add_METADATA_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.comp.add_METADATA("", "txt", "data")

    def test_add_METADATA_whitespace_name_raises(self):
        with self.assertRaises(ValueError):
            self.comp.add_METADATA("   ", "txt", "data")

    def test_add_METADATA_duplicate_name_raises(self):
        self.comp.add_METADATA("a", "JSON", '{"x": 1}')
        with self.assertRaises(ValueError):
            self.comp.add_METADATA("a", "txt", "other")
        self.assertEqual(len(self.comp.metadata_list), 1)
        self.assertEqual(self.comp.metadata_list[0].name, "a")

    def test_get_METADATA_found(self):
        self.comp.add_METADATA("stored", "txt", "some text")
        block = self.comp.get_METADATA("stored")
        self.assertIsNotNone(block)
        self.assertEqual(block.type, "txt")
        self.assertEqual(block.value, "some text")

    def test_get_METADATA_not_found(self):
        self.assertIsNone(self.comp.get_METADATA("nonexistent"))

    def test_remove_METADATA(self):
        self.comp.add_METADATA("a", "JSON", "{}")
        self.comp.add_METADATA("b", "txt", "hi")
        self.comp.remove_METADATA("a")
        self.assertEqual(len(self.comp.metadata_list), 1)
        self.assertEqual(self.comp.metadata_list[0].name, "b")

    def test_remove_METADATA_not_found(self):
        with self.assertRaises(KeyError):
            self.comp.remove_METADATA("nonexistent")

    def test_remove_METADATA_all(self):
        self.comp.add_METADATA("a", "JSON", "{}")
        self.comp.remove_METADATA("a")
        self.assertEqual(self.comp.metadata_list, [])


class TestQuoteIfNeeded(unittest.TestCase):

    def test_alphanumeric_unquoted(self):
        self.assertEqual(_quote_if_needed("JSON"), "JSON")

    def test_underscore_unquoted(self):
        self.assertEqual(_quote_if_needed("my_type"), "my_type")

    def test_slash_quoted(self):
        self.assertEqual(_quote_if_needed("mimetype/text"), '"mimetype/text"')

    def test_empty_string_quoted(self):
        self.assertEqual(_quote_if_needed(""), '""')

    def test_numeric_string_quoted(self):
        self.assertEqual(_quote_if_needed("123"), '"123"')

    def test_hyphenated_quoted(self):
        self.assertEqual(_quote_if_needed("my-data"), '"my-data"')

    def test_mime_style_quoted(self):
        self.assertEqual(_quote_if_needed("text/plain"), '"text/plain"')

    def test_identifier_with_underscore_and_digits_unquoted(self):
        self.assertEqual(_quote_if_needed("my_type2"), "my_type2")

    def test_value_with_quote_and_backslash_escaped(self):
        self.assertEqual(_quote_if_needed('a"b\\c'), '"a\\"b\\\\c"')


class TestWriteComponentMetadata(unittest.TestCase):

    def _make_comp(self):
        comp = Component("Origin", "Progress_bar",
                         AT=[0, 0, 0], AT_RELATIVE="ABSOLUTE")
        comp._unfreeze()
        comp.parameter_names = []
        comp.parameter_defaults = {}
        comp.parameter_types = {}
        comp._freeze()
        return comp

    def _write(self, comp):
        fo = io.StringIO()
        comp.write_component(fo)
        return fo.getvalue()

    def test_no_metadata_no_metadata_lines(self):
        comp = self._make_comp()
        output = self._write(comp)
        self.assertNotIn("METADATA", output)

    def test_string_includes_metadata(self):
        comp = self._make_comp()
        comp.add_METADATA("stored", "txt", "some text")
        output = str(comp)
        self.assertIn("METADATA txt stored %{", output)
        self.assertIn("some text", output)

    def test_legacy_component_without_metadata_list(self):
        comp = self._make_comp()
        del comp.metadata_list
        output = self._write(comp)
        self.assertNotIn("METADATA", output)

    def test_single_metadata_block(self):
        comp = self._make_comp()
        comp.add_METADATA("stored", "txt", "some text")
        output = self._write(comp)
        self.assertIn("METADATA txt stored %{\n", output)
        self.assertIn("some text\n", output)
        self.assertIn("%}\n", output)

    def test_component_metadata_block_is_not_written(self):
        comp = self._make_comp()
        comp.add_METADATA("instrument_data", "txt", "keep this")
        comp.metadata_list.append(
            MetadataBlock("component_data", "txt", "do not copy",
                          source="component"))
        output = self._write(comp)
        self.assertIn("METADATA txt instrument_data %{\n", output)
        self.assertNotIn("component_data", output)
        self.assertNotIn("do not copy", output)

    def test_multiple_metadata_blocks(self):
        comp = self._make_comp()
        comp.add_METADATA("a", "JSON", '{"x": 1}')
        comp.add_METADATA("b", "txt", "hello")
        output = self._write(comp)
        self.assertIn("METADATA JSON a %{\n", output)
        self.assertIn('{"x": 1}\n', output)
        self.assertIn("METADATA txt b %{\n", output)
        self.assertIn("hello\n", output)
        idx_a = output.index("METADATA JSON a")
        idx_b = output.index("METADATA txt b")
        self.assertLess(idx_a, idx_b)

    def test_quoted_type(self):
        comp = self._make_comp()
        comp.add_METADATA("stored", "mimetype/text", "data")
        output = self._write(comp)
        self.assertIn('METADATA "mimetype/text" stored %{', output)

    def test_quoted_name(self):
        comp = self._make_comp()
        comp.add_METADATA("my-data", "txt", "data")
        output = self._write(comp)
        self.assertIn('METADATA txt "my-data" %{', output)

    def test_numeric_name_quoted(self):
        comp = self._make_comp()
        comp.add_METADATA("123", "txt", "data")
        output = self._write(comp)
        self.assertIn('METADATA txt "123" %{\n', output)

    def test_name_requiring_escaping(self):
        comp = self._make_comp()
        comp.add_METADATA('my"name', "txt", "data")
        output = self._write(comp)
        self.assertIn('METADATA txt "my\\"name" %{\n', output)

    def test_metadata_after_jump(self):
        comp = self._make_comp()
        comp.JUMP = "target 3"
        comp.add_METADATA("stored", "txt", "data")
        output = self._write(comp)
        idx_jump = output.index("JUMP target 3")
        idx_meta = output.index("METADATA txt stored")
        self.assertLess(idx_jump, idx_meta)

    def test_metadata_before_c_code_after(self):
        comp = self._make_comp()
        comp.c_code_after = "printf('done');\\n"
        comp.add_METADATA("stored", "txt", "data")
        output = self._write(comp)
        idx_meta = output.index("METADATA txt stored")
        idx_ccode = output.index("printf('done')")
        self.assertLess(idx_meta, idx_ccode)

    def test_multiline_value(self):
        comp = self._make_comp()
        comp.add_METADATA("stored", "txt", "line1\nline2\nline3")
        output = self._write(comp)
        self.assertIn("line1\nline2\nline3\n", output)


if __name__ == "__main__":
    unittest.main()
