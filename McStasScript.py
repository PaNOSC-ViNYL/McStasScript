"""McStasScript classes written by Mads Bertelsen, ESS, DMSC

API for writing and running McStas instruments
"""

from __future__ import print_function

__author__ = "Mads Bertelsen"

import datetime
import os
import time
import math

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
from openpyxl.worksheet import dimensions
from boto.ec2.autoscale import limits
# From builtins import False, True

try:  # Check whether python knows about 'basestring'
    basestring
except NameError:  # No, it doesn't (it's Python3); use 'str' instead
    basestring = str


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
            type = self.info["type"]
            if "array_1d" in type:
                self.dimension = int(type[9:-2])
            if "array_2d" in type:
                self.dimension = []
                type_strings = self.info["type"].split(",")
                temp_str = type_strings[0]
                self.dimension.append(int(temp_str[9:]))
                temp_str = type_strings[1]
                self.dimension.append(int(temp_str[1:-2]))
        else:
            raise NameError("No type in mccode data section!")

        # Extract component name
        if "component" in self.info:
            self.component_name = self.info["component"].rstrip()

        # Extract filename
        if "filename" in self.info:
            self.filename = self.info["filename"].rstrip()
        else:
            raise NameError(
                "No filename found in mccode data section!")

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
                    + "data, but without xaxis" + self.name + "!")

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

def name_search(name, data_list):
    """"
    name_search returns McStasData instance with specific name if it is
    in the given data_list

    The index of certain datasets in the data_list can change if
    additional monitors are added so it is more convinient to access
    the data files using their names.

    Parameters
    ----------
    name : string
        Name of the dataset to be retrived (component_name)

    data_list : List of McStasData instances
        List of datasets to search
    """

    if not type(data_list[0]) == McStasData:
        raise InputError(
            "name_search function needs objects of type "
            + "McStasData as input.")

    list_result = []
    for check in data_list:
        if check.metadata.component_name == name:
            list_result.append(check)

    if len(list_result) == 1:
        return list_result[0]
    else:
        raise NameError("More than one match for the name search")

def name_plot_options(name, data_list, **kwargs):
    """"
    name_plot_options passes keyword arguments to dataset with certain
    name in given data list

    Function for quickly setting plotting options on a certain dataset
    n a larger list of datasets

    Parameters
    ----------
    name : string
        Name of the dataset to be modified (component_name)

    data_list : List of McStasData instances
        List of datasets to search

    kwargs : keyword arguments
        Keyword arguments passed to set_plot_options in
        McStasPlotOptions
    """

    if not isinstance(data_list[0], McStasData):
        raise InputError(
            "name_search function needs objects of type McStasData "
            + "as input.")

    object_to_modify = name_search(name, data_list)
    object_to_modify.set_plot_options(**kwargs)


class ManagedMcrun:
    """
    A class for performing a mcstas simulation and organizing the data
    into python objects

    ManagedMcrun is usually called by the instrument class of
    McStasScript but can be used independently.  It runs the mcrun
    command using the system command, and if this is not in the path,
    the absolute path can be given in a keyword argument mcrun_path.

    Attributes
    ----------
    name_of_instrumentfile : str
        Name of instrument file to be executed

    data_folder_name : str
        Name of datafolder mcrun writes to disk

    ncount : int
        Number of rays to simulate

    mpi : int
        Number of mpi threads to run

    parameters : dict
        Dictionary of parameter names and values for this simulation

    custom_flags : string
        Custom flags that are passed to the mcrun command

    mcrun_path : string
        Path to the mcrun command (can be empty if already in path)

    Methods
    -------
    run_simulation()
        Runs simulation, returns list of McStasData instances

    """

    def __init__(self, instr_name, **kwargs):
        """
        Parameters
        ----------
        instr_name : str
            Name of instrument file to be simulated

        kwargs : keyword arguments
            foldername : str
                Sets data_folder_name
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            parameters : dict
                Sets parameters
            custom_flags : str
                Sets custom_flags passed to mcrun
            mcrun_path : str
                Path to mcrun command, "" if already in path
        """

        self.name_of_instrumentfile = instr_name

        self.data_folder_name = ""
        self.ncount = 1E6
        self.mpi = 1
        self.parameters = {}
        self.custom_flags = ""
        self.mcrun_path = ""
        # mcrun_path always in kwargs
        self.mcrun_path = kwargs["mcrun_path"]

        if "foldername" in kwargs:
            self.data_folder_name = kwargs["foldername"]
        else:
            raise NameError(
                "ManagedMcrun needs foldername to load data, add "
                + "with keyword argument.")

        if "ncount" in kwargs:
            self.ncount = kwargs["ncount"]

        if "mpi" in kwargs:
            self.mpi = kwargs["mpi"]

        if "parameters" in kwargs:
            self.parameters = kwargs["parameters"]

        if "custom_flags" in kwargs:
            self.custom_flags = kwargs["custom_flags"]

    def run_simulation(self):
        """
        Runs McStas simulation described by initializing the object
        """

        # construct command to run
        option_string = ("-c"
                         + " -n " + str(self.ncount)  # Set ncount
                         + " --mpi=" + str(self.mpi)  # Set mpi
                         + " ")

        if len(self.data_folder_name) > 0:
            option_string = (option_string
                             + "-d "
                             + self.data_folder_name)

        # add parameters to command
        parameter_string = ""
        for key, val in self.parameters.items():
            parameter_string = (parameter_string + " "
                                + str(key)  # parameter name
                                + "="
                                + str(val))  # parameter value

        mcrun_full_path = self.mcrun_path + "mcrun"
        if len(self.mcrun_path) > 1:
            if not (self.mcrun_path[-1] == "\\"
                    or self.mcrun_path[-1] == "/"):
                mcrun_full_path = self.mcrun_path + "/mcrun"

        # Run the mcrun command on the system
        os.system(mcrun_full_path + " "
                  + option_string + " "
                  + self.custom_flags + " "
                  + self.name_of_instrumentfile + " "
                  + parameter_string)

        """
        Can use subprocess from spawn* instead of os.system if more
        control is needed over the spawned process, including a timeout
        """

        # Find all data files in generated folder
        files_in_folder = os.listdir(self.data_folder_name)

        # Raise an error if mccode.sim is not available
        if "mccode.sim" not in files_in_folder:
            raise NameError("mccode.sim not written to output folder.")

        # Open mccode to read metadata for all datasets written to disk
        f = open(self.data_folder_name + "/mccode.sim", "r")

        # Loop that reads mccode.sim sections
        metadata_list = []
        in_data = False
        for lines in f:
            # Could read other details about run

            if lines == "end data\n":
                # No more data for this metadata object
                # Extract the information
                current_object.extract_info()
                # Add to metadata list
                metadata_list.append(current_object)
                # Stop reading data
                in_data = False

            if in_data:
                # This line contains info to be added to metadata
                colon_index = lines.index(":")
                key = lines[2:colon_index]
                value = lines[colon_index+2:]
                current_object.add_info(key, value)

            if lines == "begin data\n":
                # Found data section, create new metadata object
                current_object = McStasMetaData()
                # Start recording data to metadata object
                in_data = True

        # Close mccode.sim
        f.close()

        # Create a list for McStasData instances to return
        results = []

        # Load datasets described in metadata list individually
        for metadata in metadata_list:
            # Load data with numpy
            data = np.loadtxt(self.data_folder_name
                              + "/"
                              + metadata.filename.rstrip())

            # Split data into intensity, error and ncount
            if type(metadata.dimension) == int:
                xaxis = data.T[0, :]
                Intensity = data.T[1, :]
                Error = data.T[2, :]
                Ncount = data.T[3, :]

            elif len(metadata.dimension) == 2:
                xaxis = []  # Assume evenly binned in 2d
                data_lines = metadata.dimension[1]
                Intensity = data.T[:, 0:data_lines - 1]
                Error = data.T[:, data_lines:2*data_lines - 1]
                Ncount = data.T[:, 2*data_lines:3*data_lines - 1]
            else:
                raise NameError(
                    "Dimension not read correctly in data set "
                    + "connected to monitor named "
                    + metadata.component_name)

            # The data is saved as a McStasData object
            result = McStasData(metadata, Intensity,
                                Error, Ncount,
                                xaxis=xaxis)

            # Add this result to the results list
            results.append(result)

            # Close the current datafile
            f.close()

        # Return list of McStasData objects
        return results


