import matplotlib.pyplot
import numpy as np
import copy
import re


class McStasMetaData:
    """
    Class for holding metadata for McStas dataset, is to be read from
    mccode.sim file.

    Attributes
    ----------
    info : dict
        Contains read strings from mccode.sim in key, value

    dimension : Int or List of Int
        Int for 1d data set with lenght of data, Array for 2d with each
        length

    component_name : str
        Name of component in McStas file

    filename : str
        Name of data file to read

    limits : List
        Limits for monitor, length=2 for 1d data and length=4 for 2d
        data, for example spatial or time limits for monitor

    title : str
        Title of monitor when plotting, placed above plot

    xlabel : str
        Text for xlabel when plotting

    ylabel : str
        Text for ylabel when plotting

    Methods
    -------
    add_info(key,value)
        Adds an element to the info dictionary

    extract_info()
        Unpacks the information in info to class attributes

    set_title(string)
        Overwrites current title

    set_xlabel(string)
        Overwrites current xlabel

    set_ylabel(string)
        Overwrites current ylabel
    """

    def __init__(self):
        """Creating a new instance, no parameters"""
        self.info = {}

        self.component_name = None
        self.parameters = None
        self.filename = None
        self.dimension = None
        self.limits = []

        self.xlabel = None
        self.ylabel = None
        self.zlabel = None
        self.title = None

        self.total_I = None
        self.total_E = None
        self.total_N = None

    def add_info(self, key, value):
        """Adding information to info dict"""
        self.info[key] = value

    def extract_info(self):
        """Extracting information from info dict to class attributes"""

        # Extract dimension
        if "type" in self.info:
            type_data = self.info["type"]
            if "array_0d" in type_data:
                self.dimension = 0
            if "array_1d" in type_data:
                type_data = type_data.split("(")[1]
                type_data = type_data.split(")")[0]
                self.dimension = int(type_data)
            if "array_2d" in type_data:
                self.dimension = []
                type_string1 = type_data.split(",")[0]
                type_string1 = type_string1.split("(")[1]
                self.dimension.append(int(type_string1))

                type_string2 = type_data.split(",")[1]
                type_string2 = type_string2.split(")")[0]
                self.dimension.append(int(type_string2))
        else:
            raise NameError("No type in mccode data section!")

        # Extract component name
        if "component" in self.info:
            self.component_name = self.info["component"].rstrip()

        if "Parameters" in self.info:
            self.parameters = self.info["Parameters"]

        # Extract filename
        if "filename" in self.info:
            self.filename = self.info["filename"].rstrip()
        else:
            # Monitors without output files do exist
            print("The component named \"" + self.component_name
                  + "\" had no data file and will not be loaded.")
            self.filename = ""

        # Extract limits
        self.limits = []
        if "xylimits" in self.info:
            # find the four numbers xmin, xmax, ymin, ymax
            temp_str = self.info["xylimits"]
            limits_string = temp_str.split()
            for limit in limits_string:
                self.limits.append(float(limit))

        if "xlimits" in self.info:
            # find the two numbers, xmin, xmax
            temp_str = self.info["xlimits"]
            limits_string = temp_str.split()
            for limit in limits_string:
                self.limits.append(float(limit))

        # Extract plotting labels and title
        if "xlabel" in self.info:
            self.xlabel = self.info["xlabel"].rstrip()
        if "ylabel" in self.info:
            self.ylabel = self.info["ylabel"].rstrip()
        if "zlabel" in self.info:
            self.zlabel = self.info["zlabel"].rstrip()
        if "title" in self.info:
            self.title = self.info["title"].rstrip()

        if "values" in self.info:
            value_list = self.info["values"]
            value_list = value_list.strip().split(" ")
            self.total_I = float(value_list[0])
            self.total_E = float(value_list[1])
            self.total_N = float(value_list[2])

    def set_title(self, string):
        """Sets title for plotting"""
        self.title = string

    def set_xlabel(self, string):
        """Sets xlabel for plotting"""
        self.xlabel = string

    def set_ylabel(self, string):
        """Sets ylabel for plotting"""
        self.ylabel = string

    def set_zlabel(self, string):
        """Sets zlabel for plotting"""
        self.zlabel = string

    def __repr__(self):
        string = "metadata object\n"
        if self.component_name is not None:
            string += "component_name: " + self.component_name + "\n"

        if self.filename is not None:
            string += "filename: " + str(self.filename) + "\n"

        if self.dimension is not None:
            if type(self.dimension) == int and self.dimension == 0:
                string += "0D data"
                if self.xlabel is not None:
                    string += " " + self.xlabel + "\n"
                if self.ylabel is not None:
                    string += " " + self.ylabel + "\n"
                if self.zlabel is not None:
                    string += " " + self.zlabel + "\n"

            elif type(self.dimension) == int and self.dimension != 0:
                string += "1D data of length " + str(self.dimension) + "\n"
                if self.limits is not None:
                    string += "  [" + str(self.limits[0]) + ": "
                    string += str(self.limits[1]) + "]"
                if self.xlabel is not None:
                    string += " " + self.xlabel + "\n"
                if self.ylabel is not None:
                    string += " " + self.ylabel + "\n"
                if self.zlabel is not None:
                    string += " " + self.zlabel + "\n"

            elif len(self.dimension) == 2:
                string += "2D data of dimension (" + str(self.dimension[0])
                string += ", " + str(self.dimension[1]) + ")\n"
                if self.xlabel is not None:
                    if self.limits is not None:
                        string += "  [" + str(self.limits[0]) + ": "
                        string += str(self.limits[1]) + "]"
                    string += " " + self.xlabel + "\n"

                if self.ylabel is not None:
                    if self.limits is not None and len(self.limits) == 4:
                        string += "  [" + str(self.limits[2]) + ": "
                        string += str(self.limits[3]) + "]"
                    string += " " + self.ylabel + "\n"

                if self.zlabel is not None:
                    string += " " + self.zlabel + "\n"

        if self.parameters is not None and len(self.parameters)>0:
            string += "Instrument parameters: \n"
            for key in self.parameters:
                string += " " + str(key) + " = "
                string += str(self.parameters[key]) + "\n"

        return string


