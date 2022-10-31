import matplotlib.pyplot as plt
import numpy as np

from mcstasscript.instrument_diagnostics.diagnostics_instrument import DiagnosticsInstrument
from mcstasscript.interface.functions import name_search

class IntensityDiagnostics(DiagnosticsInstrument):
    def __init__(self, instr):
        super().__init__(instr)

        self.data = None
        self.monitors = None

    def add_monitor(self, before):
        name = "I_before_" + before.name
        mon = self.instr.add_component(name, "Monitor_nD", before=before)

        options = f'"square boarders intensity"'
        mon.set_parameters(restore_neutron=1,
                           xwidth=100, yheight=100,
                           options=options,
                           filename='"' + name + ".diag" + '"')

        mon.set_AT(before.AT_data, RELATIVE=before.AT_reference)
        if before.ROTATED_specified:
            mon.set_ROTATED(before.ROTATED_data, RELATIVE=before.ROTATED_reference)

        return name

    def run(self):#, start=None, end=None):
        self.reset_instr()
        self.remove_previous_use()

        self.monitors = []
        for comp in self.component_list[1:]:
            mon_name = self.add_monitor(comp)
            self.monitors.append((mon_name, comp.name))

        self.correct_target_index()

        self.data = self.instr.backengine()

    def plot(self, figsize=None, ax=None, show_comp_names=True,
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

        ax.step(intensities, y_positions, where="post", color="k", zorder=3.5)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(component_names, fontsize=18)
        ax.set_xlabel("Intensity [n/s]", fontsize=18, color="k")
        ax.set_xscale("log", nonpositive='clip')
        ax.xaxis.set_tick_params(labelsize=16)

        if ylimits is None:
            ax.set_ylim([-0.5, index + 0.5])
        else:
            ax.set_ylim(ylimits)

        ax.grid(True)

        ax2 = ax.twiny()
        ax2.step(ray_counts, y_positions, where="post", color="g", linestyle="--", zorder=3.6)
        ax2.set_xlabel("Ray count", fontsize=18, color="g")
        ax2.set_xscale("log", nonpositive='clip')
        ax2.xaxis.set_tick_params(labelsize=16)
        xlim = ax2.get_xlim()
        ax2.set_xlim([xlim[0]*0.9, xlim[1]*1.1])