class make_plot:
    """
    make_plot plots contents of McStasData objects

    Plotting is controlled through options assosciated with the
    McStasData objects.

    If a list is given, the plots appear individually.
    """

    def __init__(self, data_list):
        """
        plots McStasData, single object or list of McStasData

        The options concerning plotting are stored with the data

        Parameters
        ----------
        data_list : McStasData or list of McStasData
            McStasData to be plotted
        """

        # Relevant options:
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (orders of magnitude)
        #  compare several 1d
        #  compare 2D

        if isinstance(data_list, McStasData):
            # Only a single element, put it in a list for easier syntax later
            data_list = [data_list]

        number_of_plots = len(data_list)

        print("number of elements in data list = " + str(len(data_list)))

        index = -1
        for data in data_list:
            index = index + 1

            print("Plotting data with name " + data.metadata.component_name)
            if type(data.metadata.dimension) == int:
                fig = plt.figure(0)

                # print(data.T)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error

                plt.errorbar(x, y, yerr=y_err)

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                plt.xlim(data.metadata.limits[0], data.metadata.limits[1])

                # Add a title
                plt.title(data.metadata.title)

                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)

            elif len(data.metadata.dimension) == 2:

                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                if data.plot_options.log:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)

                    to_plot = np.log10(Intensity)

                    max_value = to_plot.max()

                    if (max_value - min_value
                            > data.plot_options.orders_of_mag):
                        min_value = (max_value
                                     - data.plot_options.orders_of_mag)
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis (might be switched?)
                X = np.linspace(data.metadata.limits[0],
                                data.metadata.limits[1],
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2],
                                data.metadata.limits[3],
                                data.metadata.dimension[1])

                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y, X)

                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value,
                                                            max_value)

                # Select colormap
                cmap = plt.get_cmap('hot')
                norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

                # Create the figure
                fig, (ax0) = plt.subplots()

                # Plot the data on the meshgrids
                if data.plot_options.log:
                    color_norm = matplotlib.colors.LogNorm(vmin=min_value,
                                                           vmax=max_value)
                    im = ax0.pcolormesh(x, y, to_plot,
                                        cmap=cmap, norm=color_norm)
                else:
                    im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)

                # Add the colorbar
                fig.colorbar(im, ax=ax0)

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)

            else:
                print("Error, dimension not read correctly")

        plt.show()