class McStasPlotOptions:
    """
    Class that holds plotting options related to McStas data set

    Attributes
    ----------
    log : bool, default False
        To plot on logarithmic or not, standard is linear

    orders_of_mag : float, default 300
        If plotting on log scale, restrict max range to orders_of_mag
        below maximum value

    colormap : string, default jet
        Chosen colormap for 2d data, should be available in matplotlib

    show_colorbar : bool, default True
        Selects if colorbar should be shown or not

    cut_max : float, default 1
        Factor multiplied onto maximum data value to set upper plot limit

    cut_min : float, default 0
        Removes given fraction of the plot range from the lower limit

    x_limit_multiplier : float, default 1
        Multiplies x axis limits with factor, useful for unit changes

    y_limit_multiplier : float, default 1
        Multiplies y axis limits with factor, useful for unit changes

    custom_ylim_bottom : bool, default False
        Indicates whether a manual lower limit for y axis has been set

    custom_ylim_top : bool, default False
        Indicates whether a manual upper limit for y axis has been set

    custom_xlim_left : bool, default False
        Indicates whether a manual lower limit for x axis has been set

    custom_xlim_right : bool, default False
        Indicates whether a manual upper limit for x axis has been set

    Methods
    -------
    set_options(keyword arguments)
        Can set the class attributes using keyword options

    """

    def __init__(self, *args, **kwargs):
        """Setting default values for plotting preferences"""
        self.log = False
        self.orders_of_mag = 300
        self.colormap = "jet"
        self.show_colorbar = True
        self.cut_max = 1
        self.cut_min = 0
        self.x_limit_multiplier = 1
        self.y_limit_multiplier = 1

        self.custom_ylim_bottom = False
        self.custom_ylim_top = False
        self.custom_xlim_left = False
        self.custom_xlim_right = False

        self.top_lim = None
        self.bottom_lim = None
        self.left_lim = None
        self.right_lim = None

    def set_options(self, **kwargs):
        """
        Set custom values for plotting preferences

        Keyword arguments
        -----------------

        log : bool, default False
            To plot on logarithmic or not, standard is linear

        orders_of_mag : float, default 300
            If plotting on log scale, restrict max range to orders_of_mag
            below maximum value

        colormap : string, default jet
            Chosen colormap for 2d data, should be available in matplotlib

        show_colorbar : bool, default True
            Selects if colorbar should be shown or not

        cut_max : float, default 1
            Factor multiplied onto maximum data value to set upper plot limit

        cut_min : float, default 0
            Removes given fraction of the plot range from the lower limit

        x_limit_multiplier : float, default 1
            Multiplies x axis limits with factor, useful for unit changes

        y_limit_multiplier : float, default 1
            Multiplies y axis limits with factor, useful for unit changes

        bottom_lim : float
            Set manual lower limit for y axis

        top_lim : float
            Set manual upper limit for y axis

        left_lim : float
            Set manual lower limit for x axis

        right_lim : float
            Set manual upper limit for x axis

        """
        if "log" in kwargs:
            self.log = bool(kwargs["log"])

        if "orders_of_mag" in kwargs:
            self.orders_of_mag = kwargs["orders_of_mag"]
            if not isinstance(self.orders_of_mag, (float, int)):
                raise ValueError("orders_of_mag must be a number, got: "
                                 + str(self.orders_of_mag))

        if "colormap" in kwargs:
            all_colormaps = matplotlib.pyplot.colormaps()
            self.colormap = kwargs["colormap"]
            if self.colormap not in all_colormaps:
                raise ValueError("Chosen colormap not available in "
                                 + "matplotlib, was: "
                                 + str(self.colormap))

        if "show_colorbar" in kwargs:
            self.show_colorbar = bool(kwargs["show_colorbar"])

        if "cut_max" in kwargs:
            self.cut_max = kwargs["cut_max"]
            if not isinstance(self.cut_max, (float, int)):
                raise ValueError("cut_max has to be a number, was given: "
                                 + str(self.cut_max))

        if "cut_min" in kwargs:
            self.cut_min = kwargs["cut_min"]
            if not isinstance(self.cut_min, (float, int)):
                raise ValueError("cut_min has to be a number, was given: "
                                 + str(self.cut_min))

        if "x_axis_multiplier" in kwargs:
            self.x_limit_multiplier = kwargs["x_axis_multiplier"]
            if not isinstance(self.x_limit_multiplier, (float, int)):
                raise ValueError("x_limit_multiplier has to be a number, was "
                                 + "given: " + str(self.x_limit_multiplier))

        if "y_axis_multiplier" in kwargs:
            self.y_limit_multiplier = kwargs["y_axis_multiplier"]
            if not isinstance(self.y_limit_multiplier, (float, int)):
                raise ValueError("y_limit_multiplier has to be a number, was "
                                 + "given: " + str(self.y_limit_multiplier))

        if "top_lim" in kwargs:
            self.top_lim = kwargs["top_lim"]
            self.custom_ylim_top = True
            if not isinstance(self.top_lim, (float, int)):
                raise ValueError("top_lim has to be a number, was "
                                 + "given: " + str(self.top_lim))

        if "bottom_lim" in kwargs:
            self.bottom_lim = kwargs["bottom_lim"]
            self.custom_ylim_bottom = True
            if not isinstance(self.bottom_lim, (float, int)):
                raise ValueError("bottom_lim has to be a number, was "
                                 + "given: " + str(self.bottom_lim))

        if "left_lim" in kwargs:
            self.left_lim = kwargs["left_lim"]
            self.custom_xlim_left = True
            if not isinstance(self.left_lim, (float, int)):
                raise ValueError("left_lim has to be a number, was "
                                 + "given: " + str(self.left_lim))

        if "right_lim" in kwargs:
            self.right_lim = kwargs["right_lim"]
            self.custom_xlim_right = True
            if not isinstance(self.right_lim, (float, int)):
                raise ValueError("right_lim has to be a number, was "
                                 + "given: " + str(self.right_lim))

    def __repr__(self):

        string = "plot_options"

        string += " log: " + str(self.log) + "\n"
        if self.log:
            string += " orders_of_mag: " + str(self.orders_of_mag) + "\n"

        string += " colormap: " + str(self.colormap) + "\n"
        string += " show_colorbar: " + str(self.show_colorbar) + "\n"
        string += " cut_min: " + str(self.cut_min) + "\n"
        string += " cut_max: " + str(self.cut_max) + "\n"
        string += " x_limit_multiplier: " + str(self.x_limit_multiplier) + "\n"
        string += " y_limit_multiplier: " + str(self.y_limit_multiplier) + "\n"

        if self.custom_xlim_left:
            string += "manual x lower limit: " + str(self.left_lim)

        if self.custom_xlim_right:
            string += "manual x upper limit: " + str(self.right_lim)

        if self.custom_ylim_bottom:
            string += "manual y lower limit: " + str(self.bottom_lim)

        if self.custom_ylim_bottom:
            string += "manual y upper limit: " + str(self.top_lim)

        return string


