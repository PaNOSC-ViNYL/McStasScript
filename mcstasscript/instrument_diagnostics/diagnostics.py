import matplotlib.pyplot as plt
import numpy as np
import copy

from mcstasscript.helper.mcstas_objects import Component
from mcstasscript.instrument_diagnostics.beam_diagnostics import BeamDiagnostics
from mcstasscript.instrument_diagnostics.intensity_diagnostics import IntensityDiagnostics


class Diagnostics:
    def __init__(self, instr):
        self.diag_beam = BeamDiagnostics(instr)
        self.diag_intensity = IntensityDiagnostics(instr)




def sanitise_comp_name(comp_name):
    if isinstance(comp_name, Component):
        comp_name = Component.name

    if not isinstance(comp_name, str):
        raise ValueError("comp_name should be a string or component object!")

    return comp_name

class DiagnosticsInstrument:
    def __init__(self, instr):
        self.original_instr = instr
        self.instr = None
        self.reset_instr()

        self.component_list = self.instr.make_component_subset()

    def reset_instr(self):
        self.instr = copy.deepcopy(self.original_instr)

    def remove_previous_use(self):
        self.component_list = self.instr.make_component_subset()
        previous_component = None
        for comp in self.component_list:
            if comp.AT_reference == "PREVIOUS":
                comp.set_AT_RELATIVE(previous_component)

            if comp.ROTATED_specified:
                if comp.ROTATED_reference == "PREVIOUS":
                    comp.set_ROTATED_RELATIVE(previous_component)

            previous_component = comp

    def correct_target_index(self):
        """
        Need to correct target_index based on original instrument
        """
        original_component_list = self.original_instr.make_component_subset()
        original_comp_names = [x.name for x in original_component_list]

        modified_component_list = self.instr.make_component_subset()
        modified_comp_names = [x.name for x in modified_component_list]

        for comp in original_component_list:
            # Find components that use target index

            if not hasattr(comp, "target_index"):
                # Component doesnt have the target_index setting
                continue
            if comp.target_index is None:
                # A value has not been specified for target_index setting
                continue
            if comp.target_index == 0:
                # target_index is disabled
                continue

            # Only here if target_index is used, correct it in modified instr

            # Find original index and the name of the original target
            original_comp_index = original_comp_names.index(comp.name)
            comp_target_name = original_comp_names[original_comp_index + comp.target_index]

            # Find index of the original and target in modified instrument
            modified_comp_index = modified_comp_names.index(comp.name)
            index_of_new_target = modified_comp_names.index(comp_target_name)
            new_target_index = index_of_new_target - modified_comp_index

            # Apply the new target_index to the component in the modified instrument
            modified_comp = self.instr.get_component(comp.name)
            modified_comp.target_index = new_target_index

