import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import BoundaryNorm

from mcstasscript.instrument_diagnostics.diagnostics_instrument import DiagnosticsInstrument
from mcstasscript.interface.functions import name_search
from mcstasscript.data.data import McStasDataBinned
from mcstasscript.helper.plot_helper import _plot_fig_ax

class IntensityDiagnostics(DiagnosticsInstrument):
    def __init__(self, instr):
        super().__init__(instr)

        self.data = None
        self.data_dim = None
        self.monitors = None

    def add_monitor(self, before, options):
        name = "I_before_" + before.name
        mon = self.instr.add_component(name, "Monitor_nD", before=before)

        mon.set_parameters(restore_neutron=1,
                           xwidth=100, yheight=100,
                           options=options,
                           filename='"' + name + ".diag" + '"')

        mon.set_AT(before.AT_data, RELATIVE=before.AT_reference)
        if before.ROTATED_specified:
            mon.set_ROTATED(before.ROTATED_data, RELATIVE=before.ROTATED_reference)

        return name

    def run_general(self, variable=None, limits=None):#, start=None, end=None):
        self.reset_instr()
        self.remove_previous_use()

        if limits is None:
            limit_string = "auto"
        else:
            if not isinstance(limits, list) or len(limits) != 2:
                raise TypeError("limits has to be a list of length 2.")
            limit_string = f"limits=[{limits[0]},{limits[1]}]"

        if variable is None:
            options = f'"square boarders intensity"'
            self.data_dim = 0
        else:
            options = f'"square {variable} {limit_string} bins=300"'
            self.data_dim = 1

        self.monitors = []
        for comp in self.component_list[1:]:
            mon_name = self.add_monitor(before=comp, options=options)
            self.monitors.append((mon_name, comp.name))

        self.correct_target_index()

        self.data = self.instr.backengine()

    def run(self):#, start=None, end=None):
        self.reset_instr()
        self.remove_previous_use()

        options = f'"square boarders intensity"'
        self.monitors = []
        for comp in self.component_list[1:]:
            mon_name = self.add_monitor(before=comp, options=options)
            self.monitors.append((mon_name, comp.name))

        self.correct_target_index()

        self.data = self.instr.backengine()

    def plot(self, figsize=None, ax=None, fig=None, show_comp_names=True,
             y_tick_positions=None, ylimits=None):

        if self.data_dim == 0:
            self.plot_0D(figsize=figsize, ax=ax, fig=fig,
                         show_comp_names=show_comp_names,
                         y_tick_positions=y_tick_positions,
                         ylimits=ylimits)
        elif self.data_dim == 1:
            self.plot_1D(figsize=figsize, ax=ax, fig=fig,
                         show_comp_names=show_comp_names,
                         y_tick_positions=y_tick_positions,
                         ylimits=ylimits)

    def plot_1D(self, figsize=None, ax=None, fig=None, show_comp_names=True,
                y_tick_positions=None, ylimits=None):

        if figsize is None:
            figsize = (8, len(self.component_list) / 5 + 1)

        data_sets = []
        for I_monitor_name, component_name in self.monitors:
            mon_data = name_search(I_monitor_name, self.data)
            intensity = mon_data.Intensity
            axis = mon_data.xaxis
            data_sets.append({"name": component_name, "I": intensity, "axis": axis})

        if y_tick_positions is None:
            y_positions = np.linspace(1, len(data_sets), len(data_sets))
            y_sep = y_positions[1] - y_positions[0]
            y_positions = np.append(y_positions, y_positions[-1] + y_sep)
        else:
            #y_tick_positions.reverse()
            y_positions = y_tick_positions

        # Find min and max for axis
        for index, data_set in enumerate(data_sets):
            if index == 0:
                max_axis = max(data_set["axis"])
                min_axis = min(data_set["axis"])
            else:
                max_axis = max(max(data_set["axis"]), max_axis)
                min_axis = min(min(data_set["axis"]), min_axis)

        # New axis from min to max
        n_bins = 300
        axis = np.linspace(min_axis, max_axis, n_bins)
        sep = axis[1] - axis[0]
        bin_axis = np.append(axis - 0.5 * sep, axis[-1] + sep)
        intensities = np.zeros((len(data_sets), len(axis)))

        for index, data_set in enumerate(data_sets):
            new_bins = np.digitize(data_set["axis"], bin_axis)
            boarder_bins = np.where(new_bins == n_bins)
            new_bins[boarder_bins] -= 1
            intensities[index, new_bins] += data_set["I"]

        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=figsize)

        component_names = [x.name for x in self.original_instr.make_component_subset()]
        component_names.reverse()
        if not show_comp_names:
            component_names = [""] * len(component_names)

        metadata = mon_data.metadata
        metadata.dimension = [len(axis), len(y_positions) - 1]
        metadata.limits = [0, 0, 0, 0]
        metadata.limits[0] = min(axis)
        metadata.limits[1] = max(axis)
        metadata.limits[2] = min(y_positions)
        metadata.limits[3] = max(y_positions)

        display_data = np.flip(intensities, 0)
        data = McStasDataBinned(metadata, display_data, np.zeros((1, 1)), np.zeros((1, 1)))

        data.set_plot_options(show_colorbar=False, log=True, orders_of_mag=5)
        data.set_ylabel("")

        _plot_fig_ax(data, fig, ax)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(component_names, fontsize=18)
        ax.set_xlabel(mon_data.metadata.xlabel, fontsize=18)

    def plot_0D(self, figsize=None, ax=None, fig=None, show_comp_names=True,
                y_tick_positions=None, ylimits=None):

        if figsize is None:
            figsize = (8, len(self.component_list)/5 + 1)

        intensities = []
        ray_counts = []
        component_names = []
        indicies = []

        index = 0
        for I_monitor_name, component_name in self.monitors:
            mon_data = name_search(I_monitor_name, self.data)
            values = mon_data.metadata.info["values"].split()
            # values contain strings of: Intensity, Error, Ncount
            intensities.append(float(values[0]))
            ray_counts.append(float(values[2]))
            component_names.append(component_name)
            indicies.append(index)
            index += 1

        # Extend with the last one
        intensities.append(intensities[-1])
        ray_counts.append(ray_counts[-1])
        indicies.append(index)
        component_names = [self.component_list[0].name] + component_names

        if not show_comp_names:
            component_names = [""] * len(component_names)

        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=figsize)

        intensities.reverse()
        ray_counts.reverse()
        component_names.reverse()

        if y_tick_positions is None:
            y_positions = indicies
        else:
            y_tick_positions.reverse()
            y_positions = y_tick_positions

        # Ensure x scale for intensity and n count share same tick marks
        I_limits, N_limits = common_range_limits(intensities, ray_counts)

        ax.step(intensities, y_positions, where="post", color="k", zorder=3.5)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(component_names, fontsize=18)
        ax.set_xlabel("Intensity [n/s]", fontsize=18, color="k")
        ax.set_xscale("log", nonpositive='clip')
        ax.xaxis.set_tick_params(labelsize=16)
        ax.set_xlim(I_limits)

        if ylimits is None:
            ax.set_ylim([-0.5, index + 0.5])
        else:
            ax.set_ylim(ylimits)

        ax.grid(True)

        ax2 = ax.twiny()
        ax2.step(ray_counts, y_positions, where="post", color="g", linestyle="--", zorder=3.6)
        ax2.set_xlabel("Ray count", fontsize=18, color="g")
        ax2.set_xscale("log", nonpositive='clip')
        ax2.xaxis.set_tick_params(labelsize=16, colors="g")
        ax2.set_xlim(N_limits)

