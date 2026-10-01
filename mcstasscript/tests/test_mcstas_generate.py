import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcstasscript.tools.mcstas_generate import mcstas_pygen, mcxtrace_pygen


GENERATED_MODULE = """\
from types import SimpleNamespace


def make(input_path=None):
    return SimpleNamespace(input_path=input_path)
"""


class TestPygen(unittest.TestCase):
    def _write_generated_file(self, command, **kwargs):
        Path(command[2]).write_text(GENERATED_MODULE)
        return subprocess.CompletedProcess(command, 0, stdout="generated")

    def _input_file(self, directory):
        filename = Path(directory) / "example.instr"
        filename.write_text("instrument example()\n")
        return filename

    def test_default_destination_and_input_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)
            input_path = Path(temp_dir) / "components"
            input_path.mkdir()

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                side_effect=self._write_generated_file,
            ) as run:
                instrument = mcstas_pygen(
                    input_file,
                    input_path=input_path,
                )

            generated_file = input_file.with_name("example_generated.py")
            self.assertTrue(generated_file.is_file())
            self.assertEqual(instrument.input_path, str(input_path))
            self.assertEqual(run.call_args.args[0][0], "mcstas-pygen")
            self.assertEqual(
                run.call_args.kwargs["cwd"],
                str(input_file.resolve().parent),
            )

    def test_mcxtrace_generator_and_destination_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)
            destination = Path(temp_dir) / "generated"
            destination.mkdir()

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                side_effect=self._write_generated_file,
            ) as run:
                instrument = mcxtrace_pygen(input_file, destination=destination)

            self.assertTrue(
                (destination / "example_generated.py").is_file()
            )
            self.assertIsNone(instrument.input_path)
            self.assertEqual(run.call_args.args[0][0], "mcxtrace-pygen")

    def test_destination_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)
            destination = Path(temp_dir) / "custom.py"

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                side_effect=self._write_generated_file,
            ):
                mcstas_pygen(input_file, destination=destination)

            self.assertTrue(destination.is_file())

    def test_rejects_missing_input(self):
        with self.assertRaises(FileNotFoundError):
            mcstas_pygen("missing.instr")

    def test_rejects_non_instr_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "example.txt"
            input_file.write_text("not an instrument")

            with self.assertRaises(ValueError):
                mcstas_pygen(input_file)

    def test_rejects_missing_input_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)

            with self.assertRaises(FileNotFoundError):
                mcstas_pygen(
                    input_file,
                    input_path=Path(temp_dir) / "missing",
                )

    def test_reports_generator_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)
            process = subprocess.CompletedProcess(
                [], 2, stdout="component compilation failed"
            )

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                return_value=process,
            ):
                with self.assertRaisesRegex(RuntimeError, "component compilation failed"):
                    mcstas_pygen(input_file)

    def test_reports_missing_generator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                side_effect=FileNotFoundError("mcstas-pygen"),
            ):
                with self.assertRaisesRegex(RuntimeError, "mcstas-pygen"):
                    mcstas_pygen(input_file)

    def test_reports_missing_generated_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)
            process = subprocess.CompletedProcess([], 0, stdout="no output")

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                return_value=process,
            ):
                with self.assertRaisesRegex(FileNotFoundError, "did not create"):
                    mcstas_pygen(input_file)

    def test_reports_missing_make_function(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self._input_file(temp_dir)

            def write_invalid_module(command, **kwargs):
                Path(command[2]).write_text("value = 1\n")
                return subprocess.CompletedProcess(command, 0, stdout="generated")

            with patch(
                "mcstasscript.tools.mcstas_generate.subprocess.run",
                side_effect=write_invalid_module,
            ):
                with self.assertRaisesRegex(AttributeError, "does not define a make"):
                    mcstas_pygen(input_file)


if __name__ == "__main__":
    unittest.main()
