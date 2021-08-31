import matplotlib.pyplot
import numpy as np


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

    def add_info(self, key, value):
        """Adding information to info dict"""
        self.info[key] = value

    def extract_info(self):
        """Extracting information from info dict to class attributes"""

        # Extract dimension
        if "type" in self.info:
            type_data = self.info["type"]
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
        if "title" in self.info:
            self.title = self.info["title"].rstrip()

    def set_title(self, string):
        """Sets title for plotting"""
        self.title = string

    def set_xlabel(self, string):
        """Sets xlabel for plotting"""
        self.xlabel = string

    def set_ylabel(self, string):
        """Sets ylabel for plotting"""
        self.ylabel = string


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

    # Methods xlabel, ylabel and title as they might not be found
    def set_xlabel(self, string):
        self.metadata.set_xlabel(string)

    def set_ylabel(self, string):
        self.metadata.set_ylabel(string)

    def set_title(self, string):
        self.metadata.set_title(string)

    def set_plot_options(self, **kwargs):
        self.plot_options.set_options(**kwargs)

    def __str__(self):
        """
        Returns string with quick summary of data
        """

        string = "McStasData: "
        string += self.name + " "
        if type(self.metadata.dimension) == int:
            string += "type: 1D "
        elif len(self.metadata.dimension) == 2:
            string += "type: 2D "
        else:
            string += "type: other "

        if "values" in self.metadata.info:
            values = self.metadata.info["values"]
            values = values.strip()
            values = values.split(" ")
            if len(values) == 3:
                string += " I:" + str(values[0])
                string += " E:" + str(values[1])
                string += " N:" + str(values[2])

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

        if type(self.metadata.dimension) == int:
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

        # Intensity for compatibility with plotting routine
        data_lines = metadata.dimension[1]
        self.Intensity = self.Events[0:data_lines, :]

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
