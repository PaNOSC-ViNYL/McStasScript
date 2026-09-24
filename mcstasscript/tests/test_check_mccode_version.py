import unittest
from unittest import mock

from mcstasscript.helper.check_mccode_version import _parse_version
from mcstasscript.helper.check_mccode_version import check_mcstas_version
from mcstasscript.helper.check_mccode_version import check_mcxtrace_version
from mcstasscript.interface.instr import McCode_instr
from mcstasscript.interface.instr import McStas_instr
from mcstasscript.interface.instr import McXtrace_instr


class TestParseVersion(unittest.TestCase):

    def test_stable_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32"),
                         (3, 4, "32"))

    def test_suffixed_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32a0"),
                         (3, 4, "32a0"))

    def test_parenthesized_version(self):
        self.assertEqual(_parse_version(b"McStas version 3.4.32 (git)"),
                         (3, 4, "32"))

    def test_two_component_version(self):
        self.assertEqual(_parse_version(b"McXtrace version 1.2"),
                         (1, 2, "0"))

    def test_suffixed_minor(self):
        self.assertEqual(_parse_version(b"McStas version 3.4b1.32"),
                         (3, 4, "32"))

    @mock.patch("mcstasscript.helper.check_mccode_version.subprocess.check_output")
    def test_mcstas_version_probes_once(self, check_output):
        check_output.return_value = b"McStas version 3.7.14a0"

        version = check_mcstas_version("/opt/mcstas/bin")

        self.assertEqual(version, (3, 7, "14a0"))
        check_output.assert_called_once_with(
            ["/opt/mcstas/bin/mcstas", "-v"])

    @mock.patch("mcstasscript.helper.check_mccode_version.subprocess.check_output")
    def test_mcxtrace_version_probes_once(self, check_output):
        check_output.return_value = b"McXtrace version 1.6.2"

        version = check_mcxtrace_version("/opt/mcxtrace/bin")

        self.assertEqual(version, (1, 6, "2"))
        check_output.assert_called_once_with(
            ["/opt/mcxtrace/bin/mcxtrace", "-v"])

    def test_mcstas_instrument_stores_version_fields(self):
        def fake_base_init(instrument, name, **kwargs):
            instrument._run_settings = {"executable_path": "/opt/mcstas/bin"}

        with mock.patch.object(McCode_instr, "__init__", fake_base_init), \
                mock.patch("mcstasscript.interface.instr.check_mcstas_version",
                            return_value=(3, 7, "14a0")) as check_version:
            instrument = McStas_instr("test")

        self.assertEqual(instrument.mccode_version, 3)
        self.assertEqual(instrument.mccode_major_version, 3)
        self.assertEqual(instrument.mccode_minor_version, 7)
        self.assertEqual(instrument.mccode_patch_version, "14a0")
        check_version.assert_called_once_with("/opt/mcstas/bin")

    def test_mcxtrace_instrument_stores_version_fields(self):
        def fake_base_init(instrument, name, **kwargs):
            instrument._run_settings = {"executable_path": "/opt/mcxtrace/bin"}

        with mock.patch.object(McCode_instr, "__init__", fake_base_init), \
                mock.patch("mcstasscript.interface.instr.check_mcxtrace_version",
                            return_value=(1, 6, "2")) as check_version:
            instrument = McXtrace_instr("test")

        self.assertEqual(instrument.mccode_version, 1)
        self.assertEqual(instrument.mccode_major_version, 1)
        self.assertEqual(instrument.mccode_minor_version, 6)
        self.assertEqual(instrument.mccode_patch_version, "2")
        check_version.assert_called_once_with("/opt/mcxtrace/bin")


if __name__ == "__main__":
    unittest.main()
