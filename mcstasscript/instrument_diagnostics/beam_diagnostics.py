from mcstasscript.helper.mcstas_objects import DeclareVariable
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

class DiagnosticsPoint:
    def __init__(self, instr, comp_name, before=True, rays=50000):
        comp_name = sanitise_comp_name(comp_name)
        try:
            instr.get_component(comp_name)
        except KeyError:
            raise KeyError("Component '" + comp_name + "' not found in instrument.")

        self.component = comp_name
        self.before = before # False for after

        if isinstance(rays, str):
            if not rays == "all":
                raise ValueError("The ray keyword for a point should be all or an integer.")
        else:
            rays = int(rays)

        self.rays = rays

        # Attributes set by add_monitors
        self.filename = None
        # Attributes set by read_data
        self.recorded_rays = None

    def set_filename(self, filename):
        self.filename = filename

    def set_recorded_rays(self, rays):
        self.recorded_rays = rays

    def __eq__(self, other):
        return self.component == other.component and self.before == other.before

    def __repr__(self):
        string = "Diagnostics point "
        if self.before:
            string += "before: "
        else:
            string += "after:  "

        string += self.component.ljust(25)
        string += " - rays: "
        if self.recorded_rays is not None:
            string += str(self.recorded_rays)
            string += " / "
        string += str(self.rays)

        return string

