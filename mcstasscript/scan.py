"""Utilities for running parameter scans."""

import numbers

import matplotlib.pyplot as plt
import numpy as np


class ParameterScan:
    """Run an instrument for evenly spaced values of one parameter.

    Parameters
    ----------
    instrument : McStas_instr or McXtrace_instr
        Instrument to run.
    parameter_name : str
        Name of the instrument parameter to scan.
    start, stop : numbers.Real
        First and last values in the scan.
    steps : int
        Number of values in the scan, including both endpoints.
    monitor_name : str, optional
        If provided, show a live plot of this monitor's ``total_I`` while the
        scan runs.
    x_padding : float, default 0.05
        Fraction of the scan range added to either side of the live plot.

    Notes
    -----
    The constructor performs the scan immediately. ``data`` contains one
    complete result list from ``instrument.backengine()`` for each scan value.
    """

    def __init__(self, instrument, parameter_name, start, stop, steps,
                 monitor_name=None, x_padding=0.05):
        if not isinstance(parameter_name, str):
            raise TypeError("parameter_name must be a string.")
        if not isinstance(steps, numbers.Integral) or isinstance(steps, bool):
            raise TypeError("steps must be an integer.")
        if steps < 1:
            raise ValueError("steps must be at least 1.")
        if not isinstance(start, numbers.Real) or not isinstance(stop, numbers.Real):
            raise TypeError("start and stop must be real numbers.")
        if (not isinstance(x_padding, numbers.Real) or
                isinstance(x_padding, bool) or x_padding < 0):
            raise ValueError("x_padding must be a non-negative number.")

        self.instrument = instrument
        self.parameter_name = parameter_name
        self.monitor_name = monitor_name
        self.x_padding = x_padding
        self.scan_values = np.linspace(start, stop, int(steps))
        self.data = []
        self._live_fig = None
        self._live_ax = None
        self._live_line = None
        self._live_errorbar = None
        self._live_display = None

        if monitor_name is not None:
            if not isinstance(monitor_name, str):
                raise TypeError("monitor_name must be a string.")
            self._setup_live_plot()

        # Write once before the scan so the first run compiles the instrument.
        self.instrument.write_full_instrument()
        previous_force_compile = self.instrument._run_settings["force_compile"]

        try:
            self.instrument.settings(force_compile=False)
            for index, value in enumerate(self.scan_values):
                self.instrument.set_parameters(
                    {self.parameter_name: value.item()}
                )
                point_data = self.instrument.backengine()
                self.data.append(point_data)
                if self.monitor_name is not None:
                    self._update_live_plot(value, point_data)
                print("Scan point {}/{} complete: {} = {}".format(
                    index + 1, len(self.scan_values), self.parameter_name, value
                ), flush=True)
        finally:
            self.instrument.settings(force_compile=previous_force_compile)

    def get_dataset(self, point):
        """Return all monitor datasets generated at a scan point.

        ``point`` is the zero-based index into ``scan_values`` and ``data``.
        Standard list indexing is supported, including negative indices.
        """
        return self.data[point]

    def get_data(self, point):
        """Alias for :meth:`get_dataset`."""
        return self.get_dataset(point)

    def get_monitor_data(self, monitor_name):
        """Return scan values, intensity, and error for one monitor.

        Returns
        -------
        tuple of numpy.ndarray
            ``(parameter_values, intensity, error)``.
        """
        intensity = np.asarray(self._intensities(monitor_name))
        error = np.asarray(self._errors(monitor_name))
        return self.scan_values.copy(), intensity, error

    def _monitor_names(self):
        names = []
        for point_data in self.data:
            for monitor in self._as_monitor_list(point_data):
                if monitor.name not in names:
                    names.append(monitor.name)
        if not names:
            raise ValueError("The scan contains no monitor data.")
        return names

    @staticmethod
    def _as_monitor_list(point_data):
        if point_data is None:
            return []
        if isinstance(point_data, list):
            return point_data
        return [point_data]

    def _intensities(self, monitor_name):
        intensities = []
        found = False
        for point_data in self.data:
            monitor = self._find_monitor(point_data, monitor_name)
            if monitor is not None:
                intensity = monitor.metadata.total_I
                found = True
            else:
                intensity = np.nan
            intensities.append(intensity)

        if not found:
            raise ValueError("No monitor named '" + str(monitor_name) + "' found.")
        return intensities

    def _errors(self, monitor_name):
        errors = []
        for point_data in self.data:
            monitor = self._find_monitor(point_data, monitor_name)
            error = (None if monitor is None
                     else getattr(monitor.metadata, "total_E", None))
            if error is None:
                errors.append(np.nan)
            else:
                errors.append(error)
        return errors

    def _find_monitor(self, point_data, monitor_name):
        for monitor in self._as_monitor_list(point_data):
            if monitor.name == monitor_name:
                return monitor
        return None

    def _setup_live_plot(self):
        was_interactive = plt.isinteractive()
        plt.ioff()
        self._live_fig, self._live_ax = plt.subplots()
        self._live_errorbar = self._live_ax.errorbar(
            [], [], yerr=[], fmt="o-", color="black", label=self.monitor_name
        )
        self._live_line = self._live_errorbar.lines[0]
        self._live_ax.set_xlabel(self.parameter_name)
        self._live_ax.set_ylabel("Total intensity")
        self._set_live_xlim()
        self._live_ax.legend()
        self._live_fig.tight_layout()
        if was_interactive:
            plt.ion()

        # Updating a display handle makes progress visible with both inline
        # and widget backends while the constructor is still running.
        in_ipython = False
        try:
            from IPython import get_ipython
            from IPython.display import display
            if get_ipython() is not None:
                in_ipython = True
                backend = plt.get_backend().lower()
                if "ipympl" in backend or "nbagg" in backend:
                    # show() displays the widget and consumes its pending
                    # display entry, preventing a duplicate post-execute plot.
                    plt.show(block=False)
                else:
                    # Inline backends need the displayed image replaced.
                    self._live_display = display(self._live_fig,
                                                  display_id=True)
        except ImportError:
            pass

        if not in_ipython:
            plt.ion()
            plt.show(block=False)

    def _set_live_xlim(self):
        start = float(self.scan_values[0])
        stop = float(self.scan_values[-1])
        if start == stop:
            padding = max(abs(start) * self.x_padding, 0.5)
            self._live_ax.set_xlim(start - padding, stop + padding)
        else:
            lower = min(start, stop)
            upper = max(start, stop)
            padding = (upper - lower) * self.x_padding
            self._live_ax.set_xlim(lower - padding, upper + padding)

    def _update_live_plot(self, value, point_data):
        monitor = self._find_monitor(point_data, self.monitor_name)
        if monitor is None:
            raise ValueError("No monitor named '" + self.monitor_name
                             + "' found at scan point "
                             + str(len(self.data)) + ".")

        x_values = list(self._live_line.get_xdata())
        y_values = list(self._live_line.get_ydata())
        x_values.append(value)
        y_values.append(monitor.metadata.total_I)
        errors = self._errors(self.monitor_name)
        self._remove_live_errorbar()
        self._live_errorbar = self._live_ax.errorbar(
            x_values, y_values, yerr=errors, fmt="o-", color="black",
            label=self.monitor_name
        )
        self._live_line = self._live_errorbar.lines[0]
        self._live_ax.relim()
        self._live_ax.autoscale_view(scalex=False, scaley=True)
        self._live_fig.canvas.draw()
        self._live_fig.canvas.flush_events()
        if self._live_display is not None:
            self._live_display.update(self._live_fig)

    def _remove_live_errorbar(self):
        for artist_group in self._live_errorbar.lines:
            if isinstance(artist_group, (tuple, list)):
                for artist in artist_group:
                    artist.remove()
            else:
                artist_group.remove()

    def _plot(self, monitor_names, ax=None, show=True, logx=False, logy=False,
              **kwargs):
        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.get_figure()

        fmt = kwargs.pop("fmt", "o-")
        for monitor_name in monitor_names:
            ax.errorbar(self.scan_values, self._intensities(monitor_name),
                        yerr=self._errors(monitor_name), fmt=fmt,
                        label=monitor_name, **kwargs)

        ax.set_xlabel(self.parameter_name)
        ax.set_ylabel("Total intensity")
        if logx:
            ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        if len(monitor_names) > 1:
            ax.legend()
        fig.tight_layout()
        if show:
            plt.show()
        return fig, ax

    def plot_all_monitors(self, ax=None, show=True, logx=False, logy=False,
                          **kwargs):
        """Plot ``metadata.total_I`` and ``metadata.total_E``.

        One errorbar series is drawn for each monitor found in the scan.
        Returns the ``(figure, axes)`` pair so callers can further customize
        the plot.
        """
        return self._plot(self._monitor_names(), ax=ax, show=show,
                          logx=logx, logy=logy, **kwargs)

    def plot_monitor(self, monitor_name, ax=None, show=True, logx=False,
                     logy=False, **kwargs):
        """Plot one monitor's ``total_I`` with ``total_E`` errorbars."""
        return self._plot([monitor_name], ax=ax, show=show, logx=logx,
                          logy=logy, **kwargs)