class McStasData:
    """
    Class for holding full McStas dataset with data, metadata and
    plotting preferences

    Attributes
    ----------
    metadata : McStasMetaData instance
        Holds the metadata for the dataset

    name : str
        Name of component, extracted from metadata

    plot_options : McStasPlotOptions instance
        Holds the plotting preferences for the dataset

    Methods
    -------
    set_xlabel : string
        sets xlabel of data for plotting

    set_ylabel : string
        sets ylabel of data for plotting

    set_title : string
        sets title of data for plotting

    set_options : keyword arguments
        sets plot options, keywords passed to McStasPlotOptions method
    """

    def __init__(self, metadata):
        """
        Initialize a new McStas dataset, 4 positional arguments, pass
        xaxis as kwarg if 1d data

        Parameters
        ----------
        metadata : McStasMetaData instance
            Holds the metadata for the dataset
        """

        # attach meta data
        self.metadata = metadata
        # get name from metadata
        self.name = self.metadata.component_name
        # initialize PlotOptions
        self.plot_options = McStasPlotOptions()

        self.data_type = None
        self.original_data_location = None

    # Methods xlabel, ylabel and title as they might not be found
    def set_xlabel(self, string):
        self.metadata.set_xlabel(string)

    def set_ylabel(self, string):
        self.metadata.set_ylabel(string)

    def set_zlabel(self, string):
        self.metadata.set_zlabel(string)

    def set_title(self, string):
        self.metadata.set_title(string)

    def set_plot_options(self, **kwargs):
        self.plot_options.set_options(**kwargs)

    def set_data_location(self, data_location):
        self.original_data_location = data_location

    def get_data_location(self):
        return self.original_data_location

    def __str__(self):
        """
        Returns string with quick summary of data
        """

        string = "McStasData: "
        string += self.name + " "
        if type(self.metadata.dimension) == int and self.metadata.dimension == 0:
            string += "type: 0D "
        elif type(self.metadata.dimension) == int and self.metadata.dimension != 0:
            string += "type: 1D "
        elif len(self.metadata.dimension) == 2:
            string += "type: 2D "
        else:
            string += "type: other "

        if self.metadata.total_I is not None:
            string += " I:" + str(self.metadata.total_I)
        if self.metadata.total_E is not None:
            string += " E:" + str(self.metadata.total_E)
        if self.metadata.total_N is not None:
            string += " N:" + str(self.metadata.total_N)

        return string

    def __repr__(self):
        return "\n" + self.__str__()


