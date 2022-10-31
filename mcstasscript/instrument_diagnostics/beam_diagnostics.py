from mcstasscript.helper.mcstas_objects import Component
from mcstasscript.instrument_diagnostics.diagnostics_instrument import DiagnosticsInstrument
from mcstasscript.instrument_diagnostics.view import View
from mcstasscript.instrument_diagnostics.plot_overview import PlotOverview
from mcstasscript.instrument_diagnostics import event_plotter
from mcstasscript.interface.functions import name_search

def sanitise_comp_name(comp_name):
    if isinstance(comp_name, Component):
        comp_name = Component.name

    if not isinstance(comp_name, str):
        raise ValueError("comp_name should be a string or component object!")

    return comp_name


class BeamDiagnostics(DiagnosticsInstrument):
    def __init__(self, instr):
        super().__init__(instr)

        # Set of Component names
        self.points = set()
        self.point_collect_rays = {}
        self.monitor_names = {}

        self.views = []

        self.data = None

        self.event_plotters = []

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
        del self.point_collect_rays[comp_name]

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

