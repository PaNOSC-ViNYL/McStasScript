import os
import numpy as np
import subprocess
import mmap
import warnings

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasDataBinned
from mcstasscript.data.data import McStasDataEvent


class ManagedMcrun:
    """
    A class for performing a mcstas simulation and organizing the data
    into python objects

    ManagedMcrun is usually called by the instrument class of
    McStasScript but can be used independently.  It runs the mcrun
    command using the system command, and if this is not in the path,
    the absolute path can be given in a keyword argument executable_path.

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

    executable_path : string
        Path to the mcrun command (can be empty if already in path)

    Methods
    -------
    run_simulation()
        Runs simulation, returns list of McStasData instances

    """

    def __init__(self, instr_name, **kwargs):
        """
        Performs call to McStas with given options

        Uses subprocess to call mcrun / mxrun to perform simulation of given
        instrument file.

        Parameters
        ----------
        instr_name : str
            Name of instrument file to be simulated

        kwargs : keyword arguments
            output_path : str, required
                Sets data_folder_name
            ncount : int, default 1E6
                Sets ncount
            mpi : int, default None
                Sets thread count, None to disable mpi
            gravity : bool, default False
                Enables gravity if True
            parameters : dict
                Sets parameters
            custom_flags : str, default ""
                Sets custom_flags passed to mcrun
            executable_path : str
                Path to mcrun command, "" if already in path
            increment_folder_name : bool, default True
                If True, automatically appends output_path to make it unique
            force_compile : bool, default True
                If True, forces compile. If False no new instrument is written
            run_folder : str
                Path to folder in which to run McStas

        """

        self.name_of_instrumentfile = instr_name

        self.data_folder_name = ""
        self.ncount = int(1E6)
        self.mpi = None
        self.gravity = False
        self.parameters = {}
        self.custom_flags = ""
        self.executable_path = ""
        self.executable = ""
        self.increment_folder_name = True
        self.compile = True
        self.run_path = "."
        self.seed = None
        # executable_path always in kwargs
        if "executable_path" in kwargs:
            self.executable_path = kwargs["executable_path"]

        if "executable" in kwargs:
            self.executable = kwargs["executable"]

        if "output_path" in kwargs:
            self.data_folder_name = kwargs["output_path"]
        else:
            raise NameError(
                "ManagedMcrun needs output_path to load data, add "
                + "with keyword argument.")

        if "ncount" in kwargs:
            self.ncount = int(kwargs["ncount"])

            if self.ncount < 1:
                raise ValueError("ncount should be a positive integer, was "
                                 + str(self.ncount))

        if "mpi" in kwargs:
            self.mpi = kwargs["mpi"]
            try:
                self.mpi = int(self.mpi)
            except (TypeError, ValueError) as e:
                if self.mpi is not None:
                    raise RuntimeError("MPI should be an integer, was "
                                       + str(self.mpi))

            if self.mpi is not None:
                if self.mpi < 1:
                    raise ValueError("MPI should be an integer larger than"
                                     + " 0, was " + str(self.mpi))

        if "gravity" in kwargs:
            self.gravity = kwargs["gravity"]

        if "seed" in kwargs:
            self.seed = kwargs["seed"]

        if "parameters" in kwargs:
            self.parameters = kwargs["parameters"]

            if not isinstance(self.parameters, dict):
                raise RuntimeError("Parameters should be given as dict.")

        if "custom_flags" in kwargs:
            self.custom_flags = kwargs["custom_flags"]

            if not isinstance(self.custom_flags, str):
                raise RuntimeError("ManagedMcrun detected given customf_flags"
                                   + " was not a string.")

        if "increment_folder_name" in kwargs:
            self.increment_folder_name = kwargs["increment_folder_name"]

        if "force_compile" in kwargs:
            self.compile = kwargs["force_compile"]

        if "run_path" in kwargs:
            self.run_path = kwargs["run_path"]

        # get relevant paths and check their validity
        current_directory = os.getcwd()

        if not os.path.isabs(self.data_folder_name):
            self.data_folder_name = os.path.join(current_directory,
                                                 self.data_folder_name)
        else:
            split_data_path = os.path.split(self.data_folder_name)
            if not os.path.isdir(split_data_path[0]):
                raise RuntimeError("Parent folder for datafolder invalid: "
                                   + str(split_data_path[0]))

        if not os.path.isabs(self.run_path):
            self.run_path = os.path.join(current_directory, self.run_path)
        else:
            split_run_path = os.path.split(self.run_path)
            if not os.path.isdir(split_run_path[0]):
                raise RuntimeError("Parent folder for run_path invalid: "
                                   + str(split_run_path[0]))

        if not os.path.isdir(self.run_path):
            raise RuntimeError("ManagedMcrun found run_path to "
                               + "be invalid: " + str(self.run_path))

        if not os.path.isdir(self.executable_path):
            raise RuntimeError("ManagedMcrun found executable_path to "
                               + "be invalid: " + str(self.executable_path))

    def run_simulation(self, **kwargs):
        """
        Runs McStas simulation described by initializing the object
        """

        # construct command to run
        option_string = ""
        if self.compile:
            option_string += "-c "

        if self.gravity:
            option_string += "-g "

        if self.mpi is not None:
            mpi_string = "--mpi=" + str(self.mpi) + " "  # Set mpi
        else:
            mpi_string = ""

        if self.seed is not None:
            seed_string = "--seed=" + str(self.seed) + " " # Set seed
        else:
            seed_string = ""

        option_string = (option_string
                         + "-n " + str(self.ncount) + " " # Set ncount
                         + mpi_string
                         + seed_string)

        if os.path.exists(self.data_folder_name):
            if self.increment_folder_name:
                counter = 0
                new_name = self.data_folder_name + "_" + str(counter)
                while os.path.isdir(new_name):
                    counter = counter + 1
                    new_name = self.data_folder_name + "_" + str(counter)

                self.data_folder_name = new_name
            else:
                raise NameError("output_path already exists and "
                                + "increment_folder_name was set to False.")

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

        mcrun_full_path = os.path.join(self.executable_path, self.executable)
        if len(self.executable_path) > 1:
            if not (self.executable_path[-1] == "\\"
                    or self.executable_path[-1] == "/"):
                mcrun_full_path = os.path.join(self.executable_path,
                                               self.executable)
        mcrun_full_path = '"' + mcrun_full_path + '"' # Path in quotes to allow spaces

        # Run the mcrun command on the system
        full_command = (mcrun_full_path + " "
                        + option_string + " "
                        + self.custom_flags + " "
                        + self.name_of_instrumentfile
                        + parameter_string)

        process = subprocess.run(full_command, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True,
                                 cwd=self.run_path)

        if "suppress_output" in kwargs:
            if kwargs["suppress_output"] is False:
                print(process.stderr)
                print(process.stdout)
        else:
            print(process.stderr)
            print(process.stdout)

        if not os.path.isdir(self.data_folder_name):
            warnings.warn("Simulation did not create data folder, most likely failed.")

    def load_results(self, *args):
        """
        Method for loading data from a mcstas simulation

        Loads data on all monitors in a McStas data folder, and returns these
        as a list of McStasData objects.

        Parameters
        ----------

        optional first argument : str
            path to folder from which data should be loaded

        """

        if len(args) == 0:
            data_folder_name = self.data_folder_name
        elif len(args) == 1:
            data_folder_name = args[0]
        else:
            raise RuntimeError("load_results can be called "
                               + "with 0 or 1 arguments")

        if os.path.isdir(data_folder_name):
            return load_results(data_folder_name)
        else:
            warnings.warn("No data available to load.")
            return None


