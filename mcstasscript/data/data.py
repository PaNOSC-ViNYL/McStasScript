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
        data

    title : str
        Title of monitor when plotting

    xlabel : str
        Text for xlabel when plotting

    ylabel : str
        Text for ylabel when plotting

    Methods
    -------
    add_info(key,value)
        Adds a element to the info dictionary

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
            # Monitors without output files does exist
            #raise NameError(
            #    "No filename found in mccode data section!")
            print("The component named \"" + self.component_name
                  + "\" had no data file and will not be loaded.")
            self.filename = ""

        # Extract limits
        self.limits = []
        if "xylimits" in self.info:
            # find the four numbers
            temp_str = self.info["xylimits"]
            limits_string = temp_str.split()
            for limit in limits_string:
                self.limits.append(float(limit))

        if "xlimits" in self.info:
            # find the two numbers
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
    log : bool
        To plot on logarithmic or not, standard is linear

    orders_of_mag : float
        If plotting on log scale, restrict max range to orders_of_mag
        below maximum value

    colormap : string
        Chosen colormap for 2d data, should be available in matplotlib

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
        
        self.custom_ylim_top = False
        self.custom_ylim_bottom = False
        self.custom_xlim_left = False
        self.custom_xlim_right = False

    def set_options(self, **kwargs):
        """Set custom values for plotting preferences"""
        if "log" in kwargs:
            log_input = kwargs["log"]
            if type(log_input) == int:
                if log_input == 0:
                    self.log = False
                else:
                    self.log = True
            elif type(log_input) == bool:
                self.log = log_input
            else:
                raise NameError(
                    "Log input must be either Int or Bool.")

        if "orders_of_mag" in kwargs:
            self.orders_of_mag = kwargs["orders_of_mag"]

        if "colormap" in kwargs:
            self.colormap = kwargs["colormap"]
            
        if "show_colorbar" in kwargs:
            self.show_colorbar = kwargs["show_colorbar"]
            
        if "cut_max" in kwargs:
            self.cut_max = kwargs["cut_max"]
            
        if "cut_min" in kwargs:
            self.cut_min = kwargs["cut_min"]
            
        if "x_axis_multiplier" in kwargs:
            self.x_limit_multiplier = kwargs["x_axis_multiplier"]
        
        if "y_axis_multiplier" in kwargs:
            self.y_limit_multiplier = kwargs["y_axis_multiplier"]
            
        if "top_lim" in kwargs:
            self.top_lim = kwargs["top_lim"]
            self.custom_ylim_top = True
            
        if "bottom_lim" in kwargs:
            self.bottom_lim = kwargs["bottom_lim"]
            self.custom_ylim_bottom = True
            
        if "left_lim" in kwargs:
            self.left_lim = kwargs["left_lim"]
            self.custom_xlim_left = True
            
        if "right_lim" in kwargs:
            self.right_lim = kwargs["right_lim"]
            self.custom_xlim_right = True
            


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

    Intensity : numpy array
        Intensity data [n/s] in 1d or 2d numpy array, dimension in
        metadata

    Error : numpy array
        Error data [n/s] in 1d or 2d numpy array, same dimensions as
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

    set_optons : keyword arguments
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

        name : str
            Name of component, extracted from metadata

        intensity : numpy array
            Intensity data [n/s] in 1d or 2d numpy array, dimension in
            metadata

        error : numpy array
            Error data [n/s] in 1d or 2d numpy array, same dimensions
            as Intensity

        ncount : numpy array
            Number of rays in bin, 1d or 2d numpy array, same
            dimensions as Intensity

        kwargs : keyword arguments
            xaxis is required for 1d data
        """

        # attatch meta data
        self.metadata = metadata
        # get name from metadata
        self.name = self.metadata.component_name
        # three basic arrays from positional arguments
        self.Intensity = intensity
        self.Error = error
        self.Ncount = ncount

        if type(self.metadata.dimension) == int:
            if "xaxis" in kwargs:
                self.xaxis = kwargs["xaxis"]
            else:
                raise NameError(
                    "ERROR: Initialization of McStasData done with 1d "
                    + "data, but without xaxis for " + self.name + "!")

        self.plot_options = McStasPlotOptions()

    # Methods xlabel, ylabel and title as they might not be found
    def set_xlabel(self, string):
        self.metadata.set_xlabel(string)

    def set_ylabel(self, string):
        self.metadata.set_ylabel(string)

    def set_title(self, string):
        self.metadata.set_title(string)

    def set_plot_options(self, **kwargs):
        self.plot_options.set_options(**kwargs)
