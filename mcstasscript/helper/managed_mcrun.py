import os
import numpy as np
import subprocess
import mmap
import warnings
import h5py
import re

from mcstasscript.helper.formatting import bcolors
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
            openacc : bool, default False
                If True, adds the --openacc flag to mcrun call
            NeXus : bool, default False
                If True, adds the --format=NeXus to mcrun call

        """

        self.name_of_instrumentfile = instr_name

        self.data_folder_name = ""
        self.ncount = int(1E6)
        self.mpi = None
        self.gravity = False
        self.openacc = False
        self.NeXus = False
        self.parameters = {}
        self.custom_flags = ""
        self.executable_path = ""
        self.executable = ""
        self.increment_folder_name = True
        self.compile = True
        self.run_path = "."
        self.seed = None
        self.suppress_output = False

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

        if "openacc" in kwargs:
            self.openacc = kwargs["openacc"]

        if "NeXus" in kwargs:
            self.NeXus = kwargs["NeXus"]

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

        if "suppress_output" in kwargs:
            self.suppress_output = bool(kwargs["suppress_output"])


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

    def run_simulation(self):
        """
        Runs McStas simulation described by initializing the object
        """

        # construct command to run
        option_string = ""
        if self.compile:
            option_string += "-c "

        if self.gravity:
            option_string += "-g "

        if self.NeXus:
            option_string += "--format=NeXus "

        if self.openacc:
            option_string += "--openacc "

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
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 cwd=self.run_path)

        if self.suppress_output is False:
            print_sim_output(process.stdout)

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
    if "mccode.sim" in files_in_folder:
        return load_metadata_text(data_folder_name)
    elif "mccode.h5" in files_in_folder:
        return load_metadata_nexus(data_folder_name)
    else:
        raise NameError("No mccode.sim or mccode.h5 in data folder.")


def load_metadata_text(data_folder_name):
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
                value = lines[colon_index + 2:].strip()
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

        """
        # Create a list for McStasData instances to return
        results = []


        # Load datasets described in metadata list individually
        for metadata in metadata_list:

            # Load data with numpy
            data = np.loadtxt(data_folder_name
                              + "/"
                              + metadata.filename.rstrip())

            # Split data into intensity, error and ncount
            if type(metadata.dimension) == int and metadata.dimension == 0:
                Intensity = data.T

            if type(metadata.dimension) == int and metadata.dimension != 0:

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
        """

    return metadata_list


def load_metadata_nexus(data_folder_name, filename="mccode.h5"):
    instrument_parameters = {}

    # Open mccode to read metadata for all datasets written to disk
    with h5py.File(os.path.join(data_folder_name, filename), "r") as f:

        if "entry1" not in list(f.keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "data" not in list(f["entry1"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "simulation" not in list(f["entry1"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "Param" not in list(f["entry1"]["simulation"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        # Common information

        # Instrument parameters
        instrument_parameters = {}
        loaded_par_dict = f["entry1"]["simulation"]["Param"].attrs
        for par_name in loaded_par_dict:
            if par_name == "NX_class":
                continue

            try:
                value = float(loaded_par_dict[par_name])
            except:
                value = str(loaded_par_dict[par_name])

            instrument_parameters[par_name] = value

        metadata_list = []

        # For each entry in data, make a metadata object
        for key in f["entry1"]["data"].keys():

            # Make the metadata object and add instrument parameters
            metadata = McStasMetaData()
            metadata.add_info("Parameters", instrument_parameters)

            # Add NeXus field name
            metadata.add_info("NeXus_field", key)

            # Add all the read info from attribute section
            info = dict(f["entry1"]["data"][key].attrs)
            info = decode_dict(info)
            for name, value in info.items():
                if isinstance(value, bytes):
                    value = value.decode('utf-8')

                metadata.add_info(name, value)

            metadata_list.append(metadata)

            # Now all info is added, extract info loads it into nice attributes
            metadata.extract_info()

        return metadata_list


def decode_dict(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, bytes):
            dictionary[key] = value.decode('utf-8')

    return dictionary


def load_monitor(metadata, data_folder_name):
    """
    Switches to appropriate loader function
    """

    if "NeXus_field" in metadata.info:
        return load_monitor_nexus(metadata, data_folder_name)
    else:
        return load_monitor_text(metadata, data_folder_name)


def load_monitor_nexus(metadata, data_folder_name, filename="mccode.h5"):
    """
    Function that loads data given metadata and name of data folder
    This version is for a nexus file

    Loads data for single monitor and returns a McStasData object

    Parameters
    ----------

    metadata : McStasMetaData object
        McStasMetaData object corresponding to the monitor to be loaded

    data_folder_name : str
        path to folder from which metadata should be loaded

    filename : str
        Name of NeXus file
    """

    # Open mccode to read metadata for all datasets written to disk
    with h5py.File(os.path.join(data_folder_name, filename), "r") as f:

        if "entry1" not in list(f.keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "data" not in list(f["entry1"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "simulation" not in list(f["entry1"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        if "Param" not in list(f["entry1"]["simulation"].keys()):
            raise ValueError("h5 file not formatted as expected.")

        NeXus_field = metadata.info["NeXus_field"]

        available_fields = f["entry1"]["data"][NeXus_field].keys()
        if not metadata.dimension == 0 and "events" not in available_fields:
            if "data" not in available_fields:
                raise ValueError("NeXus reading: data not found! \n"
                                 + "Monitor metadata:\n" + str(metadata))

            if "errors" not in available_fields:
                raise ValueError("NeXus reading: errors not found! \n"
                                 + "Monitor metadata:\n" + str(metadata))

            if "ncount" not in available_fields:
                raise ValueError("NeXus reading: ncount not found! \n"
                                 + "Monitor metadata:\n" + str(metadata))

        # Need to check if it is binned data or event data
        if "events" in available_fields:
            Events = np.array(f["entry1"]["data"][NeXus_field]["events"])
            return McStasDataEvent(metadata, Events)

        # Split data into intensity, error and ncount
        if type(metadata.dimension) == int and metadata.dimension == 0:

            if "data" in f["entry1"]["data"][NeXus_field].keys():
                raise ValueError("Found array data in 0D dataset?")

            values = None
            if "values" in f["entry1"]["data"][NeXus_field].keys():
                values = np.array(f["entry1"]["data"][NeXus_field]["values"])

            if metadata.total_I is None:
                if values is not None:
                    Intensity = np.array(values[0])
                else:
                    raise ValueError("No info on this monitor can be found "
                                     + "in reading of NeXus file "
                                     + str(metadata))
            else:
                Intensity = np.array(metadata.total_I)

            if metadata.total_E is None:
                if values is not None:
                    Error = np.array(values[2])
                else:
                    Error = np.zeros(1)
            else:
                Error = np.array(metadata.total_E)

            if metadata.total_N is None:
                if values is not None:
                    Ncount = np.array(values[3])
                else:
                    Ncount = np.zeros(1)
            else:
                Ncount = np.array(metadata.total_N)

            return McStasDataBinned(metadata, Intensity, Error, Ncount)

        elif type(metadata.dimension) == int and metadata.dimension != 0:

            original_xlabel = metadata.info["xlabel"]

            # All special characters are substituted with _ in McStas NeXus file
            x_field = re.sub(r'[^a-zA-Z]', "_", original_xlabel)

            if x_field not in f["entry1"]["data"][NeXus_field].keys():
                error_text = ("Didn't find xaxis in NeXus file. \n"
                              + "Expected this field for x axis: "
                              + str(x_field) + "\n"
                              + "Existing fields: "
                              + str(f["entry1"]["data"][NeXus_field].keys()))

                raise ValueError(error_text)

            xaxis = np.array(f["entry1"]["data"][NeXus_field][x_field])
            Intensity = np.array(f["entry1"]["data"][NeXus_field]["data"])
            Error = np.array(f["entry1"]["data"][NeXus_field]["errors"])
            Ncount = np.array(f["entry1"]["data"][NeXus_field]["ncount"])

            # The data is saved as a McStasDataBinned object
            return McStasDataBinned(metadata, Intensity, Error, Ncount, xaxis=xaxis)

        elif len(metadata.dimension) == 2:
            xaxis = []  # Assume evenly binned in 2d
            Intensity = np.array(f["entry1"]["data"][NeXus_field]["data"]).T
            Error = np.array(f["entry1"]["data"][NeXus_field]["errors"]).T
            Ncount = np.array(f["entry1"]["data"][NeXus_field]["ncount"]).T

            # The data is saved as a McStasDataBinned object
            return McStasDataBinned(metadata, Intensity, Error, Ncount, xaxis=xaxis)
        else:
            raise NameError(
                "Dimension not read correctly in data set "
                + "connected to monitor named "
                + metadata.component_name)


def load_monitor_text(metadata, data_folder_name):
    """
    Function that loads data given metadata and name of data folder
    This version is for a text file

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
    if type(metadata.dimension) == int and metadata.dimension == 0:
        Intensity = data.T
        if metadata.total_E is None:
            Error = np.zeros(1)
        else:
            Error = np.array(metadata.total_E)

        if metadata.total_N is None:
            Ncount = np.zeros(1)
        else:
            Ncount = np.array(metadata.total_N)

        return McStasDataBinned(metadata, Intensity, Error, Ncount)

    elif type(metadata.dimension) == int and metadata.dimension != 0:
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


