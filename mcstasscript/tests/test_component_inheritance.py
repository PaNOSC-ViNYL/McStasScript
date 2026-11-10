import os
import tempfile
import unittest

from mcstasscript.helper.component_reader import ComponentReader


class TestComponentInheritance(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = self.directory.name

    def component(self, name, source):
        with open(os.path.join(self.path, name + ".comp"), "w") as output:
            output.write(source)

    def reader(self):
        return ComponentReader(self.path, input_path=self.path)

    def test_inherited_and_local_parameters_and_documentation(self):
        self.component("Base", """/*
* %P
* width: [m] Parent width
* count: [1] Parent count
*/
DEFINE COMPONENT Base
DEFINITION PARAMETERS (int count=3)
SETTING PARAMETERS (width=2, string label="base")
TRACE %{ %}
END
""")
        self.component("Child", """/*
* %P
* width: [cm] Child width
*/
DEFINE COMPONENT Child INHERIT Base
SETTING PARAMETERS (extra=4)
TRACE INHERIT Base
END
""")
        self.component("Alias", "DEFINE COMPONENT Alias INHERIT Child\nEND\n")
        info = self.reader().read_name("Alias")
        self.assertEqual(info.parameter_names, ["count", "width", "label", "extra"])
        self.assertEqual(info.parameter_defaults["count"], 3)
        self.assertEqual(info.parameter_types["label"], "string")
        self.assertEqual(info.parameter_defaults["extra"], 4.0)
        self.assertEqual(info.parameter_comments["width"], "Child width")
        self.assertEqual(info.parameter_units["width"], "cm")
        self.assertEqual(info.parameter_comments["count"], "Parent count")
        self.assertEqual(info.name, "Alias")

    def test_missing_parent_and_cycles_report_errors(self):
        self.component("Missing", "DEFINE COMPONENT Missing INHERIT Absent\nEND\n")
        self.component("First", "DEFINE COMPONENT First INHERIT Second\nEND\n")
        self.component("Second", "DEFINE COMPONENT Second INHERIT First\nEND\n")
        reader = self.reader()
        with self.assertRaisesRegex(NameError, "Absent"):
            reader.read_name("Missing")
        with self.assertRaisesRegex(ValueError, "inheritance cycle"):
            reader.read_name("First")

    def test_section_inheritance_is_not_parameter_inheritance(self):
        self.component("Local", """DEFINE COMPONENT Local
SETTING PARAMETERS (local=1)
TRACE INHERIT Absent
END
""")
        self.assertEqual(self.reader().read_name("Local").parameter_names, ["local"])