class McStasDataBinned(McStasData):
    """
    Class for holding full McStas dataset with data, metadata and
    plotting preferences

    Attributes
    ----------
    metadata : McStasMetaData instance
        Holds the metadata for the dataset

    name : str
        Name of component, extracted from metadata

    Intensity : numpy array
        Intensity data [neutrons/s] in 1d or 2d numpy array, dimension in
        metadata

    Error : numpy array
        Error data [neutrons/s] in 1d or 2d numpy array, same dimensions as
        Intensity

    Ncount : numpy array
        Number of rays in bin, 1d or 2d numpy array, same dimensions as
        Intensity

    plot_options : McStasPlotOptions instance
        Holds the plotting preferences for the dataset

    Methods
    -------
    set_xlabel : string
        sets xlabel of data for plotting

    set_ylabel : string
        sets ylabel of data for plotting

    set_zlabel : string
        sets ylabel of data for plotting

    set_title : string
        sets title of data for plotting

    set_options : keyword arguments
        sets plot options, keywords passed to McStasPlotOptions method
    """

    def __init__(self, metadata, intensity, error, ncount, **kwargs):
        """
        Initialize a new McStas dataset, 4 positional arguments, pass
        xaxis as kwarg if 1d data

        Parameters
        ----------
        metadata : McStasMetaData instance
            Holds the metadata for the dataset

        intensity : numpy array
            Intensity data [neutrons/s] in 1d or 2d numpy array, dimension in
            metadata

        error : numpy array
            Error data [neutrons/s] in 1d or 2d numpy array, same dimensions
            as Intensity

        ncount : numpy array
            Number of rays in bin, 1d or 2d numpy array, same dimensions as
            Intensity

        kwargs : keyword arguments
            xaxis is required for 1d data
        """

        super().__init__(metadata)

        # three basic arrays from positional arguments
        if not isinstance(intensity, np.ndarray):
            raise ValueError("intensity should be numpy array!")
        if not isinstance(error, np.ndarray):
            raise ValueError("error should be numpy array!")
        if not isinstance(ncount, np.ndarray):
            raise ValueError("ncount should be numpy array!")

        self.Intensity = intensity
        self.Error = error
        self.Ncount = ncount

        if type(self.metadata.dimension) == int and self.metadata.dimension == 0:
            self.data_type = "Binned 0D"
        elif type(self.metadata.dimension) == int and self.metadata.dimension != 0:
            self.data_type = "Binned 1D"
            if "xaxis" in kwargs:
                self.xaxis = kwargs["xaxis"]
            else:
                raise NameError(
                    "ERROR: Initialization of McStasData done with 1d "
                    + "data, but without xaxis for " + self.name + "!")
        elif len(self.metadata.dimension) == 2:
            self.data_type = "Binned 2D"
        else:
            self.data_type = "Binned"