def common_range_limits(data_I, data_N):
    # Convert to numpy
    data_I = np.array(data_I)
    data_I_nonzero = data_I[np.nonzero(data_I)]
    data_N = np.array(data_N)
    data_N_nonzero = data_N[np.nonzero(data_N)]

    max_I = max(data_I_nonzero)
    min_I = min(data_I_nonzero)
    I_orders_of_mag = np.log10(max_I) - np.log10(min_I)

    max_N = max(data_N_nonzero)
    min_N = min(data_N_nonzero)
    N_orders_of_mag = np.log10(max_N) - np.log10(min_N)

    I_is_largest = I_orders_of_mag > N_orders_of_mag

    if I_is_largest:
        # Use intensity scale
        max_large = max_I
        min_large = min_I
        max_small = max_N
    else:
        max_large = max_N
        min_large = min_N
        max_small = max_I

    log_extra = 0.1  # Extra scale to avoid having data just at the edge

    # Round I scale up
    log_large_scale_max = np.ceil(np.log10(max_large)) + log_extra
    log_large_scale_min = np.floor(np.log10(min_large))
    large_limits = [10 ** log_large_scale_min, 10 ** log_large_scale_max]

    # Find how many orders of mag this cover
    large_orders_of_mag = log_large_scale_max - log_large_scale_min

    # Apply same to ray count
    log_small_scale_max = np.ceil(np.log10(max_small)) + log_extra
    log_small_scale_min = log_small_scale_max - large_orders_of_mag
    small_limits = [10 ** log_small_scale_min, 10 ** log_small_scale_max]

    if I_is_largest:
        I_limits = large_limits
        N_limits = small_limits
    else:
        I_limits = small_limits
        N_limits = large_limits

    return I_limits, N_limits