class make_sub_plot:
    """
    make_plot plots contents of McStasData objects

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    def __init__(self, data_list):
        """
        plots McStasData, single object or list of McStasData

        The options concerning plotting are stored with the data

        Parameters
        ----------
        data_list : McStasData or list of McStasData
            McStasData to be plotted
        """
        if not isinstance(data_list, McStasData):
            print("number of elements in data list = "
                  + str(len(data_list)))
        else:
            # Make list from single element to simplify syntax
            data_list = [data_list]

        number_of_plots = len(data_list)

        # Relevant options:
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (o$rders of magnitude)
        #  compare several 1d
        #  compare 2D

        # Find reasonable grid size for the number of plots
        dim2 = math.ceil(math.sqrt(number_of_plots))
        dim1 = math.ceil(number_of_plots/dim2)

        fig, axs = plt.subplots(dim1, dim2, figsize=(13, 7))
        axs = np.array(axs)
        ax = axs.reshape(-1)

        index = -1
        for data in data_list:
            index = index + 1
            ax0 = ax[index]

            print("Plotting data with name "
                  + data.metadata.component_name)

            if isinstance(data.metadata.dimension, int):
                # fig = plt.figure(0)
                # plt.subplot(dim1, dim2, n_plot)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error

                ax0.errorbar(x, y, yerr=y_err)

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                ax0.set_xlim(data.metadata.limits[0],
                             data.metadata.limits[1])

                # Add a title
                # ax0.title(data.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

            elif len(data.metadata.dimension) == 2:

                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                if data.plot_options.log:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)

                    to_plot = Intensity

                    max_value = np.log10(to_plot.max())

                    if (max_value - min_value
                            > data.plot_options.orders_of_mag):
                        min_value = (max_value
                                     - data.plot_options.orders_of_mag)
                    min_value = 10.0 ** min_value
                    max_value = 10.0 ** max_value
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis (might be switched?)
                X = np.linspace(data.metadata.limits[0],
                                data.metadata.limits[1],
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2],
                                data.metadata.limits[3],
                                data.metadata.dimension[1])

                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y, X)

                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value,
                                                            max_value)

                # Select colormap
                cmap = plt.get_cmap(data.plot_options.colormap)

                # Select the colorscale normalization
                if data.plot_options.log:
                    norm = matplotlib.colors.LogNorm(vmin=min_value,
                                                     vmax=max_value)
                else:
                    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

                # Create plot
                im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)

                def fmt(x, pos):
                    a, b = '{:.2e}'.format(x).split('e')
                    b = int(b)
                    return r'${} \times 10^{{{}}}$'.format(a, b)

                # Add the colorbar
                fig.colorbar(im, ax=ax0,
                             format=matplotlib.ticker.FuncFormatter(fmt))

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

            else:
                print("Error, dimension not read correctly")

        plt.show()


class parameter_variable:
    """
    Class describing a input parameter in McStas instrument

    McStas input parameters are of default type double, but can be
    cast.  If two positional arguments are given, the first is the
    type, and the second is the parameter name.  With one input, only
    the parameter name is read.  It is also possible to assign a
    default value and a comment through keyword arguments.

    Attributes
    ----------
    type : str
        McStas type of input: Double, Int, String

    name : str
        Name of input parameter

    value : any
        Default value/string of parameter, converted to string

    comment : str
        Comment displayed next to the parameter, could contain units

    Methods
    -------
    write_parameter(fo,stop_character)
        writes the parameter to file fo, uses given stop character
    """

    def __init__(self, *args, **kwargs):
        """Initializing mcstas parameter object

        Parameters
        ----------
        If giving a type:
        Positional argument 1: type: str
            Type of the parameter, double, int or string
        Positional argument 2: name: str
            Name of input parameter

        If not giving type
        Positional argument 1: name : str
            Name of input parameter

        Keyword arguments
            value : any
                sets default value of parameter
            comment : str
                sets comment displayed next to declaration
        """
        if len(args) == 1:
            self.type = ""
            self.name = str(args[0])
        if len(args) == 2:
            self.type = args[0] + " "
            self.name = str(args[1])

        if "value" in kwargs:
            self.value_set = 1
            self.value = kwargs["value"]
        else:
            self.value_set = 0

        if "comment" in kwargs:
            self.comment = "// " + kwargs["comment"]
        else:
            self.comment = ""

        # could check for allowed types
        # they are int, double, string, are there more?

    def write_parameter(self, fo, stop_character):
        """Writes input parameter to file"""
        fo.write("%s%s" % (self.type, self.name))
        if self.value_set == 1:
            if isinstance(self.value, int):
                fo.write(" = %d" % self.value)
            elif isinstance(self.value, float):
                fo.write(" = %G" % self.value)
            else:
                fo.write(" = %s" % str(self.value))
        fo.write(stop_character)
        fo.write(self.comment)
        fo.write("\n")


class declare_variable:
    """
    Class describing a declared variable in McStas instrument

    McStas parameters are declared in declare section with c syntax.
    This class is initialized with type, name.  Using keyword
    arguments, the variable can become an array and have its initial
    value set.

    Attributes
    ----------
    type : str
        McStas type to declare: Double, Int, String

    name : str
        Name of variable

    value : any
        Initial value of variable, converted to string

    comment : str
        Comment displayed next to the declaration, could contain units

    vector : int
        0 if a single value is given, ortherwise contains the length

    value_set : int
        Internal variable displaying wether or not a value was given

    Methods
    -------
    write_line(fo)
        Writes a line to text file fo declaring the parameter in c
    """
    def __init__(self, *args, **kwargs):
        """Initializing mcstas parameter object

        Parameters
        ----------
        Positional argument 1: type : str
            Type of the parameter, double, int or string

        Positional argument 2: name : str
            Name of input parameter

        Keyword arguments
            array : int
                length of array to be allocated, 0 if single value

            value : any
                sets initial value of parameter,
                can be a list with length matching array

            comment : str
                sets comment displayed next to declaration
        """
        self.type = args[0]
        self.name = str(args[1])
        if "value" in kwargs:
            self.value_set = 1
            self.value = kwargs["value"]
        else:
            self.value_set = 0

        if "array" in kwargs:
            self.vector = kwargs["array"]
        else:
            self.vector = 0

        if "comment" in kwargs:
            self.comment = " // " + kwargs["comment"]
        else:
            self.comment = ""

    def write_line(self, fo):
        """Writes line declaring variable to file fo

        Parameters
        ----------
        fo : file object
            File the line will be written to
        """
        if self.value_set == 0 and self.vector == 0:
            fo.write("%s %s;%s" % (self.type, self.name, self.comment))
        if self.value_set == 1 and self.vector == 0:
            if self.type == "int":
                fo.write("%s %s = %d;%s" % (self.type, self.name,
                                            self.value, self.comment))
            else:
                fo.write("%s %s = %G;%s" % (self.type, self.name,
                                            self.value, self.comment))
        if self.value_set == 0 and self.vector != 0:
            fo.write("%s %s[%d];%s" % (self.type, self.name,
                                       self.vector, self.comment))
        if self.value_set == 1 and self.vector != 0:
            fo.write("%s %s[%d] = {" % (self.type, self.name, self.vector))
            for i in range(0, len(self.value) - 1):
                fo.write("%G," % self.value[i])
            fo.write("%G};%s" % (self.value[-1], self.comment))


class component:
    """
    A class describing a McStas component to be written to a instrument

    This class is used by the instrument class when setting up
    components, but can also be used independently.  Most information
    can be given on initialize using keyword arguments, but there are
    methods for setting the attributes describing the component. The
    class contains both methods to write the component to a instrument
    file and methods for printing to the python terminal for checking
    the information.

    Attributes
    ----------
    name : str
        Name of the component instance in McStas (must be unique)

    component_name : str
        Name of the component code to use, e.g. Arm, Guide_gravity, ...

    AT_data : list of 3 floats
        Position data of the component

    AT_relative : str
        Name of former component to use as reference for position

    ROTATED_data : list of 3 floats
        Rotation data of the component

    ROTATED_relative : str
        Name of former component to use as reference for position

    WHEN : str
        String with logical c expression x for when component is active

    EXTEND : str
        c code for McStas EXTEND section

    GROUP : str
        Name of group the component should belong to

    JUMP : str
        String describing use of JUMP, need to contain all after "JUMP"

    component_parameters : dict
        Parameters to be used with component in dictionary

    comment : str
        Comment inserted before the component as an explanation

    Methods
    -------
    set_AT(at_list,**kwargs)
        Sets AT_data, can set AT_relative using keyword

    set_ROTATED(rotated_list,**kwargs)
        Sets ROTATED_data, can set ROTATED_relative using keyword

    set_RELATIVE(relative_name)
        Set both AT_relative and ROTATED_relative to relative_name

    set_parameters(dict_input)
        Adds dictionary entries to parameter dictionary

    set_WHEN(string)
        Sets WHEN string

    set_GROUP(string)
        Sets GROUP name

    set_JUMP(string)
        Sets JUMP string

    append_EXTEND(string)
        Append string to EXTEND string

    set_comment(string)
        Sets comment for component

    write_component(fo)
        Writes component code to instrument file

    print_long()
        Prints basic view of component code (not correct syntax)

    print_short(**kwargs)
        Prints short description, used in print_components
    """
    def __init__(self, instance_name, component_name, **kwargs):
        """
        Initializes McStas component with specified name and component

        Parameters
        ----------
        instance_name : str
            name of the instance of the component

        component_name : str
            name of the component type e.g. Arm, Guide_gravity, ...

        keyword arguments:
            AT : list of 3 floats
                Sets AT_data describing position of component

            AT_RELATIVE : str
                sets AT_relative, describing position reference

            ROTATED : list of 3 floats
                Sets ROTATED_data, describing rotation of component

            ROTATED_RELATIVE : str
                Sets ROTATED_relative, sets reference for rotation

            RELATIVE : str
                Sets both AT_relative and ROTATED_relative

            WHEN : str
                Sets WHEN string, should contain logical c expression

            EXTEND : str
                Sets initial EXTEND string, should contain c code

            GROUP : str
                Sets name of group the component should belong to

            JUMP : str
                Sets JUMP str

            comment: str
                Sets comment string
        """
        self.name = instance_name
        self.component_name = component_name

        if "AT" in kwargs:
            self.AT_data = kwargs["AT"]
        else:
            self.AT_data = [0, 0, 0]
        # Could check if AT_RELATIVE is a string
        if "AT_RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["AT_RELATIVE"]
        else:
            self.AT_relative = "ABSOLUTE"

        if "ROTATED" in kwargs:
            self.ROTATED_data = kwargs["ROTATED"]
        else:
            self.ROTATED_data = [0, 0, 0]
        # Could check if ROTATED_RELATIVE is a string
        if "ROTATED_RELATIVE" in kwargs:
            self.ROTATED_relative = kwargs["ROTATED_RELATIVE"]
        else:
            self.ROTATED_relative = "ABSOLUTE"

        # Could check if RELATIVE is a string
        if "RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["RELATIVE"]
            self.ROTATED_relative = "RELATIVE " + kwargs["RELATIVE"]

        if "WHEN" in kwargs:
            self.WHEN = "WHEN (" + kwargs["WHEN"] + ")\n"
        else:
            self.WHEN = ""

        if "EXTEND" in kwargs:
            self.EXTEND = kwargs["EXTEND"] + "\n"
        else:
            self.EXTEND = ""

        if "GROUP" in kwargs:
            self.GROUP = kwargs["GRPUP"]
        else:
            self.GROUP = ""

        if "JUMP" in kwargs:
            self.JUMP = kwargs["JUMP"]
        else:
            self.JUMP = ""

        if "comment" in kwargs:
            self.comment = kwargs["comment"]
        else:
            self.comment = ""

        self.component_parameters = {}

        """
        Could store an option for whether this component should be
        printed in instrument file or in a seperate file which would
        then be included.
        """

    def set_AT(self, at_list, **kwargs):
        """Sets AT data, List of 3 floats"""
        self.AT_data = at_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.AT_relative = relative_name
            else:
                self.AT_relative = "RELATIVE " + relative_name

    def set_ROTATED(self, rotated_list, **kwargs):
        """Sets ROTATED data, List of 3 floats"""
        self.ROTATED_data = rotated_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.ROTATED_relative = relative_name
            else:
                self.ROTATED_relative = "RELATIVE " + relative_name

    def set_RELATIVE(self, relative_name):
        """Sets both AT_relative and ROTATED_relative"""
        if relative_name == "ABSOLUTE":
            self.AT_relative = relative_name
            self.ROTATED_relative = relative_name
        else:
            self.AT_relative = "RELATIVE " + relative_name
            self.ROTATED_relative = "RELATIVE " + relative_name

    def set_parameters(self, dict_input):
        """Adds parameters and their values from dictionary input"""
        self.component_parameters.update(dict_input)

    def set_WHEN(self, string):
        """Sets WHEN string, should be a c logical expression"""
        self.WHEN = string

    def set_GROUP(self, string):
        """Sets GROUP name"""
        self.GROUP = string

    def set_JUMP(self, string):
        """Sets JUMP string, should contain all text after JUMP"""
        self.JUMP = string

    def append_EXTEND(self, string):
        """Appends a line of code to EXTEND block of component"""
        self.EXTEND = self.EXTEND + string + "\n"

    def set_comment(self, string):
        """Method that sets a comment to be written to instrument file"""
        self.comment = string

    def write_component(self, fo):
        """Method that writes component to file"""
        parameters_per_line = 2
        # Could use character limit on lines instead
        parameters_written = 0  # internal parameter
        number_of_parameters = len(self.component_parameters)

        # Write comment if present
        if len(self.comment) > 1:
            fo.write("// %s\n" % (str(self.comment)))

        # Write component name and component type
        fo.write("COMPONENT %s = %s(" % (self.name, self.component_name))

        if number_of_parameters == 0:
            fo.write(")\n")  # If there are no parameters, close immediately
        else:
            fo.write("\n")  # If there are parameters, start a new line

        for key, val in self.component_parameters.items():
            if isinstance(val, float):  # CHeck if value is a number
                # Small or large numbers written in scientific format
                fo.write(" %s = %G" % (str(key), val))
            else:
                fo.write(" %s = %s" % (str(key), str(val)))
            parameters_written = parameters_written + 1
            if parameters_written < number_of_parameters:
                fo.write(",")  # Comma between parameters
                if parameters_written % parameters_per_line == 0:
                    fo.write("\n")
            else:
                fo.write(")\n")  # End paranthesis after last parameter

        # Optional WHEN section
        if not self.WHEN == "":
            fo.write("WHEN(%s)\n" % self.WHEN)

        # Write AT and ROTATED section
        fo.write("AT (%s,%s,%s)" % (str(self.AT_data[0]),
                                    str(self.AT_data[1]),
                                    str(self.AT_data[2])))
        fo.write(" %s\n" % self.AT_relative)
        fo.write("ROTATED (%s,%s,%s)" % (str(self.ROTATED_data[0]),
                                         str(self.ROTATED_data[1]),
                                         str(self.ROTATED_data[2])))
        fo.write(" %s\n" % self.ROTATED_relative)

        if not self.GROUP == "":
            fo.write("GROUP %s\n" % self.GROUP)

        # Optional EXTEND section
        if not self.EXTEND == "":
            fo.write("EXTEND %{\n")
            fo.write("%s" % self.EXTEND)
            fo.write("%}\n")

        if not self.JUMP == "":
            fo.write("JUMP %s\n" % self.JUMP)

        # Leave a new line between components for readability
        fo.write("\n")

    def print_long(self):
        """Prints contained information to Python terminal"""
        print("// " + self.comment)
        print("COMPONENT", str(self.name),
              "=", str(self.component_name))
        for key, val in self.component_parameters.items():
            print(" ", key, "=", val)
        if not self.WHEN == "":
            print("WHEN (" + self.WHEN + ")")
        print("AT", self.AT_data, self.AT_relative)
        print("ROTATED", self.ROTATED_data, self.ROTATED_relative)
        if not self.GROUP == "":
            print("GROUP " + self.GROUP)
        if not self.EXTEND == "":
            print("%{")
            print(self.EXTEND + "%}")
        if not self.JUMP == "":
            print("JUMP " + self.JUMP)

    def print_short(self, **kwargs):
        """Prints short description of component to list print"""
        if "longest_name" in kwargs:
            print("test")
            number_of_spaces = 3+kwargs["longest_name"]-len(self.name)
            print(str(self.name) + " "*number_of_spaces, end='')
            print(str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, self.ROTATED_relative)
        else:
            print(str(self.name), "=", str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, self.ROTATED_relative)


class McStas_instr:
    """
    Main class for writing a McStas instrument using McStasScript

    Initialization of McStas_instr sets the name of the instrument file
    and its methods are used to add all aspects of the instrument file.
    The class also holds methods for writing the finished instrument
    file to disk and to run the simulation.

    Attributes
    ----------
    name : str
        name of instrument file

    author : str
        name of user of McStasScript, written to the file

    origin : str
        origin of instrument file (affiliation)

    mcrun_path : str
        absolute path of mcrun command, or empty if it is in path

    parameter_list : list of parameter_variable instances
        contains all input parameters to be written to file

    declare_list : list of declare_variable instances
        contains all declare parrameters to be written to file

    initialize_section : str
        string containing entire initialize section to be written

    trace_section : str
        string containing trace section (OBSOLETE)

    finally_section : str
        string containing entire finally section to be written

    component_list : list of component instances
        list of components in the instrument

    component_name_list : list of strings
        list of names of the components in the instrument

    Methods
    -------
    add_parameter(*args,**kwargs)
        Adds input parameter to the define section

    add_declare_var()
        Adds declared variable ot the declare section

    append_initialize(string)
        Appends a string to the initialize section, then adds new line

    append_initialize_no_new_line(string)
        Appends a string to the initialize section

    append_finally(string)
        Appends a string to finally section, then adds new line

    append_finally_no_new_line(string)
        Appends a string to finally section

    append_trace(string)
        Obsolete method, add components instead (used in write_c_files)

    add_component(instance_name,component_name,**kwargs)
        Add a component to the instrument file

    get_component(instance_name)
        Returns component instance with name instance_name

    get_last_component()
        Returns component instance of last component

    set_component_parameter(instance_name,dict)
        Adds parameters as dict to component with instance_name

    set_component_AT(instance_name,AT_data,**kwargs)
        Sets position of component named instance_name

    set_component_ROTATED(instance_name,ROTATED_data,**kwargs)
        Sets rotation of component named instance_name

    set_component_RELATIVE(instane_name,string)
        Sets position and rotation reference for named component

    set_component_WHEN(instance_name,string)
        Sets WHEN condition of named component, is logical c expression

    set_component_GROUP(instance_name,string)
        Sets GROUP name of component named instance_name

    append_component_EXTEND(instance_name,string)
        Appends a line to EXTEND section of named component

    set_component_JUMP(instance_name,string)
        Sets JUMP code for named component

    set_component_comment(instance_name,string)
        Sets comment to be written before named component

    print_component(instance_name)
        Prints an overview of current state of named component

    print_component_short(instance_name)
        Prints short overview of current state of named component

    print_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    run_full_instrument(**kwargs)
        Writes instrument files and runs simulation.
        Returns list of McStasData
    """

    def __init__(self, name, **kwargs):
        """
        Initialization of McStas Instrument

        Parameters
        ----------
        name : str
            Name of project, instrument file will be name + ".instr"

        keyword arguments:
            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            mcrun_path : str
                Absolute path of mcrun or empty if already in path
        """
        self.name = name

        if "author" in kwargs:
            self.author = kwargs["author"]
        else:
            self.author = "Python McStas Instrument Generator"

        if "origin" in kwargs:
            self.origin = kwargs["origin"]
        else:
            self.origin = "ESS DMSC"

        if "mcrun_path" in kwargs:
            self.mcrun_path = kwargs["mcrun_path"]
        else:
            self.mcrun_path = ""

        self.parameter_list = []
        self.declare_list = []
        self.initialize_section = ("// Start of initialize for generated "
                                   + name + "\n")
        self.trace_section = ("// Start of trace section for generated "
                              + name + "\n")
        self.finally_section = ("// Start of finally for generated "
                                + name + "\n")
        # Handle components
        self.component_list = []  # List of components (have to be ordered)
        self.component_name_list = []  # List of component names

    def add_parameter(self, *args, **kwargs):
        """
        Method for adding input parameter to instrument

        Parameters
        ----------

        (optional) parameter type : str
            type of input parameter, double, int, string

        parameter name : str
            name of parameter

        keyword arguments
            value : any
                Default value of parameter

            comment : str
                Comment displayed next to declaration of parameter
        """
        # parameter_variable class documented independently
        self.parameter_list.append(parameter_variable(*args, **kwargs))

    def add_declare_var(self, *args, **kwargs):
        """
        Method for adding declared variable to instrument

        Parameters
        ----------

        parameter type : str
            type of input parameter

        parameter name : str
            name of parameter

        keyword arguments
            array : int
                default 0 for scalar, if specified length of array

            value : any
                Initial value of parameter, can be list of length vector

            comment : str
                Comment displayed next to declaration of parameter

        """
        # declare_variable class documented independently
        self.declare_list.append(declare_variable(*args, **kwargs))

    def append_initialize(self, string):
        """
        Method for appending code to the intialize section

        The intialize section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        on a new line for each call to this method.

        Parameters
        ----------
        string : str
            code to be added to initialize section
        """
        self.initialize_section = self.initialize_section + string + "\n"

    def append_initialize_no_new_line(self, string):
        """
        Method for appending code to the intialize section, no new line

        The intialize section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        to the current line.

        Parameters
        ----------
        string : str
            code to be added to initialize section

        """

        self.initialize_section = self.initialize_section + string

    def append_finally(self, string):
        """
        Method for appending code to the finally section of instrument

        The finally section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        on a new line for each call to this method.

        Parameters
        ----------
        string : str
            code to be added to finally section

        """

        self.finally_section = self.finally_section + string + "\n"

    def append_finally_no_new_line(self, string):
        """
        Method for appending code to the finally section of instrument

        The finally section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        to the current line.

        Parameters
        ----------
        string : str
            code to be added to finally section
        """

        self.finally_section = self.finally_section + string

    """
    # Handle trace string differently when components also exists
    #  A) Coul d have trace string as a component attribute and set
    #     it before / after
    #  B) Could have trace string as a McStas_instr attribute and
    #     still attach placement to components
    #  C) Could have trace string as a different object and place it
    #     in component_list, but have a write function named as the
    #     component write function?
    """

    def append_trace(self, string):
        """
        Appends code to trace section, only used in write_c_files

        The most common way to add code to the trace section is to add
        components using the seperate methods for this.  This method is
        kept as is still used for writing to c files used in legacy
        code.  Each call creates a new line.

        Parameters
        ----------
        string : str
            code to be added to trace
        """

        self.trace_section = self.trace_section + string + "\n"

    def append_trace_no_new_line(self, string):
        """
        Appends code to trace section, only used in write_c_files

        The most common way to add code to the trace section is to add
        components using the seperate methods for this.  This method is
        kept as is still used for writing to c files used in legacy
        code.  No new line is made with this call.

        Parameters
        ----------
        string : str
            code to be added to trace
        """

        self.trace_section = self.trace_section + string

    def add_component(self, *args, **kwargs):
        """
        Method for adding a new component instance to the instrument

        Creates a new component instance in the instrument.  This
        requires a unique instance name of the component to be used for
        future reference and the name of the McStas component to be
        used.  The component is placed at the end of the instrument file
        unless otherwise specified with the after and before keywords.
        The component may be initialized using other keyword arguments,
        but all attributes can be set with approrpiate methods.

        Parameters
        ----------
        First positional argument : str
            Unique name of component instance

        Second positional argument : str
            Name of McStas component to create instance of

        Keyword arguments:
            after : str
                Place this component after component with given name

            before : str
                Place this component before component with given name

            AT : List of 3 floats
                Sets AT_data, position relative to reference

            AT_RELATIVE : str
                Sets reference component for postion

            ROTATED : List of 3 floats
                Sets ROTATED_data, rotation relative to reference

            ROTATED_RELATIVE : str
                Sets reference component for rotation

            RELATIVE : str
                Sets reference component for both position and rotation

            WHEN : str
                Sets when condition which must be a logical c expression

            EXTEND : str
                Initialize the extend section with a line of c code

            GROUP : str
                Name of the group this component should belong to

            JUMP : str
                Set code for McStas JUMP statement

            comment : str
                Comment that will be displayed before the component
        """

        if args[0] in self.component_name_list:
            raise NameError(("Component name \"" + str(args[0])
                             + "\" used twice, McStas does not allow this."
                             + " Rename or remove one instance of this"
                             + " name."))

        # Insert component after component with this name
        if "after" in kwargs:
            if kwargs["after"] not in self.component_name_list:
                raise NameError(("Trying to add a component after a component"
                                 + " named \"" + str(kwargs["after"])
                                 + "\", but a component with that name was"
                                 + " not found."))

            new_index = self.component_name_list.index(kwargs["after"])
            self.component_list.insert(new_index+1,
                                       component(*args, **kwargs))
            self.component_name_list.insert(new_index+1, args[0])

        # Insert component after component with this name
        elif "before" in kwargs:
            if kwargs["before"] not in self.component_name_list:
                raise NameError(("Trying to add a component before a "
                                 + "component named \""
                                 + str(kwargs["before"])
                                 + "\", but a component with that "
                                 + "name was not found."))

            new_index = self.component_name_list.index(kwargs["before"])
            self.component_list.insert(new_index, component(*args, **kwargs))
            self.component_name_list.insert(new_index, args[0])

        # If after or before keywords absent, place component at the end
        else:
            self.component_list.append(component(*args, **kwargs))
            self.component_name_list.append(args[0])

    def get_component(self, name):
        """
        Get the component instance of component with specified name

        This method is used to get direct access to any component
        instance in the instrument.  The component instance can be
        manipulated in much the same way, but it is not necessary to
        specify the name in each call.

        Parameters
        ----------
        name : str
            Unique name of component whos instance should be returned
        """

        if name in self.component_name_list:
            index = self.component_name_list.index(name)
            return self.component_list[index]
        else:
            raise NameError(("No component was found with name \""
                             + str(name) + "\"!"))

    def get_last_component(self):
        """
        Get the component instance of last component in the instrument

        This method is used to get direct access to any component
        instance in the instrument.  The component instance can be
        manipulated in much the same way, but it is not necessary to
        specify the name in each call.
        """

        return self.component_list[-1]

    def set_component_parameter(self, name, input_dict):
        """
        Add parameters and their values as dictionary to component

        This method is the primary way of specifying parameters in a
        component.  Parameters are added to a dictionary specifying
        parameter name and value pairs.

        Parameters
        ----------
        name : str
            Unique name of component to modify

        input_dict : dict
            Set of new parameter name and value pairs to add
        """

        component = self.get_component(name)
        component.set_parameters(input_dict)

    def set_component_AT(self, name, at_list, **kwargs):
        """
        Method for setting position of component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        at_list : List of 3 floats
            Position of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for position
        """

        component = self.get_component(name)
        component.set_AT(at_list, **kwargs)

    def set_component_ROTATED(self, name, rotated_list, **kwargs):
        """
        Method for setting rotiation of component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        rotated_list : List of 3 floats
            Rotation of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for rotation
        """

        component = self.get_component(name)
        component.set_ROTATED(rotated_list, **kwargs)

    def set_component_RELATIVE(self, name, relative):
        """
        Method for setting reference of component position and rotation

        Parameters
        ----------
        name : str
            Unique name of component to modify

        relative : str
            Reference component for position and rotation
        """

        component = self.get_component(name)
        component.set_RELATIVE(relative)

    def set_component_WHEN(self, name, WHEN):
        """
        Method for setting WHEN c expression to named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        WHEN : str
            Sets WHEN c expression for named McStas component
        """
        component = self.get_component(name)
        component.set_WHEN(WHEN)

    def append_component_EXTEND(self, name, EXTEND):
        """
        Method for adding line of c to EXTEND section of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        EXTEND : str
            Line of c code added to EXTEND section of named component
        """

        component = self.get_component(name)
        component.append_EXTEND(EXTEND)

    def set_component_GROUP(self, name, GROUP):
        """
        Method for setting GROUP name of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        GROUP : str
            Sets GROUP name for named McStas component
        """

        component = self.get_component(name)
        component.set_GROUP(GROUP)

    def set_component_JUMP(self, name, JUMP):
        """
        Method for setting JUMP expression of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        JUMP : str
            Sets JUMP expression for named McStas component
        """

        component = self.get_component(name)
        component.set_JUMP(JUMP)

    def set_component_comment(self, name, string):
        """
        Sets a comment displayed before the component in written files

        Parameters
        ----------
        name : str
            Unique name of component to modify

        string : str
            Comment string

        """

        component = self.get_component(name)
        component.set_comment(string)

    def print_component(self, name):
        """
        Method for printing summary of contents in named component

        Parameters
        ----------
        name : str
            Unique name of component to print
        """

        component = self.get_component(name)
        component.print_long()

    def print_component_short(self, name):
        """
        Method for printing summary of contents in named component

        Parameters
        ----------
        name : str
            Unique name of component to print
        """

        component = self.get_component(name)
        component.print_short()

    def print_components(self):
        """
        Method for printing overview of all components in instrument

        Provides overview of component names, what McStas component is
        used for each and their position and rotation in space.
        """

        longest_name = len(max(self.component_name_list, key=len))

        # Investigate how this could have been done in a better way
        # Find longest field for each type of data printed
        component_type_list = []
        at_x_list = []
        at_y_list = []
        at_z_list = []
        at_relative_list = []
        rotated_x_list = []
        rotated_y_list = []
        rotated_z_list = []
        rotated_relative_list = []
        for component in self.component_list:
            component_type_list.append(component.component_name)
            at_x_list.append(str(component.AT_data[0]))
            at_y_list.append(str(component.AT_data[1]))
            at_z_list.append(str(component.AT_data[2]))
            at_relative_list.append(component.AT_relative)
            rotated_x_list.append(str(component.ROTATED_data[0]))
            rotated_y_list.append(str(component.ROTATED_data[1]))
            rotated_z_list.append(str(component.ROTATED_data[2]))
            rotated_relative_list.append(component.ROTATED_relative)

        longest_component_name = len(max(component_type_list, key=len))
        longest_at_x_name = len(max(at_x_list, key=len))
        longest_at_y_name = len(max(at_y_list, key=len))
        longest_at_z_name = len(max(at_z_list, key=len))
        longest_at_relative_name = len(max(at_relative_list, key=len))
        longest_rotated_x_name = len(max(rotated_x_list, key=len))
        longest_rotated_y_name = len(max(rotated_y_list, key=len))
        longest_rotated_z_name = len(max(rotated_z_list, key=len))
        longest_rotated_relative_name = len(max(rotated_relative_list,
                                                key=len))

        # Have longest field for each type, use ljust to align all columns
        for component in self.component_list:
            print(str(component.name).ljust(longest_name+2), end=' ')

            comp_name = component.component_name
            comp_name_print = str(comp_name).ljust(longest_component_name + 2)
            print(comp_name_print, end=' ')

            comp_at_data = str(component.AT_data)
            longest_at_xyz_sum = (longest_at_x_name
                                  + longest_at_y_name
                                  + longest_at_z_name)
            print("AT ",
                  comp_at_data.ljust(longest_at_xyz_sum + 11),
                  end='')

            comp_at_relative = component.AT_relative
            print(comp_at_relative.ljust(longest_at_relative_name + 2),
                  end=' ')

            comp_rotated_data = str(component.ROTATED_data)
            longest_rotated_xyz_sum = (longest_rotated_x_name
                                       + longest_rotated_y_name
                                       + longest_rotated_z_name)
            print("ROTATED ",
                  comp_rotated_data.ljust(longest_rotated_xyz_sum + 11),
                  end='')
            print(component.ROTATED_relative)
            # print("")

    def write_c_files(self):
        """
        Obsolete method for writing instrument parts to c files

        It is possible to use this function to write c files to a folder
        called generated_includes that can then be included in the
        different sections of a McStas instrument. Component objects are
        NOT written to these files, but rather the contents of the
        trace_section that can be set using the append_trace method.
        """
        path = os.getcwd()
        path = path + "/generated_includes"
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except OSError:
                print("Creation of the directory %s failed" % path)

        fo = open("./generated_includes/" + self.name + "_declare.c", "w")
        fo.write("// declare section for %s \n" % self.name)
        fo.close()
        fo = open("./generated_includes/" + self.name + "_declare.c", "a")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.close()

        fo = open("./generated_includes/" + self.name + "_initialize.c", "w")
        fo.write(self.initialize_section)
        fo.close()

        fo = open("./generated_includes/" + self.name + "_trace.c", "w")
        fo.write(self.trace_section)
        fo.close()

        fo = open("./generated_includes/" + self.name
                  + "_component_trace.c", "w")
        for component in self.component_list:
            component.write_component(fo)
        fo.close()

    def write_full_instrument(self):
        """
        Method for writing full instrument file to disk

        This method writes the instrument described by the instrument
        objects to disk with the name specified in the initialization of
        the object.
        """

        # Create file identifier
        fo = open(self.name + ".instr", "w")

        # Write quick doc start
        fo.write("/" + 80*"*" + "\n")
        fo.write("* \n")
        fo.write("* McStas, neutron ray-tracing package\n")
        fo.write("*         Copyright (C) 1997-2008, All rights reserved\n")
        fo.write("*         Risoe National Laboratory, Roskilde, Denmark\n")
        fo.write("*         Institut Laue Langevin, Grenoble, France\n")
        fo.write("* \n")
        fo.write("* This file was written by McStasScript, which is a \n")
        fo.write("* python based McStas instrument generator written by \n")
        fo.write("* Mads Bertelsen in 2019 while employed at the \n")
        fo.write("* European Spallation Source Data Management and \n")
        fo.write("* Software Center\n")
        fo.write("* \n")
        fo.write("* Instrument %s\n" % self.name)
        fo.write("* \n")
        fo.write("* %Identification\n")  # Could allow the user to insert this
        fo.write("* Written by: %s\n" % self.author)
        t_format = "%H:%M:%S on %B %d, %Y"
        fo.write("* Date: %s\n" % datetime.datetime.now().strftime(t_format))
        fo.write("* Origin: %s\n" % self.origin)
        fo.write("* %INSTRUMENT_SITE: Generated_instruments\n")
        fo.write("* \n")
        fo.write("* \n")
        fo.write("* %Parameters\n")
        # Add description of parameters here
        fo.write("* \n")
        fo.write("* %End \n")
        fo.write("*"*80 + "/\n")
        fo.write("\n")
        fo.write("DEFINE INSTRUMENT %s (" % self.name)
        fo.write("\n")
        # Add loop that inserts parameters here
        for variable in self.parameter_list[0:-1]:
            variable.write_parameter(fo, ",")
        if len(self.parameter_list) > 0:
            self.parameter_list[-1].write_parameter(fo, " ")
        fo.write(")\n")
        fo.write("\n")

        # Write declare
        fo.write("DECLARE \n%{\n")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.write("%}\n\n")

        # Write initialize
        fo.write("INITIALIZE \n%{\n")
        fo.write(self.initialize_section)
        # Alternatively hide everything in include
        """
        fo.write("%include "generated_includes/"
                  + self.name + "_initialize.c")
        """
        fo.write("%}\n\n")

        # Write trace
        fo.write("TRACE \n")
        for component in self.component_list:
            component.write_component(fo)

        # Write finally
        fo.write("FINALLY \n%{\n")
        fo.write(self.finally_section)
        # Alternatively hide everything in include
        fo.write("%}\n")

        # End instrument file
        fo.write("\nEND\n")

    def run_full_instrument(self, *args, **kwargs):
        """
        Runs McStas instrument described by this class, returns list of
        McStasData

        This method will write the instrument to disk and then run it
        using the mcrun command of the system. Options are set using
        keyword arguments.  Some options are mandatory, for example
        foldername, which can not already exist, if it does data will
        be read from this folder.  If the mcrun command is not in the
        path of the system, the absolute path can be given with the
        mcrun_path keyword argument.  This path could also already have
        been set at initialization of the instrument object.

        Parameters
        ----------
        Keyword arguments
            foldername : str
                Sets data_folder_name
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            parameters : dict
                Sets parameters
            custom_flags : str
                Sets custom_flags passed to mcrun
            mcrun_path : str
                Path to mcrun command, "" if already in path
        """
        # Write the instrument file
        self.write_full_instrument()

        # Make sure mcrun path is in kwargs
        if "mcrun_path" not in kwargs:
            kwargs["mcrun_path"] = self.mcrun_path

        # Set up the simulation
        simulation = ManagedMcrun(self.name + ".instr", **kwargs)

        # Run the simulation and return data
        return simulation.run_simulation()
