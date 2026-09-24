import io
import os
import unittest
import unittest.mock

from mcstasscript.interface import instr

METADATA_MIN_VERSION = (3, 4)


def _mcstas_supports_metadata():
    """Check if the installed McStas version supports the METADATA keyword."""
    try:
        Instr = instr.McStas_instr("version_check")
        version = (Instr.mccode_version, Instr.mccode_minor_version)
        return version >= METADATA_MIN_VERSION
    except Exception:
        return False


def setup_metadata_instrument():
    Instr = instr.McStas_instr("integration_test_metadata")

    source = Instr.add_component("Source", "Source_div")
    source.xwidth = 0.03
    source.yheight = 0.01
    source.focus_aw = 0.01
    source.focus_ah = 0.01
    source.E0 = 81.81
    source.dE = 1.0
    source.flux = 1E10

    source.add_METADATA("stored", "txt", "Hello from METADATA")

    file_writer = Instr.add_component("file_writer", "File")
    file_writer.filename = "\"metadata_output.txt\""
    file_writer.metadatakey = "\"Source:stored\""
    file_writer.keep = 1

    PSD = Instr.add_component("PSD_1D", "PSDlin_monitor")
    PSD.set_AT([0, 0, 1], RELATIVE="Source")
    PSD.xwidth = 0.1
    if Instr.mccode_version > 2:
        PSD.nbins = 100
    else:
        PSD.nx = 100
    PSD.yheight = 0.03
    PSD.filename = "\"PSD.dat\""
    PSD.restore_neutron = 1

    return Instr


class TestMetadataIntegration(unittest.TestCase):
    """
    Integration test that METADATA blocks are written to the .instr
    file and that File.comp can consume them at simulation runtime.
    """

    def setUp(self):
        self.CURRENT_DIR = os.getcwd()
        self.THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(self.THIS_DIR)

    def tearDown(self):
        os.chdir(self.CURRENT_DIR)
        for f in ("integration_test_metadata.instr",
                  "metadata_output.txt"):
            path = os.path.join(self.THIS_DIR, f)
            if os.path.exists(path):
                os.remove(path)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_metadata_written_to_instr_file(self, mock_stdout):
        """
        Verify that METADATA blocks appear in the generated .instr file.
        """
        Instr = setup_metadata_instrument()
        Instr.write_full_instrument()

        instr_file = os.path.join(
            self.THIS_DIR, "integration_test_metadata.instr")

        self.assertTrue(os.path.exists(instr_file))

        with open(instr_file) as f:
            content = f.read()

        self.assertIn("METADATA txt stored %{", content)
        self.assertIn("Hello from METADATA", content)

    @unittest.skipUnless(
        _mcstas_supports_metadata(),
        "Installed McStas does not support the METADATA keyword")
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_metadata_file_comp(self, mock_stdout):
        """
        Run a full simulation and verify that File.comp wrote the
        METADATA content to the output file.
        """
        Instr = setup_metadata_instrument()
        Instr.run_full_instrument(
            foldername="integration_test_metadata_run",
            ncount=1E6, mpi=1,
            increment_folder_name=True)

        output_file = os.path.join(self.THIS_DIR, "metadata_output.txt")

        self.assertTrue(os.path.exists(output_file),
                        f"File not found: {output_file}")

        with open(output_file) as f:
            content = f.read()

        self.assertIn("Hello from METADATA", content)


if __name__ == "__main__":
    unittest.main()
