import numpy as np

class Layer:
    def __init__(self, name, cryostat,
                 origin_to_bottom, bottom_thickness, origin_to_top, top_thickness=0.01,
                 inner_radius=None, outer_radius=None, thickness=None,
                 material="Al", p_interact=0):
        """
        Layer of cryostat with a shell made of given material and hollowed by vacuum

        Describes a layer of a cryostat with given geometry and materials. The geometry
        is specified with distance from origin to top and bottom, along with a
        thickness of these. In addition an outer and inner radius is needed, here the
        user can specify two of inner_radius, outer_radius and thickness.
        The Layer is given the cryostat object of which is it a part to access methods
        and attributes in a simple way.
        The layer is built from Union components, and so are not allowed to perfectly
        intersect the planes from other layers. These are registered and check with the
        cryostat class. If a custom material is given instead of Al, that material has
        to exist as a Union_make_material component.

        It is possible to add windows to a layer, these are added with the add_window
        method, windows can be a reduction of radius from the inside, outside or both.

        Parameters
        ----------

        origin_to_bottom: float
            Distance from origin to bottom of layer [m] (bottom thickness added)

        bottom_thickness: float
            Thickness of layer bottom [m]

        origin_to_top: float
            Distance from origin to top of layer [m] (top thickness added)

        top_thickness: float
            Thickness of layer top [m]

        inner_radius: float
            Inner radius of the cryostat layer [m]

        outer_radius: float
            Outer radius of the cryostat layer [m]

        thickness: float
            Thickness of the shell, can be provided instead of either inner or outer radius [m]

        material: string
            Material of which the cryostat layer should be made

        p_interact: float
            p_interact set for all Union geometry components
        """

        self.name = name
        self.material = material
        self.p_interact = p_interact

        self.cryostat = cryostat
        self.instr = self.cryostat.instr
        self.reference = self.cryostat.origin

        try:
            self.instr.get_component(self.material)
        except:
            raise RuntimeError("No material named '" + str(self.material)
                               + "' found in given instrument file. \n"
                               + "Construct with Union_make_material.")

        self.shell_lowest_point = -origin_to_bottom - bottom_thickness
        self.shell_highest_point = origin_to_top + top_thickness
        self.shell_center = 0.5 * (self.shell_lowest_point + self.shell_highest_point)
        self.shell_height = self.shell_highest_point - self.shell_lowest_point

        # Check with the database these wont cause a collision
        self.cryostat.add_y_plane(self.shell_lowest_point)
        self.cryostat.add_y_plane(self.shell_highest_point)

        self.vac_lowest_point = -origin_to_bottom
        self.vac_highest_point = origin_to_top
        self.vac_center = 0.5 * (self.vac_highest_point + self.vac_lowest_point)
        self.vac_height = self.vac_highest_point - self.vac_lowest_point

        # Check with the database these wont cause a collision
        self.cryostat.add_y_plane(self.vac_lowest_point)
        self.cryostat.add_y_plane(self.vac_highest_point)

        self.inner_radius, self.outer_radius = self.check_radius_input(inner_radius, outer_radius, thickness)

        # Check with the database these wont cause a collision
        self.cryostat.add_radius(self.inner_radius)
        self.cryostat.add_radius(self.outer_radius)

        # Set up shell
        layer = self.instr.add_component(self.name + "_layer", "Union_cylinder")
        layer.material_string = '"' + self.material + '"'
        layer.p_interact = self.p_interact

        layer.radius = self.outer_radius
        layer.yheight = self.shell_height

        layer.set_AT([0, self.shell_center, 0], RELATIVE=self.reference)

        self.layer = layer

        # Set up vacuum
        layer_vac = self.instr.add_component(self.name + "_layer_vac", "Union_cylinder")
        layer_vac.material_string = '"Vacuum"'

        layer_vac.radius = self.inner_radius
        layer_vac.yheight = self.vac_height

        layer_vac.set_AT([0, self.vac_center, 0], RELATIVE=self.reference)

        self.layer_vac = layer_vac

        # List of union components, highest priority first
        self.outer_cuts = []
        self.inner_cuts = []
        # self.main_union_components = [self.layer_vac, self.layer]
        self.union_components = [self.layer_vac, self.layer]

        # Prepare for windows
        self.inner_window_index = 0
        self.outer_window_index = 0

    def count_inputs(self, *args):
        """
        Counts how many of given inputs are not None
        """
        n_inputs = 0
        for arg in args:
            if arg is not None:
                n_inputs += 1
        return n_inputs

    def check_radius_input(self, inner_radius, outer_radius, thickness):
        """
        Returns inner and outer radius from user input that may include thickness

        The inner_radius, outer_radius and thickness can have one not specified,
        and this method will calculate the inner and out radius from the two given.
        A input not given is specified as None.
        """

        n_inputs = self.count_inputs(inner_radius, outer_radius, thickness)

        if n_inputs != 2:
            raise RuntimeError("Set two of inner_radius, outer_radius, and thickness.")

        if inner_radius is None:
            inner_radius = outer_radius - thickness
        else:
            inner_radius = inner_radius

        if outer_radius is None:
            outer_radius = inner_radius + thickness
        else:
            outer_radius = outer_radius

        return inner_radius, outer_radius

    def add_window(self, inner_radius=None, outer_radius=None, thickness=None,
                   height=None, origin_to_top=None, origin_to_bottom=None):
        """
        Adds 360 deg window in given height interval

        Adds window as a reduction in thickness of the layer in a certain height
        interval. The reduction can be both from the outside, inside or both.
        If only outer_radius is given, a reduction of the outside is assumed.
        If only inner_radius is given, the window will be on the inside.
        If two of the three parameters inner_radius, outer_radius and thickness
        is given, material will be removed from both the outside and inside, only
        use this if necessary, never specify inner / outer radius identical to the
        main layer.
        Any two of height, origin_to_top and origin_to_bottom can be given, or if
        the window is symmetrical in height around the origin position, the height
        alone is sufficient.
        It is possible to add multiple multiple windows by calling this method
        multiple times, add the tallest first.

        Keyword arguments
        -----------------

        inner_radius : float
            inner radius of window (should be larger than main inner_radius)

        outer_radius : float
            outer radius of window (should be less than main outer_radius)

        thickness : float
            thickness of the window

        height : float
            height of window

        origin_to_top : float
            distance from origin to top of window

        origin_to_bototm : float
            distance from origin to bottom of window
        """

        # Assume no cuts are made
        outer_cut = False
        inner_cut = False

        # Check if cuts are made to inner, outer or both
        if self.count_inputs(inner_radius, outer_radius, thickness) == 1:
            if inner_radius is not None:
                inner_cut = True
                outer_radius = self.outer_radius
            elif outer_radius is not None:
                outer_cut = True
                inner_radius = self.inner_radius
            else:
                # could center this window
                raise RuntimeError("Cant tell if window is on inside or outside.")

        inner_radius, outer_radius = self.check_radius_input(inner_radius, outer_radius, thickness)

        if inner_radius < self.inner_radius:
            raise RuntimeError("Window has smaller inner radius than main layer, needs to be larger.")

        if outer_radius > self.outer_radius:
            raise RuntimeError("Window has larger outer radius than main layer, needs to be smaller.")

        if abs(inner_radius - self.inner_radius) > 1E-5:
            inner_cut = True

        if abs(outer_radius - self.outer_radius) > 1E-5:
            outer_cut = True

        if self.count_inputs(height, origin_to_top, origin_to_bottom) == 3:
            raise RuntimeError("Ambigious definition of window height.")

        if height is not None:
            window_top = height / 2
            window_bottom = -height / 2
            if origin_to_top is not None:
                window_top = origin_to_top
                window_bottom = origin_to_top - height
            if origin_to_bottom is not None:
                window_top = -origin_to_bottom + height
                window_bottom = -origin_to_bottom
        else:
            window_top = origin_to_top
            window_bottom = -origin_to_bottom

        window_height = window_top - window_bottom
        window_position = 0.5 * (window_top + window_bottom)

        if outer_cut:
            name = self.name + "_outer_cut_" + str(self.outer_window_index)
            o_cut = self.instr.add_component(name, "Union_cylinder")
            o_cut.set_AT([0, window_position, 0], RELATIVE=self.reference)

            o_cut.material_string = '"Vacuum"'
            o_cut.radius = self.outer_radius + 1E-6
            o_cut.yheight = window_height + 1E-6

            # Check these radius and y_planes do not collide with others
            self.cryostat.add_radius(o_cut.radius)
            self.cryostat.add_y_plane(window_top + 0.5E-6)
            self.cryostat.add_y_plane(window_bottom - 0.5E-6)

            name = self.name + "_outer_cut_replace_" + str(self.outer_window_index)
            o_cut_m = self.instr.add_component(name, "Union_cylinder")
            o_cut_m.set_AT([0, window_position, 0], RELATIVE=self.reference)

            o_cut_m.material_string = '"' + self.material + '"'
            o_cut_m.p_interact = self.p_interact
            o_cut_m.radius = outer_radius
            o_cut_m.yheight = window_height + 5E-6

            # Check these radius and y_planes do not collide with others
            self.cryostat.add_radius(o_cut_m.radius)
            self.cryostat.add_y_plane(window_top + 2.5E-6)
            self.cryostat.add_y_plane(window_bottom - 2.5E-6)

            # Update list of outer cut components, order is important
            self.outer_cuts = [o_cut_m, o_cut] + self.outer_cuts

            self.outer_window_index += 1

        if inner_cut:
            name = self.name + "_inner_cut_" + str(self.inner_window_index)
            i_cut = self.instr.add_component(name, "Union_cylinder")
            i_cut.set_AT([0, window_position, 0], RELATIVE=self.reference)

            i_cut.material_string = '"Vacuum"'
            i_cut.radius = inner_radius
            i_cut.yheight = window_height

            # Check these radius and y_planes do not collide with others
            self.cryostat.add_radius(i_cut.radius)
            self.cryostat.add_y_plane(window_top)
            self.cryostat.add_y_plane(window_bottom)

            # Update list of inner cut components, order is important
            self.inner_cuts = [i_cut] + self.inner_cuts

            self.inner_window_index += 1

        # Create full list of Union components used in order from highest to lowest priority
        self.union_components = [self.layer_vac] + self.inner_cuts + self.outer_cuts + [self.layer]