class McStasDataEvent(McStasData):
    """
    Class for holding McStas event dataset with data, metadata and
    plotting preferences. Usually data the first one million events
    is plotted.

    Attributes
    ----------
    metadata : McStasMetaData instance
        Holds the metadata for the dataset

    name : str
        Name of component, extracted from metadata

    Events : numpy array
        Event data

    plot_options : McStasPlotOptions instance
        Holds the plotting preferences for the dataset

    Methods
    -------
    set_xlabel : string
        sets xlabel of data for plotting

    set_ylabel : string
        sets ylabel of data for plotting

    set_zlabel : string
        sets zlabel of data for plotting

    set_title : string
        sets title of data for plotting

    set_options : keyword arguments
        sets plot options, keywords passed to McStasPlotOptions method
    """

    def __init__(self, metadata, events, **kwargs):
        """
        Initialize a new McStas event dataset, 2 positional arguments

        Parameters
        ----------
        metadata : McStasMetaData instance
            Holds the metadata for the dataset

        events : numpy array
            event data
        """

        super().__init__(metadata)

        # three basic arrays from positional arguments
        if not isinstance(events, np.ndarray):
            raise ValueError("events should be numpy array!")

        self.Events = events
        self.data_type = "Events"

        self.variables = self.metadata.info["variables"].strip()
        self.variables = self.variables.split()

        # Calculate I, E and N
        if "p" in self.variables:
            p_array = self.get_data_column("p")
            total_I = p_array.sum()
            total_E = np.sqrt((p_array ** 2).sum())
            total_N = len(p_array)

            self.metadata.total_I = total_I
            self.metadata.total_E = total_E
            self.metadata.total_N = total_N

        else:

            self.metadata.total_I = None
            self.metadata.total_E = None
            self.metadata.total_N = None

        self.labels = {"t": "t [s]",
                       "x": "x [m]",
                       "y": "y [m]",
                       "z": "z [m]",
                       "vx": "vx [m/s]",
                       "vy": "vy [m/s]",
                       "vz": "vz [m/s]",
                       "l": "wavelength [AA]",
                       "e": "energy [meV]",
                       "speed": "speed [m/s]",
                       "dx": "divergence x [deg]",
                       "dy": "divergence y [deg]"}

    def find_variable_index(self, axis, flag_info=None):
        """
        Returns variable index for given axis name

        Parameters:

        axis : str
            Name of desired axis

        flag_info: list
            List of flag names used for user variables in event data
        """
        if flag_info is not None:
            # If flag info given, use it to find user var string
            for index, flag in enumerate(flag_info):
                if axis == flag:
                    axis = f"U{index + 1}"

        return self.variables.index(axis)

    def scale_weights(self, factor):
        """
        Scales all event weights with given factor

        Parameters:

        factor : float
            Factor with which all weights are scaled
        """
        self.Events[:, self.find_variable_index("p")] *= factor

    def get_label(self, axis, flag_info=None):
        """
        Returns data label corresponding to given axis name

        Parameters:

        axis : str
            Name of parameter

        flag_info : list
            list of names for user variables in event data set
        """
        axis = axis.lower()

        if flag_info is not None:
            # If flag info given, use it to find user var string
            for index, flag in enumerate(flag_info):
                if axis == flag:
                    return f"User{index+1}: {flag}"

        if axis in self.labels:
            return self.labels[axis]
        else:
            return ""

    def get_data_column(self, axis, flag_info=None):
        """
        Returns data column corresponding to given axis name

        Parameters:

        axis : str
            Name of parameter

        flag_info : list
            list of names for user variables in event data set
        """

        m_n_const = 1.674927e-27
        h_const = 6.626068e-34

        if axis.lower() == "speed":
            # Convert velocity to speed (must be before l and e)
            vx = self.Events[:, self.find_variable_index("vx")]
            vy = self.Events[:, self.find_variable_index("vy")]
            vz = self.Events[:, self.find_variable_index("vz")]
            return np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)

        elif axis.lower() == "l":
            # Convert speed to lambda
            speed = self.get_data_column("speed")
            lambda_meter = h_const / (m_n_const*speed)
            return lambda_meter*1E10

        elif axis.lower() == "e":
            # Convert speed to energy
            speed = self.get_data_column("speed")
            energy_joule = 0.5 * m_n_const * speed ** 2
            return energy_joule/1.60217663E-19*1E3

        elif axis.lower() == "dx":
            # Convert velocity to divergence x
            vx = self.Events[:, self.find_variable_index("vx")]
            vz = self.Events[:, self.find_variable_index("vz")]
            return np.arctan(vx/vz) * 180 / np.pi

        elif axis.lower() == "dy":
            # Convert velocity to divergence y
            vy = self.Events[:, self.find_variable_index("vy")]
            vz = self.Events[:, self.find_variable_index("vz")]
            return np.arctan(vy/vz) * 180 / np.pi

        else:
            index = self.find_variable_index(axis, flag_info=flag_info)
            return self.Events[:, index]

    def make_1d(self, axis1, n_bins=50, flag_info=None):
        """
        Bin event data along to given axis to create binned dataset

        Parameters:

        axis1 : str
            Name of parameter for binned axis

        n_bins : integer
            Number of bins for histogramming

        flag_info : list
            list of names for user variables in event data set
        """
        data = self.get_data_column(axis1, flag_info)
        label = self.get_label(axis1, flag_info)

        weights = self.get_data_column("p", flag_info)
        intensity, edges = np.histogram(data, bins=n_bins, weights=weights)
        error_squared, edges = np.histogram(data, bins=n_bins, weights=weights**2)
        error = np.sqrt(error_squared)
        ncount, edges = np.histogram(data, bins=n_bins)

        centers = edges[0:-1] + 0.5*(edges[1] - edges[0])

        metadata = copy.deepcopy(self.metadata)
        metadata.dimension = len(centers)
        metadata.info["type"] = "array_1d"
        metadata.limits = [centers[0], centers[-1]]

        total_I = np.sum(intensity)
        total_E = np.sqrt(error_squared.sum())
        total_N = np.sum(ncount)
        metadata.info["values"] = "{:2.6E} {:2.6E} {:2.6E}".format(total_I, total_E, total_N)
        metadata.total_I = total_I
        metadata.total_E = total_E
        metadata.total_N = total_N

        binned = McStasDataBinned(metadata, intensity=intensity,
                                  error=error, ncount=ncount, xaxis=centers)

        binned.set_title("Binned data generated from events")
        binned.set_xlabel(label)
        binned.set_ylabel("Intensity per bin [n/s]")

        return binned

    def make_2d(self, axis1, axis2, n_bins=100, flag_info=None):
        """
        Bin event data along to given axes to create binned dataset

        Parameters:

        axis1 : str
            Name of parameter for first axis

        axis2 : str
            Name of parameter for second axis

        n_bins : integer or list
            Number of bins for histogramming, can be list with two elements

        flag_info : list
            list of names for user variables in event data set
        """

        data1 = self.get_data_column(axis1, flag_info)
        label1 = self.get_label(axis1, flag_info)
        data2 = self.get_data_column(axis2, flag_info)
        label2 = self.get_label(axis2, flag_info)

        if isinstance(n_bins, list):
            n_bins.reverse()

        weights = self.get_data_column("p", flag_info)
        intensity, edges2, edges1 = np.histogram2d(data2, data1, bins=n_bins, weights=weights)
        error_squared, edges2, edges1 = np.histogram2d(data2, data1, bins=n_bins, weights=weights**2)
        error = np.sqrt(error_squared)
        ncount, edges2, edges1 = np.histogram2d(data2, data1, bins=n_bins)

        centers1 = edges1[0:-1] + 0.5*(edges1[1] - edges1[0])
        centers2 = edges2[0:-1] + 0.5*(edges2[1] - edges2[0])

        metadata = copy.deepcopy(self.metadata)
        metadata.dimension = [len(centers1), len(centers2)]
        metadata.info["type"] = "array_2d"
        metadata.limits = [centers1[0], centers1[-1], centers2[0], centers2[-1]]

        total_I = intensity.sum()
        total_E = np.sqrt(error_squared.sum())
        total_N = ncount.sum()
        metadata.info["values"] = "{:2.6E} {:2.6E} {:2.6E}".format(total_I, total_E, total_N)
        metadata.total_I = total_I
        metadata.total_E = total_E
        metadata.total_N = total_N

        binned = McStasDataBinned(metadata, intensity=intensity,
                                  error=error, ncount=ncount)
        binned.set_title("Binned data generated from events")
        binned.set_xlabel(label1)
        binned.set_ylabel(label2)

        return binned

    def __str__(self):
        """
        Returns string with quick summary of data
        """

        string = "McStasDataEvent: "
        string += self.name + " with "
        string += str(len(self.Events)) + " events."
        if "variables" in self.metadata.info:
            string += " Variables: "
            string += self.metadata.info["variables"].strip()

        return string

    def __repr__(self):
        return "\n" + self.__str__()

