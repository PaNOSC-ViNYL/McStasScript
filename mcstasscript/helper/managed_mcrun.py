import os
import numpy as np
import subprocess

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasData


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
        Parameters
        ----------
        instr_name : str
            Name of instrument file to be simulated

        kwargs : keyword arguments
            foldername : str, required
                Sets data_folder_name
            ncount : int, default 1E6
                Sets ncount
            mpi : int, default None
                Sets thread count, None to disable mpi
            parameters : dict
                Sets parameters
            custom_flags : str, default ""
                Sets custom_flags passed to mcrun
            executable_path : str
                Path to mcrun command, "" if already in path
            increment_folder_name : bool, default False
                If True, automatically appends foldername to make it unique
            force_compile : bool, default True
                If True, forces compile. If False no new instrument is written
            run_folder : str
                Path to folder in which to run McStas

        """

        self.name_of_instrumentfile = instr_name

        self.data_folder_name = ""
        self.ncount = int(1E6)
        self.mpi = None
        self.parameters = {}
        self.custom_flags = ""
        self.executable_path = ""
        self.executable = ""
        self.increment_folder_name = False
        self.compile = True
        self.run_path = "."
        # executable_path always in kwargs
        if "executable_path" in kwargs:
            self.executable_path = kwargs["executable_path"]

        if "executable" in kwargs:
            self.executable = kwargs["executable"]

        if "foldername" in kwargs:
            self.data_folder_name = kwargs["foldername"]
        else:
            raise NameError(
                "ManagedMcrun needs foldername to load data, add "
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
            except ValueError:
                if self.mpi is not None:
                    raise RuntimeError("MPI should be an integer, was "
                                       + str(self.mpi))

            if self.mpi is not None:
                if self.mpi < 1:
                    raise ValueError("MPI should be an integer larger than"
                                     + " 0, was " + str(self.mpi))

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
            option_string = "-c "

        if self.mpi is not None:
            mpi_string = " --mpi=" + str(self.mpi) + " " # Set mpi
        else:
            mpi_string = " "

        option_string = (option_string
                         + "-n " + str(self.ncount)  # Set ncount
                         + mpi_string)

        if self.increment_folder_name and os.path.isdir(self.data_folder_name):
            counter = 0
            new_name = self.data_folder_name + "_" + str(counter)
            while os.path.isdir(new_name):
                counter = counter + 1
                new_name = self.data_folder_name + "_" + str(counter)

            self.data_folder_name = new_name

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

        # Run the mcrun command on the system
        full_command = (mcrun_full_path + " "
                  + option_string + " "
                  + self.custom_flags + " "
                  + self.name_of_instrumentfile
                  + parameter_string)

        try:
            process = subprocess.run(full_command, shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True,
                                     cwd=self.run_path)
        except:
            raise RuntimeError("Could not run McStas command.")

        if "suppress_output" in kwargs:
            if kwargs["suppress_output"] is False:
                print(process.stderr)
                print(process.stdout)
        else:
            print(process.stderr)
            print(process.stdout)

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
            raise RuntimeError("load_results can be called with 0 or 1 arguments")

        return load_results(data_folder_name)


def load_results(data_folder_name):
    """
    Function for loading data from a mcstas simulation

    Loads data on all monitors in a McStas data folder, and returns these
    as a list of McStasData objects.

    Parameters
    ----------

    first argument : str
        path to folder from which data should be loaded

    """

    if not os.path.isdir(data_folder_name):
        raise NameError("Given data directory does not exist.")

    # Find all data files in generated folder
    files_in_folder = os.listdir(data_folder_name)

    # Raise an error if mccode.sim is not available
    if "mccode.sim" not in files_in_folder:
        raise NameError("No mccode.sim in data folder.")

    # Open mccode to read metadata for all datasets written to disk
    with open(os.path.join(data_folder_name, "mccode.sim"), "r") as f:

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
                if current_object.filename != "":
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

    # Create a list for McStasData instances to return
    results = []

    # Load datasets described in metadata list individually
    for metadata in metadata_list:
        # Load data with numpy
        data = np.loadtxt(os.path.join(data_folder_name,
                          metadata.filename.rstrip()))

        # Split data into intensity, error and ncount
        if type(metadata.dimension) == int:
            xaxis = data.T[0, :]
            Intensity = data.T[1, :]
            Error = data.T[2, :]
            Ncount = data.T[3, :]

        elif len(metadata.dimension) == 2:
            xaxis = []  # Assume evenly binned in 2d
            data_lines = metadata.dimension[1]

            Intensity = data[0:data_lines, :]
            Error = data[data_lines:2*data_lines, :]
            Ncount = data[2*data_lines:3*data_lines, :]
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

    # Return list of McStasData objects
    return results
