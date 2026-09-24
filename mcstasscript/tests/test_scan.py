import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import matplotlib.pyplot as plt
import numpy as np

from mcstasscript.scan import ParameterScan


def make_monitor(name, total_I, total_E=0.1):
    return SimpleNamespace(
        name=name,
        metadata=SimpleNamespace(total_I=total_I, total_E=total_E),
    )


class TestParameterScan(unittest.TestCase):
    def make_instrument(self):
        instrument = Mock()
        instrument._run_settings = {"force_compile": True}
        instrument.backengine.side_effect = [
            [make_monitor("monitor_a", 1.0), make_monitor("monitor_b", 2.0)],
            [make_monitor("monitor_a", 3.0), make_monitor("monitor_b", 4.0)],
            [make_monitor("monitor_a", 5.0), make_monitor("monitor_b", 6.0)],
        ]
        return instrument

    def test_runs_scan_and_restores_force_compile(self):
        instrument = self.make_instrument()

        scan = ParameterScan(instrument, "theta", 0, 2, 3)

        instrument.write_full_instrument.assert_called_once_with()
        self.assertEqual(
            instrument.settings.call_args_list[0].args,
            (),
        )
        self.assertEqual(
            [call.kwargs for call in instrument.settings.call_args_list],
            [{"force_compile": False}, {"force_compile": True}],
        )
        self.assertEqual(
            [call.args[0] for call in instrument.set_parameters.call_args_list],
            [{"theta": 0.0}, {"theta": 1.0}, {"theta": 2.0}],
        )
        self.assertEqual(len(scan.data), 3)
        self.assertIs(scan.get_dataset(1), scan.data[1])
        self.assertIs(scan.get_data(1), scan.data[1])

    def test_plot_methods_use_monitor_total_intensity(self):
        instrument = self.make_instrument()
        output = StringIO()
        with redirect_stdout(output):
            scan = ParameterScan(instrument, "theta", 0, 2, 3)

        self.assertEqual(output.getvalue().count("Scan point"), 3)

        fig, ax = scan.plot_all_monitors(show=False)
        self.assertEqual(len(ax.lines), 2)
        np.testing.assert_array_equal(ax.lines[0].get_ydata(), [1.0, 3.0, 5.0])
        np.testing.assert_array_equal(ax.lines[1].get_ydata(), [2.0, 4.0, 6.0])
        self.assertEqual(len(ax.containers), 2)

        fig, ax = scan.plot_monitor("monitor_b", show=False)
        self.assertEqual(len(ax.lines), 1)
        np.testing.assert_array_equal(ax.lines[0].get_ydata(), [2.0, 4.0, 6.0])

        fig, ax = scan.plot_monitor("monitor_a", show=False,
                                    logx=True, logy=True)
        self.assertEqual(ax.get_xscale(), "log")
        self.assertEqual(ax.get_yscale(), "log")

    def test_get_monitor_data_returns_arrays(self):
        instrument = self.make_instrument()
        scan = ParameterScan(instrument, "theta", 0, 2, 3)

        parameter_values, intensity, error = scan.get_monitor_data("monitor_b")

        np.testing.assert_array_equal(parameter_values, [0.0, 1.0, 2.0])
        np.testing.assert_array_equal(intensity, [2.0, 4.0, 6.0])
        np.testing.assert_array_equal(error, [0.1, 0.1, 0.1])

    def test_optional_monitor_creates_live_plot(self):
        instrument = self.make_instrument()

        scan = ParameterScan(instrument, "theta", 0, 2, 3,
                             monitor_name="monitor_a")

        np.testing.assert_array_equal(scan._live_line.get_xdata(), [0.0, 1.0, 2.0])
        np.testing.assert_array_equal(scan._live_line.get_ydata(), [1.0, 3.0, 5.0])
        self.assertEqual(tuple(scan._live_ax.get_xlim()), (-0.1, 2.1))
        self.assertEqual(len(scan._live_ax.get_legend().texts), 1)
        plt.close(scan._live_fig)
        plt.ioff()

    def test_force_compile_is_restored_when_scan_fails(self):
        instrument = self.make_instrument()
        instrument.backengine.side_effect = RuntimeError("run failed")

        with self.assertRaises(RuntimeError):
            ParameterScan(instrument, "theta", 0, 1, 2)

        self.assertEqual(
            [call.kwargs for call in instrument.settings.call_args_list],
            [{"force_compile": False}, {"force_compile": True}],
        )


if __name__ == "__main__":
    unittest.main()