def parse_coordinates(line, keyword):
    # Extract the coordinates from the line
    match = re.search(r'\(([^)]+)\)', line)
    if match:
        coords = match.group(1).split(',')
        coords = [float(coord.strip()) for coord in coords]
        return {f'{keyword}_x': coords[0], f'{keyword}_y': coords[1], f'{keyword}_z': coords[2]}
    return {}

class ComponentData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def read(self):

        components = {}

        current_component = None

        with open(self.file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('COMPONENT'):
                    match = re.match(r'COMPONENT (\S+) = (\S+)', line)
                    if match:
                        component_name = match.group(1)
                        component_type = match.group(2)
                        current_component = {'component': component_type}
                        components[component_name] = current_component
                        current_component["parameters"] = {}
                elif '=' in line:
                    if current_component is not None:
                        key, value = line.split('=',1)
                        try:
                            value = float(value)
                        except:
                            pass
                        current_component["parameters"][key] = value
                elif line.startswith('AT'):
                    if current_component is not None:
                        current_component.update(parse_coordinates(line, 'AT'))
                        if line.endswith('ABSOLUTE'):
                            current_component['AT_relative'] = "ABSOLUTE"
                        else:
                            current_component['AT_relative'] = line.split('RELATIVE')[1].strip()
                elif line.startswith('ROTATED'):
                    if current_component is not None:
                        current_component.update(parse_coordinates(line, 'ROTATED'))
                        if line.endswith('ABSOLUTE'):
                            current_component['ROTATED_relative'] = "ABSOLUTE"
                        else:
                            current_component['ROTATED_relative'] = line.split('RELATIVE')[1].strip()

        self.data = components

        return components