def load_results(data_folder_name):
    """
    Function for loading data from a mcstas simulation

    Loads data on all monitors in a McStas data folder, and returns these
    as a list of McStasData objects.

    Parameters
    ----------

    data_folder_name : str
        path to folder from which data should be loaded

    """

    metadata_list = load_metadata(data_folder_name)

    results = []
    for metadata in metadata_list:
        result = load_monitor(metadata, data_folder_name)
        result.set_data_location(data_folder_name)
        results.append(result)

    return results


def load_metadata(data_folder_name):
    """
    Function that loads metadata from a mcstas simulation

    Returns list of metadata objects corresponding to each monitor, all
    information is taken from mccode.sim file.

    Parameters
    ----------

    first argument : str
        path to folder from which metadata should be loaded
    """

    if not os.path.isdir(data_folder_name):
        raise NameError("Given data directory does not exist.")

    # Find all data files in generated folder
    files_in_folder = os.listdir(data_folder_name)

    # Raise an error if mccode.sim is not available
    if "mccode.sim" not in files_in_folder:
        raise NameError("No mccode.sim in data folder.")
        
    instrument_parameters = {}

    # Open mccode to read metadata for all datasets written to disk
    with open(os.path.join(data_folder_name, "mccode.sim"), "r") as f:

        # Loop that reads mccode.sim sections
        metadata_list = []
        current_object = None
        in_data = False
        in_sim = False
        for lines in f:
            # Could read other details about run

            if lines == "end data\n":
                # No more data for this metadata object
                # Add parameter information
                current_object.add_info("Parameters", instrument_parameters)
                # Extract the information
                current_object.extract_info()
                # Add to metadata list
                if current_object.filename != "":
                    metadata_list.append(current_object)
                # Stop reading data
                in_data = False
                
            if in_sim:
                if "Param" in lines:
                    parm_lst = lines.split(':')[1].split('=')
                    try:
                        value = float(parm_lst[1].strip())
                    except ValueError:
                        value = parm_lst[1].strip()

                    instrument_parameters[parm_lst[0].strip()] = value
                    
            if in_data:
                # This line contains info to be added to metadata
                colon_index = lines.index(":")
                key = lines[2:colon_index]
                value = lines[colon_index+2:].strip()
                current_object.add_info(key, value)

            if lines == "begin data\n":
                # Found data section, create new metadata object
                current_object = McStasMetaData()
                # Start recording data to metadata object
                in_data = True

            if 'begin simulation:' in lines:
                in_sim = True
            if 'end simulation:' in lines:
                in_sim = False

        # Close mccode.sim
        f.close()

        # Create a list for McStasData instances to return
        results = []

        # Load datasets described in metadata list individually
        for metadata in metadata_list:
            # Load data with numpy
            data = np.loadtxt(data_folder_name
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

    return metadata_list


def load_monitor(metadata, data_folder_name):
    """
    Function that loads data given metadata and name of data folder

    Loads data for single monitor and returns a McStasData object

    Parameters
    ----------

    metadata : McStasMetaData object
        McStasMetaData object corresponding to the monitor to be loaded

    data_folder_name : str
        path to folder from which metadata should be loaded
    """
    # Load data with numpy
    filename = os.path.join(data_folder_name, metadata.filename.rstrip())
    data = np.loadtxt(filename)

    # Split data into intensity, error and ncount
    if type(metadata.dimension) == int:
        xaxis = data.T[0, :]
        Intensity = data.T[1, :]
        Error = data.T[2, :]
        Ncount = data.T[3, :]

        # The data is saved as a McStasDataBinned object
        return McStasDataBinned(metadata, Intensity, Error, Ncount, xaxis=xaxis)

    elif len(metadata.dimension) == 2:
        # Need to check if it is binned data or event data

        with open(filename, 'rb', 0) as file, \
                mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
            if s.find(b'# Errors') != -1:
                data_type = "Binned"
            else:
                data_type = "Events"

        if data_type == "Events":
            Events = data

            return McStasDataEvent(metadata, Events)

        elif data_type == "Binned":
            # Binned 2D data
            xaxis = []  # Assume evenly binned in 2d
            data_lines = metadata.dimension[1]
            Intensity = data[0:data_lines, :]
            Error = data[data_lines:2 * data_lines, :]
            Ncount = data[2 * data_lines:3 * data_lines, :]

            # The data is saved as a McStasDataBinned object
            return McStasDataBinned(metadata, Intensity, Error, Ncount, xaxis=xaxis)
    else:
        raise NameError(
            "Dimension not read correctly in data set "
            + "connected to monitor named "
            + metadata.component_name)

