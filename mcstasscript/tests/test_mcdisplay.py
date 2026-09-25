import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mcstasscript.geometry_viewer.mcdisplay import (
    McdisplayError,
    _format_parameter,
    display_mcdisplay_html,
    run_mcdisplay,
)


class TestMcdisplay(unittest.TestCase):
    def _instrument(self, input_path, output_path):
        instrument = SimpleNamespace(
            name="test_instrument",
            package_name="McStas",
            parameters=[],
            input_path=input_path,
            _run_settings={"output_path": output_path},
        )
        instrument.write_full_instrument = Mock()
        return instrument

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

    def test_custom_output_path_is_incremented_and_input_path_is_cwd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input")
            output_path = os.path.join(temp_dir, "results")
            os.mkdir(input_path)
            instrument = self._instrument(input_path, output_path)

            def run_command(command, **kwargs):
                output_dir = command[2]
                if not os.path.isabs(output_dir):
                    output_dir = os.path.join(kwargs["cwd"], output_dir)
                os.mkdir(output_dir)
                with open(os.path.join(output_dir, "index.html"), "w") as handle:
                    handle.write("<html></html>")
                return Mock(returncode=0, stdout="", stderr="")

            with patch("mcstasscript.geometry_viewer.mcdisplay._find_executable", return_value="mcdisplay"), \
                    patch("mcstasscript.geometry_viewer.mcdisplay.subprocess.run", side_effect=run_command) as run:
                first = run_mcdisplay(instrument)
                second = run_mcdisplay(instrument)

            self.assertEqual(first, os.path.join(output_path, "index.html"))
            self.assertEqual(second, os.path.join(output_path + "_0", "index.html"))
            self.assertEqual(
                run.call_args_list[0].args[0][2],
                os.path.relpath(output_path, input_path),
            )
            self.assertEqual(run.call_args_list[0].kwargs["cwd"], input_path)
            self.assertEqual(run.call_args_list[1].kwargs["cwd"], input_path)

    def test_window_backend_ignores_close_return_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            instrument = self._instrument(temp_dir, os.path.join(temp_dir, "results"))
            process = Mock(returncode=1, stdout="window output", stderr="Qt shutdown output")

            with patch("mcstasscript.geometry_viewer.mcdisplay._find_executable", return_value="mcdisplay"), \
                    patch("mcstasscript.geometry_viewer.mcdisplay.subprocess.run", return_value=process):
                result = run_mcdisplay(instrument, format="window")

            self.assertIsNone(result)

    def test_notebook_html_display_uses_relative_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "instrument_mcdisplay")
            os.mkdir(output_dir)
            html_path = os.path.join(output_dir, "index.html")
            with open(html_path, "w") as html_file:
                html_file.write("<html></html>")

            with patch("mcstasscript.geometry_viewer.mcdisplay._is_notebook", return_value=True), \
                    patch("mcstasscript.geometry_viewer.mcdisplay.os.getcwd", return_value=temp_dir), \
                    patch("IPython.display.IFrame") as iframe:
                display_mcdisplay_html(html_path)

            self.assertEqual(iframe.call_args.kwargs["src"], "instrument_mcdisplay/index.html")

    def test_nonzero_return_code_raises_concise_error_with_process_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            instrument = self._instrument(temp_dir, os.path.join(temp_dir, "results"))
            process = Mock(returncode=7, stdout="stdout details", stderr="stderr details")

            with patch("mcstasscript.geometry_viewer.mcdisplay._find_executable", return_value="mcdisplay"), \
                    patch("mcstasscript.geometry_viewer.mcdisplay.subprocess.run", return_value=process):
                with self.assertRaises(McdisplayError) as raised:
                    run_mcdisplay(instrument)

            self.assertIn("return code 7", str(raised.exception))
            self.assertEqual(raised.exception.returncode, 7)
            self.assertEqual(raised.exception.stderr, "stderr details")

    def test_missing_output_raises_error_after_successful_process(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            instrument = self._instrument(temp_dir, os.path.join(temp_dir, "results"))
            process = Mock(returncode=0, stdout="", stderr="")

            with patch("mcstasscript.geometry_viewer.mcdisplay._find_executable", return_value="mcdisplay"), \
                    patch("mcstasscript.geometry_viewer.mcdisplay.subprocess.run", return_value=process):
                with self.assertRaisesRegex(McdisplayError, "did not create"):
                    run_mcdisplay(instrument)


if __name__ == "__main__":
    unittest.main()
