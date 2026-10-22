import os
import shutil
import subprocess
import tempfile
import unittest

from mcstasscript.integration_tests.test_add_test import make_test_instrument


class TestIncludeDir(unittest.TestCase):
    """Integration test for add_include_dir."""

    def test_include_dir_with_mctest(self):
        """
        An instrument including a header from a separate directory compiles
        and runs, when the directory is added with add_include_dir.
        """
        if shutil.which("mctest") is None:
            self.skipTest("mctest is not available")

        instrument_name = "integration_test_include_dir"
        expected_intensity = 6.283e8

        with tempfile.TemporaryDirectory() as instrument_dir, \
                tempfile.TemporaryDirectory() as include_dir, \
                tempfile.TemporaryDirectory() as test_output:
            with open(os.path.join(include_dir, "test_include.h"), "w") as f:
                f.write("#define INCLUDED_SOURCE_FLUX 1e10\n")

            instrument = make_test_instrument(instrument_name, instrument_dir)
            instrument.append_declare('#include "test_include.h"')
            instrument.get_component("source").flux = "INCLUDED_SOURCE_FLUX"
            instrument.add_include_dir(include_dir)
            instrument.add_test("monitor", intensity=expected_intensity)
            instrument.write_full_instrument()

            result = subprocess.run(
                ["mctest", "--local", instrument_dir,
                 "--testdir", test_output,
                 "--instr", instrument_name,
                 "--ncount", "100000", "--skipnontest"],
                cwd=instrument_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertIn("SUCCESS", result.stdout)
        self.assertIn("[val:", result.stdout, msg=result.stdout)