class DiagnosticsOld:
    def __init__(self, instr):
        self.original_instr = instr
        self.instr = None
        self.reset_instr()

        # Set of Component names
        self.points = set()
        self.point_collect_rays = {}
        self.monitor_names = {}

        self.views = []

        self.data = None

        self.event_plotters = []

        # Analysis
        self.I_data = None
        self.I_monitors = None

    def reset_instr(self):
        self.instr = copy.deepcopy(self.original_instr)

    def add_point(self, comp_name, rays=50000):
        comp_name = sanitise_comp_name(comp_name)
        try:
            self.instr.get_component(comp_name)
        except KeyError:
            raise KeyError("Component '" + comp_name + "' not found in instrument.")

        self.points.add(comp_name)

        if not isinstance(rays, int):
            if not rays == "all":
                raise ValueError("The ray keyword for a point should be all or an integer")

        self.point_collect_rays[comp_name] = rays

    def remove_point(self, comp_name):
        comp_name = sanitise_comp_name(comp_name)
        self.points.remove(comp_name)
        self.point_collect_rays.remove(comp_name)

    def add_view(self, axis1, axis2=None, bins=100, same_scale=True, **kwargs):
        view = View(axis1=axis1, axis2=axis2, bins=bins, same_scale=same_scale, **kwargs)
        self.views.append(view)

    def clear_views(self):
        self.views = []

    def add_monitors(self):
        comp_names = [x.name for x in self.instr.make_component_subset()]
        self.monitor_names = {}
        ordered_point_list = []
        for name in comp_names:
            if name in self.points:
                ordered_point_list.append(name)

        for name in ordered_point_list:
            comp = self.instr.get_component(name)
            file_name = self.add_monitor(comp)
            self.monitor_names[name] = file_name

    def add_monitor(self, before):
        name = "Diag_before_" + before.name
        mon = self.instr.add_component(name, "Monitor_nD", before=before)

        rays = self.point_collect_rays[before.name]
        options = f'"square boarders n x y z vx vy vz t, list {rays} neutrons"'
        mon.set_parameters(restore_neutron=1,
                           xwidth=100, yheight=100,
                           options=options,
                           filename='"' + name + ".diag" + '"')

        mon.set_AT(before.AT_data, RELATIVE=before.AT_reference)
        if before.ROTATED_specified:
            mon.set_ROTATED(before.ROTATED_data, RELATIVE=before.ROTATED_reference)

        return name

    def run(self):
        self.reset_instr()
        self.remove_previous_use()

        self.add_monitors()

        self.correct_target_index()

        self.data = self.instr.backengine()

        self.read_data()

    def read_data(self):

        self.event_plotters = []
        for comp in self.monitor_names:
            name = self.monitor_names[comp]
            event_data = name_search(name, self.data)
            plotter = event_plotter.EventPlotter(name, event_data)

            self.event_plotters.append(plotter)

    def plot(self):

        overview = PlotOverview(self.event_plotters, self.views)
        overview.plot_all()

    def remove_previous_use(self):
        self.I_component_list = self.instr.make_component_subset()
        previous_component = None
        for comp in self.I_component_list:
            if comp.AT_reference == "PREVIOUS":
                comp.set_AT_RELATIVE(previous_component)

            if comp.ROTATED_specified:
                if comp.ROTATED_reference == "PREVIOUS":
                    comp.set_ROTATED_RELATIVE(previous_component)

            previous_component = comp

    def correct_target_index(self):
        """
        Need to correct target_index based on original instrument
        """
        original_component_list = self.original_instr.make_component_subset()
        original_comp_names = [x.name for x in original_component_list]

        modified_component_list = self.instr.make_component_subset()
        modified_comp_names = [x.name for x in modified_component_list]

        for comp in original_component_list:
            # Find components that use target index

            if not hasattr(comp, "target_index"):
                # Component doesnt have the target_index setting
                continue
            if comp.target_index is None:
                # A value has not been specified for target_index setting
                continue
            if comp.target_index == 0:
                # target_index is disabled
                continue

            # Only here if target_index is used, correct it in modified instr

            # Find original index and the name of the original target
            original_comp_index = original_comp_names.index(comp.name)
            comp_target_name = original_comp_names[original_comp_index + comp.target_index]

            # Find index of the original and target in modified instrument
            modified_comp_index = modified_comp_names.index(comp.name)
            index_of_new_target = modified_comp_names.index(comp_target_name)
            new_target_index = index_of_new_target - modified_comp_index

            # Apply the new target_index to the component in the modified instrument
            modified_comp = self.instr.get_component(comp.name)
            modified_comp.target_index = new_target_index

    def add_I_monitor(self, before):
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

    def intensity_analysis(self):#, start=None, end=None):
        self.reset_instr()
        self.remove_previous_use()

        self.I_monitors = []
        for comp in self.I_component_list[1:]:
            mon_name = self.add_I_monitor(comp)
            self.I_monitors.append((mon_name, comp.name))

        self.correct_target_index()

        self.I_data = self.instr.backengine()

    def plot_I_analysis(self, figsize=None):

        if figsize is None:
            figsize = (8, len(self.I_component_list)/5 + 1)

        intensities = []
        ray_counts = []
        component_names = []
        indicies = []

        index = 0
        for I_monitor_name, component_name in self.I_monitors:
            mon_data = name_search(I_monitor_name, self.I_data)
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
        component_names = [self.I_component_list[0].name] + component_names

        fig, ax = plt.subplots(1, 1, figsize=figsize)

        intensities.reverse()
        ray_counts.reverse()
        component_names.reverse()

        ax.step(intensities, indicies, where="post", color="k")
        ax.set_yticks(indicies)
        ax.set_yticklabels(component_names, fontsize=18)
        ax.set_xlabel("Intensity [n/s]", fontsize=18, color="k")
        ax.set_xscale("log", nonpositive='clip')
        ax.xaxis.set_tick_params(labelsize=16)
        ax.set_ylim([-0.5, index + 0.5])

        ax.grid(True)

        ax2 = ax.twiny()
        ax2.step(ray_counts, indicies, where="post", color="g", linestyle="--")
        ax2.set_xlabel("Ray count", fontsize=18, color="g")
        ax2.set_xscale("log", nonpositive='clip')
        ax2.xaxis.set_tick_params(labelsize=16)
        xlim = ax2.get_xlim()
        ax2.set_xlim([xlim[0]*0.9, xlim[1]*1.1])