def print_sim_output(sim_output):
    print(highlight(sim_output, "error", return_section=True, after_lines=10, highlight_type="FAIL"))
    print(highlight(sim_output, "error", return_section=False, highlight_type="FAIL"))


def highlight(string, search_term, return_section=False, highlight_type=None, after_lines=5):
    """
    Highlights search term in string and returns it, if return_section only sections with term is returned
    """

    search_term = search_term.lower()

    if not isinstance(string, str):
        return None

    # Early exit if search term is not in string
    output = string.lower().find(search_term)
    if output == -1:
        if return_section:
            return ""
        else:
            return string

    if return_section:
        instances = list(findall(string, search_term))
        n_instances = len(instances)
        print(f"---- Found {n_instances} places in McStas output with "
              f"keyword '{search_term}'. \n")

    if highlight_type is None:
        highlight_start = ""
        highlight_end = ""
    else:
        if not hasattr(bcolors, highlight_type):
            raise RuntimeError(f"Used highlight_type {highlight_type} "
                               f"in highlight not found in bcolors.")
        else:
            highlight_start = getattr(bcolors, highlight_type)
            highlight_end = bcolors.ENDC

    return_string = ""

    lines = string.split("\n")
    total_lines = len(lines)
    for index, line in enumerate(lines):
        output = line.lower().find(search_term)
        if output == -1:
            if not return_section:
                return_string += line + "\n"
        else:
            replaced_string = line[:output]
            replaced_string += highlight_start
            replaced_string += line[output:output + len(search_term)]
            replaced_string += highlight_end
            replaced_string += line[output + len(search_term):]
            replaced_string += "\n"

            return_string += replaced_string
            if return_section:
                extra_lines = min(total_lines - index, after_lines)
                for line_index in range(1, extra_lines):
                    line_to_include = lines[index + line_index]
                    if line_to_include.lower().find(search_term) != -1:
                        break
                    return_string += line_to_include + "\n"
                return_string += "-"*70 + "\n"

    return return_string


def findall(s, p):
    """
    Yields all the positions of the pattern p in the string s.
    """
    i = s.lower().find(p)
    while i != -1:
        yield i
        i = s.lower().find(p, i+1)