class Cryostat:
    def __init__(self, name, instr, reference="PREVIOUS",
                 min_priority=20, max_priority=100):
        """
        Handles addition of a cryostat with multiple layers and windows

        This class can add a description of a cryostat to a McStasScript
        instrument object. The cryostat is made of several layers consisting
        of a shell and vacuum, these are added with the add_layer method and
        should be added in the order from smallest (inside) to largest. Each
        layer can be accessed with the last_layer attribute, and one can add
        windows to each layer. Consult the Layer class for details. When all
        layers are added, it is necessary to build the cryostat, this step is
        necessary to adjust the priority of each Union component.
        The position of the cryostat can be adjusted with the set_AT and
        set_ROTATED methods that works as the standard McStasScript versions.
        It is possible to add logger components that show scattering in the
        system with the add_spatial_loggers method.
        The position of the cryostat refers to the sample position and is
        called the origin. It can be placed in McStas with set_AT and
        set_ROTATED methods on the cryostat object.

        Parameters
        ----------

        name : str
            Name of the cryostat, will be used in naming of all added components

        instr : instrument object inherited from McCode_instr
            Instrument object where the cryostat should be added

        Keyword arguments
        -----------------

        reference : str
            Name of the component which the cryostat should be located relative to

        min_priority : float
            Minimum Union priority used (default 20)

        max_priority : float
            Maximum Union priority used, add a sample with higher priority (default 100)
        """
        self.name = str(name)
        self.instr = instr
        self.reference = reference
        self.min_priority = min_priority
        self.max_priority = max_priority

        self.layers = []
        self.last_layer = None

        self.origin = self.instr.add_component(self.name, "Arm")
        self.origin.set_AT([0, 0, 0], RELATIVE=reference)

        # Check if Al exists, if not add it!
        try:
            Al_component = None
            Al_component = instr.get_component("Al")
        except:
            Al_inc = self.instr.add_component("Al_inc", "Incoherent_process")
            Al_inc.sigma = 4 * 0.0082  # Incoherent cross section in Barns
            Al_inc.unit_cell_volume = 66.4  # Unit cell volume in AA^3

            Al_pow = self.instr.add_component("Al_pow", "Powder_process")
            Al_pow.reflections = "\"Al.laz\""  # Data file with powder lines

            Al = self.instr.add_component("Al", "Union_make_material")
            Al.my_absorption = "100*4*0.231/66.4"  # Inverse penetration depth in 1/m
            Al.process_string = '"Al_inc,Al_pow"'  # Make a material with aluminium incoherent and aluminium powder`

        # Set intial state of loggers, not having been added yet
        # Important to avoid multiple sets of the same kind added
        self.spatial_loggers_set = False
        self.time_logger_set = False
        self.animation_loggers = []

        # Height database
        self.used_y_planes = []
        self.used_radius_values = []

    def set_AT(self, *args, **kwargs):
        """
        Sets position of cryostat, sample position used as reference
        """
        self.origin.set_AT(*args, **kwargs)

    def set_ROTATED(self, *args, **kwargs):
        """
        Sets rotation of cryostat, sample position used as reference
        """
        self.origin.set_AT(*args, **kwargs)

    def add_layer(self, *args, **kwargs):
        """
        Adds layer to cryostat, all arguments passed to Layer. Consult Layer
        class for additional help on adding a layer.
        """

        if "name" not in kwargs:
            kwargs["name"] = self.name + "_layer_" + str(len(self.layers))

        if "cryostat" not in kwargs:
            kwargs["cryostat"] = self

        layer = Layer(*args, **kwargs)
        self.last_layer = layer
        self.layers.append(layer)

    def find_cryostat_dimensions(self):
        """
        Returns spatial extend of cryostat with padding for plotting

        Returns tuple with x, lowest y, highest y and z
        """
        # find outer dimensions:
        max_radius = self.last_layer.outer_radius
        highest_point = self.last_layer.shell_highest_point
        lowest_point = self.last_layer.shell_lowest_point

        if highest_point > abs(lowest_point):
            height = 2 * highest_point
        else:
            height = 2 * abs(lowest_point)

        mon_z = 1.1 * max_radius
        mon_x = 1.1 * max_radius
        if lowest_point < 0:
            mon_y_low = 1.1 * lowest_point
        else:
            mon_y_low = 0.9 * lowest_point

        if highest_point > 0:
            mon_y_high = 1.1 * highest_point
        else:
            mon_y_high = 0.9 * highest_point

        return mon_x, mon_y_low, mon_y_high, mon_z

    def add_spatial_loggers(self, n_x=500, n_y=500, n_z=500):
        """
        Adds spatial Union loggers to the code

        The spatial loggers will be set so they cover the entire cryostat and
        include views from top, side and front along with a close up of the
        windows as a slice in zy with limited z of +/- 5 mm.

        Keyword arguments
        -----------------

        n_x : int
            Number of bins in x direction

        n_y : int
            Number of bins in y direction

        n_z : int
            Number of bins in z direction
        """

        if self.spatial_loggers_set:
            raise RuntimeError("Can not add two sets of spatial loggers.")

        self.spatial_loggers_set = True

        # find outer dimensions:
        mon_x, mon_y_low, mon_y_high, mon_z = self.find_cryostat_dimensions()

        space_2D_zx = self.instr.add_component(self.name + "_logger_space_zx", "Union_logger_2D_space")
        space_2D_zx.set_AT([0, 0, 0], RELATIVE=self.origin)
        space_2D_zx.filename = '"' + self.name + '_space_zx.dat"'
        space_2D_zx.D_direction_1 = '"z"'
        space_2D_zx.n1 = n_z
        space_2D_zx.D1_min = -mon_z
        space_2D_zx.D1_max = mon_z
        space_2D_zx.D_direction_2 = '"x"'
        space_2D_zx.n2 = n_x
        space_2D_zx.D2_min = -mon_x
        space_2D_zx.D2_max = mon_x

        space_2D_zy = self.instr.add_component(self.name + "_logger_space_zy", "Union_logger_2D_space")
        space_2D_zy.set_AT([0, 0, 0], RELATIVE=self.origin)
        space_2D_zy.filename = '"' + self.name + '_space_zy.dat"'
        space_2D_zy.D_direction_1 = '"z"'
        space_2D_zy.n1 = n_z
        space_2D_zy.D1_min = -mon_z
        space_2D_zy.D1_max = mon_z
        space_2D_zy.D_direction_2 = '"y"'
        space_2D_zy.n2 = n_y
        space_2D_zy.D2_min = mon_y_low
        space_2D_zy.D2_max = mon_y_high

        space_2D_xy = self.instr.add_component(self.name + "_logger_space_xy", "Union_logger_2D_space")
        space_2D_xy.set_AT([0, 0, 0], RELATIVE=self.origin)
        space_2D_xy.filename = '"' + self.name + '_space_xy.dat"'
        space_2D_xy.D_direction_1 = '"x"'
        space_2D_xy.n1 = n_x
        space_2D_xy.D1_min = -mon_x
        space_2D_xy.D1_max = mon_x
        space_2D_xy.D_direction_2 = '"y"'
        space_2D_xy.n2 = n_y
        space_2D_xy.D2_min = mon_y_low
        space_2D_xy.D2_max = mon_y_high

        # Adding monitor that shows windows better
        lowest_inner_radius = self.layers[0].inner_radius
        largest_outer_radius = self.layers[-1].outer_radius

        space_3D_zy = self.instr.add_component(self.name + "_logger_space_zy_close", "Union_logger_3D_space")
        space_3D_zy.set_AT([0, 0, 0], RELATIVE=self.origin)
        space_3D_zy.filename = '"' + self.name + '_space_zy_close.dat"'
        space_3D_zy.D_direction_1 = '"z"'
        space_3D_zy.n1 = n_z
        space_3D_zy.D1_min = -1.02 * largest_outer_radius
        space_3D_zy.D1_max = -0.9 * lowest_inner_radius
        space_3D_zy.D_direction_2 = '"y"'
        space_3D_zy.n2 = n_y
        space_3D_zy.D2_min = mon_y_low
        space_3D_zy.D2_max = mon_y_high
        space_3D_zy.D_direction_3 = '"x"'
        space_3D_zy.n3 = 1
        space_3D_zy.D3_min = -0.005
        space_3D_zy.D3_max = 0.005

    def add_time_histogram(self, t_min=0, t_max=0.1):
        """
        Adds histogram of scattering intensity as function of time

        Very useful when setting time range for animation, only one can be added.

        Parameters
        ----------

        t_min : float
            Lowest time recorded in [s]

        t_max : float
            Highest time recorded in [s]
        """

        if self.time_logger_set:
            raise RuntimeError("Can not add two sets of time_histogram loggers.")

        self.time_logger_set = True

        time_mon = self.instr.add_component(self.name + "_logger_time", "Union_logger_1D")
        time_mon.variable = '"time"'
        time_mon.min_value = t_min
        time_mon.max_value = t_max
        time_mon.n1 = 1000

    def add_animation(self, t_min=0, t_max=0.1, n_frames=10,
                      d1="z", n1=300, d2="y", n2=300):
        """
        Adds 2D_space_time logger that records the information necessary for animation

        Adds a 2D_space_time logger that records the requested number of frames, n_frames.
        The time span of both is from t_min to t_max. The default orientation is in the zy
        plane, but this can be chosen along with the desired resolution.
        Errors can happen with too many empty frames, so it is recommended to set
        t_min close to the first scattering time.
        Select the appropriate animation data from simulation output and use
        plotter.make_animation with a filename to save the animation as a gif.

        Parameters
        ----------

        t_min : float
            Lowest time recorded in [s]

        t_max : float
            Highest time recorded in [s]

        n_frames : int
            Number of frames in space 2D time logger

        d1 : str
            First direction of space 2D time logger, "x", "y" or "z"

        n1 : int
            Number of bins in first direction

        d2 : str
            Second direction of space 2D time logger, "x", "y" or "z"

        n2 : int
            Number of bins in second direction
        """

        if d1 == d2:
            raise RuntimeError("Cant have both d1 and d2 along the same axis.")

        if d1 + d2 in self.animation_loggers:
            raise RuntimeError("Can only add one animation logger with the same axis.")

        self.animation_loggers.append(d1 + d2)

        # find outer dimensions:
        mon_x, mon_y_low, mon_y_high, mon_z = self.find_cryostat_dimensions()

        name = self.name + "_logger_space_" + d1 + d2 + "_time"
        ani_logger = self.instr.add_component(name, "Union_logger_2D_space_time")
        ani_logger.set_AT([0, 0, 0], RELATIVE=self.origin)
        ani_logger.filename = '"' + name + '.dat"'
        ani_logger.time_bins = int(n_frames)
        ani_logger.time_min = t_min
        ani_logger.time_max = t_max

        ani_logger.D_direction_1 = '"' + d1 + '"'
        ani_logger.n1 = int(n1)
        if d1 == "x":
            ani_logger.D1_min = -mon_x
            ani_logger.D1_max = mon_x
        elif d1 == "y":
            ani_logger.D1_min = mon_y_low
            ani_logger.D1_max = mon_y_high
        elif d1 == "z":
            ani_logger.D1_min = -mon_z
            ani_logger.D1_max = mon_z
        else:
            raise RuntimeError("Dimension: '" + d1 + "' not recoignized, must be x, y or z.")

        ani_logger.D_direction_2 = '"' + d2 + '"'
        ani_logger.n2 = int(n2)
        if d2 == "x":
            ani_logger.D2_min = -mon_x
            ani_logger.D2_max = mon_x
        elif d2 == "y":
            ani_logger.D2_min = mon_y_low
            ani_logger.D2_max = mon_y_high
        elif d2 == "z":
            ani_logger.D2_min = -mon_z
            ani_logger.D2_max = mon_z
        else:
            raise RuntimeError("Dimension: '" + d2 + "' not recoignized, must be x, y or z.")

    def add_y_plane(self, value):
        """
        Adds a y plane to database, checking if it is already present

        If duplicates occur, errors would happen in the Union algorithm
        """

        for y_plane in self.used_y_planes:
            if abs(y_plane - value) < 1E-7:
                raise RuntimeError("Two planes overlap with the same y value.")

        self.used_y_planes.append(value)

    def add_radius(self, value):
        """
        Adds a radius to databse, checking if it is already present

        If duplicates occur, errors would happen in the Union algorithm
        """

        for radius in self.used_radius_values:
            if abs(radius - value) < 1E-7:
                raise RuntimeError("The radius of two cylinders are almost equal.")

        self.used_radius_values.append(value)

    def build(self, include_master=True):
        """
        Assigns priorities to the internal components of the cryostat

        The build method must be called after all layers and windows are added
        in order for priorities to be assigned according to the priority window
        given at class initialization. It is optional to include the Union_master
        with the build method, if it is not included it must be manually provided
        later.

        Keyword arguments
        -----------------

        inclde_master : bool
            If True a Union_master component is added to the instrument file
        """

        union_component_list = []

        for layer in self.layers:
            union_component_list += layer.union_components

        priorities = np.linspace(self.max_priority, self.min_priority, len(union_component_list))

        for component, priority in zip(union_component_list, priorities):
            component.priority = priority

        if include_master:
            master = self.instr.add_component(self.name + "_master", "Union_master")