class BeamDiagnostics(DiagnosticsInstrument):
    def __init__(self, instr):
        super().__init__(instr)

        # points to investigate with options
        self.points = []
        self.ordered_point_list = []

        # flags for monitor_nD user variables
        self.flags = []

        self.monitor_names = []

        self.views = []

        self.data = None

        self.event_plotters = []

    def __repr__(self):
        string = f"Instrument diagnostics for: {self.instr.name}\n"
        string += "Diagnostics points: \n"

        if len(self.points) == 0:
            string += "  No diagnostics points yet\n"
        for point in self.points:
            string += "  " + point.__repr__() + "\n"

        string += "Views: \n"
        if len(self.views) == 0:
            string += "  No views yet\n"

        for view in self.views:
            string += "  " + view.__repr__() + "\n"

        if len(self.flags) != 0:
            string += "Recording following user variables:\n"
        for flag in self.flags:
            string += "  " + str(flag) + "\n"

        if self.data is None:
            string += "Does not yet contain simulated data"
        else:
            string += "Does contain simulated data"

        return string

    def add_flag(self, flag):
        """
        Adds flag to be monitored in event list, maximum of 3 allowed

        The flag must be available in declared variables or user vars.

        Parameters:

        flag: str
            str with variable name to be recorded to event dataset
        """
        if not isinstance(flag, str):
            raise ValueError("flag has to be a string.")

        # find declare and user_var names in instrument
        names = [x.name for x in self.instr.declare_list
                 if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.instr.user_var_list
                  if isinstance(x, DeclareVariable)]

        if flag not in names:
            raise ValueError(f"flag {flag} was not found in declared "
                             f"variables or uservars of the instrument.")

        if len(self.flags) >= 3:
            raise ValueError("Can't add more than three flags")

        self.flags.append(flag)

    def clear_flags(self):
        """
        Clears flags
        """
        self.flags = []

    def show_flags(self):
        """
        Shows list of current flags
        """
        if self.flags is not None:
            for index, flag in enumerate(self.flags):
                print(f" user{index+1}={flag}")

    def add_point(self, before=None, after=None, rays=50000):
        """
        Adds point in which the beam is investigated with given number of rays

        Can be before and/or after components, this is chosen by using the
        appropriate keyword argument.

        Parameters:

        before : str or component instance
            Reference to component beam should be monitored just before

        after : str or component instance
            Reference to component beam should be monitored just after

        rays : int or "all"
            Number of rays to record, either integer or the string "all"
        """
        if before is None and after is None:
            raise ValueError("Specify either before or after with component name.")

        if before is not None:
            self._add_diagnostics_point(comp_name=before, before=True, rays=rays)

        if after is not None:
            self._add_diagnostics_point(comp_name=after, before=False, rays=rays)

    def _add_diagnostics_point(self, comp_name, before, rays):
        """
        Internal function to add the DiagnosticsPoint to list
        """
        point = DiagnosticsPoint(self.instr, comp_name=comp_name, before=before, rays=rays)
        if point in self.points:
            # overwrite that point
            index = self.points.index(point)
            self.points[index] = point
        else:
            # add point to list
            self.points.append(point)

    def remove_point(self, before=None, after=None):
        """
        Removes a point from the list

        Specify whether the point in question is before or after the
        given component name or instance by using the appropriate
        keyword argument

        Parameter:

        before : str or component instance
            Name or component instance for which point before should be removed

        after : str or component instance
            Name or component instance for which point after should be removed
        """
        if before is None and after is None:
            raise ValueError("Specify either before or after with component name.")

        if before is not None:
            before = sanitise_comp_name(before)
            for index, point in enumerate(self.points):
                if point.component == before and point.before:
                    del self.points[index]

        if after is not None:
            after = sanitise_comp_name(after)
            for index, point in enumerate(self.points):
                if point.component == after and not point.before:
                    del self.points[index]

    def clear_points(self):
        """
        Remove all points
        """
        self.points = []

    def show_points(self):
        """
        Shows current diagnostics points
        """
        for point in self.points:
            print(point)

    def add_view(self, axis1, axis2=None, bins=100, same_scale=False, **kwargs):
        """
        Add a view with one or two axes that will be shown at all diagnostics points

        Parameters:
        axis1: str
            Name of parameter for first axis

        axis2: str
            Name of parameter for second axis

        bins : int or list of length 2
            Number of bins for histogram (can be list of length 2 for 2D)

        same_scale : bool
            Select if the same scale should be ensured for all points with this view
        """
        view = View(axis1=axis1, axis2=axis2, bins=bins, same_scale=same_scale, **kwargs)
        self.views.append(view)

    def clear_views(self):
        """
        Clear list of views
        """
        self.views = []

    def show_views(self):
        """
        Shows views
        """
        for view in self.views:
            print(view)

    def add_monitors(self):
        """
        Adds monitors as specified by list of diagnostics points

        The method sorts the points with the component sequence so the
        resulting plots are in the correct order.
        """
        comp_names = [x.name for x in self.instr.make_component_subset()]
        self.monitor_names = []
        self.ordered_point_list = []
        point_names = [x.component for x in self.points]

        for name in comp_names:
            before_point = None
            after_point = None
            if name in point_names:
                for point in self.points:
                    if point.component == name:
                        if point.before:
                            before_point = point
                        else:
                            after_point = point

            if before_point is not None:
                self.ordered_point_list.append(before_point)
            if after_point is not None:
                self.ordered_point_list.append(after_point)

        for point in self.ordered_point_list:
            comp = self.instr.get_component(point.component)
            filename = self.add_monitor(point, comp)
            point.set_filename(filename)

    def add_monitor(self, point, comp_instance):
        """
        Adds monitor_nD event monitor to diagnostics instrument for given point

        Needs point and component instance that match

        Parameters:

        point : DiagnosticsPoint
            Point for which monitor should be added

        comp_instance : Component
            Component instance relative to which the monitor should be placed
        """

        if not point.component == comp_instance.name:
            raise RuntimeError("Given point and component instance should match!")

        user_vars = [None, None, None]
        flags_str = ""
        for index, flag in enumerate(self.flags):
            flags_str += " user" + str(index+1)
            if self.instr.mccode_version == 2:
                # Monitor_nD in McStas 2.X needs to be a raw variable
                user_vars[index] = flag
            else:
                # Monitor_nD in McStas 3.X (and onwards) needs to be a string
                user_vars[index] = '"' + flag + '"'

        if isinstance(point.rays, (float, int)):
            ray_value = point.rays
            if self.instr.mccode_version == 3:
                ray_value += 1 # In McStas 3.0 Monitor_nD grabs one event too few
            ray_str = str(int(ray_value)) # Monitor_nD seems to record one ray less than requested
        else:
            ray_str = point.rays # Case of rays set to all

        if point.before:
            name = "Diag_before_" + point.component
            options = f'"square boarders n x y z vx vy vz t{flags_str}, list {ray_str}"'
            mon = self.instr.add_component(name, "Monitor_nD", before=point.component)
        else:
            name = "Diag_after_" + point.component
            options = f'"previous n x y z vx vy vz t{flags_str}, list {ray_str}"'
            mon = self.instr.add_component(name, "Monitor_nD", after=point.component)

        mon.set_parameters(restore_neutron=1,
                           xwidth=100, yheight=100,
                           options=options,
                           user1=user_vars[0], user2=user_vars[1], user3=user_vars[2],
                           filename='"' + name + ".diag" + '"')


        mon.set_AT(comp_instance.AT_data, RELATIVE=comp_instance.AT_reference)
        if comp_instance.ROTATED_specified:
            mon.set_ROTATED(comp_instance.ROTATED_data, RELATIVE=comp_instance.ROTATED_reference)

        return name

    def run(self):
        """
        Runs diagnostics with all included points

        Saves data in data attribute and the resulting instrument can be found
        in the instr attribute
        """
        self.reset_instr()
        self.remove_previous_use()

        self.add_monitors()

        self.correct_target_index()

        self.data = self.instr.backengine()

        self.read_data()

    def read_data(self):
        """
        Reads the generated data and organizes it as event plotter instances
        """

        self.event_plotters = []

        for point in self.ordered_point_list:
            try:
                event_data = name_search(point.filename, self.data)
            except NameError:
                # Data was not generated, no neutrons reached it or simulation failed
                continue

            point.set_recorded_rays(event_data.metadata.total_N)
            plotter = event_plotter.EventPlotter(point.filename, event_data,
                                                 flag_info=self.flags)

            self.event_plotters.append(plotter)

    def plot(self):
        """
        Plots the generated data for all points with all views
        """

        if len(self.event_plotters) == 0:
            if len(self.views) == 0:
                print("No data to plot! Add views and run.")
            else:
                print("No data to plot! Use the run method to generate data.")

        overview = PlotOverview(self.event_plotters, self.views)
        overview.plot_all()

